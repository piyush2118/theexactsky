"""Palettes and type. Starting values, to be tuned on the printed sample.

Colours are chosen for paper, not for a screen. The indigo ground is the one
risk: a large flat dark field bands on a six-colour press, so every theme with a
dark ground carries a noise amount and the layouts lay a faint monochrome grain
over it. That gets judged on the Stage 0 Gelato sample before anything is listed.
"""

from __future__ import annotations

from dataclasses import dataclass

LATIN = "EB Garamond"
DEVANAGARI = "Tiro Devanagari Sanskrit"


@dataclass(frozen=True)
class Theme:
    id: str
    title: str

    ground: str            # the paper's field
    ink: str               # primary text and the horizon ring
    accent: str            # planets, the Moon's nakshatra, rules
    highlight: str         # the one warm mark: kumkum
    muted: str             # secondary text, ticks
    star: str              # star fill
    ecliptic: str          # the ecliptic arc

    noise_opacity: float = 0.02   # monochrome grain, against banding in the dark
    star_opacity: float = 0.95
    latin: str = LATIN
    devanagari: str = DEVANAGARI

    @property
    def dark_ground(self) -> bool:
        return self.noise_opacity > 0.0


PICHWAI = Theme(
    id="pichwai",
    title="Pichwai",
    # Indigo and gold out of Nathdwara Pichwai painting, which is what an Indian
    # buyer reads as "ours" and an Etsy-generic navy does not.
    ground="#0F1B3D",
    ink="#F3E9D2",
    accent="#C9A227",
    highlight="#B23A48",
    muted="#6B7A99",
    star="#F3E9D2",
    ecliptic="#C9A227",
    noise_opacity=0.02,
)

BETHLEHEM = Theme(
    id="bethlehem",
    title="Bethlehem",
    # Warmer and quieter: this one is sold in November under an astronomy
    # framing, so it must not read as an astrology poster.
    ground="#0B1220",
    ink="#EDE4D3",
    accent="#D8B36A",
    highlight="#8FA9C4",
    muted="#5F6E85",
    star="#FFF8E7",
    ecliptic="#8FA9C4",
    noise_opacity=0.02,
)

PLATE = Theme(
    id="plate",
    title="Plate",
    # For the six-panel evidence plate. Nearly monochrome on purpose: the plate
    # is an argument, and a decorative palette would undercut it.
    ground="#111418",
    ink="#E8E6E1",
    accent="#C8A15A",
    highlight="#C25B4E",
    muted="#7A7E86",
    star="#E8E6E1",
    ecliptic="#7A7E86",
    noise_opacity=0.015,
    star_opacity=0.9,
)

THEMES = {t.id: t for t in (PICHWAI, BETHLEHEM, PLATE)}


def get(theme_id: str) -> Theme:
    try:
        return THEMES[theme_id]
    except KeyError:
        raise KeyError(
            f"unknown theme {theme_id!r}; have {', '.join(sorted(THEMES))}") from None
