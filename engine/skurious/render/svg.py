"""A very small SVG builder. Units are millimetres; output is deterministic.

Three rules make the golden-image tests possible, and they are the only reason
this exists instead of a library:

* every float is rounded to 3 decimal places on the way in, so a rounding wobble
  in the last bit of a double never changes a byte;
* elements come out in the order they went in, and attributes in sorted order;
* nothing carries a timestamp, a random id, or a locale-dependent format.

A print is 457 × 610 mm. Authoring in mm and letting the rasteriser pick the DPI
is what lets the same layout be an 8×10 and an 18×24 without a scale factor
anywhere in the layout code.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field

PRECISION = 3


def num(value: float) -> str:
    """3 dp, no trailing zeros, no negative zero. The determinism lives here."""
    rounded = round(float(value), PRECISION)
    if rounded == 0:
        rounded = 0.0
    text = f"{rounded:.{PRECISION}f}".rstrip("0").rstrip(".")
    return text or "0"


def _attrs(pairs: dict[str, object]) -> str:
    out = []
    for key in sorted(pairs):
        value = pairs[key]
        if value is None:
            continue
        if isinstance(value, float):
            value = num(value)
        out.append(f'{key.replace("_", "-")}="{html.escape(str(value), quote=True)}"')
    return " ".join(out)


@dataclass
class Element:
    tag: str
    attrs: dict[str, object] = field(default_factory=dict)
    children: list["Element"] = field(default_factory=list)
    text: str | None = None

    def render(self, indent: int = 0) -> list[str]:
        pad = "  " * indent
        a = _attrs(self.attrs)
        head = f"<{self.tag}{' ' + a if a else ''}"
        if self.text is not None:
            return [f"{pad}{head}>{html.escape(self.text)}</{self.tag}>"]
        if not self.children:
            return [f"{pad}{head}/>"]
        lines = [f"{pad}{head}>"]
        for child in self.children:
            lines += child.render(indent + 1)
        lines.append(f"{pad}</{self.tag}>")
        return lines


@dataclass
class Comment:
    body: str

    def render(self, indent: int = 0) -> list[str]:
        safe = self.body.replace("--", "-")
        return [f"{'  ' * indent}<!-- {safe} -->"]


class Group:
    """Anything you can add elements to. `SVG` and `<g>` are both one of these."""

    def __init__(self, element: Element) -> None:
        self._element = element

    def add(self, tag: str, **attrs) -> Element:
        el = Element(tag, attrs)
        self._element.children.append(el)
        return el

    def group(self, **attrs) -> "Group":
        return Group(self.add("g", **attrs))

    # -- shapes -----------------------------------------------------------
    def rect(self, x, y, w, h, **attrs) -> Element:
        return self.add("rect", x=x, y=y, width=w, height=h, **attrs)

    def circle(self, cx, cy, r, **attrs) -> Element:
        return self.add("circle", cx=cx, cy=cy, r=r, **attrs)

    def line(self, x1, y1, x2, y2, **attrs) -> Element:
        return self.add("line", x1=x1, y1=y1, x2=x2, y2=y2, **attrs)

    def path(self, d: str, **attrs) -> Element:
        return self.add("path", d=d, **attrs)

    def polyline(self, points: list[tuple[float, float]], **attrs) -> Element:
        pts = " ".join(f"{num(x)},{num(y)}" for x, y in points)
        return self.add("polyline", points=pts, **attrs)

    def text(self, x, y, content: str, **attrs) -> Element:
        el = Element("text", {"x": x, "y": y, **attrs}, text=content)
        self._element.children.append(el)
        return el

    def text_path(self, path_id: str, content: str, offset: str = "50%",
                  **attrs) -> Element:
        """Text riding a path — how the nakshatra ring gets its curved labels."""
        outer = Element("text", dict(attrs))
        inner = Element("textPath", {"href": f"#{path_id}",
                                     "startOffset": offset,
                                     "text-anchor": "middle"}, text=content)
        outer.children.append(inner)
        self._element.children.append(outer)
        return outer

    def defs(self) -> "Group":
        return Group(self.add("defs"))

    def comment(self, text: str) -> None:
        """A layout nobody can read in the file is a layout nobody can correct."""
        self._element.children.append(Comment(text))


class SVG(Group):
    def __init__(self, width_mm: float, height_mm: float,
                 bleed_mm: float = 0.0) -> None:
        self.width = width_mm + 2 * bleed_mm
        self.height = height_mm + 2 * bleed_mm
        self.bleed = bleed_mm
        root = Element("svg", {
            "xmlns": "http://www.w3.org/2000/svg",
            "xmlns:xlink": "http://www.w3.org/1999/xlink",
            "width": f"{num(self.width)}mm",
            "height": f"{num(self.height)}mm",
            "viewBox": f"0 0 {num(self.width)} {num(self.height)}",
        })
        super().__init__(root)
        # Order is fixed here rather than left to call order: <defs> first, then
        # everything drawn, so a layout cannot accidentally paint its ground over
        # its own contents by asking for the two groups the wrong way round.
        self._defs = Group(self.add("defs"))
        self._content = self.group(
            transform=f"translate({num(bleed_mm)},{num(bleed_mm)})")

    @property
    def content(self) -> Group:
        """A group shifted so layout coordinates can ignore the bleed entirely."""
        return self._content

    def defs(self) -> Group:  # type: ignore[override]
        return self._defs

    def to_string(self) -> str:
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines += self._element.render()
        return "\n".join(lines) + "\n"


def arc_path(cx: float, cy: float, r: float, start_deg: float,
             end_deg: float, sweep: int = 1) -> str:
    """An arc as an SVG path, angles measured clockwise from twelve o'clock."""
    import math

    def point(angle: float) -> tuple[float, float]:
        a = math.radians(angle - 90.0)
        return cx + r * math.cos(a), cy + r * math.sin(a)

    x1, y1 = point(start_deg)
    x2, y2 = point(end_deg)
    large = 1 if abs(end_deg - start_deg) % 360.0 > 180.0 else 0
    return (f"M {num(x1)} {num(y1)} A {num(r)} {num(r)} 0 {large} {sweep} "
            f"{num(x2)} {num(y2)}")


def ring_sector(cx: float, cy: float, r_inner: float, r_outer: float,
                start_deg: float, end_deg: float) -> str:
    """One wedge of an annulus — a nakshatra sector on the outer ring."""
    import math

    def point(r: float, angle: float) -> tuple[float, float]:
        a = math.radians(angle - 90.0)
        return cx + r * math.cos(a), cy + r * math.sin(a)

    large = 1 if abs(end_deg - start_deg) % 360.0 > 180.0 else 0
    x1, y1 = point(r_outer, start_deg)
    x2, y2 = point(r_outer, end_deg)
    x3, y3 = point(r_inner, end_deg)
    x4, y4 = point(r_inner, start_deg)
    return (f"M {num(x1)} {num(y1)} "
            f"A {num(r_outer)} {num(r_outer)} 0 {large} 1 {num(x2)} {num(y2)} "
            f"L {num(x3)} {num(y3)} "
            f"A {num(r_inner)} {num(r_inner)} 0 {large} 0 {num(x4)} {num(y4)} Z")
