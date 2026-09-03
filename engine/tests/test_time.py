"""Time is where the silent errors live, so this is the longest test file.

Every case here is a real birth or a real date that a naive implementation gets
wrong: a US birth on the autumn fold, a Nepali birth on a 45-minute offset, an
Indian birth during the 1942-45 wartime offset, a date in the ten days that the
Gregorian reform deleted, and a date before year 1 that Python's own datetime
cannot represent at all.
"""

from __future__ import annotations

import pytest
import swisseph as swe

from skurious import geo
from skurious.errors import AmbiguousLocalTime, NonexistentLocalTime
from skurious.geo import Place
from skurious.time import (Instant, both_year_forms, delta_t_sigma, era_year,
                           format_local, instant, local_parts, parse_date,
                           resolve_calendar)


def place(lat: float, lon: float, tz: str) -> Place:
    return Place(id="t", name="test", admin="", country="", lat=lat, lon=lon,
                 tz=tz)


# --------------------------------------------------------------------------
# calendars and year numbering
# --------------------------------------------------------------------------

def test_gregorian_reform_boundary():
    """15 October 1582 Gregorian and 5 October 1582 Julian are the same day."""
    assert swe.julday(1582, 10, 15, 0.0, swe.GREG_CAL) == \
           swe.julday(1582, 10, 5, 0.0, swe.JUL_CAL)


def test_auto_calendar_switches_at_the_reform():
    assert resolve_calendar("auto", 1582, 10, 14) == "julian"
    assert resolve_calendar("auto", 1582, 10, 15) == "gregorian"
    assert resolve_calendar("auto", 1582, 10, 4) == "julian"
    assert resolve_calendar("auto", 1583, 1, 1) == "gregorian"


def test_astronomical_year_numbering():
    assert parse_date("-3066-11-22") == (-3066, 11, 22)
    assert era_year(-3066) == "3067 BCE"
    assert era_year(0) == "1 BCE"
    assert era_year(1994) == "1994 CE"
    assert "astronomical -3066" in both_year_forms(-3066)


def test_year_zero_exists_and_is_1_bce():
    """Astronomical numbering has a year 0; the era convention does not."""
    p = place(29.97, 76.88, "LMT")
    inst = instant("0000-03-21", "12:00", p, calendar="julian")
    assert local_parts(inst)[0] == 0
    assert "1 BCE" in format_local(inst)


# --------------------------------------------------------------------------
# time zones
# --------------------------------------------------------------------------

def test_us_dst_fold_is_refused_not_guessed():
    """01:30 on 3 November 2019 happens twice in New York."""
    p = place(40.5, -74.4, "America/New_York")
    with pytest.raises(AmbiguousLocalTime):
        instant("2019-11-03", "01:30", p)


def test_us_dst_gap_is_refused():
    """02:30 on 10 March 2019 never happens in New York."""
    p = place(40.5, -74.4, "America/New_York")
    with pytest.raises(NonexistentLocalTime):
        instant("2019-03-10", "02:30", p)


def test_nepal_is_five_forty_five():
    p = place(27.7, 85.3, "Asia/Kathmandu")
    assert instant("2000-06-01", "12:00", p).utc_offset == pytest.approx(5.75)


def test_nepal_was_five_thirty_before_1986():
    """Nepal moved to +05:45 in 1986; a 1980 birth is not on today's offset."""
    p = place(27.7, 85.3, "Asia/Kathmandu")
    assert instant("1980-06-01", "12:00", p).utc_offset == pytest.approx(5.5)


def test_indian_wartime_offset():
    """India ran on +06:30 from 1942 to 1945. Births in that window are common."""
    p = place(28.6, 77.2, "Asia/Kolkata")
    assert instant("1943-06-01", "12:00", p).utc_offset == pytest.approx(6.5)
    assert instant("2000-06-01", "12:00", p).utc_offset == pytest.approx(5.5)


def test_lmt_mode_uses_longitude():
    p = place(29.97, 76.8783, "Asia/Kolkata")
    inst = instant("1850-01-01", "12:00", p, timescale="lmt")
    assert inst.timescale == "lmt"
    assert inst.utc_offset == pytest.approx(76.8783 / 15.0)
    assert inst.tz_label.startswith("LMT")


def test_bce_dates_fall_back_to_lmt():
    """zoneinfo cannot represent year < 1, and no zone existed then anyway."""
    p = place(29.97, 76.8783, "Asia/Kolkata")
    inst = instant("-3066-11-22", "06:00", p)
    assert inst.timescale == "lmt"


def test_local_parts_round_trips_the_input():
    p = place(40.5, -74.4, "America/New_York")
    inst = instant("2019-02-14", "19:30", p)
    y, m, d, hour = local_parts(inst)
    assert (y, m, d) == (2019, 2, 14)
    assert hour == pytest.approx(19.5, abs=1e-6)


def test_real_place_carries_its_own_zone(edison):
    inst = instant("2019-02-14", "19:30", edison)
    assert inst.utc_offset == pytest.approx(-5.0)
    assert "America/New_York" in inst.tz_label


# --------------------------------------------------------------------------
# ΔT
# --------------------------------------------------------------------------

def test_delta_t_is_tiny_now_and_enormous_in_the_bronze_age(edison):
    modern = instant("2019-02-14", "19:30", edison)
    assert 60.0 < modern.delta_t < 80.0

    ancient = instant("-3066-11-22", "06:00",
                      geo.resolve("kurukshetra"), calendar="julian")
    # Roughly 21 hours at 3067 BCE: enough to change what is rising by most of a
    # rotation, and not nearly enough to move a planet out of its nakshatra.
    assert 18 * 3600 < ancient.delta_t < 24 * 3600


def test_delta_t_sigma_interpolates_and_flags_extrapolation():
    sigma_2000, extrapolated = delta_t_sigma(2000)
    assert sigma_2000 == pytest.approx(0.0)
    assert not extrapolated

    sigma_0, extrapolated = delta_t_sigma(0)
    assert sigma_0 == pytest.approx(200.0)
    assert not extrapolated

    # Between the -720 anchor (400 s) and -1000 (624 s).
    sigma_mid, _ = delta_t_sigma(-860)
    assert 400.0 < sigma_mid < 624.0

    sigma_ancient, extrapolated = delta_t_sigma(-3000)
    assert extrapolated
    assert sigma_ancient > 1000.0


def test_sigma_is_printed_only_for_ancient_renders(edison, kurukshetra):
    assert not instant("2019-02-14", "19:30", edison).show_sigma
    assert instant("-3066-11-22", "06:00", kurukshetra,
                   calendar="julian").show_sigma


def test_delta_t_sigma_is_monotonic_going_back():
    """Nobody's uncertainty about the Earth's rotation shrinks with age."""
    years = [-6000, -5000, -3000, -1000, -720, 0, 1000, 1600, 1900, 2000]
    sigmas = [delta_t_sigma(y)[0] for y in years]
    assert sigmas == sorted(sigmas, reverse=True)


# --------------------------------------------------------------------------
# shifting an instant
# --------------------------------------------------------------------------

def test_with_offset_minutes_moves_exactly(wedding_instant: Instant):
    shifted = wedding_instant.with_offset_minutes(30)
    assert shifted.jd_ut - wedding_instant.jd_ut == pytest.approx(30 / 1440)
    assert shifted.calendar == wedding_instant.calendar
    assert shifted.utc_offset == wedding_instant.utc_offset
