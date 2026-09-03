"""Star positions, through Swiss Ephemeris rather than around it.

`scripts/build_stars.py` converts BSC5 into `data/ephe/sefstars.txt`. Reading it
back through `swe_fixstar2_ut` rather than projecting the catalogue ourselves
means every star gets the same precession, nutation and proper-motion path the
planets get — which is the only reason a 5561 BCE star field can be drawn beside
a 5561 BCE planet and be about the same sky.

All 9,096 stars take about 20 ms for one instant, so there is no reason to
pre-filter for anything but drawing.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass

import swisseph as swe

from .paths import EPHE, STAR_FILE, require


@dataclass(frozen=True)
class Star:
    hr: int
    name: str                  # Bayer/Flamsteed designation, or HRnnnn
    ra: float
    dec: float
    alt: float
    az: float
    mag: float


@dataclass(frozen=True)
class CatalogueEntry:
    hr: int
    name: str
    designation: str
    mag: float


@functools.lru_cache(maxsize=1)
def catalogue() -> list[CatalogueEntry]:
    """The magnitudes, read from our own file: Swiss returns positions, not mags."""
    require(STAR_FILE, "scripts/build_stars.py")
    out = []
    for line in STAR_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        f = line.split(",")
        if len(f) < 14:
            continue
        out.append(CatalogueEntry(hr=int(f[0][2:]), name=f[0],
                                  designation=f[1], mag=float(f[13])))
    return out


def positions(inst, place, mag_limit: float = 5.5,
              above_horizon: bool = True) -> list[Star]:
    """Every catalogue star brighter than `mag_limit`, in horizontal coordinates.

    Sorted by HR number so that two runs of the same render emit the same SVG in
    the same order; the layouts depend on that for byte-identical output.
    """
    require(EPHE / "sepl_18.se1", "scripts/fetch_ephe.py")
    swe.set_ephe_path(str(EPHE))
    jd = inst.jd_ut
    geo = [place.lon, place.lat, 0.0]
    flags = swe.FLG_SWIEPH | swe.FLG_EQUATORIAL

    out = []
    for entry in catalogue():
        if entry.mag > mag_limit:
            continue
        try:
            values, _name, _flag = swe.fixstar2_ut(entry.name, jd, flags)
        except swe.Error:                     # pragma: no cover - bad catalogue row
            continue
        ra, dec, dist = values[0], values[1], values[2]
        az_south, alt, _apparent = swe.azalt(
            jd, swe.EQU2HOR, geo, 0.0, 0.0, [ra, dec, dist])
        if above_horizon and alt <= 0.0:
            continue
        out.append(Star(hr=entry.hr, name=entry.designation, ra=ra, dec=dec,
                        alt=alt, az=(az_south + 180.0) % 360.0, mag=entry.mag))
    out.sort(key=lambda s: s.hr)
    return out


def by_designation(designation: str, inst, place) -> Star | None:
    """One named star — for the Stellarium reconciliation test."""
    match = next((e for e in catalogue() if e.designation == designation), None)
    if match is None:
        return None
    require(EPHE / "sepl_18.se1", "scripts/fetch_ephe.py")
    swe.set_ephe_path(str(EPHE))
    values, _name, _flag = swe.fixstar2_ut(
        match.name, inst.jd_ut, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)
    ra, dec, dist = values[0], values[1], values[2]
    az_south, alt, _ = swe.azalt(inst.jd_ut, swe.EQU2HOR,
                                 [place.lon, place.lat, 0.0], 0.0, 0.0,
                                 [ra, dec, dist])
    return Star(hr=match.hr, name=match.designation, ra=ra, dec=dec, alt=alt,
                az=(az_south + 180.0) % 360.0, mag=match.mag)
