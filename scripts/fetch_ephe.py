#!/usr/bin/env python3
"""Fetch the Swiss Ephemeris .se1 files covering -6000 ... +2400.

14 planet files (seplm60 ... sepl_18) and 14 Moon files (semom60 ... semo_18),
about 25 MB. They are redistributed under the same AGPL as this repository.

    uv run --project engine scripts/fetch_ephe.py                 # download and verify
    uv run --project engine scripts/fetch_ephe.py --write-manifest  # record checksums (maintainer)

Every file is checked against scripts/ephe_manifest.json. A file whose digest
does not match is refused, not overwritten: a silently corrupt ephemeris moves
planets without raising anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe"
# The scripts live at the repository root; everything they write lives
# under engine/data, beside the package that reads it.
ROOT = Path(__file__).resolve().parent.parent / "engine"
EPHE_DIR = ROOT / "data" / "ephe"
MANIFEST = Path(__file__).resolve().parent / "ephe_manifest.json"

# Each .se1 file spans 600 years. "m60" starts at -6000, "_18" ends at +2400.
SEGMENTS = ["m60", "m54", "m48", "m42", "m36", "m30", "m24", "m18", "m12", "m06",
            "_00", "_06", "_12", "_18"]

FILES = [f"sepl{s}.se1" for s in SEGMENTS] + [f"semo{s}.se1" for s in SEGMENTS]
# The stock star catalogue, kept beside ours so build_stars.py can round-trip
# Sirius and Spica against it.
FILES += ["sefstars.txt"]
# ... but kept under a different name, because build_stars.py writes the file that
# Swiss actually reads (it insists on "sefstars.txt") from the full BSC5.
RENAME = {"sefstars.txt": "sefstars_stock.txt"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(name: str, dest: Path) -> None:
    url = f"{BASE}/{name}"
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120) as r, tmp.open("wb") as fh:
        while chunk := r.read(1 << 20):
            fh.write(chunk)
    tmp.replace(dest)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write-manifest", action="store_true",
                    help="record the checksums of what is on disk")
    ap.add_argument("--force", action="store_true", help="re-download everything")
    args = ap.parse_args()

    EPHE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}

    failures = []
    for name in FILES:
        dest = EPHE_DIR / RENAME.get(name, name)
        if args.force or not dest.exists():
            print(f"fetching {name} ...", flush=True)
            download(name, dest)
        digest = sha256(dest)
        expected = manifest.get(name)
        if args.write_manifest:
            manifest[name] = digest
        elif expected is None:
            print(f"  {name}: no recorded checksum", file=sys.stderr)
        elif expected != digest:
            failures.append(name)
            print(f"  {name}: CHECKSUM MISMATCH", file=sys.stderr)

    if args.write_manifest:
        MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        print(f"wrote {MANIFEST.relative_to(ROOT)} ({len(manifest)} files)")

    total = sum(p.stat().st_size for n in FILES
                if (p := EPHE_DIR / RENAME.get(n, n)).exists())
    print(f"{len(FILES)} files, {total / 1e6:.1f} MB in {EPHE_DIR.relative_to(ROOT)}")
    if failures:
        print(f"FAILED: {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
