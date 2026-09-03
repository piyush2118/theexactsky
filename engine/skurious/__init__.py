"""Skurious — one sidereal sky engine, many faces.

    from skurious import geo, sky
    from skurious.sidereal import Scheme
    from skurious.time import instant

    place = geo.resolve("Edison")
    state = sky.build(place, instant("2019-02-14", "19:30", place), Scheme())
    state.moon.nakshatra_name        # 'Mṛgaśīrṣa'

Everything downstream — prints, cards, worksheets, calendars, plates, and
eventually a web route — is a layout over `SkyState` and the objects beside it.
No product gets its own maths.

Licensed AGPL-3.0-or-later: this links to Swiss Ephemeris, and Astrodienst
treats a network service as distribution.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .errors import (AmbiguousLocalTime, ClaimError, DataMissing,
                     NonexistentLocalTime, OutOfEphemerisRange, PlaceNotFound,
                     SkuriousError)
from .geo import Place
from .sidereal import Scheme
from .sky import SkyState
from .time import Instant

__all__ = [
    "AmbiguousLocalTime", "ClaimError", "DataMissing", "Instant",
    "NonexistentLocalTime", "OutOfEphemerisRange", "Place", "PlaceNotFound",
    "Scheme", "SkuriousError", "SkyState", "__version__",
]
