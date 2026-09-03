"""Place search. The reason this uses cities500 rather than cities15000.

Indian birthplaces are usually towns nobody outside the district has heard of.
A calculator that cannot find them sends the buyer to the nearest big city and
silently moves their Lagna, so the size of the gazetteer is a correctness
property, not a nicety.
"""

from __future__ import annotations

import pytest

from skurious import geo
from skurious.errors import PlaceNotFound


def test_the_gazetteer_is_the_big_one():
    con = geo._db()
    (count,) = con.execute("SELECT count(*) FROM places").fetchone()
    assert count > 190_000, "this looks like cities15000, not cities500"


def test_search_ranks_by_population():
    results = geo.search("Edison", limit=5)
    assert results[0].name == "Edison"
    assert results[0].admin == "New Jersey"
    assert [p.population for p in results] == sorted(
        (p.population for p in results), reverse=True)


def test_small_indian_towns_are_present():
    """The exact case cities15000 would drop.

    Nearly half of the Indian rows are places under fifteen thousand people.
    Those are birthplaces, and a gazetteer without them sends the buyer to the
    nearest city and moves their Lagna by minutes of sidereal time.
    """
    for town in ("Nathdwara", "Abhaneri", "Thanesar"):
        assert geo.search(town, limit=3), f"{town} is missing from the gazetteer"

    con = geo._db()
    (small,) = con.execute(
        "SELECT count(*) FROM places WHERE cc = 'IN' AND population < 15000"
    ).fetchone()
    assert small > 3000


@pytest.mark.parametrize("typed, expected", [
    ("Bombay", "Mumbai"),
    ("Calcutta", "Kolkata"),
    ("Bangalore", "Bengaluru"),
    ("बंगलौर", "Bengaluru"),
])
def test_places_answer_to_the_name_the_buyer_knows(typed, expected):
    """A grandmother in New Jersey types Bombay, and a buyer types Devanagari.

    GeoNames prefers the current official name; the family uses the old one.
    Indexing every alternate name is what closes that gap.
    """
    assert geo.search(typed, limit=1)[0].name == expected


def test_a_claims_observer_need_not_be_in_the_gazetteer():
    """Kurukshetra is filed under Thānesar, and a claim still resolves it.

    That is what data/geo/places.yaml is for: an observer a claim names is part
    of the claim's citation, not a lookup that can quietly return a neighbour.
    """
    assert not geo.search("Kurukshetra", limit=1)
    place = geo.resolve("kurukshetra")
    assert place.name == "Kurukshetra"
    assert place.tz == "LMT"


def test_places_carry_a_timezone_not_an_offset():
    place = geo.by_id(5097529)
    assert place.tz == "America/New_York"
    assert place.label == "Edison, New Jersey, United States"
    assert "40°31′N" in place.coords and "74°24′W" in place.coords


def test_resolve_accepts_an_id_a_name_and_coordinates():
    assert geo.resolve("5097529").name == "Edison"
    assert geo.resolve(5097529).name == "Edison"
    assert geo.resolve("kurukshetra").name == "Kurukshetra"
    assert geo.resolve("Edison").admin == "New Jersey"


def test_bare_coordinates_default_to_local_mean_time():
    """A latitude and longitude does not say whose clock anybody was on."""
    place = geo.resolve("29.97,76.88")
    assert place.lat == pytest.approx(29.97)
    assert place.tz == "LMT"
    assert geo.resolve("29.97,76.88@Asia/Kolkata").tz == "Asia/Kolkata"


def test_named_observers_carry_their_own_citation():
    observers = geo.named_observers()
    assert {"kurukshetra", "jerusalem", "babylon", "ujjain"} <= set(observers)
    assert all(p.tz == "LMT" for p in observers.values())


def test_nonsense_is_refused():
    with pytest.raises(PlaceNotFound):
        geo.resolve("qqzzxx not a place")
    with pytest.raises(PlaceNotFound):
        geo.by_id(-1)


def test_punctuation_in_a_query_does_not_break_fts():
    assert geo.search("St. Louis", limit=3)
    assert geo.search("Coeur d'Alene", limit=3)
