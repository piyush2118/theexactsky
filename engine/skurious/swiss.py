"""Process-wide Swiss Ephemeris setup shared by time and body calculations.

Swiss keeps the ephemeris path as process-global state. Any code that asks Swiss
for data-dependent values (including Delta-T via ``deltat_ex``) must configure
that state first. Keeping the setup here prevents test/process ordering from
silently deciding whether the engine works.
"""

from __future__ import annotations

import functools

import swisseph as swe

from .paths import EPHE, require


@functools.lru_cache(maxsize=1)
def init_ephemeris() -> None:
    """Point Swiss at the vendored ephemeris exactly once per process."""
    require(EPHE / "sepl_18.se1", "scripts/fetch_ephe.py")
    swe.set_ephe_path(str(EPHE))
