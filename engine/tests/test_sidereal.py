"""Sidereal arithmetic and the rule tables.

The table tests are structural: the lord cycle, the nadi cycle and the gana
counts are properties the tradition guarantees, so a typo in one of 27 YAML rows
shows up here rather than on somebody's print.
"""

from __future__ import annotations

import pytest

from skurious.errors import SkuriousError
from skurious.sidereal import (NAKSHATRA_ARC, PADA_ARC, Scheme, ayanamsa,
                               degrees_in_nakshatra, karana, nakshatra,
                               nakshatra_by_name, nakshatra_centre,
                               nakshatra_index, nakshatra_table,
                               naming_syllable, norm360, pada, rasi_index,
                               rasi_table, signed_delta, tithi, yoga)

LORDS = ["ketu", "venus", "sun", "moon", "mars", "rahu", "jupiter", "saturn",
         "mercury"]
# Nadi runs as a boustrophedon over triples: Adi-Madhya-Antya forward, then the
# same three backward, nine times. It is *not* a repeating period-9 cycle, and
# assuming it is puts Magha in the wrong nadi.
NADI_TRIPLE = ["adi", "madhya", "antya"]


# --------------------------------------------------------------------------
# boundaries
# --------------------------------------------------------------------------

def test_nakshatra_boundaries_are_exact():
    for i in range(27):
        start = i * NAKSHATRA_ARC
        assert nakshatra_index(start) == i
        assert nakshatra_index(start + NAKSHATRA_ARC - 1e-9) == i
    assert nakshatra_index(360.0 - 1e-9) == 26


def test_a_longitude_exactly_on_a_boundary_belongs_to_the_later_nakshatra():
    """Half-open intervals, consistently: [start, end). No longitude is homeless."""
    assert nakshatra_index(NAKSHATRA_ARC) == 1
    assert nakshatra_index(NAKSHATRA_ARC - 1e-12) == 0


def test_pada_cycles_four_times_per_nakshatra():
    for i in range(108):
        lon = i * PADA_ARC + PADA_ARC / 2
        assert pada(lon) == i % 4 + 1
        assert nakshatra_index(lon) == i // 4


def test_longitudes_wrap_at_360():
    assert nakshatra_index(370.0) == nakshatra_index(10.0)
    assert pada(-1.0) == pada(359.0)
    assert rasi_index(-30.0) == rasi_index(330.0)
    assert norm360(-0.5) == pytest.approx(359.5)


def test_rasi_boundaries():
    for i in range(12):
        assert rasi_index(i * 30.0) == i
        assert rasi_index(i * 30.0 + 29.999) == i


def test_signed_delta_takes_the_short_way_round():
    assert signed_delta(350.0, 10.0) == pytest.approx(20.0)
    assert signed_delta(10.0, 350.0) == pytest.approx(-20.0)
    assert signed_delta(0.0, 180.0) == pytest.approx(-180.0)   # [-180, 180)


# --------------------------------------------------------------------------
# the tables
# --------------------------------------------------------------------------

def test_twenty_seven_nakshatras_and_twelve_rasis():
    assert len(nakshatra_table()) == 27
    assert len(rasi_table()) == 12
    assert [r["n"] for r in nakshatra_table()] == list(range(1, 28))
    assert [r["n"] for r in rasi_table()] == list(range(1, 13))


def test_lord_cycle_repeats_three_times():
    assert [r["lord"] for r in nakshatra_table()] == LORDS * 3


def test_nadi_zigzags_over_triples():
    expected = []
    for triple in range(9):
        expected += (NADI_TRIPLE if triple % 2 == 0 else NADI_TRIPLE[::-1])
    assert [r["nadi"] for r in nakshatra_table()] == expected
    # Nine of each, which is what makes the Nadi koota's 8 points all-or-nothing.
    assert all(expected.count(n) == 9 for n in NADI_TRIPLE)


def test_gana_is_nine_of_each():
    counts: dict[str, int] = {}
    for row in nakshatra_table():
        counts[row["gana"]] = counts.get(row["gana"], 0) + 1
    assert counts == {"deva": 9, "manushya": 9, "rakshasa": 9}


def test_yoni_has_fourteen_animals_paired_by_sex():
    animals = {r["yoni"] for r in nakshatra_table()}
    assert len(animals) == 14
    for row in nakshatra_table():
        assert row["yoni_sex"] in ("m", "f")


def test_every_nakshatra_has_four_syllables_in_both_scripts():
    for row in nakshatra_table():
        assert len(row["syllables"]) == 4
        assert len(row["syllables_iast"]) == 4
        assert all(s.strip() for s in row["syllables"])


def test_varna_follows_the_element():
    expected = {"fire": "kshatriya", "earth": "vaishya", "air": "shudra",
                "water": "brahmana"}
    for row in rasi_table():
        assert row["varna"] == expected[row["element"]]


def test_naming_syllable_matches_the_pada():
    row = nakshatra_table()[0]                     # Aśvinī
    for p in range(4):
        lon = p * PADA_ARC + PADA_ARC / 2
        deva, iast = naming_syllable(lon)
        assert deva == row["syllables"][p]
        assert iast == row["syllables_iast"][p]


def test_nakshatra_lookup_tolerates_transliteration():
    assert nakshatra_by_name("rohini") == 3
    assert nakshatra_by_name("Rohiṇī") == 3
    assert nakshatra_by_name("jyeshtha") == 17
    assert nakshatra_by_name("Jyeṣṭhā") == 17
    assert nakshatra_by_name("मृगशीर्ष") == 4
    with pytest.raises(SkuriousError):
        nakshatra_by_name("not-a-nakshatra")


def test_nakshatra_centre_is_the_midpoint():
    assert nakshatra_centre(0) == pytest.approx(NAKSHATRA_ARC / 2)
    assert nakshatra_centre(3) == pytest.approx(3 * NAKSHATRA_ARC
                                                + NAKSHATRA_ARC / 2)


# --------------------------------------------------------------------------
# panchanga arithmetic
# --------------------------------------------------------------------------

def test_tithi_yoga_karana_ranges():
    for sun in range(0, 360, 17):
        for moon in range(0, 360, 23):
            assert 1 <= tithi(sun, moon) <= 30
            assert 1 <= yoga(sun, moon) <= 27
            assert 1 <= karana(sun, moon) <= 60


def test_new_moon_is_tithi_one_and_full_moon_is_sixteen():
    assert tithi(100.0, 100.0) == 1
    assert tithi(100.0, 280.0) == 16


def test_karana_is_half_a_tithi():
    for elongation in (0.5, 30.0, 179.0, 359.0):
        assert karana(0.0, elongation) in (2 * tithi(0.0, elongation) - 1,
                                           2 * tithi(0.0, elongation))


# --------------------------------------------------------------------------
# schemes
# --------------------------------------------------------------------------

def test_lahiri_ayanamsa_at_j2000():
    """The plan's own acceptance gate: 23°51′ ± 1′ at J2000."""
    value = ayanamsa(2451545.0, Scheme())
    assert value == pytest.approx(23.0 + 51.0 / 60.0, abs=1.0 / 60.0)


def test_ayanamsa_grows_with_precession():
    early = ayanamsa(2451545.0 - 36525.0, Scheme())      # J1900
    late = ayanamsa(2451545.0 + 36525.0, Scheme())       # J2100
    assert late - early == pytest.approx(200 * 50.29 / 3600.0, rel=0.02)


def test_schemes_differ_from_each_other():
    lahiri = ayanamsa(2451545.0, Scheme(ayanamsa="lahiri"))
    raman = ayanamsa(2451545.0, Scheme(ayanamsa="raman"))
    kp = ayanamsa(2451545.0, Scheme(ayanamsa="krishnamurti"))
    assert lahiri != raman != kp
    assert abs(lahiri - raman) > 0.3        # Raman is about 1° behind Lahiri


def test_unknown_scheme_values_are_refused_not_defaulted():
    with pytest.raises(SkuriousError):
        Scheme(ayanamsa="made-up")
    with pytest.raises(SkuriousError):
        Scheme(nakshatra_boundaries="unequal")
    with pytest.raises(SkuriousError):
        Scheme(house_system="koch")
    with pytest.raises(SkuriousError):
        Scheme(node="either")


def test_scheme_id_names_every_choice():
    ident = Scheme().id
    for part in ("lahiri", "equal", "whole_sign", "mean-node"):
        assert part in ident


def test_degrees_in_nakshatra_is_the_offset_from_its_start():
    assert degrees_in_nakshatra(NAKSHATRA_ARC + 3.0) == pytest.approx(3.0)
    assert nakshatra(NAKSHATRA_ARC + 3.0)["iast"] == "Bharaṇī"
