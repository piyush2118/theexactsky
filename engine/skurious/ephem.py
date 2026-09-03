"""Planetary positions: the one place that calls Swiss Ephemeris for a body.

Every body comes back with all four coordinate systems at once — tropical
ecliptic, sidereal ecliptic, equatorial, and horizontal — because a print needs
alt/az to place the dot and the nakshatra ring needs the sidereal longitude for
the same body in the same picture, and computing them in two places is how they
drift apart.

Azimuth is converted to the compass convention (0 = north, 90 = east). Swiss
returns it measured from the south westward, which is correct and surprising.
Altitude is geometric: refraction is off, because a print draws the sky, not the
atmosphere.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass

import swisseph as swe

from .errors import SkuriousError
from .paths import EPHE, require
from .sidereal import Scheme, nakshatra, norm360, pada, rasi

FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

# The nine grahas, plus the two outer planets that belong on a star map but not
# in a kundali. Ketu is not a Swiss body: it is the node reflected.
SWE_BODY = {
    "sun": swe.SUN, "moon": swe.MOON, "mercury": swe.MERCURY,
    "venus": swe.VENUS, "mars": swe.MARS, "jupiter": swe.JUPITER,
    "saturn": swe.SATURN, "uranus": swe.URANUS, "neptune": swe.NEPTUNE,
}
NODE_BODY = {"mean": swe.MEAN_NODE, "true": swe.TRUE_NODE}

GRAHAS = ("sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn",
          "rahu", "ketu")
SKY_BODIES = GRAHAS + ("uranus", "neptune")

GLYPHS = {
    "sun": "☉", "moon": "☾", "mercury": "☿", "venus": "♀", "mars": "♂",
    "jupiter": "♃", "saturn": "♄", "uranus": "♅", "neptune": "♆",
    "rahu": "☊", "ketu": "☋",
}
LABELS = {
    "sun": "Sūrya", "moon": "Candra", "mercury": "Budha", "venus": "Śukra",
    "mars": "Maṅgala", "jupiter": "Guru", "saturn": "Śani", "rahu": "Rāhu",
    "ketu": "Ketu", "uranus": "Uranus", "neptune": "Neptune",
}


@dataclass(frozen=True)
class BodyPosition:
    body: str
    lon_trop: float
    lon_sid: float
    lat: float
    speed: float               # degrees of ecliptic longitude per day
    retrograde: bool
    ra: float
    dec: float
    alt: float                 # geometric, no refraction
    az: float                  # degrees east of north
    nakshatra: int             # 0-based
    pada: int
    rasi: int                  # 0-based
    distance: float = 0.0

    @property
    def glyph(self) -> str:
        return GLYPHS[self.body]

    @property
    def label(self) -> str:
        return LABELS[self.body]

    @property
    def nakshatra_name(self) -> str:
        from .sidereal import nakshatra_table
        return nakshatra_table()[self.nakshatra]["iast"]

    @property
    def rasi_name(self) -> str:
        from .sidereal import rasi_table
        return rasi_table()[self.rasi]["iast"]

    @property
    def above_horizon(self) -> bool:
        return self.alt > 0.0


@dataclass(frozen=True)
class MoonPhase:
    illuminated: float         # 0..1
    phase_angle: float         # degrees
    elongation: float          # signed: positive waxing, negative waning

    @property
    def waxing(self) -> bool:
        return self.elongation >= 0

    @property
    def name(self) -> str:
        e = abs(self.elongation)
        if e < 6:
            return "new moon"
        if e > 174:
            return "full moon"
        quarter = "first quarter" if self.waxing else "last quarter"
        if abs(e - 90) < 6:
            return quarter
        shape = "crescent" if e < 90 else "gibbous"
        return f"{'waxing' if self.waxing else 'waning'} {shape}"


@functools.lru_cache(maxsize=1)
def init_ephemeris() -> None:
    """Point Swiss at the vendored ephemeris exactly once per process."""
    require(EPHE / "sepl_18.se1", "scripts/fetch_ephe.py")
    swe.set_ephe_path(str(EPHE))


def _calc(jd: float, ipl: int, flags: int) -> tuple[float, ...]:
    init_ephemeris()
    try:
        values, _ = swe.calc_ut(jd, ipl, flags)
    except swe.Error as exc:                      # pragma: no cover - swiss text
        raise SkuriousError(f"Swiss Ephemeris refused body {ipl}: {exc}") from exc
    return values


def _horizontal(jd: float, place, ra: float, dec: float, dist: float
                ) -> tuple[float, float]:
    """(altitude, azimuth) in degrees, azimuth east of north, no refraction."""
    az_south, true_alt, _apparent = swe.azalt(
        jd, swe.EQU2HOR, [place.lon, place.lat, 0.0], 0.0, 0.0, [ra, dec, dist])
    return true_alt, (az_south + 180.0) % 360.0


def body_position(inst, place, scheme: Scheme, body: str) -> BodyPosition:
    """One body, in every coordinate system the layouts need."""
    if body == "ketu":
        rahu = body_position(inst, place, scheme, "rahu")
        return _reflect_node(inst, place, rahu)
    if body == "rahu":
        ipl = NODE_BODY[scheme.node]
    elif body in SWE_BODY:
        ipl = SWE_BODY[body]
    else:
        raise SkuriousError(f"unknown body {body!r}")

    jd = inst.jd_ut
    trop = _calc(jd, ipl, FLAGS)
    scheme.apply()
    sid = _calc(jd, ipl, FLAGS | swe.FLG_SIDEREAL)
    equ = _calc(jd, ipl, FLAGS | swe.FLG_EQUATORIAL)
    alt, az = _horizontal(jd, place, equ[0], equ[1], equ[2])

    lon_sid = norm360(sid[0])
    return BodyPosition(
        body=body, lon_trop=norm360(trop[0]), lon_sid=lon_sid, lat=trop[1],
        speed=trop[3], retrograde=trop[3] < 0.0, ra=equ[0], dec=equ[1],
        alt=alt, az=az, nakshatra=nakshatra(lon_sid)["n"] - 1,
        pada=pada(lon_sid), rasi=rasi(lon_sid)["n"] - 1, distance=trop[2])


def _reflect_node(inst, place, rahu: BodyPosition) -> BodyPosition:
    """Ketu is Rahu's opposite point; Swiss has no body for it."""
    lon_sid = norm360(rahu.lon_sid + 180.0)
    ra = (rahu.ra + 180.0) % 360.0
    dec = -rahu.dec
    alt, az = _horizontal(inst.jd_ut, place, ra, dec, 1.0)
    return BodyPosition(
        body="ketu", lon_trop=norm360(rahu.lon_trop + 180.0), lon_sid=lon_sid,
        lat=-rahu.lat, speed=rahu.speed, retrograde=rahu.retrograde,
        ra=ra, dec=dec, alt=alt, az=az, nakshatra=nakshatra(lon_sid)["n"] - 1,
        pada=pada(lon_sid), rasi=rasi(lon_sid)["n"] - 1, distance=rahu.distance)


def positions(inst, place, scheme: Scheme,
              bodies: tuple[str, ...] = SKY_BODIES) -> list[BodyPosition]:
    return [body_position(inst, place, scheme, b) for b in bodies]


def moon_phase(inst) -> MoonPhase:
    init_ephemeris()
    pheno = swe.pheno_ut(inst.jd_ut, swe.MOON, swe.FLG_SWIEPH)
    sun = _calc(inst.jd_ut, swe.SUN, FLAGS)[0]
    moon = _calc(inst.jd_ut, swe.MOON, FLAGS)[0]
    signed = (moon - sun + 180.0) % 360.0 - 180.0
    return MoonPhase(illuminated=pheno[1], phase_angle=pheno[0],
                     elongation=signed)


def ecliptic_path(inst, place, samples: int = 361) -> list[tuple[float, float]]:
    """(altitude, azimuth) along the whole ecliptic, for the arc on the print.

    Drawn from the tropical ecliptic at the instant's own obliquity, which is
    the curve a camera would see, not a sidereal abstraction.
    """
    init_ephemeris()
    jd = inst.jd_ut
    eps = swe.calc_ut(jd, swe.ECL_NUT, swe.FLG_SWIEPH)[0][0]
    out = []
    for i in range(samples):
        lon = 360.0 * i / (samples - 1)
        ra, dec = swe.cotrans([lon, 0.0, 1.0], -eps)[:2]
        out.append(_horizontal(jd, place, ra, dec, 1.0))
    return out


def local_midnight(inst) -> float:
    """The Julian day of 00:00 on the instant's own local calendar date."""
    from .time import local_parts

    _y, _m, _d, hour = local_parts(inst)
    return inst.jd_ut - hour / 24.0


def rise_set(inst, place, body: str = "sun") -> tuple[float | None, float | None]:
    """The rise and set of this instant's own local day, as Julian days.

    Searching starts at local midnight, not at the instant. Starting anywhere
    else silently returns the neighbouring day's sunrise, which shifts a claim
    whose event is "at sunrise" by twenty-four hours — the kind of error that
    survives every test that only looks at longitudes.
    """
    init_ephemeris()
    ipl = SWE_BODY.get(body)
    if ipl is None:
        raise SkuriousError(f"cannot compute rise/set for {body!r}")
    geo = [place.lon, place.lat, 0.0]
    start = local_midnight(inst)
    out = []
    for event in (swe.CALC_RISE, swe.CALC_SET):
        try:
            code, times = swe.rise_trans(start, ipl, event, geo, 0.0, 0.0,
                                         swe.FLG_SWIEPH)
            out.append(times[0] if code >= 0 else None)
        except swe.Error:            # polar day or night: neither happens
            out.append(None)
    return out[0], out[1]
