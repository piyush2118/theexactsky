"""Searching the sky for events: eclipses and close approaches.

Two searches, both written so that a claim can be *tested* rather than
illustrated. The conjunction finder in particular is asked to find the three
Jupiter–Saturn minima of 7 BCE without being told where they are, because a
finder that is handed the answer proves nothing about the claim.
"""

from __future__ import annotations

from dataclasses import dataclass

import swisseph as swe

from ..ephem import FLAGS, SWE_BODY, init_ephemeris
from ..errors import SkuriousError
from ..sidereal import separation


@dataclass(frozen=True)
class Eclipse:
    kind: str                  # "lunar" | "solar"
    jd_max: float
    jd_begin: float
    jd_end: float
    flags: int

    @property
    def type_name(self) -> str:
        names = []
        if self.flags & swe.ECL_TOTAL:
            names.append("total")
        if self.flags & swe.ECL_ANNULAR:
            names.append("annular")
        if self.flags & swe.ECL_PARTIAL:
            names.append("partial")
        if self.flags & swe.ECL_PENUMBRAL:
            names.append("penumbral")
        return "/".join(names) or "eclipse"


@dataclass(frozen=True)
class Conjunction:
    body_a: str
    body_b: str
    jd: float
    separation: float          # degrees
    lon_a: float
    lon_b: float


def find_eclipses(jd_start: float, jd_end: float, kind: str) -> list[Eclipse]:
    """Every eclipse of one kind in a window, globally — not as seen from a place.

    A dating claim that says "a lunar eclipse followed a solar one within
    thirteen days" is a statement about the Earth–Moon–Sun geometry, not about
    what any one observer could see, so the search is global. A visibility
    constraint is a separate thing and is not implemented yet.
    """
    init_ephemeris()
    if kind not in ("lunar", "solar"):
        raise SkuriousError(f"unknown eclipse kind {kind!r}")

    out: list[Eclipse] = []
    jd = jd_start
    guard = 0
    while jd < jd_end and guard < 10_000:
        guard += 1
        if kind == "lunar":
            flags, times = swe.lun_eclipse_when(jd, swe.FLG_SWIEPH, 0, False)
            begin, end = times[2], times[3]
        else:
            flags, times = swe.sol_eclipse_when_glob(jd, swe.FLG_SWIEPH, 0, False)
            begin, end = times[2], times[3]
        jd_max = times[0]
        if jd_max > jd_end:
            break
        out.append(Eclipse(kind=kind, jd_max=jd_max, jd_begin=begin,
                           jd_end=end, flags=flags))
        jd = jd_max + 1.0
    return out


def _separation_at(jd: float, ipl_a: int, ipl_b: int) -> tuple[float, float, float]:
    a = swe.calc_ut(jd, ipl_a, FLAGS)[0]
    b = swe.calc_ut(jd, ipl_b, FLAGS)[0]
    return separation(a[0], a[1], b[0], b[1]), a[0], b[0]


def find_conjunctions(body_a: str, body_b: str, jd_start: float, jd_end: float,
                      *, max_sep: float = 5.0, step_days: float = 1.0,
                      ) -> list[Conjunction]:
    """Local minima of the true angular separation between two bodies.

    Coarse scan, then a ternary refinement inside each bracketing triple. A
    triple conjunction shows up as three separate minima with no special-casing,
    which is the point: the finder discovers the pattern rather than assuming it.
    """
    init_ephemeris()
    for name in (body_a, body_b):
        if name not in SWE_BODY:
            raise SkuriousError(f"cannot search for {name!r}")
    ipl_a, ipl_b = SWE_BODY[body_a], SWE_BODY[body_b]

    jds = []
    seps = []
    jd = jd_start
    while jd <= jd_end:
        seps.append(_separation_at(jd, ipl_a, ipl_b)[0])
        jds.append(jd)
        jd += step_days

    out: list[Conjunction] = []
    for i in range(1, len(seps) - 1):
        if not (seps[i] < seps[i - 1] and seps[i] <= seps[i + 1]):
            continue
        jd_min = _refine_minimum(jds[i - 1], jds[i + 1], ipl_a, ipl_b)
        sep, lon_a, lon_b = _separation_at(jd_min, ipl_a, ipl_b)
        if sep <= max_sep:
            out.append(Conjunction(body_a=body_a, body_b=body_b, jd=jd_min,
                                   separation=sep, lon_a=lon_a, lon_b=lon_b))
    return out


def _refine_minimum(lo: float, hi: float, ipl_a: int, ipl_b: int,
                    tol_days: float = 1e-4) -> float:
    """Ternary search: the separation is unimodal inside a bracketing triple."""
    while hi - lo > tol_days:
        third = (hi - lo) / 3.0
        m1, m2 = lo + third, hi - third
        if _separation_at(m1, ipl_a, ipl_b)[0] < _separation_at(m2, ipl_a, ipl_b)[0]:
            hi = m2
        else:
            lo = m1
    return (lo + hi) / 2.0
