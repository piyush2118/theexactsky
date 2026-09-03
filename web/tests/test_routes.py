"""The routes, end to end. Cards are drawn for real; there is no mock ephemeris.

The tests that matter here are not "does it return 200". They are: does a link
carry no name, does a damaged link refuse rather than draw a wrong sky, and does
the OpenGraph image resolve to something WhatsApp can actually fetch — because
that link preview is the entire growth loop the plan is built around.
"""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

TMP = tempfile.mkdtemp(prefix="skurious-test-")
os.environ.setdefault("SKURIOUS_CACHE", f"{TMP}/cards")
os.environ.setdefault("SKURIOUS_DB", f"{TMP}/test.sqlite")

from app.main import app, initials  # noqa: E402

EDISON = 5097529


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def token(client) -> str:
    r = client.post("/sky", data={"date": "2019-02-14", "time": "19:30",
                                  "place_id": str(EDISON)},
                    follow_redirects=False)
    assert r.status_code == 303
    return r.headers["location"].split("?")[0].removeprefix("/s/")


def test_healthz(client):
    body = client.get("/healthz").json()
    assert body["ok"] and body["resvg"]


def test_the_form_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Draw this sky" in r.text


# --------------------------------------------------------------------------
# typeahead
# --------------------------------------------------------------------------

def test_typeahead_answers_to_the_name_the_family_uses(client):
    assert client.get("/geo", params={"q": "Bombay"}).json()[0]["label"].startswith("Mumbai")
    assert client.get("/geo", params={"q": "बंगलौर"}).json()[0]["label"].startswith("Bengaluru")


def test_typeahead_returns_the_timezone_so_the_form_can_show_it(client):
    row = client.get("/geo", params={"q": "Edison"}).json()[0]
    assert row["tz"] == "America/New_York"
    assert row["id"] == EDISON


def test_typeahead_ignores_short_and_hostile_queries(client):
    assert client.get("/geo", params={"q": "a"}).json() == []
    # FTS5 syntax in the query must not reach the query planner as syntax.
    for junk in ('" OR "', "*", "NEAR/", "^"):
        assert client.get("/geo", params={"q": junk}).status_code == 200


# --------------------------------------------------------------------------
# making a card
# --------------------------------------------------------------------------

def test_a_valid_form_redirects_to_a_link_that_carries_the_inputs(client, token):
    from skurious.token import decode

    subjects, _ruleset = decode(token)
    assert len(subjects) == 1
    assert subjects[0].place_id == EDISON


def test_names_travel_in_the_query_not_the_link(client):
    """The privacy property the plan asks for, checked at the HTTP layer."""
    r = client.post("/sky", data={"date": "2019-02-14", "time": "19:30",
                                  "place_id": str(EDISON),
                                  "names": "Priya, Arjun"},
                    follow_redirects=False)
    location = r.headers["location"]
    path, _, query = location.partition("?")
    assert "Priya" not in path and "Arjun" not in path
    assert "Priya" in query


def test_an_ambiguous_birth_time_is_explained_not_guessed(client):
    """01:30 on the autumn fold happens twice; the form must say so."""
    r = client.post("/sky", data={"date": "2019-11-03", "time": "01:30",
                                  "place_id": str(EDISON)},
                    follow_redirects=False)
    assert r.status_code == 400
    assert "twice" in r.text


def test_a_nonexistent_birth_time_is_refused(client):
    r = client.post("/sky", data={"date": "2019-03-10", "time": "02:30",
                                  "place_id": str(EDISON)},
                    follow_redirects=False)
    assert r.status_code == 400
    assert "does not exist" in r.text


def test_an_unknown_place_is_refused(client):
    r = client.post("/sky", data={"date": "2019-02-14", "time": "19:30",
                                  "place_id": "999999999"},
                    follow_redirects=False)
    assert r.status_code == 400


# --------------------------------------------------------------------------
# the result page
# --------------------------------------------------------------------------

def test_the_result_page_shows_the_computed_facts(client, token):
    r = client.get(f"/s/{token}")
    assert r.status_code == 200
    assert "Mṛgaśīrṣa" in r.text          # the Moon's nakshatra that night
    assert "Edison, New Jersey" in r.text
    assert "waxing gibbous" in r.text


def test_the_result_page_prints_the_scheme(client, token):
    """A page that will not say how it computed a number cannot be checked."""
    r = client.get(f"/s/{token}")
    assert "Lahiri" in r.text and "equal nakshatras" in r.text


def test_opengraph_tags_point_at_a_real_image(client, token):
    """The WhatsApp link preview is the growth loop; a broken og:image kills it."""
    import re

    page = client.get(f"/s/{token}?names=Priya,%20Arjun").text
    url = re.search(r'property="og:image" content="([^"]+)"', page).group(1)
    assert url.startswith("http")
    assert 'og:image:width" content="1080"' in page

    card = client.get(url.split("/", 3)[-1].replace("//", "/"))
    assert card.status_code == 200
    assert card.headers["content-type"] == "image/png"


def test_a_damaged_link_refuses_rather_than_drawing_a_wrong_sky(client, token):
    bad = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")
    r = client.get(f"/s/{bad}")
    assert r.status_code == 404
    assert "damaged" in r.text or "not a card" in r.text or "malformed" in r.text


# --------------------------------------------------------------------------
# the card
# --------------------------------------------------------------------------

def test_the_card_is_the_size_whatsapp_wants(client, token):
    import io

    from PIL import Image

    r = client.get(f"/c/{token}.png")
    assert r.status_code == 200
    with Image.open(io.BytesIO(r.content)) as im:
        assert im.size == (1080, 1350)


def test_the_card_is_cached_immutably(client, token):
    r = client.get(f"/c/{token}.png")
    assert "immutable" in r.headers["cache-control"]


def test_the_same_link_gives_the_same_bytes(client, token):
    """Determinism, through the whole stack. A card can be redrawn years later."""
    a = client.get(f"/c/{token}.svg").content
    b = client.get(f"/c/{token}.svg").content
    assert a == b


def test_initials_never_become_names():
    assert initials("Priya, Arjun") == "PA"
    assert initials("Anne-Marie, Arjun") == "AA"
    assert initials("") == ""
    assert initials("a, b, c, d, e, f") == "ABCD"     # capped
    assert initials("!!!, ???") == ""


def test_a_card_with_initials_still_carries_no_name(client, token):
    r = client.get(f"/c/{token}.svg", params={"i": "PA"})
    assert r.status_code == 200
    assert "Priya" not in r.text and "Arjun" not in r.text
    assert "P" in r.text


# --------------------------------------------------------------------------
# claims and events
# --------------------------------------------------------------------------

def test_the_claims_page_evaluates_live_and_reaches_no_verdict(client):
    r = client.get("/claims")
    assert r.status_code == 200
    assert "1 of 3 constraints met" in r.text          # the 3067 BCE panel
    assert "Citation unverified" in r.text
    assert "reaches no verdict" in r.text


def test_the_beacon_records_only_known_event_types(client, token):
    import sqlite3

    assert client.post("/e", data={"type": "share_click", "token": token}).status_code == 204
    assert client.post("/e", data={"type": "nonsense"}).status_code == 204
    with sqlite3.connect(os.environ["SKURIOUS_DB"]) as db:
        kinds = {r[0] for r in db.execute("SELECT DISTINCT type FROM events")}
    assert "share_click" in kinds
    assert "nonsense" not in kinds


def test_events_never_store_the_link_itself(client, token):
    """A token is the birth details; an analytics table must not become a store."""
    import sqlite3

    client.get(f"/s/{token}")
    with sqlite3.connect(os.environ["SKURIOUS_DB"]) as db:
        rows = db.execute("SELECT token_hash FROM events "
                          "WHERE token_hash IS NOT NULL").fetchall()
    assert rows
    assert all(r[0] != token for r in rows)
    assert all(len(r[0]) == 16 for r in rows)
