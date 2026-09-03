"""Errors the engine raises rather than guessing.

Every one of these is a place where a silent default would put a planet in the
wrong nakshatra or a chart on the wrong day. The CLI turns them into a question.
"""

from __future__ import annotations


class SkuriousError(Exception):
    """Base class for everything this package raises deliberately."""


class DataMissing(SkuriousError):
    """A vendored data file has not been built yet. Names the script to run."""


class PlaceNotFound(SkuriousError):
    pass


class AmbiguousLocalTime(SkuriousError):
    """The wall clock reads this time twice, on the autumn DST fold."""


class NonexistentLocalTime(SkuriousError):
    """The wall clock skips this time, on the spring DST jump."""


class OutOfEphemerisRange(SkuriousError):
    """Outside the -6000 ... +2400 span the vendored .se1 files cover."""


class ClaimError(SkuriousError):
    """A dating claim is malformed or names a constraint type we do not have."""
