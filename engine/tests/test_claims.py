"""Claims, eclipse search and the conjunction finder.

Two of these are regression tests against events anybody can look up: the
Jupiter–Saturn conjunction of 21 December 2020, and the triple conjunction of
7 BCE. The finder is given a two-year window and no hint about where the minima
are, because a finder that is told the answer proves nothing about the claim it
is meant to check.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import swisseph as swe

from skurious import claims, geo
from skurious.errors import ClaimError
from skurious.sidereal import Scheme
from skurious.time import instant

MAHABHARATA = Path("data/claims/mahabharata")


@pytest.fixture(scope="module")
def mahabharata() -> list[claims.Claim]:
    return claims.load_dir(MAHABHARATA)


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def test_the_six_claims_load(mahabharata):
    assert len(mahabharata) == 6
    assert {c.id for c in mahabharata} == {
        "vartak-5561", "traditional-3138", "kaliyuga-3105", "achar-3067",
        "proposal-1478", "proposal-1198"}
    for claim in mahabharata:
        assert claim.source.strip()
        assert claim.observer == "kurukshetra"
        assert claim.calendar == "julian"
        assert len(claim.constraints) == 3


def test_every_claim_declares_whether_its_citation_was_checked(mahabharata):
    """A plate that mixes checked and unchecked citations silently is worthless."""
    for claim in mahabharata:
        assert claim.citation_status in ("verified", "unverified")
        assert claim.date_status in ("stated", "placeholder")
    verified = [c for c in mahabharata if c.citation_status == "verified"]
    assert {c.id for c in verified} == {"vartak-5561", "achar-3067"}


def test_an_unimplemented_constraint_type_is_refused(tmp_path):
    doc = tmp_path / "bad.yaml"
    doc.write_text(
        "id: bad\nsource: nowhere\nobserver: kurukshetra\n"
        "events: {e: {date: '-3066-11-22'}}\n"
        "constraints: [{id: c1, type: heliacal_rising, at: e}]\n")
    with pytest.raises(ClaimError, match="heliacal_rising"):
        claims.load(doc)


def test_a_constraint_pointing_at_no_event_is_refused(tmp_path):
    doc = tmp_path / "bad.yaml"
    doc.write_text(
        "id: bad\nsource: nowhere\nobserver: kurukshetra\n"
        "events: {e: {date: '-3066-11-22'}}\n"
        "constraints: [{id: c1, type: retrograde, body: mars, at: nope}]\n")
    with pytest.raises(ClaimError):
        claims.evaluate(claims.load(doc))


# --------------------------------------------------------------------------
# evaluation
# --------------------------------------------------------------------------

def test_sunrise_events_land_on_the_stated_date(mahabharata):
    """Resolving 'sunrise' must not slide the event onto the neighbouring day."""
    for claim in mahabharata:
        result = claims.evaluate(claim)
        stated = claim.events["war_day1"].date
        assert result.instants["war_day1"].source_local_iso.startswith(stated)


def test_achar_3067_puts_saturn_in_rohini(mahabharata):
    """Reproducing the central astronomical claim of the 3067 BCE proposal.

    This is the load-bearing test in the whole suite: it exercises the Julian
    calendar, astronomical year numbering, ΔT of about 21 hours, Local Mean
    Time, sunrise at a named observer, the Lahiri ayanamsa five thousand years
    out, and the nakshatra tables — and it lands on a published result computed
    by somebody else with different software.
    """
    claim = next(c for c in mahabharata if c.id == "achar-3067")
    saturn = next(r for r in claims.evaluate(claim).results if r.id == "c1")
    assert saturn.passes
    assert saturn.evidence["nakshatra"] == "Rohiṇī"
    assert abs(saturn.evidence["offset_from_centre_deg"]) < 6.67


def test_the_other_five_dates_do_not_put_saturn_in_rohini(mahabharata):
    """The plate would say nothing at all if every date passed."""
    others = [c for c in mahabharata if c.id != "achar-3067"]
    for claim in others:
        saturn = next(r for r in claims.evaluate(claim).results if r.id == "c1")
        assert not saturn.passes


def test_results_report_both_what_was_asked_and_what_happened(mahabharata):
    result = claims.evaluate(mahabharata[0])
    for r in result.results:
        assert r.stated and r.computed
        assert r.evidence
    assert result.total == 3
    assert "of 3 constraints met" in result.summary


def test_a_claim_can_be_re_run_under_another_ayanamsa(mahabharata):
    """The answer to 'scholars disagree about the ayanamsa' is a table, not a side."""
    claim = next(c for c in mahabharata if c.id == "achar-3067")
    lahiri = claims.evaluate(claim, Scheme(ayanamsa="lahiri", calendar="julian"))
    raman = claims.evaluate(claim, Scheme(ayanamsa="raman", calendar="julian"))
    a = next(r for r in lahiri.results if r.id == "c1")
    b = next(r for r in raman.results if r.id == "c1")
    assert a.evidence["lon_sid"] != b.evidence["lon_sid"]
    assert lahiri.scheme.id != raman.scheme.id


def test_nakshatra_tolerance_is_measured_from_the_centre(tmp_path):
    """The default 6.67° is exactly the nakshatra; widening it lets neighbours in."""
    body = ("id: t\nsource: test\ncalendar: julian\nobserver: kurukshetra\n"
            "events: {{e: {{date: '-3066-11-22', time: '06:00'}}}}\n"
            "constraints: [{{id: c1, type: planet_in_nakshatra, body: saturn, "
            "nakshatra: krittika, at: e, tol_deg: {tol}}}]\n")
    tight = tmp_path / "tight.yaml"
    tight.write_text(body.format(tol=6.67))
    wide = tmp_path / "wide.yaml"
    wide.write_text(body.format(tol=20.0))
    assert not claims.evaluate(claims.load(tight)).results[0].passes
    assert claims.evaluate(claims.load(wide)).results[0].passes


# --------------------------------------------------------------------------
# eclipse search
# --------------------------------------------------------------------------

def test_finds_the_total_solar_eclipse_of_august_2017(edison):
    start = instant("2017-08-01", "00:00", edison).jd_ut
    end = instant("2017-09-01", "00:00", edison).jd_ut
    found = claims.find_eclipses(start, end, "solar")
    assert len(found) == 1
    y, m, d, _h = swe.revjul(found[0].jd_max, swe.GREG_CAL)
    assert (y, m, d) == (2017, 8, 21)
    assert "total" in found[0].type_name


def test_finds_the_total_lunar_eclipse_of_january_2019(edison):
    start = instant("2019-01-01", "00:00", edison).jd_ut
    end = instant("2019-02-01", "00:00", edison).jd_ut
    found = claims.find_eclipses(start, end, "lunar")
    assert len(found) == 1
    y, m, d, _h = swe.revjul(found[0].jd_max, swe.GREG_CAL)
    assert (y, m, d) == (2019, 1, 21)


def test_eclipse_search_is_bounded_by_its_window(edison):
    start = instant("2017-08-01", "00:00", edison).jd_ut
    end = instant("2018-08-01", "00:00", edison).jd_ut
    for e in claims.find_eclipses(start, end, "solar"):
        assert start <= e.jd_max <= end


# --------------------------------------------------------------------------
# the conjunction finder
# --------------------------------------------------------------------------

def test_the_great_conjunction_of_2020(edison):
    """21 December 2020: Jupiter and Saturn about a tenth of a degree apart."""
    start = instant("2020-10-01", "00:00", edison).jd_ut
    end = instant("2021-03-01", "00:00", edison).jd_ut
    found = claims.find_conjunctions("jupiter", "saturn", start, end, max_sep=2.0)
    assert len(found) == 1
    y, m, d, _h = swe.revjul(found[0].jd, swe.GREG_CAL)
    assert (y, m, d) == (2020, 12, 21)
    assert found[0].separation == pytest.approx(0.10, abs=0.02)


def test_the_finder_discovers_the_7_bce_triple_conjunction():
    """Three minima in one year, found from a two-year window and nothing else.

    These are the dates the Bethlehem argument turns on. The finder is not told
    that there are three, or when; it is told two body names and a range.
    """
    jerusalem = geo.resolve("jerusalem")
    start = instant("-0007-01-01", "00:00", jerusalem, calendar="julian",
                    timescale="lmt").jd_ut
    end = instant("-0005-12-31", "00:00", jerusalem, calendar="julian",
                  timescale="lmt").jd_ut
    found = claims.find_conjunctions("jupiter", "saturn", start, end, max_sep=2.0)

    assert len(found) == 3
    dates = [swe.revjul(k.jd, swe.JUL_CAL)[:3] for k in found]
    assert dates == [(-6, 5, 29), (-6, 9, 30), (-6, 12, 5)]   # 7 BCE
    assert all(k.separation < 1.1 for k in found)
    # All three happen in the same part of the sky, which is what made them read
    # as one long event.
    assert max(k.lon_a for k in found) - min(k.lon_a for k in found) < 10.0


def test_the_finder_returns_nothing_when_nothing_is_close(edison):
    start = instant("2015-01-01", "00:00", edison).jd_ut
    end = instant("2015-06-01", "00:00", edison).jd_ut
    assert claims.find_conjunctions("jupiter", "saturn", start, end,
                                    max_sep=0.5) == []
