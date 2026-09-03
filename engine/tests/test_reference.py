"""Reconciliation against work computed by other people, with other code.

Every other test in this suite checks the engine against itself. That is worth
having, and it is not enough: a suite of self-consistent tests passes just as
happily when `set_ephe_path` points nowhere and Swiss silently falls back to its
built-in Moshier approximation, which stops at 3000 BCE and would make the
5561 BCE plate quietly wrong. Stage 0's acceptance gates are specifically about
external agreement, and this file is where that happens.

Three independent authorities are used:

* **JPL DE421** through Skyfield, for planetary and lunar longitudes. Different
  ephemeris source, different library, different implementations of light-time,
  aberration, precession and nutation.
* **Hipparcos** (ESA), for star positions. BSC5 carries FK5 proper motions from
  the 1980s; Hipparcos carries space astrometry. They are not copies.
* **The Indian Calendar Reform Committee's own definition** of the Lahiri
  ayanamsa, and the historical eclipse canon, for the things no ephemeris
  library can adjudicate.

Run `uv run --project engine scripts/fetch_reference.py` first; without the
reference data these skip.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
import swisseph as swe

from skurious import ephem, geo, stars
from skurious.sidereal import (Scheme, ayanamsa, nakshatra_index, norm360,
                               pada, signed_delta)
from skurious.time import instant

REF = Path("data/_reference")
DE421 = REF / "de421.bsp"
HIPPARCOS = REF / "hip_bright.tsv"

pytestmark = pytest.mark.reference

skyfield = pytest.importorskip("skyfield", reason="skyfield is a dev dependency")

needs_de421 = pytest.mark.skipif(
    not DE421.exists(),
    reason="run scripts/fetch_reference.py to download JPL DE421")
needs_hipparcos = pytest.mark.skipif(
    not HIPPARCOS.exists(),
    reason="run scripts/fetch_reference.py to download the Hipparcos subset")

# Swiss body -> the name DE421 knows it by. The outer planets are barycentres in
# DE421, which for Mars outward is well below the tolerance here.
BODIES = [("sun", "sun"), ("moon", "moon"), ("mercury", "mercury"),
          ("venus", "venus"), ("mars", "mars barycenter"),
          ("jupiter", "jupiter barycenter"), ("saturn", "saturn barycenter")]

# Twenty instants, chosen to be awkward rather than convenient: both hemispheres,
# half-hour and three-quarter-hour zones, DST and not, a leap day, both sides of
# midnight, and a spread across the Moon's cycle so the reconciliation is not all
# at one lunar phase.
INPUTS = [
    ("1994-05-03", "05:40", "Asia/Kolkata", 28.6139, 77.2090),
    ("1988-11-17", "23:55", "Asia/Kolkata", 19.0760, 72.8777),
    ("2001-02-28", "12:00", "Asia/Kathmandu", 27.7172, 85.3240),
    ("1996-07-04", "16:20", "America/New_York", 40.7128, -74.0060),
    ("1979-12-31", "18:45", "Europe/London", 51.5074, -0.1278),
    ("2004-02-29", "06:15", "Australia/Adelaide", -34.9285, 138.6007),
    ("1966-09-09", "09:09", "Asia/Tokyo", 35.6762, 139.6503),
    ("2012-06-21", "00:30", "America/Los_Angeles", 34.0522, -118.2437),
    ("1955-01-15", "14:05", "Asia/Kolkata", 13.0827, 80.2707),
    ("2019-02-14", "19:30", "America/New_York", 40.5187, -74.4121),
    ("1943-06-01", "07:00", "Asia/Kolkata", 22.5726, 88.3639),
    ("2023-10-14", "11:11", "America/Chicago", 41.8781, -87.6298),
    ("1987-03-21", "05:00", "Asia/Kolkata", 26.9124, 75.7873),
    ("2000-01-01", "00:01", "Pacific/Auckland", -36.8485, 174.7633),
    ("1971-08-08", "21:40", "Africa/Nairobi", -1.2921, 36.8219),
    ("2016-11-14", "13:52", "Asia/Dubai", 25.2048, 55.2708),
    ("1998-04-26", "03:33", "Europe/Berlin", 52.5200, 13.4050),
    ("2008-05-20", "20:20", "America/Sao_Paulo", -23.5505, -46.6333),
    ("1962-10-30", "10:45", "Asia/Kolkata", 17.3850, 78.4867),
    ("2021-12-04", "08:08", "Africa/Johannesburg", -26.2041, 28.0473),
]

STAR_EPOCH = ("2024-03-20", "21:00")     # a fixed modern instant, per the gate


def _place(tz: str, lat: float, lon: float):
    return geo.Place(id="ref", name="ref", admin="", country="", lat=lat,
                     lon=lon, tz=tz)


@pytest.fixture(scope="module")
def de421():
    from skyfield.api import load, load_file
    return load_file(str(DE421)), load.timescale()


def _skyfield_longitude(eph, ts, inst, sf_name: str) -> float:
    """Apparent geocentric ecliptic longitude of date, the JPL way."""
    y, mo, d, hour = swe.revjul(inst.jd_ut, swe.GREG_CAL)
    t = ts.ut1(y, mo, d, 0, 0, hour * 3600.0)
    astrometric = eph["earth"].at(t).observe(eph[sf_name])
    _lat, lon, _dist = astrometric.apparent().ecliptic_latlon("date")
    return lon.degrees


# --------------------------------------------------------------------------
# is the ephemeris even being used?
# --------------------------------------------------------------------------

def test_swiss_is_reading_the_vendored_files_not_its_builtin_fallback():
    """The failure mode this whole file exists to catch.

    With a bad ephemeris path Swiss does not raise. It falls back to Moshier,
    returns plausible numbers, and stops being valid before 3000 BCE — so the
    Vartak panel of the plate would be silently wrong while every self-consistent
    test in the suite stayed green.
    """
    ephem.init_ephemeris()
    _values, retflag = swe.calc_ut(2451545.0, swe.SUN, swe.FLG_SWIEPH)
    assert retflag & swe.FLG_SWIEPH, "Swiss fell back to Moshier"
    assert not retflag & swe.FLG_MOSEPH

    # And it reaches the far end of the plate, which Moshier cannot.
    ancient = swe.julday(-5560, 10, 16, 6.0, swe.JUL_CAL)
    _values, retflag = swe.calc_ut(ancient, swe.SATURN, swe.FLG_SWIEPH)
    assert retflag & swe.FLG_SWIEPH


# --------------------------------------------------------------------------
# the ayanamsa, against its own defining document
# --------------------------------------------------------------------------

def test_lahiri_matches_the_calendar_reform_committee_definition():
    """Lahiri is *defined* as 23°15′00″ at 21 March 1956, 00:00 UT.

    No other program can settle this one: it is a convention fixed by the Indian
    Calendar Reform Committee, and every ayanamsa disagreement downstream is
    really a disagreement about this anchor. Checking the anchor rather than
    another library's opinion of it is the difference between reconciliation and
    two programs sharing an assumption.
    """
    value = ayanamsa(swe.julday(1956, 3, 21, 0.0), Scheme(ayanamsa="lahiri"))
    assert value * 3600 == pytest.approx((23 * 60 + 15) * 60, abs=2.0)


def test_the_ayanamsa_is_actually_applied():
    """`set_sid_mode` is process-global state, and forgetting it is silent.

    A missing `scheme.apply()` makes the sidereal longitude equal the tropical
    one — every nakshatra wrong by roughly two, and nothing raises.
    """
    place = _place("Asia/Kolkata", 28.6, 77.2)
    inst = instant("1994-05-03", "05:40", place)
    moon = ephem.body_position(inst, place, Scheme(), "moon")
    offset = norm360(moon.lon_trop - moon.lon_sid)
    assert offset == pytest.approx(ayanamsa(inst.jd_ut, Scheme()), abs=1e-6)
    assert 23.0 < offset < 25.0


# --------------------------------------------------------------------------
# longitudes, against JPL DE421
# --------------------------------------------------------------------------

@needs_de421
@pytest.mark.parametrize("date, clock, tz, lat, lon", INPUTS)
def test_longitudes_match_jpl_de421(de421, date, clock, tz, lat, lon):
    eph, ts = de421
    place = _place(tz, lat, lon)
    inst = instant(date, clock, place)
    for name, sf_name in BODIES:
        ours = ephem.body_position(inst, place, Scheme(), name).lon_trop
        theirs = _skyfield_longitude(eph, ts, inst, sf_name)
        arcsec = abs(signed_delta(theirs, ours)) * 3600
        assert arcsec < 1.0, f"{name} on {date}: {arcsec:.3f}″ apart"


@needs_de421
def test_moon_nakshatra_and_pada_survive_swapping_the_ephemeris(de421):
    """The Stage 0 gate, decomposed into the two things it actually asserts.

    A nakshatra is `floor((tropical longitude − ayanamsa) / 13°20′)`. So it is
    right exactly when the longitude is right and the ayanamsa is right. The
    longitude is checked here against JPL, by recomputing the whole chain from
    Skyfield's number instead of Swiss's; the ayanamsa is checked above against
    the Calendar Reform Committee; the floor arithmetic is checked in
    test_sidereal.py at every boundary.

    What this does *not* settle is whether a Jyotish program agrees about
    conventions — apparent versus true position, geocentric versus topocentric.
    That needs Jagannatha Hora and a person; `test_writes_the_jyotish_fixture`
    below generates the sheet to check against.
    """
    eph, ts = de421
    mismatches = []
    for date, clock, tz, lat, lon in INPUTS:
        place = _place(tz, lat, lon)
        inst = instant(date, clock, place)
        scheme = Scheme()

        ours = ephem.body_position(inst, place, scheme, "moon")
        jpl_sidereal = norm360(_skyfield_longitude(eph, ts, inst, "moon")
                               - ayanamsa(inst.jd_ut, scheme))
        if (nakshatra_index(jpl_sidereal), pada(jpl_sidereal)) != \
                (ours.nakshatra, ours.pada):
            mismatches.append((date, ours.lon_sid, jpl_sidereal))
    assert not mismatches, f"nakshatra/pada differ on {mismatches}"


@needs_de421
def test_the_reconciliation_would_notice_if_it_were_broken(de421):
    """A guard on the guard: nudge the ephemeris and the comparison must fail.

    A reconciliation test that cannot fail is decoration. Half a degree is well
    inside one nakshatra, so this also shows the 1″ tolerance is not slack.
    """
    eph, ts = de421
    place = _place("Asia/Kolkata", 28.6, 77.2)
    inst = instant("1994-05-03", "05:40", place)
    theirs = _skyfield_longitude(eph, ts, inst, "moon")
    ours = ephem.body_position(inst, place, Scheme(), "moon").lon_trop
    assert abs(signed_delta(theirs, ours)) * 3600 < 1.0
    assert abs(signed_delta(theirs, ours + 0.5)) * 3600 > 1000.0


# --------------------------------------------------------------------------
# stars, against Hipparcos
# --------------------------------------------------------------------------

def _hipparcos_rows() -> list[tuple[int, float, float, float, float, float]]:
    out = []
    for line in HIPPARCOS.read_text(encoding="latin-1").splitlines():
        if line.startswith("#") or not line.strip() or line.startswith("---"):
            continue
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 6 or not parts[0].isdigit():
            continue
        try:
            out.append((int(parts[0]), float(parts[1]), float(parts[2]),
                        float(parts[3]), float(parts[4]), float(parts[5])))
        except ValueError:
            continue
    return out


@needs_hipparcos
@needs_de421
def test_fifty_bright_stars_agree_with_hipparcos(de421):
    """Stage 0's star gate: fifty bright stars, a 2024 instant, inside 0.1°.

    Our positions come from BSC5 through Swiss Ephemeris; the reference comes
    from Hipparcos through Skyfield. Two catalogues, two precession and nutation
    implementations, two proper-motion systems. They are matched by position
    rather than by an identifier crosswalk, which for stars this bright is
    unambiguous — the nearest neighbours are degrees apart.
    """
    from skyfield.api import Star, load, wgs84

    eph, ts = de421
    place = geo.resolve("5097529")
    inst = instant(*STAR_EPOCH, place)
    ours = stars.positions(inst, place, mag_limit=2.6, above_horizon=False)
    assert len(ours) >= 50

    y, mo, d, hour = swe.revjul(inst.jd_ut, swe.GREG_CAL)
    t = ts.ut1(y, mo, d, 0, 0, hour * 3600.0)
    observer = eph["earth"] + wgs84.latlon(place.lat, place.lon)

    by_position = {}
    for hip, ra, dec, pm_ra, pm_dec, vmag in _hipparcos_rows():
        star = Star(ra_hours=ra / 15.0, dec_degrees=dec,
                    ra_mas_per_year=pm_ra, dec_mas_per_year=pm_dec,
                    epoch=ts.tt(1991.25))
        alt, az, _dist = observer.at(t).observe(star).apparent().altaz()
        by_position[hip] = (alt.degrees, az.degrees, vmag)

    checked, worst = 0, 0.0
    for star in ours:
        # Match on the sky rather than on catalogue numbers.
        best_hip, best_sep = None, 1e9
        for hip, (alt, az, vmag) in by_position.items():
            if abs(vmag - star.mag) > 0.35:
                continue
            sep = math.hypot(alt - star.alt,
                             ((az - star.az + 180) % 360 - 180)
                             * math.cos(math.radians(star.alt)))
            if sep < best_sep:
                best_hip, best_sep = hip, sep
        if best_hip is None or best_sep > 0.5:
            continue                     # not in the V < 2.6 reference subset
        checked += 1
        worst = max(worst, best_sep)
        assert best_sep < 0.1, (
            f"HR{star.hr} ({star.name}) is {best_sep * 60:.2f}′ from HIP{best_hip}")

    assert checked >= 50, f"only matched {checked} stars, need 50"
    print(f"\n  {checked} stars matched, worst separation {worst * 3600:.1f}″")


# --------------------------------------------------------------------------
# ancient eclipses, against the historical canon
# --------------------------------------------------------------------------

@pytest.mark.parametrize("label, search_from, expect", [
    # Three eclipses whose dates are fixed by dated historical records rather
    # than by any ephemeris — which is what makes them a check on ΔT and on the
    # eclipse search at once.
    ("Bur-Sagale (Assyrian eponym canon)", (-762, 6, 1), (-762, 6, 15)),
    ("Thales' eclipse (Herodotus)", (-584, 5, 1), (-584, 5, 28)),
    ("the eclipse of Ugarit", (-1222, 3, 1), (-1222, 3, 5)),
])
def test_ancient_solar_eclipses_land_on_their_recorded_dates(label, search_from,
                                                             expect):
    ephem.init_ephemeris()
    jd = swe.julday(*search_from, 0.0, swe.JUL_CAL)
    flags, times = swe.sol_eclipse_when_glob(jd, swe.FLG_SWIEPH, 0, False)
    y, m, d, _h = swe.revjul(times[0], swe.JUL_CAL)
    assert (y, m, d) == expect, f"{label}: got {y}-{m:02d}-{d:02d}"
    assert flags & (swe.ECL_TOTAL | swe.ECL_ANNULAR), f"{label} was not central"


# --------------------------------------------------------------------------
# the part that needs a person
# --------------------------------------------------------------------------

def test_writes_the_jyotish_fixture(tmp_path_factory):
    """Emit the sheet a human checks against Jagannatha Hora.

    The plan wants two reference programs. JPL settles the astronomy and the
    Calendar Reform Committee settles the ayanamsa, but neither has an opinion
    about Jyotish convention. This writes out the twenty inputs with our answers
    so somebody can paste in a second column and see any disagreement at a
    glance. It is not a passing gate; it is the worksheet for one.
    """
    out = Path("tests/fixtures/jyotish_reconciliation.tsv")
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Paste Jagannatha Hora's answers into the last two columns.",
             "# Stage 0 is not signed off until these agree on all twenty rows.",
             "#",
             "\t".join(["date", "time", "tz", "lat", "lon", "moon_sid_lon",
                        "nakshatra", "pada", "jh_nakshatra", "jh_pada"])]
    for date, clock, tz, lat, lon in INPUTS:
        place = _place(tz, lat, lon)
        inst = instant(date, clock, place)
        moon = ephem.body_position(inst, place, Scheme(), "moon")
        lines.append("\t".join([
            date, clock, tz, f"{lat:.4f}", f"{lon:.4f}",
            f"{moon.lon_sid:.5f}", moon.nakshatra_name, str(moon.pada), "", ""]))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert len(lines) == 24
