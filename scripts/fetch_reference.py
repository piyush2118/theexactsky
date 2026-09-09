#!/usr/bin/env python3
"""Fetch the independent references the reconciliation tests check against.

These are *not* shipped data. Nothing in `skurious` imports them and no render
touches them. They exist so that `tests/test_reference.py` can check the engine
against ephemerides and catalogues produced by other people, with other code,
from other source data:

* **JPL DE421** (NASA/JPL, public domain) read through Skyfield — a completely
  separate implementation of light-time, aberration, precession and nutation
  from Swiss Ephemeris. If the two agree to a hundredth of an arcsecond, they
  are not agreeing by sharing a bug.
* **Hipparcos** (ESA, via CDS/VizieR) — the astrometric catalogue, against which
  our BSC5-derived star positions are checked. Different source data, different
  proper motions, different reduction. BSC5 carries FK5 proper motions from the
  1980s and Hipparcos carries space-astrometry ones, so they are not copies of
  each other and agreement is meaningful.

    uv run --project engine scripts/fetch_reference.py
    uv run --project engine scripts/fetch_reference.py --write-manifest

Roughly 17 MB. Without them the reconciliation tests skip and the rest of the
suite still runs, but Stage 0's acceptance gates are not met — a suite that only
checks the engine against itself would pass just as happily with Swiss
Ephemeris misconfigured.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "engine"
REF = ROOT / "data" / "_reference"
MANIFEST = Path(__file__).resolve().parent / "reference_manifest.json"

FILES = {
    # JPL planetary and lunar ephemeris, 1900-2050. Enough for the modern
    # reconciliation instants; the ancient checks are against the eclipse canon,
    # which needs no file.
    "de421.bsp": "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de421.bsp",
    # Every Hipparcos star brighter than V = 2.6, with ICRS positions at epoch
    # J1991.25 and proper motions. A hundred rows rather than the whole 118,218,
    # because the gate asks about fifty bright stars and streaming the full
    # catalogue out of VizieR takes minutes and frequently times out.
    "hip_bright.tsv":
        "https://vizier.cds.unistra.fr/viz-bin/asu-tsv?-source=I/239/hip_main"
        "&-out=HIP,RAICRS,DEICRS,pmRA,pmDE,Vmag&Vmag=%3C2.6"
        "&-out.max=300&-out.meta=",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=600) as r, tmp.open("wb") as fh:
        while chunk := r.read(1 << 20):
            fh.write(chunk)
    tmp.replace(dest)


def canonicalize_hipparcos(path: Path) -> None:
    """Strip unstable VizieR response metadata and keep only catalogue rows.

    VizieR's dynamic TSV endpoint can change comments/metadata without changing
    the Hipparcos rows. Hashing that transport wrapper made CI fail on harmless
    server-side metadata drift. The reconciliation tests consume only the six
    requested data columns, so checksum the canonical scientific payload instead.
    """
    rows: list[tuple[int, float, float, float, float, float]] = []
    for line in path.read_text(encoding="latin-1").splitlines():
        if not line.strip() or line.startswith("#") or line.startswith("---"):
            continue
        parts = [part.strip() for part in line.split("\t")]
        if len(parts) < 6 or not parts[0].isdigit():
            continue
        try:
            row = (
                int(parts[0]),
                float(parts[1]),
                float(parts[2]),
                float(parts[3]),
                float(parts[4]),
                float(parts[5]),
            )
        except ValueError:
            continue
        rows.append(row)

    # The reference test needs at least fifty bright stars. A tiny/empty result
    # is more likely a changed/error response than valid catalogue data.
    if len(rows) < 50:
        raise RuntimeError(
            f"Hipparcos query returned only {len(rows)} usable rows; "
            "refusing to canonicalize an incomplete reference"
        )

    rows.sort(key=lambda row: row[0])
    if len({row[0] for row in rows}) != len(rows):
        raise RuntimeError("Hipparcos query returned duplicate HIP identifiers")

    # Fixed numeric formatting makes the checksum describe the selected
    # scientific values, not whitespace/formatting chosen by the HTTP service.
    canonical = [
        f"{hip}\t{ra:.10f}\t{dec:.10f}\t{pm_ra:.5f}\t{pm_dec:.5f}\t{vmag:.5f}"
        for hip, ra, dec, pm_ra, pm_dec, vmag in rows
    ]
    path.write_text("\n".join(canonical) + "\n", encoding="ascii")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write-manifest", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    REF.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}

    failures = []
    for name, url in FILES.items():
        dest = REF / name
        if args.force or not dest.exists():
            print(f"fetching {name} ...", flush=True)
            download(url, dest)
        if name == "hip_bright.tsv":
            canonicalize_hipparcos(dest)
        digest = sha256(dest)
        if args.write_manifest:
            manifest[name] = digest
        elif manifest.get(name) not in (None, digest):
            failures.append(name)
            print(
                f"  {name}: CHECKSUM MISMATCH "
                f"(expected {manifest.get(name)}, got {digest})",
                file=sys.stderr,
            )

    if args.write_manifest:
        MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        print(f"wrote {MANIFEST.name}")

    total = sum((REF / n).stat().st_size for n in FILES if (REF / n).exists())
    print(f"{len(FILES)} files, {total / 1e6:.1f} MB in "
          f"{REF.relative_to(ROOT.parent)}")
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
