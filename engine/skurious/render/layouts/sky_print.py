"""Render 1: the personalised sky print. The product everything else pays for.

One disc of sky, one nakshatra ring around it, and a caption block that says
exactly which sky this is. The engine writes no adjectives: names, occasion,
date, place, coordinates, and the scheme the numbers came from. Anything that
judges the sky is the practitioner's job and goes out under their name.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ...sidereal import naming_syllable
from ...sky import SkyState
from ...time import format_local, scheme_footer
from ..raster import Size
from ..svg import SVG
from ..themes import Theme
from . import common


@dataclass
class Caption:
    """What the buyer typed. None of it is computed; all of it is printed."""

    names: list[str] = field(default_factory=list)
    occasion: str = ""
    message: str = ""


def render(sky: SkyState, theme: Theme, size: Size, caption: Caption,
           *, bleed: bool = False, mag_limit: float = 5.5,
           show_syllable: bool = False) -> SVG:
    """Author in millimetres; the rasteriser decides how many pixels that is."""
    bleed_mm = size.bleed_mm if bleed else 0.0
    svg = SVG(size.width_mm, size.height_mm, bleed_mm)
    canvas = svg.content
    defs = svg.defs()
    common.add_grain(defs, theme)

    w, h = size.width_mm, size.height_mm
    scale = w / 457.2                      # everything is authored against 18×24

    # Full-bleed ground: the ink must run past the trim, not up to it.
    canvas.rect(-bleed_mm, -bleed_mm, svg.width, svg.height, fill=theme.ground)
    if theme.dark_ground:
        canvas.rect(-bleed_mm, -bleed_mm, svg.width, svg.height,
                    filter="url(#grain)", opacity=theme.noise_opacity)

    margin = 36.0 * scale
    r_outer = (w - 2 * margin) / 2.0
    ring_width = 15.0 * scale
    r_ring_in = r_outer - ring_width
    r_horizon = r_ring_in - 5.5 * scale     # room for the compass letters
    cx = w / 2.0
    cy = margin + r_outer

    common.clip_circle(defs, "sky-clip", cx, cy, r_horizon)
    canvas.comment("sky disc: zenith-centred stereographic, north up, east left")
    common.draw_disc(canvas, sky, theme, cx, cy, r_horizon,
                     clip_id="sky-clip", mag_limit=mag_limit,
                     planet_size=scale)
    canvas.comment("nakshatra ring: sidereal longitude 0 at top, clockwise")
    common.draw_nakshatra_ring(canvas, defs, sky, theme, cx, cy,
                               r_ring_in, r_outer, prefix="print", scale=scale)

    _caption_block(canvas, sky, theme, caption, cx, cy + r_outer, w, h, scale,
                   show_syllable)
    return svg


def _caption_block(canvas, sky: SkyState, theme: Theme, caption: Caption,
                   cx: float, top: float, w: float, h: float, scale: float,
                   show_syllable: bool) -> None:
    """Set the caption as one measured column, then centre it in the space left.

    The block is laid out twice: once to measure, once to draw. A print whose
    caption floats a hand's width above the bottom edge looks like a mistake
    even when every number on it is right, and the block's height depends on how
    much the buyer typed.
    """
    place = sky.place
    moon = sky.moon
    row = _moon_line(sky)

    # (text, font, size, colour, tracking, gap after) — in millimetres at 18×24.
    lines: list[tuple[str, str, float, str, float, float]] = []
    if caption.names:
        lines.append(("  ·  ".join(caption.names), theme.latin, 13.0,
                      theme.ink, 1.6, 11.5))
    if caption.occasion:
        lines.append((caption.occasion.upper(), theme.latin, 5.0,
                      theme.accent, 3.0, 13.0))
    rule_after = len(lines)
    lines.append((format_local(sky.instant), theme.latin, 6.2, theme.ink,
                  0.5, 8.6))
    lines.append((place.label, theme.latin, 6.2, theme.ink, 0.5, 7.2))
    lines.append((place.coords, theme.latin, 4.4, theme.muted, 0.8, 13.0))
    lines.append((row["deva"], theme.devanagari, 6.8, theme.accent, 0.0, 7.2))
    lines.append((row["latin"], theme.latin, 4.4, theme.muted, 0.7, 10.0))
    if show_syllable:
        deva, iast = naming_syllable(moon.lon_sid)
        lines.append((deva, theme.devanagari, 10.0, theme.highlight, 0.0, 6.6))
        lines.append((f"naming syllable · {iast}", theme.latin, 4.0,
                      theme.muted, 0.8, 10.0))
    if caption.message:
        lines.append((caption.message, theme.latin, 5.0, theme.muted, 0.0, 0.0))

    block = sum(gap for *_rest, gap in lines[:-1]) + lines[-1][2]
    footer_y = h - 16.0 * scale
    free = footer_y - 8.0 * scale - top
    y = top + max(18.0 * scale, (free - block * scale) / 2.0) + lines[0][2] * scale

    for i, (text, font, size, colour, tracking, gap) in enumerate(lines):
        if i == rule_after:
            canvas.line(cx - 46 * scale, y - 7.0 * scale, cx + 46 * scale,
                        y - 7.0 * scale, stroke=theme.accent,
                        stroke_width=0.3 * scale, opacity=0.6)
        style = {"font_style": "italic"} if text == caption.message else {}
        canvas.text(cx, y, text, font_family=font, font_size=size * scale,
                    fill=colour, text_anchor="middle",
                    letter_spacing=tracking * scale, **style)
        y += gap * scale

    canvas.text(cx, footer_y, scheme_footer(sky.instant, sky.scheme),
                font_family=theme.latin, font_size=3.1 * scale,
                fill=theme.muted, text_anchor="middle",
                letter_spacing=0.5 * scale, opacity=0.85)


def _moon_line(sky: SkyState) -> dict[str, str]:
    """The Moon's nakshatra and pada — the one computed fact on the print."""
    from ...sidereal import nakshatra_table

    moon = sky.moon
    row = nakshatra_table()[moon.nakshatra]
    return {
        "deva": row["deva"],
        "latin": f"Moon in {row['iast']} · pada {moon.pada} · "
                 f"{sky.moon_phase.name}",
    }
