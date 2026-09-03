"""Positions, and the two conventions most likely to be silently wrong.

Azimuth: Swiss measures it from the south, westward. Everybody else measures it
from the north, eastward. Getting that backwards mirrors every print and nobody
notices until a buyer who was there says the Moon was on the other side.

Ketu: Swiss has no body for it, so it is the node reflected, and a reflection
that forgets the declination puts it on the wrong side of the sky.
"""

from __future__ import annotations

import math

import pytest

from skurious import ephem, geo
from skurious.errors import SkuriousError
from skurious.sidereal import Scheme, norm360
from skurious.time import instant


def test_the_sun_is_up_at_local_noon_and_down_at_midnight(edison, scheme):
    noon = ephem.body_position(instant("2019-06-21", "13:00", edison),
                               edison, scheme, "sun")
    midnight = ephem.body_position(instant("2019-06-21", "01:00", edison),
                                   edison, scheme, "sun")
    assert noon.alt > 60.0                   # midsummer, 40°N
    assert midnight.alt < -15.0


def test_the_noon_sun_is_due_south_in_the_northern_hemisphere(edison, scheme):
    """Azimuth is east of north, so due south is 180°, not 0°."""
    noon = ephem.body_position(instant("2019-06-21", "12:57", edison),
                               edison, scheme, "sun")
    assert noon.az == pytest.approx(180.0, abs=3.0)


def test_the_sun_rises_in_the_east(edison, scheme):
    rise = ephem.body_position(instant("2019-03-20", "07:00", edison),
                               edison, scheme, "sun")
    assert 80.0 < rise.az < 110.0            # equinox sunrise, close to due east


def test_sidereal_longitude_is_tropical_less_the_ayanamsa(edison, scheme):
    from skurious.sidereal import ayanamsa

    inst = instant("2019-02-14", "19:30", edison)
    sun = ephem.body_position(inst, edison, scheme, "sun")
    assert norm360(sun.lon_trop - ayanamsa(inst.jd_ut, scheme)) == \
        pytest.approx(sun.lon_sid, abs=1e-6)


def test_ketu_is_exactly_opposite_rahu(wedding_instant, edison, scheme):
    rahu = ephem.body_position(wedding_instant, edison, scheme, "rahu")
    ketu = ephem.body_position(wedding_instant, edison, scheme, "ketu")
    assert norm360(ketu.lon_sid - rahu.lon_sid) == pytest.approx(180.0, abs=1e-9)
    assert ketu.dec == pytest.approx(-rahu.dec, abs=1e-9)
    assert abs(ketu.rasi - rahu.rasi) == 6


def test_the_nodes_move_backwards(wedding_instant, edison, scheme):
    """The lunar nodes regress, always. A positive speed means a sign error."""
    rahu = ephem.body_position(wedding_instant, edison, scheme, "rahu")
    assert rahu.speed < 0
    assert rahu.retrograde


def test_mean_and_true_node_differ_but_not_by_much(wedding_instant, edison):
    mean = ephem.body_position(wedding_instant, edison, Scheme(node="mean"), "rahu")
    true = ephem.body_position(wedding_instant, edison, Scheme(node="true"), "rahu")
    assert mean.lon_sid != true.lon_sid
    assert abs(mean.lon_sid - true.lon_sid) < 2.0


def test_mars_was_retrograde_in_the_2018_opposition(edison, scheme):
    """Mars retrograded from late June to late August 2018. A fixed, checkable fact."""
    during = ephem.body_position(instant("2018-07-27", "12:00", edison),
                                 edison, scheme, "mars")
    after = ephem.body_position(instant("2018-10-01", "12:00", edison),
                                edison, scheme, "mars")
    assert during.retrograde and during.speed < 0
    assert not after.retrograde and after.speed > 0


def test_venus_never_strays_far_from_the_sun(edison, scheme):
    """Elongation caps at about 47°; a larger value means a body mix-up."""
    from skurious.sidereal import signed_delta

    for date in ("2019-01-06", "2019-05-05", "2019-09-09", "2020-03-24"):
        inst = instant(date, "12:00", edison)
        sun = ephem.body_position(inst, edison, scheme, "sun")
        venus = ephem.body_position(inst, edison, scheme, "venus")
        assert abs(signed_delta(sun.lon_trop, venus.lon_trop)) < 48.0


def test_moon_phase_matches_elongation(edison):
    """A full moon is opposite the Sun and fully lit; a new moon is neither.

    The instant is the maximum of the total lunar eclipse of 21 January 2019,
    05:12 UTC — which in New Jersey was 00:12 EST. Passing the UTC clock time as
    a local one is the exact mistake the whole time module exists to prevent.
    """
    full = ephem.moon_phase(instant("2019-01-21", "00:12", edison))
    assert full.illuminated > 0.99
    assert abs(abs(full.elongation) - 180.0) < 2.0
    assert full.name == "full moon"


def test_moon_phase_names_cover_the_cycle(edison):
    names = {ephem.moon_phase(instant(f"2019-06-{d:02d}", "12:00", edison)).name
             for d in range(1, 29)}
    assert "new moon" in names
    assert "full moon" in names
    assert any("crescent" in n for n in names)
    assert any("gibbous" in n for n in names)


def test_rise_and_set_bracket_the_day(edison, wedding_instant):
    rise, sett = ephem.rise_set(wedding_instant, edison, "sun")
    midnight = ephem.local_midnight(wedding_instant)
    assert rise is not None and sett is not None
    assert midnight < rise < sett < midnight + 1.0


def test_rise_set_uses_the_instants_own_day(edison):
    """An evening instant and a morning instant on one date share one sunrise."""
    morning = ephem.rise_set(instant("2019-02-14", "06:00", edison), edison)
    evening = ephem.rise_set(instant("2019-02-14", "23:00", edison), edison)
    assert morning[0] == pytest.approx(evening[0])


def test_ecliptic_path_is_a_closed_loop(edison, wedding_instant):
    path = ephem.ecliptic_path(wedding_instant, edison)
    assert len(path) == 361
    assert path[0] == pytest.approx(path[-1])
    # Half the ecliptic is above the horizon at any moment, give or take.
    up = sum(1 for alt, _az in path if alt > 0)
    assert 120 < up < 240


def test_the_ecliptic_passes_through_the_sun(edison, wedding_instant, scheme):
    """The Sun is on the ecliptic by definition; if it is not, a frame is wrong."""
    sun = ephem.body_position(wedding_instant, edison, scheme, "sun")
    path = ephem.ecliptic_path(wedding_instant, edison)
    closest = min(math.hypot(alt - sun.alt,
                             (az - sun.az + 180) % 360 - 180) for alt, az in path)
    assert closest < 1.0


def test_unknown_bodies_are_refused(wedding_instant, edison, scheme):
    with pytest.raises(SkuriousError):
        ephem.body_position(wedding_instant, edison, scheme, "vulcan")


def test_ancient_positions_work_at_the_edge_of_the_ephemeris(kurukshetra, scheme):
    inst = instant("-5560-10-16", "06:00", kurukshetra, calendar="julian")
    bodies = ephem.positions(inst, kurukshetra, scheme, ephem.GRAHAS)
    assert len(bodies) == len(ephem.GRAHAS)
    assert all(0.0 <= b.lon_sid < 360.0 for b in bodies)


def test_out_of_range_years_are_refused(kurukshetra):
    from skurious.errors import OutOfEphemerisRange

    with pytest.raises(OutOfEphemerisRange):
        instant("-7000-01-01", "12:00", kurukshetra, calendar="julian")
