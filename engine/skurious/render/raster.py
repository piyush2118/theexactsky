"""SVG to pixels, through resvg, plus the size presets.

resvg, pinned, and nothing else. cairosvg does not shape Devanagari conjuncts:
क्ष comes out as three separate glyphs, which on a print sold to Indian families
is not a rendering bug, it is a returned order. resvg goes through rustybuzz and
shapes correctly, and pinning the binary is what makes the golden-PNG diffs in
CI stable.
"""

from __future__ import annotations

import functools
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..errors import SkuriousError
from ..paths import FONTS

MM_PER_INCH = 25.4


@dataclass(frozen=True)
class Size:
    id: str
    width_mm: float
    height_mm: float
    label: str
    bleed_mm: float = 3.0

    def pixels(self, dpi: int, with_bleed: bool = False) -> tuple[int, int]:
        bleed = 2 * self.bleed_mm if with_bleed else 0.0
        return (round((self.width_mm + bleed) / MM_PER_INCH * dpi),
                round((self.height_mm + bleed) / MM_PER_INCH * dpi))


SIZES = {s.id: s for s in [
    Size("8x10", 203.2, 254.0, "8 × 10 in"),
    Size("12x16", 304.8, 406.4, "12 × 16 in"),
    Size("18x24", 457.2, 609.6, "18 × 24 in"),
    Size("a4", 210.0, 297.0, "A4"),
    Size("a3", 297.0, 420.0, "A3"),
    Size("a2", 420.0, 594.0, "A2"),
    # Screen sizes: no bleed, and the DPI is whatever makes the pixel count right.
    Size("card", 91.44, 114.3, "WhatsApp card 1080×1350", bleed_mm=0.0),
    Size("reel", 91.44, 162.56, "Instagram reel 1080×1920", bleed_mm=0.0),
    Size("plate", 594.0, 420.0, "Six-panel plate, A2 landscape", bleed_mm=0.0),
]}

SCREEN_DPI = 300     # card at 91.44 mm × 300 dpi = 1080 px exactly


def size(size_id: str) -> Size:
    try:
        return SIZES[size_id]
    except KeyError:
        raise SkuriousError(
            f"unknown size {size_id!r}; have {', '.join(SIZES)}") from None


@functools.lru_cache(maxsize=1)
def resvg_version() -> str:
    exe = shutil.which("resvg")
    if exe is None:
        raise SkuriousError(
            "resvg is not on PATH. Install it with `brew install resvg`; it is "
            "the only rasteriser that shapes Devanagari conjuncts correctly.")
    out = subprocess.run([exe, "--version"], capture_output=True, text=True,
                         check=True).stdout.strip()
    return re.sub(r"[^0-9.]", "", out) or out


def to_png(svg_path: Path, png_path: Path, dpi: int = 300,
           background: str | None = None) -> Path:
    """Rasterise at a physical DPI. The SVG's own mm dimensions set the size."""
    exe = shutil.which("resvg")
    if exe is None:
        raise SkuriousError("resvg is not on PATH; `brew install resvg`")
    cmd = [exe, "--dpi", str(dpi), "--use-fonts-dir", str(FONTS),
           "--skip-system-fonts", str(svg_path), str(png_path)]
    if background:
        cmd[1:1] = ["--background", background]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SkuriousError(
            f"resvg failed on {svg_path.name}:\n{result.stderr.strip()}")
    if result.stderr.strip():
        # resvg warns about missing glyphs on stderr while still exiting 0. A
        # missing glyph on a print is a refund, so it is not allowed to be quiet.
        raise SkuriousError(
            f"resvg warned while rendering {svg_path.name}, which on a print "
            f"means a missing glyph or font:\n{result.stderr.strip()}")
    return png_path


def to_jpeg(png_path: Path, jpeg_path: Path, quality: int = 90,
            max_bytes: int | None = None) -> Path:
    """For Etsy digital downloads, which cap each file at 20 MB."""
    from PIL import Image

    with Image.open(png_path) as im:
        rgb = im.convert("RGB")
        q = quality
        while True:
            rgb.save(jpeg_path, "JPEG", quality=q, optimize=True,
                     progressive=True, subsampling=0)
            if max_bytes is None or jpeg_path.stat().st_size <= max_bytes or q <= 60:
                break
            q -= 5
    return jpeg_path
