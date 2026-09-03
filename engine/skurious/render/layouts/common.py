"""The pieces every layout shares: the sky disc, the nakshatra ring, the Moon.

`sky_print` and `plate6` are both a disc plus captions. Keeping the disc here
means the six-panel plate and the wall print are provably the same picture at
different sizes, which is the point of the whole architecture: a historian who
checks the plate is checking the code that made somebody's wedding print.
"""

from __future__ import annotations

import math

from ...ephem import BodyPosition
from ...sidereal import NAKSHATRA_ARC, nakshatra_table
from ...sky import SkyState, project, star_radius
from ..svg import Group, arc_path, num, ring_sector
from ..themes import Theme

# The nakshatra ring puts sidereal longitude 0° (the start of Aśvinī) at twelve
# o'clock and runs clockwise. The ring is the sidereal zodiac, not a view of the
# sky, so it gets a fixed orientation rather than one that follows the horizon.
RING_ZERO_AT_TOP = True

COMPASS = [("N", 0.0), ("E", 90.0), ("S", 180.0), ("W", 270.0)]


def add_grain(defs: Group, theme: Theme, filter_id: str = "grain") -> None:
    """Monochrome grain over the ground.

    A large flat indigo field bands on a six-colour press. Two per cent of noise
    is below the eye's threshold on paper and above the press's quantisation, so
    the gradient in the dark stays smooth. Fixed seed, so renders stay identical.
    """
    if not theme.dark_ground:
        return
    f = Group(defs.add("filter", id=filter_id, x="0%", y="0%", width="100%",
                       height="100%", color_interpolation_filters="sRGB"))
    f.add("feTurbulence", type="fractalNoise", baseFrequency="0.85",
          numOctaves="3", seed="7", result="noise")
    f.add("feColorMatrix", **{"in": "noise", "type": "saturate", "values": "0"})


def paint_ground(canvas: Group, theme: Theme, width: float, height: float,
                 filter_id: str = "grain") -> None:
    canvas.rect(0, 0, width, height, fill=theme.ground)
    if theme.dark_ground:
        canvas.rect(0, 0, width, height, filter=f"url(#{filter_id})",
                    opacity=theme.noise_opacity)


def moon_path(r: float, illuminated: float) -> str:
    """The lit part of the Moon, drawn about the origin with the limb on +x.

    The terminator is the projection of a circle seen edge-on, so it is a
    half-ellipse whose x semi-axis is r·(1 − 2k). At k = 0.5 that collapses to a
    straight line, which is exactly right for a half moon; below 0.5 the ellipse
    curves back across the disc and gives a crescent.
    """
    k = max(0.0, min(1.0, illuminated))
    xr = abs(r * (1.0 - 2.0 * k))
    terminator_sweep = 1 if k > 0.5 else 0
    return (f"M 0 {num(-r)} "
            f"A {num(r)} {num(r)} 0 0 1 0 {num(r)} "
            f"A {num(xr)} {num(r)} 0 0 {terminator_sweep} 0 {num(-r)} Z")


def draw_moon(canvas: Group, cx: float, cy: float, r: float,
              illuminated: float, bright_limb_deg: float, theme: Theme) -> None:
    """Place the phase and turn it so the lit limb faces the Sun.

    `moon_path` draws the lit half on +x, and SVG's rotate() turns clockwise on
    screen, so the rotation is simply the screen-plane bearing to the Sun.
    """
    d = moon_path(r, illuminated)
    g = canvas.group(transform=f"translate({num(cx)},{num(cy)}) "
                               f"rotate({num(bright_limb_deg)})")
    g.circle(0, 0, r, fill="none", stroke=theme.muted, stroke_width=r * 0.09,
             opacity=0.7)
    g.path(d, fill=theme.ink)


def bright_limb_angle(moon: BodyPosition, sun: BodyPosition,
                      radius: float) -> float:
    """Which way the Moon's lit side faces, as a clockwise screen angle from +x.

    Computed in the picture rather than on the sky, because the projection
    rotates things and a phase pointing the wrong way is the kind of error a
    buyer who was actually there will notice. When the Sun is below the horizon
    it still has a projected position outside the disc, and the direction to it
    is still right.
    """
    mx, my = project(moon.alt, moon.az, radius)
    # tan(z/2) runs away near the nadir; clamping keeps the direction and drops
    # the infinity, and the direction is all this needs.
    sx, sy = project(max(sun.alt, -80.0), sun.az, radius)
    return math.degrees(math.atan2(sy - my, sx - mx))


def _above_horizon_runs(samples: list[tuple[float, float]], radius: float
                        ) -> list[list[tuple[float, float]]]:
    """Split (alt, az) samples into the stretches that are actually in the sky."""
    runs: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    for alt, az in samples:
        if alt > 0.0:
            current.append(project(alt, az, radius))
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


def draw_disc(canvas: Group, sky: SkyState, theme: Theme, cx: float, cy: float,
              radius: float, *, clip_id: str, mag_limit: float = 5.5,
              label_compass: bool = True, planet_size: float = 1.0,
              label_scale: float | None = None) -> None:
    """The star field, the ecliptic, the horizon ring, the planets and the Moon.

    Everything inside the horizon is clipped to the disc; the horizon ring and
    its compass letters sit on top of the clip so they are never cut.
    """
    canvas.circle(cx, cy, radius, fill=theme.ground, opacity=0.55)

    inside = canvas.group(clip_path=f"url(#{clip_id})")

    # -- stars ------------------------------------------------------------
    stars = inside.group(fill=theme.star, opacity=theme.star_opacity)
    for star in sky.stars:
        if star.mag > mag_limit:
            continue
        r = star_radius(star.mag, mag_limit) * planet_size
        if r <= 0:
            continue
        x, y = project(star.alt, star.az, radius)
        stars.circle(cx + x, cy + y, r)

    # -- the ecliptic -----------------------------------------------------
    # Drawn as separate runs. The ecliptic leaves and re-enters the sky, and a
    # single polyline over the whole sample list draws a chord straight across
    # the disc at every gap.
    for run in _above_horizon_runs(sky.ecliptic_path, radius):
        if len(run) < 2:
            continue
        inside.polyline([(cx + x, cy + y) for x, y in run], fill="none",
                        stroke=theme.ecliptic, stroke_width=0.35 * planet_size,
                        opacity=0.55, stroke_dasharray="2.2 1.6")

    # -- planets ----------------------------------------------------------
    for body in sky.grahas:
        if body.body in ("moon", "rahu", "ketu") or body.alt <= 0:
            continue
        x, y = project(body.alt, body.az, radius)
        size = (2.3 if body.body in ("sun",) else 1.5) * planet_size
        inside.circle(cx + x, cy + y, size, fill=theme.accent)
        inside.circle(cx + x, cy + y, size * 2.6, fill="none",
                      stroke=theme.accent, stroke_width=0.18 * planet_size,
                      opacity=0.45)

    moon = sky.moon
    if moon.alt > 0:
        x, y = project(moon.alt, moon.az, radius)
        draw_moon(inside, cx + x, cy + y, 3.2 * planet_size,
                  sky.moon_phase.illuminated,
                  bright_limb_angle(moon, sky.sun, radius), theme)

    # -- the horizon itself -----------------------------------------------
    canvas.circle(cx, cy, radius, fill="none", stroke=theme.ink,
                  stroke_width=0.5 * planet_size, opacity=0.8)
    if label_compass:
        # Inside the horizon, not outside it: the gap between the horizon and
        # the nakshatra ring belongs to the ring, and a letter parked in it
        # reads as part of the ring rather than as a compass point. Label size
        # is its own knob, because a plate panel shrinks the sky but still needs
        # letters somebody can read.
        ls = planet_size if label_scale is None else label_scale
        for letter, azimuth in COMPASS:
            a = math.radians(azimuth)
            lx, ly = -math.sin(a), -math.cos(a)
            canvas.line(cx + lx * radius, cy + ly * radius,
                        cx + lx * (radius - 2.4 * ls),
                        cy + ly * (radius - 2.4 * ls),
                        stroke=theme.ink, stroke_width=0.4 * ls, opacity=0.7)
            canvas.text(cx + lx * (radius - 7.4 * ls),
                        cy + ly * (radius - 7.4 * ls) + 1.5 * ls,
                        letter, font_family=theme.latin, font_size=4.4 * ls,
                        fill=theme.muted, text_anchor="middle",
                        letter_spacing=0.4 * ls)


def draw_nakshatra_ring(canvas: Group, defs: Group, sky: SkyState, theme: Theme,
                        cx: float, cy: float, r_inner: float, r_outer: float, *,
                        prefix: str, labels: bool = True,
                        scale: float = 1.0) -> None:
    """The signature: 27 sidereal sectors, the Moon's filled, planets marked.

    This ring is what makes the print a *nakshatra* sky rather than a generic
    star map, and it is on every layout for that reason.
    """
    table = nakshatra_table()
    moon_nak = sky.moon.nakshatra
    mid = (r_inner + r_outer) / 2.0

    ring = canvas.group()
    for i, row in enumerate(table):
        start = i * NAKSHATRA_ARC
        end = start + NAKSHATRA_ARC
        occupied = i == moon_nak
        ring.path(ring_sector(cx, cy, r_inner, r_outer, start, end),
                  fill=theme.accent if occupied else "none",
                  fill_opacity=0.11 if occupied else 0,
                  stroke=theme.accent if occupied else theme.muted,
                  stroke_width=(0.4 if occupied else 0.18) * scale,
                  stroke_opacity=1.0 if occupied else 0.55)

        if labels:
            path_id = f"{prefix}-nak-{i}"
            # Labels on the bottom half must ride a reversed arc or they read
            # upside down.
            bottom = 90.0 < (start + NAKSHATRA_ARC / 2.0) < 270.0
            radius = mid - 1.2 * scale if bottom else mid - 2.4 * scale
            d = (arc_path(cx, cy, radius, end, start, sweep=0) if bottom
                 else arc_path(cx, cy, radius, start, end, sweep=1))
            defs.path(d, id=path_id, fill="none")
            ring.text_path(
                path_id, row["deva"],
                font_family=theme.devanagari, font_size=3.5 * scale,
                fill=theme.ink if occupied else theme.muted,
                opacity=1.0 if occupied else 0.8)

            iast_id = f"{prefix}-nak-iast-{i}"
            radius2 = mid + 3.4 * scale if bottom else mid + 2.2 * scale
            d2 = (arc_path(cx, cy, radius2, end, start, sweep=0) if bottom
                  else arc_path(cx, cy, radius2, start, end, sweep=1))
            defs.path(d2, id=iast_id, fill="none")
            ring.text_path(
                iast_id, row["iast"],
                font_family=theme.latin, font_size=2.1 * scale,
                fill=theme.muted, opacity=0.85, letter_spacing=0.25 * scale)

    # -- every graha marked at its own sidereal longitude ------------------
    for body in sky.grahas:
        angle = math.radians(body.lon_sid - 90.0)
        for radius, size in ((r_inner - 2.6 * scale, 1.05 * scale),):
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            colour = theme.highlight if body.body == "moon" else theme.accent
            ring.circle(x, y, size, fill=colour)

    ring.circle(cx, cy, r_inner, fill="none", stroke=theme.muted,
                stroke_width=0.25 * scale, opacity=0.5)
    ring.circle(cx, cy, r_outer, fill="none", stroke=theme.accent,
                stroke_width=0.35 * scale, opacity=0.7)


def clip_circle(defs: Group, clip_id: str, cx: float, cy: float,
                r: float) -> None:
    Group(defs.add("clipPath", id=clip_id)).circle(cx, cy, r)
