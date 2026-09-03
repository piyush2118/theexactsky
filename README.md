# Skurious

One Python library computes the sky for any instant and place between 6000 BCE
and 2400 CE, derives the sidereal quantities from it (nakshatra, pada, rasi),
and evaluates a historical dating claim against it. Every picture in this repo
is a layout over that one computation.

**The engine computes; it never interprets.** Code here produces numbers,
tables, pass/fail evidence and pictures. Prose that judges a match or a date is
written by a named person, under their name, in a separate private repository.

This is Stage 0 of [technical-plan.md](technical-plan.md): the engine and three
pictures. Kundali, kuta, the birth-time band, panchanga, muhurta and the web app
are Stage 2 and later, and are not built yet — see [Status](#status).

## Install

```sh
brew install resvg                 # the only rasteriser that shapes Devanagari
uv python install 3.12
uv sync --project engine
```

Then fetch the data. About 90 MB, all of it public domain or under a licence
compatible with this one, and all of it checksummed:

```sh
uv run --project engine scripts/fetch_ephe.py     # Swiss Ephemeris, -6000..+2400
uv run --project engine scripts/build_stars.py    # BSC5 -> sefstars.txt
uv run --project engine scripts/fetch_fonts.py    # EB Garamond, Tiro Devanagari
uv run --project engine scripts/build_geo.py      # GeoNames cities500 -> SQLite
```

Everything below runs from the `engine/` directory.

## The three renders

Each is one command, and each is deterministic: the same inputs give a
byte-identical SVG and a pixel-identical PNG, today or in five years.

**1 — the sky over Edison, New Jersey, on a wedding night.** The product.

```sh
uv run sk render sky --date 2019-02-14 --time 19:30 --place 5097529 \
    --size 18x24 --theme pichwai --names "Priya,Arjun" \
    --occasion "Wedding night" --message "Under this sky" --out render1
```

**2 — six proposed dates for the Mahābhārata war, one constraint list.**

```sh
uv run sk claims plate data/claims/mahabharata --out render2
```

**3 — the Jupiter–Saturn triple conjunction of 7 BCE over Jerusalem.** The
finder is given two body names and a two-year window; it locates all three
minima on its own.

```sh
uv run sk conj find --bodies jupiter,saturn --from "-0007-01-01" \
    --to "-0005-12-31" --place jerusalem --calendar julian --render --out render3
```

## What the CLI can do

```sh
sk geo search "Edison"              # place ids for the render commands
sk geo show kurukshetra
sk render sky   --date ... --time ... --place ... --size 18x24
sk render birth --date ... --time ... --place ...   # + pada, naming syllable
sk claims check data/claims/mahabharata [--scheme raman]
sk claims plate data/claims/mahabharata
sk conj find --bodies jupiter,saturn --from ... --to ... --place ...
sk info                             # versions and data on disk
```

A place can be a GeoNames id (`5097529`), a name (`Edison`, `Bombay`, `बंगलौर`),
a named observer from `data/geo/places.yaml` (`kurukshetra`), or bare
coordinates (`29.97,76.88@Asia/Kolkata`).

## Five things this gets right that are usually got wrong

**Every scheme is explicit and printed.** Ayanamsa, nakshatra boundaries, house
system, calendar and which lunar node — all in one `Scheme` object, all in the
footer of every render. A picture that does not say how it was computed cannot
be checked by anybody.

**Ambiguous local times are refused, not guessed.** 01:30 on the autumn fold
happens twice and 02:30 on the spring jump never happens; both raise rather than
silently picking one. Nepal's +05:45, India's 1942–45 wartime +06:30, and
pre-zone Local Mean Time all resolve correctly.

**ΔT carries its uncertainty.** Swiss Ephemeris gives ΔT with no error bar. At
3067 BCE ΔT is about 21 hours, and how well it is known decides what was rising.
`data/rules/deltat_sigma.yaml` carries a σ curve with its source, and anything
below 720 BCE is marked as extrapolated on the render itself.

**Devanagari conjuncts are tested, not assumed.** क्ष must be one glyph, not
three. The test measures the rendered ink and fails if it is wider than a
shaped conjunct can be, and a missing glyph is an error rather than a warning on
stderr that exits zero.

**Claims say whether anybody has checked them.** Each dating claim records
`citation_status` and `date_status`, and the plate prints "citation unverified"
under any panel that rests on one. Four of the six currently do — see
[Status](#status).

## Layout

```
engine/skurious/
  time.py        local date/time/place -> Instant; calendars, LMT, ΔT and σ(ΔT)
  geo.py         FTS5 place search over GeoNames; named observers
  sidereal.py    Scheme; nakshatra, pada, rasi, tithi, yoga, karana
  ephem.py       planets and nodes in four coordinate systems at once
  stars.py       9,096 BSC5 stars, through Swiss so precession matches the planets
  sky.py         SkyState; zenith-centred stereographic projection
  claims/        the dating-claim DSL, its evaluator, eclipse and conjunction search
  render/        SVG builder, themes, layouts, resvg wrapper
  cli.py         sk
engine/data/     ephemeris, rule tables, claims, gazetteer, fonts
engine/tests/    132 tests
scripts/         fetch and build the vendored data
```

## Tests

```sh
uv run --project engine pytest
```

The suite covers the things that fail silently: calendar and timezone edge
cases, nakshatra and pada boundaries at exact longitudes, the structure of the
rule tables, the azimuth and Ketu conventions, render determinism, size presets,
and Devanagari shaping. Two are regression tests against events anyone can look
up — the Jupiter–Saturn conjunction of 21 December 2020 (0.10°) and the triple
conjunction of 7 BCE — and one reproduces the central astronomical claim of the
3067 BCE Mahābhārata proposal from scratch.

## Status

Built (Stage 0): time, geo, ephem, sidereal, stars, sky, claims v0, the SVG and
raster pipeline, the `sky_print` and `plate6` layouts, and the CLI.

Not built yet, and deliberately: `kundali`, `kuta`, `band`, `dasha`,
`panchanga`, `muhurta`, the Typst document pipeline, and the web app. Those are
Stage 2 and later in the plan.

Two things need a person, not more code:

1. **Four of the six Mahābhārata claims carry unverified citations** and
   placeholder days-of-year. Only the 5561 BCE (Vartak) and 3067 BCE (Achar)
   dates have been checked against a primary source. The files say so and the
   plate prints it; they should be corrected from the publications before the
   plate is posted anywhere.
2. **The koota tables are not written yet.** When they are, the plan requires
   reconciling them against two independent programs on twenty fixed input pairs
   before anything goes live.

## Licence

AGPL-3.0-or-later, because this links to Swiss Ephemeris and Astrodienst treats
a network service as distribution. The vendored ephemeris files are redistributed
under the same licence. BSC5 and GeoNames are public domain and CC-BY 4.0
respectively; EB Garamond and Tiro Devanagari Sanskrit are under the SIL Open
Font License, whose text is vendored beside them.
