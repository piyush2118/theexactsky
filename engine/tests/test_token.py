"""Card links. These carry the inputs, so a wrong one must refuse, not guess."""

from __future__ import annotations

import pytest

from skurious import geo
from skurious.errors import SkuriousError
from skurious.time import instant
from skurious.token import (EPOCH_JD, FLAG_APPROX_A, Subject, decode, encode)


def test_a_single_subject_round_trips(edison):
    inst = instant("2019-02-14", "19:30", edison)
    subject = Subject.from_instant(inst, edison)
    token = encode([subject])
    back, ruleset = decode(token)
    assert back == [subject]
    assert ruleset == 0
    assert back[0].jd_ut == pytest.approx(inst.jd_ut, abs=1 / 1440)


def test_two_subjects_round_trip(edison):
    a = Subject.from_instant(instant("1994-05-03", "05:40", edison), edison, True)
    b = Subject.from_instant(instant("1992-11-08", "14:05", edison), edison)
    token = encode([a, b], ruleset=3)
    back, ruleset = decode(token)
    assert back == [a, b]
    assert ruleset == 3
    assert back[0].approximate and not back[1].approximate


def test_link_lengths_match_the_plan(edison):
    """The plan budgets 20 bytes and 27 characters for a two-person card."""
    one = Subject.from_instant(instant("2019-02-14", "19:30", edison), edison)
    assert len(encode([one])) == 16          # 12 bytes, no base64 padding
    assert len(encode([one, one])) == 27     # 20 bytes, one '=' stripped


def test_a_damaged_link_is_refused_not_drawn(edison):
    """A transposed character must fail, not render a plausible wrong sky."""
    token = encode([Subject.from_instant(
        instant("2019-02-14", "19:30", edison), edison)])
    swapped = token[:6] + token[7] + token[6] + token[8:]
    assert swapped != token
    with pytest.raises(SkuriousError, match="damaged"):
        decode(swapped)


@pytest.mark.parametrize("count", [1, 2])
def test_every_single_character_corruption_is_caught(edison, count):
    """Every one-character slip must be refused, for both link lengths.

    Not every character change is a corruption: base64 leaves spare low bits in
    its final character when the payload is not a multiple of three, so several
    spellings decode to identical bytes. Those are the same link, not a damaged
    one, so this compares decoded bytes rather than assuming.
    """
    import base64 as b64
    import string

    one = Subject.from_instant(instant("2019-02-14", "19:30", edison), edison)
    token = encode([one] * count)

    def raw(t: str) -> bytes | None:
        try:
            return b64.urlsafe_b64decode(t + "=" * (-len(t) % 4))
        except Exception:
            return None

    original = raw(token)
    alphabet = string.ascii_letters + string.digits + "-_"
    missed = []
    for i in range(len(token)):
        for ch in alphabet:
            if ch == token[i]:
                continue
            candidate = token[:i] + ch + token[i + 1:]
            if raw(candidate) == original:
                continue            # a different spelling of the same bytes
            try:
                decode(candidate)
            except SkuriousError:
                continue
            missed.append(candidate)
    assert not missed, f"{len(missed)} corrupted links decoded anyway: {missed[:3]}"


def test_rubbish_is_refused():
    for junk in ("", "hello", "!!!!", "A", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"):
        with pytest.raises(SkuriousError):
            decode(junk)


def test_a_link_carries_no_name(edison):
    """The privacy property, asserted rather than assumed.

    A forwarded card shows a time and a place. Names are typed on the form and
    drawn into the picture; they never enter the link, so a link that leaks
    cannot identify anybody.
    """
    token = encode([Subject.from_instant(
        instant("2019-02-14", "19:30", edison), edison)])
    subjects, _ = decode(token)
    assert not hasattr(subjects[0], "name")
    assert set(vars(subjects[0])) == {"minutes", "place_id", "approximate"}


def test_places_without_a_geonames_id_are_refused():
    """Bare coordinates have no id, and silently dropping them loses the place."""
    manual = geo.resolve("29.97,76.88")
    with pytest.raises(SkuriousError, match="GeoNames id"):
        Subject.from_instant(instant("2019-02-14", "19:30", manual), manual)


def test_dates_outside_the_link_range_are_refused(kurukshetra):
    ancient = instant("-3066-11-22", "06:00", kurukshetra, calendar="julian")
    with pytest.raises(SkuriousError, match="outside the range"):
        Subject.from_instant(ancient, kurukshetra)


def test_the_epoch_is_1900(edison):
    subject = Subject(minutes=0, place_id=1)
    assert subject.jd_ut == EPOCH_JD


def test_tokens_are_url_safe(edison):
    """No padding, no slashes: the link goes in a WhatsApp message unescaped."""
    for date in ("1950-01-01", "2019-02-14", "2044-12-31"):
        token = encode([Subject.from_instant(
            instant(date, "12:00", edison), edison)])
        assert "=" not in token and "/" not in token and "+" not in token
