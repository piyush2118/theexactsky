"""Evaluate a claim's constraints against the sky, and say nothing else.

Each constraint returns what the claim stated, what the sky did, and a boolean.
Nothing here decides whether a claim is *true*: a claim can meet every
constraint it wrote for itself and still be wrong, because it chose the
constraints. That is exactly the argument the plate is meant to let a reader
have, and the code stays out of it.
"""

from __future__ import annotations

import swisseph as swe

from .. import ephem, geo
from ..errors import ClaimError
from ..sidereal import (NAKSHATRA_ARC, Scheme, nakshatra_by_name,
                        nakshatra_centre, nakshatra_table, signed_delta)
from ..time import Instant, instant, instant_from_jd
from .model import Claim, ClaimResult, Constraint, ConstraintResult, Event
from .search import find_conjunctions, find_eclipses


def observer_place(claim: Claim):
    return geo.resolve(claim.observer)


def resolve_event(claim: Claim, event: Event, place) -> Instant:
    """A named event to an `Instant`, resolving 'sunrise' at the observer.

    Claims usually state a date and leave the time to the reader; "at sunrise"
    is the convention, and it is the observer's own sunrise, not a timezone's.
    """
    if event.time.lower() in ("sunrise", "sunset"):
        midnight = instant(event.date, "00:00", place, calendar=claim.calendar,
                           timescale="lmt")
        rise, sett = ephem.rise_set(midnight, place, "sun")
        jd = rise if event.time.lower() == "sunrise" else sett
        if jd is None:
            raise ClaimError(
                f"the Sun neither rises nor sets at {place.label} on "
                f"{event.date}; give {event.name} an explicit time")
        return instant_from_jd(jd, place, calendar=claim.calendar,
                               timescale="lmt")
    return instant(event.date, event.time, place, calendar=claim.calendar,
                   timescale="lmt")


def evaluate(claim: Claim, scheme: Scheme | None = None) -> ClaimResult:
    """Run every constraint. A constraint that cannot run is a failure, loudly."""
    scheme = scheme or claim.scheme
    place = observer_place(claim)
    instants = {name: resolve_event(claim, ev, place)
                for name, ev in claim.events.items()}

    results = [_evaluate_one(claim, c, scheme, place, instants)
               for c in claim.constraints]
    return ClaimResult(claim=claim, scheme=scheme, results=results,
                       instants=instants)


def _evaluate_one(claim: Claim, c: Constraint, scheme: Scheme, place,
                  instants: dict[str, Instant]) -> ConstraintResult:
    inst = instants.get(c.at)
    if inst is None:
        raise ClaimError(f"constraint {c.id} refers to unknown event {c.at!r}")
    handler = {
        "planet_in_nakshatra": _planet_in_nakshatra,
        "retrograde": _retrograde,
        "eclipse_pair": _eclipse_pair,
        "conjunction": _conjunction,
    }[c.type]
    return handler(c, scheme, place, inst)


# --------------------------------------------------------------------------
# constraint types
# --------------------------------------------------------------------------

def _nakshatra_window(name: str, tol_deg: float | None) -> tuple[int, float, float]:
    """Index, centre, and half-width of the acceptance window.

    `tol_deg` is measured from the nakshatra's *centre*, so the default 6.667°
    is exactly the nakshatra and nothing else. A claim that wants to allow a
    planet to have slipped into a neighbour says so by widening the tolerance,
    in the YAML, where a reader can see it.
    """
    index = nakshatra_by_name(name)
    tol = float(tol_deg) if tol_deg is not None else NAKSHATRA_ARC / 2.0
    return index, nakshatra_centre(index), tol


def _planet_in_nakshatra(c: Constraint, scheme: Scheme, place,
                         inst: Instant) -> ConstraintResult:
    body = str(c.require("body")).lower()
    wanted = str(c.require("nakshatra"))
    index, centre, tol = _nakshatra_window(wanted, c.params.get("tol_deg"))

    pos = ephem.body_position(inst, place, scheme, body)
    offset = signed_delta(centre, pos.lon_sid)
    passes = abs(offset) <= tol
    table = nakshatra_table()

    return ConstraintResult(
        id=c.id, type=c.type, passes=passes,
        stated=f"{body.title()} in {table[index]['iast']} (±{tol:.2f}°)",
        computed=f"{body.title()} at {pos.lon_sid:.3f}° sidereal, in "
                 f"{pos.nakshatra_name} pada {pos.pada} "
                 f"({offset:+.2f}° from the {table[index]['iast']} centre)",
        evidence={"body": body, "lon_sid": round(pos.lon_sid, 4),
                  "nakshatra": pos.nakshatra_name, "pada": pos.pada,
                  "offset_from_centre_deg": round(offset, 4),
                  "tolerance_deg": tol, "wanted": table[index]["iast"]},
    )


def _retrograde(c: Constraint, scheme: Scheme, place,
                inst: Instant) -> ConstraintResult:
    body = str(c.require("body")).lower()
    pos = ephem.body_position(inst, place, scheme, body)
    near = c.params.get("near_nakshatra")

    passes = pos.retrograde
    stated = f"{body.title()} retrograde"
    evidence = {"body": body, "speed_deg_per_day": round(pos.speed, 5),
                "retrograde": pos.retrograde,
                "lon_sid": round(pos.lon_sid, 4),
                "nakshatra": pos.nakshatra_name}
    computed = (f"{body.title()} moving {pos.speed:+.4f}°/day in "
                f"{pos.nakshatra_name}")

    if near is not None:
        index, centre, tol = _nakshatra_window(near, c.params.get("tol_deg"))
        offset = signed_delta(centre, pos.lon_sid)
        within = abs(offset) <= tol
        passes = passes and within
        stated += f" near {nakshatra_table()[index]['iast']} (±{tol:.2f}°)"
        computed += f", {offset:+.2f}° from the {nakshatra_table()[index]['iast']} centre"
        evidence |= {"offset_from_centre_deg": round(offset, 4),
                     "tolerance_deg": tol, "within_window": within}

    return ConstraintResult(id=c.id, type=c.type, passes=passes,
                            stated=stated, computed=computed, evidence=evidence)


def _eclipse_pair(c: Constraint, scheme: Scheme, place,
                  inst: Instant) -> ConstraintResult:
    first_kind = str(c.params.get("first", "lunar")).lower()
    second_kind = str(c.params.get("second", "solar")).lower()
    max_gap = float(c.params.get("max_gap_days", 15.0))
    window = float(c.params.get("window_days", 45.0))

    lo, hi = inst.jd_ut - window, inst.jd_ut + window
    firsts = find_eclipses(lo, hi, first_kind)
    seconds = find_eclipses(lo, hi, second_kind)

    best = None
    for a in firsts:
        for b in seconds:
            gap = b.jd_max - a.jd_max
            if 0 < gap <= max_gap and (best is None or gap < best[2]):
                best = (a, b, gap)

    stated = (f"a {first_kind} eclipse followed by a {second_kind} one within "
              f"{max_gap:g} days, inside ±{window:g} days of the event")
    if best is None:
        return ConstraintResult(
            id=c.id, type=c.type, passes=False, stated=stated,
            computed=f"no such pair; found {len(firsts)} {first_kind} and "
                     f"{len(seconds)} {second_kind} eclipses in the window",
            evidence={"first_count": len(firsts), "second_count": len(seconds),
                      "window_days": window})

    a, b, gap = best
    return ConstraintResult(
        id=c.id, type=c.type, passes=True, stated=stated,
        computed=f"{a.type_name} {first_kind} eclipse then {b.type_name} "
                 f"{second_kind} eclipse {gap:.2f} days later",
        evidence={"first_jd": round(a.jd_max, 5), "second_jd": round(b.jd_max, 5),
                  "gap_days": round(gap, 3), "first_type": a.type_name,
                  "second_type": b.type_name,
                  "first_offset_days": round(a.jd_max - inst.jd_ut, 3)})


def _conjunction(c: Constraint, scheme: Scheme, place,
                 inst: Instant) -> ConstraintResult:
    bodies = c.require("bodies")
    if len(bodies) != 2:
        raise ClaimError(f"constraint {c.id} needs exactly two bodies")
    max_sep = float(c.params.get("max_sep_deg", 1.0))
    window = float(c.params.get("window_days", 365.0))

    found = find_conjunctions(str(bodies[0]).lower(), str(bodies[1]).lower(),
                              inst.jd_ut - window, inst.jd_ut + window,
                              max_sep=max_sep, step_days=2.0)
    stated = (f"{bodies[0]} and {bodies[1]} within {max_sep:g}°, inside "
              f"±{window:g} days of the event")
    if not found:
        return ConstraintResult(
            id=c.id, type=c.type, passes=False, stated=stated,
            computed="no approach that close in the window",
            evidence={"max_sep_deg": max_sep, "window_days": window})

    best = min(found, key=lambda k: k.separation)
    offset = best.jd - inst.jd_ut
    return ConstraintResult(
        id=c.id, type=c.type, passes=True, stated=stated,
        computed=f"closest approach {best.separation:.3f}° at "
                 f"{_jd_label(best.jd)}, {offset:+.1f} days from the event",
        evidence={"separation_deg": round(best.separation, 4),
                  "jd": round(best.jd, 5), "offset_days": round(offset, 3),
                  "approaches": len(found)})


def _jd_label(jd: float) -> str:
    y, m, d, h = swe.revjul(jd, swe.JUL_CAL if jd < 2299160.5 else swe.GREG_CAL)
    from ..time import era_year
    return f"{d:02d}/{m:02d}/{era_year(y)} {int(h):02d}:{int(h % 1 * 60):02d} UT"
