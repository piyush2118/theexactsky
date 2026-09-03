"""Places: full-text search over GeoNames, plus the named ancient observers.

Two kinds of place exist here and they are not the same thing. A **GeoNames
place** has an id, a population and an IANA timezone, and is what a buyer picks
from a typeahead. A **named observer** is a hand-written entry in
`data/geo/places.yaml` — Kurukshetra, Jerusalem — that a dating claim refers to
by name and whose coordinates are part of the claim's citation, not a lookup.
"""

from __future__ import annotations

import functools
import re
import sqlite3
from dataclasses import dataclass

import yaml

from .errors import PlaceNotFound, SkuriousError
from .paths import GEO, PLACES_DB, require

MANUAL_RE = re.compile(
    r"^(?P<lat>-?\d+(?:\.\d+)?),\s*(?P<lon>-?\d+(?:\.\d+)?)"
    r"(?:@(?P<tz>[\w/+-]+))?$")


@dataclass(frozen=True)
class Place:
    id: int | str
    name: str
    admin: str
    country: str
    lat: float
    lon: float
    tz: str                        # IANA zone name, or "LMT"
    population: int = 0

    @property
    def label(self) -> str:
        """'Edison, New Jersey, United States' with empty parts dropped."""
        return ", ".join(p for p in (self.name, self.admin, self.country) if p)

    @property
    def coords(self) -> str:
        from .time import format_dms
        return f"{format_dms(self.lat, 'N', 'S')}  {format_dms(self.lon, 'E', 'W')}"


@functools.lru_cache(maxsize=1)
def _db() -> sqlite3.Connection:
    require(PLACES_DB, "scripts/build_geo.py")
    con = sqlite3.connect(f"file:{PLACES_DB}?mode=ro", uri=True,
                          check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def _row_to_place(row: sqlite3.Row) -> Place:
    return Place(id=row["id"], name=row["name"], admin=row["admin"],
                 country=row["country"], lat=row["lat"], lon=row["lon"],
                 tz=row["tz"], population=row["population"])


def _match_expression(query: str) -> str:
    """FTS5 prefix match on every token, with quoting so punctuation is inert."""
    tokens = [t for t in re.split(r"[^\w]+", query) if t]
    if not tokens:
        raise SkuriousError("empty place query")
    return " ".join(f'"{t}"*' for t in tokens)


def search(query: str, limit: int = 10) -> list[Place]:
    """Ranked by population, because the buyer means the big Edison."""
    rows = _db().execute(
        "SELECT p.* FROM places_fts f JOIN places p ON p.id = f.rowid "
        "WHERE places_fts MATCH ? ORDER BY p.population DESC LIMIT ?",
        (_match_expression(query), limit)).fetchall()
    return [_row_to_place(r) for r in rows]


def by_id(place_id: int) -> Place:
    row = _db().execute("SELECT * FROM places WHERE id = ?",
                        (int(place_id),)).fetchone()
    if row is None:
        raise PlaceNotFound(f"no GeoNames place with id {place_id}")
    return _row_to_place(row)


@functools.lru_cache(maxsize=1)
def named_observers() -> dict[str, Place]:
    path = GEO / "places.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out = {}
    for key, entry in doc.get("observers", {}).items():
        out[key] = Place(
            id=key, name=entry["name"], admin=entry.get("admin", ""),
            country=entry.get("country", ""), lat=float(entry["lat"]),
            lon=float(entry["lon"]), tz=entry.get("tz", "LMT"))
    return out


def resolve(spec: str | int) -> Place:
    """Turn a CLI argument into a Place.

    Accepts a GeoNames id (`5097529`), a named observer (`kurukshetra`), or
    bare coordinates (`29.97,76.88` or `29.97,76.88@Asia/Kolkata`). Bare
    coordinates default to Local Mean Time: a latitude and longitude do not say
    which zone anybody's clock was on.
    """
    if isinstance(spec, int):
        return by_id(spec)
    spec = spec.strip()
    if spec.isdigit():
        return by_id(int(spec))
    if (m := MANUAL_RE.match(spec)):
        lat, lon = float(m["lat"]), float(m["lon"])
        return Place(id=f"{lat},{lon}", name=f"{lat:.4f}, {lon:.4f}", admin="",
                     country="", lat=lat, lon=lon, tz=m["tz"] or "LMT")
    if (place := named_observers().get(spec.lower())) is not None:
        return place
    matches = search(spec, limit=1)
    if not matches:
        raise PlaceNotFound(
            f"no place matches {spec!r}; try `sk geo search {spec!r}`")
    return matches[0]
