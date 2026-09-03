"""The star catalogue and the projection.

The projection tests are the ones that keep east on the left. Every other
convention in this file can be argued about; that one is what a star-map buyer
already knows, and getting it backwards makes a mirror image of the sky.
"""

from __future__ import annotations

import math

import pytest

from skurious import sky as sky_mod, stars
from skurious.sky import project, star_radius, unproject
from skurious.time import instant

J2000 = 2451545.0
# BSC5 records Sirius at 06h45m08.9s, -16°42'58" (J2000), which is 101.28708°,
# -16.71611°. Swiss returns an apparent place, so aberration and nutation move
# it by a few tens of arcseconds; anything larger means the catalogue conversion
# lost a column.
SIRIUS_J2000 = (101.28708, -16.71611)


# --------------------------------------------------------------------------
# the catalogue
# --------------------------------------------------------------------------

def test_catalogue_is_the_whole_bright_star_catalogue():
    entries = stars.catalogue()
    assert 9000 < len(entries) < 9120
    assert all(e.name.startswith("HR") for e in entries)
    assert len({e.hr for e in entries}) == len(entries)


def test_catalogue_covers_the_naked_eye_sky():
    mags = [e.mag for e in stars.catalogue() if e.mag < 90]
    assert min(mags) < -1.4                      # Sirius
    assert max(mags) > 6.0                       # down past naked-eye limit
    assert sum(1 for m in mags if m <= 5.5) > 1500


def test_sirius_lands_where_the_catalogue_says(edison):
    inst = instant("2000-01-01", "12:00", edison)
    sirius = stars.by_designation("alCMa", inst, edison)
    assert sirius is not None
    assert sirius.mag == pytest.approx(-1.46, abs=0.01)
    assert sirius.ra == pytest.approx(SIRIUS_J2000[0], abs=0.01)
    assert sirius.dec == pytest.approx(SIRIUS_J2000[1], abs=0.01)


def test_precession_moves_the_stars_over_five_thousand_years(edison, kurukshetra):
    """Spica's right ascension shifts by roughly 70° between 3000 BCE and now."""
    now = stars.by_designation("alVir", instant("2000-01-01", "12:00", edison),
                               edison)
    then = stars.by_designation(
        "alVir", instant("-2999-01-01", "12:00", kurukshetra, calendar="julian"),
        kurukshetra)
    assert now is not None and then is not None
    drift = (now.ra - then.ra) % 360.0
    assert 55.0 < drift < 85.0


def test_magnitude_limit_is_honoured(wedding_instant, edison):
    bright = stars.positions(wedding_instant, edison, mag_limit=3.0)
    faint = stars.positions(wedding_instant, edison, mag_limit=5.5)
    assert len(bright) < len(faint)
    assert all(s.mag <= 3.0 for s in bright)


def test_only_stars_above_the_horizon_are_returned(wedding_instant, edison):
    visible = stars.positions(wedding_instant, edison, mag_limit=5.5)
    assert all(s.alt > 0.0 for s in visible)
    everything = stars.positions(wedding_instant, edison, mag_limit=5.5,
                                 above_horizon=False)
    assert len(everything) > len(visible)


def test_star_order_is_stable(wedding_instant, edison):
    """Byte-identical SVGs need a stable element order, and this is where it starts."""
    a = stars.positions(wedding_instant, edison, mag_limit=4.0)
    b = stars.positions(wedding_instant, edison, mag_limit=4.0)
    assert [s.hr for s in a] == [s.hr for s in b] == sorted(s.hr for s in a)


def test_an_ancient_star_field_renders_without_error(kurukshetra):
    inst = instant("-2999-11-22", "06:00", kurukshetra, calendar="julian")
    field = stars.positions(inst, kurukshetra, mag_limit=4.0)
    assert len(field) > 50


# --------------------------------------------------------------------------
# projection
# --------------------------------------------------------------------------

def test_the_zenith_is_the_centre_and_the_horizon_is_the_rim():
    assert project(90.0, 0.0, 100.0) == pytest.approx((0.0, 0.0))
    for az in (0.0, 90.0, 180.0, 270.0):
        x, y = project(0.0, az, 100.0)
        assert math.hypot(x, y) == pytest.approx(100.0)


def test_north_is_up_and_east_is_on_the_left():
    """A star map is read lying on your back, so the compass runs the other way."""
    r = 100.0
    assert project(0.0, 0.0, r) == pytest.approx((0.0, -r))       # N: up
    assert project(0.0, 90.0, r) == pytest.approx((-r, 0.0))      # E: left
    assert project(0.0, 180.0, r) == pytest.approx((0.0, r))      # S: down
    assert project(0.0, 270.0, r) == pytest.approx((r, 0.0))      # W: right


def test_projection_round_trips():
    for alt in (5.0, 30.0, 60.0, 89.0):
        for az in (0.0, 47.0, 123.0, 250.0, 359.0):
            x, y = project(alt, az, 120.0)
            back_alt, back_az = unproject(x, y, 120.0)
            assert back_alt == pytest.approx(alt, abs=1e-9)
            assert back_az == pytest.approx(az, abs=1e-9)


def test_below_the_horizon_falls_outside_the_disc():
    x, y = project(-10.0, 45.0, 100.0)
    assert math.hypot(x, y) > 100.0


def test_the_projection_is_monotonic_in_altitude():
    """Higher in the sky is always nearer the centre; no folding."""
    radii = [math.hypot(*project(alt, 30.0, 100.0)) for alt in range(0, 91, 5)]
    assert radii == sorted(radii, reverse=True)


def test_star_radius_shrinks_with_magnitude():
    radii = [star_radius(m) for m in (-1.5, 0.0, 2.0, 4.0, 5.4)]
    assert radii == sorted(radii, reverse=True)
    assert star_radius(6.0) == 0.0
    assert all(r > 0 for r in radii)


# --------------------------------------------------------------------------
# SkyState
# --------------------------------------------------------------------------

def test_sky_state_has_everything_a_layout_needs(wedding_sky):
    assert wedding_sky.stars
    assert len(wedding_sky.grahas) == 9
    assert wedding_sky.sunrise is not None and wedding_sky.sunset is not None
    assert wedding_sky.ecliptic_path
    assert wedding_sky.moon.body == "moon"
    assert not wedding_sky.is_daytime            # 19:30 in February


def test_sky_state_refuses_a_body_it_did_not_compute(edison, wedding_instant,
                                                     scheme):
    limited = sky_mod.build(edison, wedding_instant, scheme,
                            bodies=("sun", "moon"), with_stars=False)
    assert limited.moon.body == "moon"
    with pytest.raises(KeyError):
        limited.body("saturn")
