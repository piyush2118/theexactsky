"""Rendering: determinism, physical sizes, and Devanagari that actually shapes.

The determinism tests are what make golden images possible at all, and the
golden images are what make a change to a layout visible in review. The
Devanagari test is the one that stops a refund: क्ष rendered as three separate
letters is not a subtle typographic complaint, it is a misspelling on a wall.
"""

from __future__ import annotations

import hashlib
import shutil

import pytest

from skurious.errors import SkuriousError
from skurious.render import raster, themes
from skurious.render.layouts import sky_print
from skurious.render.svg import SVG, num, ring_sector

GOLDEN = "tests/golden"

pytestmark = pytest.mark.skipif(shutil.which("resvg") is None,
                                reason="resvg is not installed")


def card(sky) -> SVG:
    """A small deterministic render, used for every golden in this file."""
    return sky_print.render(
        sky, themes.get("pichwai"), raster.size("card"),
        sky_print.Caption(names=["P", "A"], occasion="Wedding night",
                          message="Under this sky"),
        mag_limit=4.0)


# --------------------------------------------------------------------------
# the SVG builder
# --------------------------------------------------------------------------

def test_numbers_are_rounded_to_three_places():
    assert num(1.0) == "1"
    assert num(1.23456) == "1.235"
    assert num(-0.0) == "0"
    assert num(0.0004) == "0"
    assert num(12.5000001) == "12.5"


def test_attributes_come_out_sorted_so_diffs_are_readable():
    svg = SVG(10, 10)
    svg.content.rect(1, 2, 3, 4, fill="#fff", stroke="#000", opacity=0.5)
    import re

    line = [l for l in svg.to_string().splitlines() if "<rect" in l][0]
    order = re.findall(r'([a-z-]+)="', line)
    assert order == ["fill", "height", "opacity", "stroke", "width", "x", "y"]


def test_markup_is_escaped():
    svg = SVG(10, 10)
    svg.content.text(0, 0, '<script>&"')
    out = svg.to_string()
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_ring_sector_closes_its_path():
    d = ring_sector(0, 0, 10, 20, 0, 30)
    assert d.startswith("M ") and d.endswith("Z")
    assert d.count("A ") == 2


def test_the_svg_carries_physical_dimensions():
    svg = SVG(457.2, 609.6)
    head = svg.to_string().splitlines()[1]
    assert 'width="457.2mm"' in head
    assert 'height="609.6mm"' in head


def test_bleed_grows_the_page_and_shifts_the_content():
    svg = SVG(100, 200, bleed_mm=3.0)
    assert svg.width == 106.0 and svg.height == 206.0
    assert 'transform="translate(3,3)"' in svg.to_string()


# --------------------------------------------------------------------------
# determinism
# --------------------------------------------------------------------------

def test_two_renders_of_the_same_sky_are_byte_identical(wedding_sky):
    assert card(wedding_sky).to_string() == card(wedding_sky).to_string()


def test_the_same_sky_rasterises_to_identical_pixels(wedding_sky, tmp_path):
    svg = tmp_path / "card.svg"
    svg.write_text(card(wedding_sky).to_string(), encoding="utf-8")
    digests = []
    for i in range(2):
        png = tmp_path / f"card{i}.png"
        raster.to_png(svg, png, dpi=raster.SCREEN_DPI)
        digests.append(hashlib.sha256(png.read_bytes()).hexdigest())
    assert digests[0] == digests[1]


def test_the_svg_carries_no_timestamp_or_random_id(wedding_sky):
    out = card(wedding_sky).to_string()
    for token in ("2019-09", "generated", "uuid", "random"):
        assert token.lower() not in out.lower()


# --------------------------------------------------------------------------
# sizes
# --------------------------------------------------------------------------

@pytest.mark.parametrize("size_id, expected", [
    ("8x10", (2400, 3000)),
    ("12x16", (3600, 4800)),
    ("18x24", (5400, 7200)),
    ("a4", (2480, 3508)),
    ("a3", (3508, 4961)),
    ("a2", (4961, 7016)),
    ("card", (1080, 1350)),
    ("reel", (1080, 1920)),
])
def test_size_presets_hit_their_pixel_counts(size_id, expected):
    assert raster.size(size_id).pixels(300) == expected


def test_bleed_pixels_match_the_plan():
    assert raster.size("18x24").pixels(300, with_bleed=True) == (5471, 7271)
    assert raster.size("8x10").pixels(300, with_bleed=True) == (2471, 3071)


def test_unknown_sizes_are_refused():
    with pytest.raises(SkuriousError):
        raster.size("11x17")


def test_a_rendered_print_has_the_pixel_size_its_preset_promises(wedding_sky,
                                                                 tmp_path):
    from PIL import Image

    size = raster.size("8x10")
    svg = tmp_path / "print.svg"
    svg.write_text(
        sky_print.render(wedding_sky, themes.get("pichwai"), size,
                         sky_print.Caption(names=["A"]), mag_limit=4.0
                         ).to_string(), encoding="utf-8")
    png = tmp_path / "print.png"
    raster.to_png(svg, png, dpi=300)
    with Image.open(png) as im:
        assert (im.width, im.height) == size.pixels(300)


# --------------------------------------------------------------------------
# Devanagari
# --------------------------------------------------------------------------

def _ink_width(tmp_path, text: str, name: str) -> int:
    """Render one string and measure the width of the marks it actually made."""
    from PIL import Image

    svg = SVG(80, 20)
    svg.content.rect(0, 0, 80, 20, fill="#ffffff")
    svg.content.text(4, 14, text, font_family=themes.DEVANAGARI,
                     font_size=10, fill="#000000")
    path = tmp_path / f"{name}.svg"
    path.write_text(svg.to_string(), encoding="utf-8")
    png = tmp_path / f"{name}.png"
    raster.to_png(path, png, dpi=300)
    with Image.open(png) as im:
        box = im.convert("L").point(lambda v: 255 - v).getbbox()
    assert box is not None, f"{text!r} rendered nothing at all"
    return box[2] - box[0]


def test_conjuncts_are_shaped_not_stacked_side_by_side(tmp_path):
    """क्ष is one conjunct. If it comes out as क + ष it is wider, and it is wrong.

    This is the whole reason the pipeline is resvg and not cairosvg, so it is
    checked rather than assumed.
    """
    conjunct = _ink_width(tmp_path, "क्ष", "conjunct")
    separate = _ink_width(tmp_path, "कष", "separate")
    assert conjunct < separate * 0.85


def test_the_other_conjunct_the_plan_names(tmp_path):
    assert _ink_width(tmp_path, "ज्ञ", "gya") < _ink_width(tmp_path, "जञ",
                                                           "ja_nya") * 0.9


def test_nakshatra_names_all_render(tmp_path):
    """Every one of the 27 goes on a ring; a missing glyph must fail here."""
    from skurious.sidereal import nakshatra_table

    for row in nakshatra_table():
        assert _ink_width(tmp_path, row["deva"], f"n{row['n']}") > 0


def test_missing_glyphs_are_an_error_not_a_warning(tmp_path):
    """resvg warns and exits 0 on a missing glyph. On a print that is a refund."""
    svg = SVG(40, 20)
    svg.content.text(2, 14, "✕", font_family=themes.LATIN, font_size=10)
    path = tmp_path / "missing.svg"
    path.write_text(svg.to_string(), encoding="utf-8")
    with pytest.raises(SkuriousError, match="missing glyph"):
        raster.to_png(path, tmp_path / "missing.png")


# --------------------------------------------------------------------------
# goldens
# --------------------------------------------------------------------------

def test_the_card_matches_its_golden_svg(wedding_sky, request):
    """Regenerate with: SKURIOUS_UPDATE_GOLDEN=1 uv run pytest tests/test_render.py"""
    import os
    from pathlib import Path

    golden = Path(GOLDEN) / "card.svg"
    produced = card(wedding_sky).to_string()
    if os.environ.get("SKURIOUS_UPDATE_GOLDEN"):
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(produced, encoding="utf-8")
        pytest.skip("golden regenerated")
    assert golden.exists(), f"{golden} missing; regenerate it"
    assert produced == golden.read_text(encoding="utf-8")
