"""Sidereal arithmetic: pure functions over a longitude, plus the rule tables.

Nothing here touches an ephemeris or a file handle beyond loading its YAML
tables once. Given a sidereal longitude in degrees these functions say which
nakshatra, pada and rasi it falls in; given the Sun's and Moon's longitudes they
say which tithi, yoga and karana. That is the whole of it, and it is table-driven
so that a disagreement with another program is a disagreement about a cited
table rather than about code.
"""

from __future__ import annotations

import functools
import math
from dataclasses import dataclass

import swisseph as swe
import yaml

from .errors import SkuriousError
from .paths import RULES

NAKSHATRA_ARC = 360.0 / 27.0          # 13°20'
PADA_ARC = 360.0 / 108.0              # 3°20'
RASI_ARC = 30.0

AYANAMSA_MODES = {
    "lahiri": (swe.SIDM_LAHIRI, "Lahiri"),
    "true_chitra": (swe.SIDM_TRUE_CITRA, "True Citra"),
    "raman": (swe.SIDM_RAMAN, "Raman"),
    "krishnamurti": (swe.SIDM_KRISHNAMURTI, "Krishnamurti"),
    "j2000": (swe.SIDM_J2000, "J2000"),
}

HOUSE_SYSTEMS = {"whole_sign": b"W", "placidus": b"P", "equal": b"A"}


@dataclass(frozen=True)
class Scheme:
    """Every choice that moves a number, in one object, printed on every output.

    A render that does not say which ayanamsa produced it cannot be checked by
    anybody, and a claim evaluated under an unstated scheme is not evidence.
    """

    ayanamsa: str = "lahiri"
    nakshatra_boundaries: str = "equal"
    house_system: str = "whole_sign"
    calendar: str = "auto"
    node: str = "mean"             # which lunar node Rahu and Ketu mean

    def __post_init__(self) -> None:
        if self.node not in ("mean", "true"):
            raise SkuriousError(f"unknown node {self.node!r}; want 'mean' or 'true'")
        if self.ayanamsa not in AYANAMSA_MODES:
            raise SkuriousError(
                f"unknown ayanamsa {self.ayanamsa!r}; "
                f"have {', '.join(sorted(AYANAMSA_MODES))}")
        if self.nakshatra_boundaries != "equal":
            raise SkuriousError(
                f"nakshatra boundary scheme {self.nakshatra_boundaries!r} is not "
                f"implemented; only 'equal' (360/27) exists so far")
        if self.house_system not in HOUSE_SYSTEMS:
            raise SkuriousError(f"unknown house system {self.house_system!r}")

    @property
    def sid_mode(self) -> int:
        return AYANAMSA_MODES[self.ayanamsa][0]

    @property
    def ayanamsa_label(self) -> str:
        return AYANAMSA_MODES[self.ayanamsa][1]

    @property
    def id(self) -> str:
        """The string a render prints so the computation can be reproduced."""
        return (f"{self.ayanamsa}/{self.nakshatra_boundaries}/"
                f"{self.house_system}/{self.calendar}/{self.node}-node")

    def apply(self) -> None:
        """Swiss keeps the sidereal mode as process state; set it before a call."""
        swe.set_sid_mode(self.sid_mode, 0, 0)


# --------------------------------------------------------------------------
# tables
# --------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def nakshatra_table() -> list[dict]:
    doc = yaml.safe_load((RULES / "nakshatra.yaml").read_text(encoding="utf-8"))
    rows = doc["nakshatras"]
    if len(rows) != 27:
        raise SkuriousError(f"nakshatra.yaml has {len(rows)} rows, expected 27")
    return rows


@functools.lru_cache(maxsize=1)
def rasi_table() -> list[dict]:
    doc = yaml.safe_load((RULES / "rasi.yaml").read_text(encoding="utf-8"))
    rows = doc["rasis"]
    if len(rows) != 12:
        raise SkuriousError(f"rasi.yaml has {len(rows)} rows, expected 12")
    return rows


# --------------------------------------------------------------------------
# pure arithmetic
# --------------------------------------------------------------------------

def norm360(lon: float) -> float:
    """Wrap to [0, 360). Every function below assumes its input went through here."""
    return lon % 360.0


# These three multiply before they divide. Dividing by 360/27 — which is not
# representable in binary — puts the boundary in the wrong place: 40.0°, exactly
# the start of Rohiṇī, comes out as Kṛttikā. Multiplying by 27 first keeps every
# boundary exact, because 360 divides all three counts.

def nakshatra_index(sid_lon: float) -> int:
    """0-based, so it indexes the table directly. 0 is Ashvini."""
    return int(norm360(sid_lon) * 27.0 // 360.0)


def pada(sid_lon: float) -> int:
    """1-based quarter of the nakshatra, 1..4."""
    return int(norm360(sid_lon) * 108.0 // 360.0) % 4 + 1


def rasi_index(sid_lon: float) -> int:
    """0-based, so it indexes the table directly. 0 is Aries."""
    return int(norm360(sid_lon) * 12.0 // 360.0)


def degrees_in_nakshatra(sid_lon: float) -> float:
    return norm360(sid_lon) % NAKSHATRA_ARC


def degrees_in_rasi(sid_lon: float) -> float:
    return norm360(sid_lon) % RASI_ARC


def nakshatra(sid_lon: float) -> dict:
    return nakshatra_table()[nakshatra_index(sid_lon)]


def rasi(sid_lon: float) -> dict:
    return rasi_table()[rasi_index(sid_lon)]


def nakshatra_name(sid_lon: float) -> str:
    return nakshatra(sid_lon)["iast"]


def _fold(name: str) -> str:
    """Strip diacritics and spacing so 'Mṛgaśīrṣa' and 'mrigashirsha' match.

    A claim YAML is written by a person reading a paper, and papers transliterate
    inconsistently. Refusing 'rohini' because the table says 'Rohiṇī' would make
    the DSL unusable without teaching anybody anything.
    """
    import unicodedata

    decomposed = unicodedata.normalize("NFKD", name.lower())
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    for a, b in (("sh", "s"), ("ri", "r"), ("ii", "i"), ("aa", "a"), ("uu", "u")):
        ascii_only = ascii_only.replace(a, b)
    return "".join(c for c in ascii_only if c.isalnum())


@functools.lru_cache(maxsize=1)
def _nakshatra_lookup() -> dict[str, int]:
    out: dict[str, int] = {}
    for i, row in enumerate(nakshatra_table()):
        out[_fold(row["iast"])] = i
        out[row["deva"]] = i
    return out


def nakshatra_by_name(name: str) -> int:
    """0-based index for a nakshatra written any reasonable way."""
    key = _fold(name)
    index = _nakshatra_lookup().get(key)
    if index is None:
        index = _nakshatra_lookup().get(name.strip())
    if index is None:
        raise SkuriousError(
            f"no nakshatra called {name!r}; the table is in "
            f"data/rules/nakshatra.yaml")
    return index


def nakshatra_centre(index: int) -> float:
    """Mid-longitude of a nakshatra, which is what tolerances are measured from."""
    return (index + 0.5) * NAKSHATRA_ARC


def naming_syllable(sid_lon: float) -> tuple[str, str]:
    """The Devanagari and IAST syllable a child born at this longitude is named for.

    This is the whole reason the birth print sells to grandparents: it is the one
    piece of the chart the family actually acts on.
    """
    row = nakshatra(sid_lon)
    p = pada(sid_lon)
    return row["syllables"][p - 1], row["syllables_iast"][p - 1]


def tithi(sun_lon: float, moon_lon: float) -> int:
    """1..30. The lunar day, from the Moon's elongation in 12° steps."""
    return int(norm360(moon_lon - sun_lon) // 12.0) + 1


def yoga(sun_lon: float, moon_lon: float) -> int:
    """1..27, from the sum of the two longitudes in 13°20' steps."""
    return int(norm360(sun_lon + moon_lon) // NAKSHATRA_ARC) + 1


def karana(sun_lon: float, moon_lon: float) -> int:
    """1..60, half a tithi each."""
    return int(norm360(moon_lon - sun_lon) // 6.0) + 1


def ayanamsa(jd_ut: float, scheme: Scheme) -> float:
    """The precessional offset between the tropical and sidereal zodiacs."""
    scheme.apply()
    return swe.get_ayanamsa_ex_ut(jd_ut, swe.FLG_SWIEPH)[1]


def to_sidereal(tropical_lon: float, jd_ut: float, scheme: Scheme) -> float:
    return norm360(tropical_lon - ayanamsa(jd_ut, scheme))


def nakshatra_boundaries() -> list[float]:
    """The 27 starting longitudes; the ring on every layout is drawn from these."""
    return [i * NAKSHATRA_ARC for i in range(27)]


def signed_delta(a: float, b: float) -> float:
    """b - a wrapped into [-180, 180). Used wherever two longitudes are compared."""
    return (b - a + 180.0) % 360.0 - 180.0


def separation(lon_a: float, lat_a: float, lon_b: float, lat_b: float) -> float:
    """Great-circle separation in degrees, for conjunctions."""
    la, lb = math.radians(lat_a), math.radians(lat_b)
    dl = math.radians(lon_a - lon_b)
    cos_d = math.sin(la) * math.sin(lb) + math.cos(la) * math.cos(lb) * math.cos(dl)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_d))))
