#!/usr/bin/env python3
"""Build data/geo/places.sqlite from the GeoNames cities500 dump.

cities500 is every populated place above 500 people (~200k rows). cities15000
would be a tenth of the size and would miss most Indian birthplaces, which is
the whole reason a buyer cannot find their town in other calculators.

    uv run --project engine scripts/build_geo.py

Search is FTS5 over the primary name, the ASCII name and every alternate name
GeoNames records, ranked by population so that typing "Edison" puts Edison,
New Jersey above Edison, a hamlet in Georgia -- and "Bombay" finds Mumbai.
"""

from __future__ import annotations

import argparse
import csv
import io
import sqlite3
import sys
import urllib.request
import zipfile
from pathlib import Path

# The scripts live at the repository root; everything they write lives
# under engine/data, beside the package that reads it.
ROOT = Path(__file__).resolve().parent.parent / "engine"
OUT = ROOT / "data" / "geo" / "places.sqlite"
CACHE = ROOT / "data" / "geo" / "_cache"

CITIES_URL = "https://download.geonames.org/export/dump/cities500.zip"
ADMIN1_URL = "https://download.geonames.org/export/dump/admin1CodesASCII.txt"
COUNTRY_URL = "https://download.geonames.org/export/dump/countryInfo.txt"

SCHEMA = """
PRAGMA journal_mode = OFF;
DROP TABLE IF EXISTS places;
CREATE TABLE places (
    id         INTEGER PRIMARY KEY,   -- geonameid
    name       TEXT NOT NULL,
    ascii      TEXT NOT NULL,
    alt        TEXT NOT NULL,         -- other names the place answers to
    admin      TEXT NOT NULL,         -- first-level division, resolved to its name
    country    TEXT NOT NULL,         -- country name
    cc         TEXT NOT NULL,         -- ISO-3166 alpha-2
    lat        REAL NOT NULL,
    lon        REAL NOT NULL,
    tz         TEXT NOT NULL,         -- IANA zone
    population INTEGER NOT NULL
);
DROP TABLE IF EXISTS places_fts;
CREATE VIRTUAL TABLE places_fts USING fts5(
    name, ascii, alt, admin, country,
    content='places', content_rowid='id', tokenize='unicode61'
);
"""

# GeoNames carries every name a place has ever had, in every script. Indexing
# them is what lets a grandmother in New Jersey type "Bombay" and a buyer type
# "बंगलौर". Without it the typeahead only answers to the name the gazetteer
# happens to prefer today, and the buyer gives up or picks the wrong town.


def alternate_names(raw: str, name: str, ascii_name: str) -> str:
    seen = {name.lower(), ascii_name.lower()}
    keep = []
    for alt in raw.split(","):
        alt = alt.strip()
        # Skip the link, airport-code and postcode rows GeoNames mixes in here.
        if not alt or len(alt) > 60 or alt.startswith(("http", "//")):
            continue
        if alt.lower() in seen:
            continue
        seen.add(alt.lower())
        keep.append(alt)
    return " ".join(keep)


def fetch(url: str, name: str) -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / name
    if cached.exists():
        return cached.read_bytes()
    print(f"fetching {url} ...", flush=True)
    with urllib.request.urlopen(url, timeout=180) as r:
        data = r.read()
    cached.write_bytes(data)
    return data


def load_admin1() -> dict[str, str]:
    out = {}
    text = fetch(ADMIN1_URL, "admin1CodesASCII.txt").decode("utf-8")
    for row in csv.reader(io.StringIO(text), delimiter="\t"):
        if len(row) >= 2:
            out[row[0]] = row[1]
    return out


def load_countries() -> dict[str, str]:
    out = {}
    text = fetch(COUNTRY_URL, "countryInfo.txt").decode("utf-8")
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        f = line.split("\t")
        if len(f) > 4:
            out[f[0]] = f[4]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-population", type=int, default=0,
                    help="drop places smaller than this (0 keeps everything)")
    args = ap.parse_args()

    admin1 = load_admin1()
    countries = load_countries()

    blob = fetch(CITIES_URL, "cities500.zip")
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        raw = z.read("cities500.txt").decode("utf-8")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    db = sqlite3.connect(OUT)
    db.executescript(SCHEMA)

    rows = []
    for f in csv.reader(io.StringIO(raw), delimiter="\t", quoting=csv.QUOTE_NONE):
        if len(f) < 18:
            continue
        pop = int(f[14] or 0)
        if pop < args.min_population:
            continue
        cc, a1 = f[8], f[10]
        rows.append((
            int(f[0]), f[1], f[2], alternate_names(f[3], f[1], f[2]),
            admin1.get(f"{cc}.{a1}", ""),
            countries.get(cc, cc), cc,
            float(f[4]), float(f[5]), f[17], pop,
        ))

    db.executemany(
        "INSERT OR REPLACE INTO places VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    db.execute("INSERT INTO places_fts(rowid, name, ascii, alt, admin, country) "
               "SELECT id, name, ascii, alt, admin, country FROM places")
    db.execute("CREATE INDEX idx_places_pop ON places(population DESC)")
    db.commit()
    db.execute("VACUUM")
    db.close()

    size = OUT.stat().st_size / 1e6
    print(f"{len(rows):,} places -> {OUT.relative_to(ROOT)} ({size:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
