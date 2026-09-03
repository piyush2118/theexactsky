"""Render 2: the six-panel plate. One constraint list, six proposed dates.

The plate is the calling card for the history audience, and its whole rhetorical
force comes from being boring: the same code that draws somebody's wedding sky
draws these, the same three constraints run on every panel, and every panel
prints what the sky did rather than what it should have done. Nobody is told who
is right.

Two things are printed that a decorative plate would leave out, and they are the
reason this is evidence rather than an illustration: σ(ΔT) with its extrapolation
mark, and whether each claim's citation has actually been checked by a person.
"""

from __future__ import annotations

from dataclasses import dataclass

from ...claims import ClaimResult
from ...sky import SkyState
from ...time import both_year_forms, local_parts
from ..raster import Size
from ..svg import SVG
from ..themes import Theme
from . import common

COLS, ROWS = 3, 2


@dataclass
class Panel:
    result: ClaimResult
    sky: SkyState


def render(panels: list[Panel], theme: Theme, size: Size, *,
           title: str = "The sky over Kurukshetra",
           subtitle: str = "Six proposed dates for the Mahābhārata war, "
                           "one constraint list, evaluated") -> SVG:
    if len(panels) != COLS * ROWS:
        raise ValueError(f"the plate takes exactly {COLS * ROWS} panels, "
                         f"got {len(panels)}")

    svg = SVG(size.width_mm, size.height_mm)
    canvas = svg.content
    defs = svg.defs()
    common.add_grain(defs, theme)
    w, h = size.width_mm, size.height_mm

    common.paint_ground(canvas, theme, w, h)

    canvas.text(w / 2, 20.0, title, font_family=theme.latin, font_size=9.0,
                fill=theme.ink, text_anchor="middle", letter_spacing=1.4)
    canvas.text(w / 2, 29.0, subtitle, font_family=theme.latin, font_size=4.2,
                fill=theme.muted, text_anchor="middle", letter_spacing=0.5)

    margin_x, top, bottom = 16.0, 40.0, 24.0
    cell_w = (w - 2 * margin_x) / COLS
    cell_h = (h - top - bottom) / ROWS

    for i, panel in enumerate(panels):
        col, row = i % COLS, i // COLS
        x0 = margin_x + col * cell_w
        y0 = top + row * cell_h
        _panel(canvas, defs, panel, theme, x0, y0, cell_w, cell_h, i)

    # Scheme only. ΔT is per panel, because these six skies are four thousand
    # years apart and one footer number would be wrong for five of them.
    scheme = panels[0].sky.scheme
    canvas.text(w / 2, h - 12.0,
                f"{scheme.ayanamsa_label} · {scheme.nakshatra_boundaries} "
                f"nakshatras · proleptic Julian · Local Mean Time at the "
                f"observer · rule set {scheme.id}",
                font_family=theme.latin, font_size=3.2, fill=theme.muted,
                text_anchor="middle", letter_spacing=0.4)
    canvas.text(w / 2, h - 6.5,
                "The engine computes; it does not adjudicate. "
                "Every constraint's stated and computed values are printed above.",
                font_family=theme.latin, font_size=3.0, fill=theme.muted,
                text_anchor="middle", opacity=0.75, font_style="italic")
    return svg


def _panel(canvas, defs, panel: Panel, theme: Theme, x0: float, y0: float,
           w: float, h: float, index: int) -> None:
    sky, result = panel.sky, panel.result
    claim = result.claim
    cx = x0 + w / 2

    r_outer = 55.0
    r_ring_in = r_outer - 7.5
    r_horizon = r_ring_in - 3.0
    cy = y0 + 12.0 + r_outer

    clip_id = f"plate-clip-{index}"
    common.clip_circle(defs, clip_id, cx, cy, r_horizon)
    # Small dots for a small disc, but the compass letters keep a readable size:
    # scaling the type down with the drawing is how plates become unreadable.
    common.draw_disc(canvas, sky, theme, cx, cy, r_horizon, clip_id=clip_id,
                     mag_limit=5.0, planet_size=0.45, label_compass=True,
                     label_scale=0.72)
    common.draw_nakshatra_ring(canvas, defs, sky, theme, cx, cy, r_ring_in,
                               r_outer, prefix=f"plate{index}", labels=False,
                               scale=0.5)

    y = cy + r_outer + 9.0
    canvas.text(cx, y, claim.title, font_family=theme.latin, font_size=5.0,
                fill=theme.ink, text_anchor="middle", letter_spacing=0.6)
    y += 6.0

    yy, mm, dd, _hour = local_parts(sky.instant)
    stamp = (f"{dd:02d}/{mm:02d}  {both_year_forms(yy)}  ·  "
             f"{sky.instant.source_local_iso[-8:-3]} LMT")
    canvas.text(cx, y, stamp, font_family=theme.latin, font_size=3.4,
                fill=theme.muted, text_anchor="middle", letter_spacing=0.4)
    y += 5.0

    # ΔT belongs on each panel, not in the plate's footer: the six dates span
    # four thousand years and their ΔT differs by more than a day.
    inst = sky.instant
    mark = "~" if inst.delta_t_extrapolated else "±"
    canvas.text(cx, y, f"ΔT {inst.delta_t / 3600:.1f} h {mark}"
                       f"{inst.delta_t_sigma / 60:.0f} min",
                font_family=theme.latin, font_size=3.0, fill=theme.muted,
                text_anchor="middle", opacity=0.8)
    y += 6.5

    for r in result.results:
        # A drawn mark rather than a tick character: ✓ and ✕ are not in a
        # Garamond, and a mark that silently falls back to another font is a
        # mark that changes between machines.
        colour = theme.accent if r.passes else theme.highlight
        if r.passes:
            canvas.circle(x0 + 8.0, y - 1.2, 1.5, fill=colour)
        else:
            canvas.circle(x0 + 8.0, y - 1.2, 1.5, fill="none", stroke=colour,
                          stroke_width=0.45)
        canvas.text(x0 + 12.5, y, _wrap(r.computed, 78), font_family=theme.latin,
                    font_size=3.2, fill=theme.ink, opacity=0.9)
        y += 5.2

    y += 1.5
    canvas.text(cx, y, result.summary, font_family=theme.latin, font_size=3.6,
                fill=theme.muted, text_anchor="middle", letter_spacing=0.5)

    if claim.citation_status != "verified" or claim.date_status != "stated":
        y += 5.0
        canvas.text(cx, y, _provenance(claim), font_family=theme.latin,
                    font_size=2.9, fill=theme.highlight, text_anchor="middle",
                    opacity=0.9)


def _provenance(claim) -> str:
    """Say plainly which panels rest on a citation nobody has checked yet."""
    bits = []
    if claim.citation_status != "verified":
        bits.append("citation unverified")
    if claim.date_status != "stated":
        bits.append("day-of-year is a placeholder")
    return " · ".join(bits)


def _wrap(text: str, limit: int) -> str:
    """One line, truncated. The panel has no room to reflow and must not overrun."""
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"
