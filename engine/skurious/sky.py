"""`SkyState` — one instant, one place, everything a layout needs; and the projection.

The projection is a zenith-centred stereographic disc: `r = R · tan(z/2)`, north
up, east on the left. East-on-the-left is not a mistake. A star map is read as if
you were lying on your back looking up, so the compass runs the other way round
from a ground map, and every star-print buyer has already seen it that way.

Stereographic is the right projection here because it is conformal: constellation
shapes stay recognisable all the way out to the horizon, which matters more on a
wall than equal-area does.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import ephem, stars as stars_mod
from .ephem import BodyPosition, MoonPhase
from .sidereal import Scheme
from .stars import Star
from .time import Instant


def project(alt: float, az: float, radius: float) -> tuple[float, float]:
    """Altitude and azimuth to (x, y) offsets from the disc centre, in disc units.

    `radius` is the horizon circle. Altitude 90° lands at the centre, 0° on the
    circle, and negative altitudes fall outside it — callers clip.
    """
    z = math.radians(90.0 - alt)
    r = radius * math.tan(z / 2.0)
    a = math.radians(az)
    return -r * math.sin(a), -r * math.cos(a)


def unproject(x: float, y: float, radius: float) -> tuple[float, float]:
    """Inverse of `project`, for tests and for placing labels back on the sky."""
    r = math.hypot(x, y)
    z = 2.0 * math.atan2(r, radius)
    alt = 90.0 - math.degrees(z)
    az = math.degrees(math.atan2(-x, -y)) % 360.0
    return alt, az


@dataclass(frozen=True)
class SkyState:
    """Everything about one sky. Layouts read this and nothing else."""

    place: object
    instant: Instant
    scheme: Scheme
    bodies: list[BodyPosition]
    stars: list[Star]
    moon_phase: MoonPhase
    ecliptic_path: list[tuple[float, float]]
    sunrise: float | None
    sunset: float | None

    def body(self, name: str) -> BodyPosition:
        for b in self.bodies:
            if b.body == name:
                return b
        raise KeyError(f"{name} was not computed for this sky")

    @property
    def moon(self) -> BodyPosition:
        return self.body("moon")

    @property
    def sun(self) -> BodyPosition:
        return self.body("sun")

    @property
    def is_daytime(self) -> bool:
        return self.sun.alt > 0.0

    @property
    def grahas(self) -> list[BodyPosition]:
        return [b for b in self.bodies if b.body in ephem.GRAHAS]


def build(place, instant: Instant, scheme: Scheme, *,
          mag_limit: float = 5.5,
          bodies: tuple[str, ...] = ephem.SKY_BODIES,
          with_stars: bool = True) -> SkyState:
    """Compute one sky. This is the call every render and every claim goes through."""
    sunrise, sunset = ephem.rise_set(instant, place, "sun")
    return SkyState(
        place=place,
        instant=instant,
        scheme=scheme,
        bodies=ephem.positions(instant, place, scheme, bodies),
        stars=stars_mod.positions(instant, place, mag_limit) if with_stars else [],
        moon_phase=ephem.moon_phase(instant),
        ecliptic_path=ephem.ecliptic_path(instant, place),
        sunrise=sunrise,
        sunset=sunset,
    )


def star_radius(mag: float, brightest: float = 5.5) -> float:
    """Dot radius in mm for a magnitude, on the usual perceptual curve.

    Each magnitude step is 2.512× the flux; the eye reads area, so the radius
    goes as the fourth root and the brightest stars stay dots rather than blobs.
    """
    if mag > brightest:
        return 0.0
    return 0.10 + 0.62 * ((brightest - mag) / 7.0) ** 0.55
