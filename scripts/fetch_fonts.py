#!/usr/bin/env python3
"""Vendor the two typefaces the renders use, both under the SIL Open Font License.

EB Garamond carries the Latin; Tiro Devanagari Sanskrit carries the Devanagari,
because it shapes conjuncts (क्ष, ज्ञ) correctly and most Devanagari webfonts do
not. Both are vendored rather than fetched at render time so that a render made
today and a render made in five years use the same outlines.

    uv run --project engine scripts/fetch_fonts.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

# The scripts live at the repository root; everything they write lives
# under engine/data, beside the package that reads it.
ROOT = Path(__file__).resolve().parent.parent / "engine"
FONTS = ROOT / "data" / "fonts"
MANIFEST = Path(__file__).resolve().parent / "font_manifest.json"

BASE = "https://raw.githubusercontent.com/google/fonts/main"
FILES = {
    "EBGaramond[wght].ttf": f"{BASE}/ofl/ebgaramond/EBGaramond%5Bwght%5D.ttf",
    "EBGaramond-Italic[wght].ttf":
        f"{BASE}/ofl/ebgaramond/EBGaramond-Italic%5Bwght%5D.ttf",
    "TiroDevanagariSanskrit-Regular.ttf":
        f"{BASE}/ofl/tirodevanagarisanskrit/TiroDevanagariSanskrit-Regular.ttf",
    "OFL-EBGaramond.txt": f"{BASE}/ofl/ebgaramond/OFL.txt",
    "OFL-TiroDevanagariSanskrit.txt":
        f"{BASE}/ofl/tirodevanagarisanskrit/OFL.txt",
}


def main() -> int:
    FONTS.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, url in FILES.items():
        dest = FONTS / name
        if not dest.exists():
            print(f"fetching {name} ...", flush=True)
            with urllib.request.urlopen(url, timeout=120) as r:
                dest.write_bytes(r.read())
        manifest[name] = hashlib.sha256(dest.read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"{len(FILES)} files in {FONTS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
