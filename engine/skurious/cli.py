"""`sk` — the command line. Every render in the README comes out of one of these.

The CLI is deliberately thin. It parses arguments, calls the engine, and writes
files; anything it does that the library cannot is a design mistake, because the
web app and the order pipeline call the library, not this.
"""

from __future__ import annotations

from pathlib import Path

import typer

from . import claims as claims_mod
from . import geo, sky as sky_mod
from .errors import SkuriousError
from .render import raster, themes
from .render.layouts import plate6, sky_print
from .sidereal import Scheme
from .time import both_year_forms, era_year, instant, instant_from_jd

app = typer.Typer(add_completion=False, no_args_is_help=True,
                  help="Skurious — the sidereal sky engine.")
geo_app = typer.Typer(no_args_is_help=True, help="Places.")
render_app = typer.Typer(no_args_is_help=True, help="Pictures.")
claims_app = typer.Typer(no_args_is_help=True, help="Dating claims.")
conj_app = typer.Typer(no_args_is_help=True, help="Close approaches.")
app.add_typer(geo_app, name="geo")
app.add_typer(render_app, name="render")
app.add_typer(claims_app, name="claims")
app.add_typer(conj_app, name="conj")

OUT = Path("out")


def _scheme(ayanamsa: str, calendar: str, node: str = "mean") -> Scheme:
    return Scheme(ayanamsa=ayanamsa, calendar=calendar, node=node)


def _write(svg, stem: str, dpi: int, png: bool, bleed: bool) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    svg_path = OUT / f"{stem}.svg"
    svg_path.write_text(svg.to_string(), encoding="utf-8")
    typer.echo(f"wrote {svg_path}")
    if png:
        png_path = OUT / f"{stem}.png"
        raster.to_png(svg_path, png_path, dpi=dpi)
        from PIL import Image
        with Image.open(png_path) as im:
            typer.echo(f"wrote {png_path}  {im.width}×{im.height} px @ {dpi} DPI"
                       + ("  (with bleed)" if bleed else ""))
    return svg_path


# --------------------------------------------------------------------------
# geo
# --------------------------------------------------------------------------

@geo_app.command("search")
def geo_search(query: str, limit: int = 10) -> None:
    """Find a place id to feed the render commands."""
    for p in geo.search(query, limit):
        typer.echo(f"{p.id:<10} {p.label:<46} {p.tz:<22} "
                   f"pop {p.population:>9,}  {p.coords}")


@geo_app.command("show")
def geo_show(place: str) -> None:
    """Resolve anything the other commands accept as a place, and print it."""
    p = geo.resolve(place)
    typer.echo(f"{p.id}  {p.label}\n  {p.coords}\n  timezone {p.tz}")


# --------------------------------------------------------------------------
# renders
# --------------------------------------------------------------------------

@render_app.command("sky")
def render_sky(
    date: str = typer.Option(..., help="YYYY-MM-DD; BCE uses astronomical years"),
    time_: str = typer.Option("19:30", "--time", help="HH:MM, local"),
    place: str = typer.Option(..., help="GeoNames id, named observer, or lat,lon"),
    size: str = "18x24",
    theme: str = "pichwai",
    names: str = typer.Option("", help="comma-separated"),
    occasion: str = "",
    message: str = "",
    ayanamsa: str = "lahiri",
    calendar: str = "auto",
    timescale: str = "zone",
    mag: float = typer.Option(5.5, help="faintest star drawn"),
    dpi: int = 300,
    bleed: bool = False,
    png: bool = True,
    out: str = typer.Option("", help="output stem; defaults to the layout name"),
) -> None:
    """Render 1: the personalised sky print."""
    p = geo.resolve(place)
    inst = instant(date, time_, p, calendar=calendar, timescale=timescale)
    sky = sky_mod.build(p, inst, _scheme(ayanamsa, calendar), mag_limit=mag)
    caption = sky_print.Caption(
        names=[n.strip() for n in names.split(",") if n.strip()],
        occasion=occasion, message=message)
    svg = sky_print.render(sky, themes.get(theme), raster.size(size), caption,
                           bleed=bleed, mag_limit=mag)
    typer.echo(f"{p.label} · {inst.tz_label} · Moon in {sky.moon.nakshatra_name} "
               f"pada {sky.moon.pada} · {sky.moon_phase.name}")
    _write(svg, out or "sky_print", dpi, png, bleed)


@render_app.command("birth")
def render_birth(
    date: str = typer.Option(...),
    time_: str = typer.Option(..., "--time"),
    place: str = typer.Option(...),
    size: str = "12x16",
    theme: str = "pichwai",
    names: str = "",
    ayanamsa: str = "lahiri",
    calendar: str = "auto",
    timescale: str = "zone",
    dpi: int = 300,
    bleed: bool = False,
    png: bool = True,
    out: str = "",
) -> None:
    """The janma-nakshatra print: adds pada and the naming syllable."""
    p = geo.resolve(place)
    inst = instant(date, time_, p, calendar=calendar, timescale=timescale)
    sky = sky_mod.build(p, inst, _scheme(ayanamsa, calendar))
    caption = sky_print.Caption(
        names=[n.strip() for n in names.split(",") if n.strip()],
        occasion="Janma nakṣatra")
    svg = sky_print.render(sky, themes.get(theme), raster.size(size), caption,
                           bleed=bleed, show_syllable=True)
    from .sidereal import naming_syllable
    deva, iast = naming_syllable(sky.moon.lon_sid)
    typer.echo(f"{sky.moon.nakshatra_name} pada {sky.moon.pada} · "
               f"naming syllable {deva} ({iast})")
    _write(svg, out or "birth_print", dpi, png, bleed)


# --------------------------------------------------------------------------
# claims
# --------------------------------------------------------------------------

@claims_app.command("check")
def claims_check(
    path: str = typer.Argument(..., help="a claim YAML, or a directory of them"),
    scheme: str = typer.Option("", help="re-run under another ayanamsa"),
) -> None:
    """Evaluate a claim and print what the sky did next to what it asked for."""
    target = Path(path)
    docs = (claims_mod.load_dir(target) if target.is_dir()
            else [claims_mod.load(target)])
    for claim in docs:
        override = Scheme(ayanamsa=scheme, calendar=claim.calendar) if scheme else None
        result = claims_mod.evaluate(claim, override)
        inst = result.instants[claim.constraints[0].at]
        typer.echo(f"\n{claim.title}   [{claim.id}]")
        typer.echo(f"  {inst.source_local_iso} LMT at "
                   f"{claims_mod.observer_place(claim).label}")
        typer.echo(f"  scheme {result.scheme.id}")
        if claim.citation_status != "verified":
            typer.secho("  citation unverified", fg=typer.colors.YELLOW)
        if claim.date_status != "stated":
            typer.secho("  day-of-year is a placeholder", fg=typer.colors.YELLOW)
        for r in result.results:
            mark = "PASS" if r.passes else "fail"
            colour = typer.colors.GREEN if r.passes else typer.colors.RED
            typer.secho(f"  [{mark}] {r.id}  {r.stated}", fg=colour)
            typer.echo(f"         computed: {r.computed}")
        typer.echo(f"  {result.summary}")


@claims_app.command("plate")
def claims_plate(
    path: str = typer.Argument("data/claims/mahabharata"),
    theme: str = "plate",
    size: str = "plate",
    mag: float = 5.0,
    dpi: int = 300,
    png: bool = True,
    out: str = "plate6",
) -> None:
    """Render 2: six panels, one constraint list, no verdict."""
    docs = claims_mod.load_dir(Path(path))
    panels = []
    for claim in docs:
        result = claims_mod.evaluate(claim)
        place = claims_mod.observer_place(claim)
        inst = result.instants[claim.constraints[0].at]
        sky = sky_mod.build(place, inst, result.scheme, mag_limit=mag)
        panels.append(plate6.Panel(result=result, sky=sky))
        typer.echo(f"  {claim.title}: {result.summary}")
    svg = plate6.render(panels, themes.get(theme), raster.size(size))
    _write(svg, out, dpi, png, False)


# --------------------------------------------------------------------------
# conjunctions
# --------------------------------------------------------------------------

@conj_app.command("find")
def conj_find(
    bodies: str = typer.Option("jupiter,saturn", help="two body names"),
    from_: str = typer.Option(..., "--from", help="YYYY-MM-DD"),
    to: str = typer.Option(..., help="YYYY-MM-DD"),
    place: str = typer.Option("jerusalem"),
    max_sep: float = typer.Option(2.0, help="degrees"),
    calendar: str = "auto",
    render: bool = typer.Option(False, help="also draw the closest approach"),
    theme: str = "bethlehem",
    size: str = "18x24",
    dpi: int = 300,
    out: str = "conjunction",
) -> None:
    """Search for close approaches. Render 3 is this, over Jerusalem, in 7 BCE."""
    a, b = [s.strip().lower() for s in bodies.split(",")]
    p = geo.resolve(place)
    start = instant(from_, "00:00", p, calendar=calendar, timescale="lmt")
    end = instant(to, "00:00", p, calendar=calendar, timescale="lmt")
    found = claims_mod.find_conjunctions(a, b, start.jd_ut, end.jd_ut,
                                         max_sep=max_sep, step_days=1.0)
    if not found:
        typer.echo(f"no {a}–{b} approach within {max_sep}° in that window")
        raise typer.Exit(1)

    for k in found:
        inst = instant_from_jd(k.jd, p, calendar=calendar, timescale="lmt")
        typer.echo(f"{inst.source_local_iso}  separation {k.separation:.4f}°  "
                   f"longitudes {k.lon_a:.3f}° / {k.lon_b:.3f}°")
    typer.echo(f"{len(found)} approach(es) found")

    if render:
        closest = min(found, key=lambda k: k.separation)
        inst = instant_from_jd(closest.jd, p, calendar=calendar, timescale="lmt")
        sky = sky_mod.build(p, inst, _scheme("lahiri", calendar))
        caption = sky_print.Caption(
            occasion=f"{a.title()} and {b.title()}",
            message=f"separation {closest.separation:.3f}°")
        svg = sky_print.render(sky, themes.get(theme), raster.size(size), caption)
        _write(svg, out, dpi, True, False)


# --------------------------------------------------------------------------

@app.command("info")
def info() -> None:
    """What this build would put in a footer: versions and data on disk."""
    from . import stars
    from .paths import DATA, EPHE, PLACES_DB
    import swisseph as swe

    typer.echo(f"Swiss Ephemeris {swe.version}  files in {EPHE}")
    typer.echo(f"resvg {raster.resvg_version()}")
    typer.echo(f"star catalogue: {len(stars.catalogue()):,} entries")
    typer.echo(f"places: {PLACES_DB}")
    typer.echo(f"data root: {DATA}")


def main() -> None:  # pragma: no cover - entry point
    try:
        app()
    except SkuriousError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise SystemExit(2)


if __name__ == "__main__":  # pragma: no cover
    main()
