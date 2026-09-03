"""Where the vendored data lives, and the private ops directory if one is set."""

from __future__ import annotations

import os
from pathlib import Path

from .errors import DataMissing

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
DATA = ROOT / "data"

EPHE = DATA / "ephe"
RULES = DATA / "rules"
CLAIMS = DATA / "claims"
GEO = DATA / "geo"
FONTS = DATA / "fonts"

PLACES_DB = GEO / "places.sqlite"
STAR_FILE = EPHE / "sefstars.txt"


def require(path: Path, script: str) -> Path:
    """Fail with the command that fixes it, not with a FileNotFoundError."""
    if not path.exists():
        raise DataMissing(
            f"{path.relative_to(ROOT)} is missing. Build it with: "
            f"uv run --project engine {script}")
    return path


def ops_dir() -> Path | None:
    """The private skurious-ops checkout, if the environment points at one.

    Nothing under here is ever imported by the engine; it holds orders, letters
    and brand assets, which are not AGPL and not public.
    """
    raw = os.environ.get("SKURIOUS_OPS_DIR")
    return Path(raw).expanduser() if raw else None
