"""One page in front of the engine.

The whole app is this file, two templates and a stylesheet, which is the point.
There are no accounts, no chart database and no frontend framework, because the
plan says not to build them and because the card link already carries everything
needed to redraw a card years later.

What is stored: an `events` row per action, with a session cookie and a hash of
the token. No IP addresses, no birth details, no names. A card is a pure function
of its URL, so the server has nothing to lose.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               RedirectResponse)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from skurious import geo, sky as sky_mod
from skurious.errors import SkuriousError
from skurious.render import raster, themes
from skurious.render.layouts import sky_print
from skurious.sidereal import Scheme, naming_syllable
from skurious.time import format_local, instant, scheme_footer
from skurious.token import Subject, decode, encode

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CACHE = Path(os.environ.get("SKURIOUS_CACHE", ROOT / "var" / "cards"))
DB_PATH = Path(os.environ.get("SKURIOUS_DB", ROOT / "var" / "skurious.sqlite"))
BASE_URL = os.environ.get("SKURIOUS_BASE_URL", "").rstrip("/")

SCHEME = Scheme()
CARD = raster.size("card")

templates = Jinja2Templates(directory=str(ROOT / "templates"))

SCHEMA = """
PRAGMA journal_mode = WAL;
CREATE TABLE IF NOT EXISTS events (
    ts         INTEGER NOT NULL,
    session    TEXT NOT NULL,
    type       TEXT NOT NULL,
    token_hash TEXT,
    ref        TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type, ts);
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    CACHE.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.executescript(SCHEMA)
    yield


app = FastAPI(title="Skurious", lifespan=lifespan, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


# --------------------------------------------------------------------------
# plumbing
# --------------------------------------------------------------------------

def token_hash(token: str) -> str:
    """Events reference a card by hash, never by the link itself.

    The link is the birth details. Logging it would turn an analytics table into
    a personal-data store, which is exactly what the stateless design avoids.
    """
    return hashlib.sha256(token.encode()).hexdigest()[:16]


def record(request: Request, response: Response, kind: str,
           token: str | None = None, ref: str | None = None) -> None:
    session = request.cookies.get("s")
    if not session:
        session = secrets.token_urlsafe(9)
        response.set_cookie("s", session, max_age=60 * 60 * 24 * 90,
                            httponly=True, samesite="lax")
    try:
        with sqlite3.connect(DB_PATH, timeout=2.0) as db:
            db.execute(
                "INSERT INTO events (ts, session, type, token_hash, ref) "
                "VALUES (?,?,?,?,?)",
                (int(time.time()), session, kind,
                 token_hash(token) if token else None, ref))
    except sqlite3.Error:
        pass                      # analytics must never take the page down


def absolute(request: Request, path: str) -> str:
    return f"{BASE_URL}{path}" if BASE_URL else str(request.base_url).rstrip("/") + path


def build_sky(token: str):
    """A card link back into a drawn sky. The only place the token is spent."""
    subjects, _ruleset = decode(token)
    subject = subjects[0]
    place = geo.by_id(subject.place_id)
    inst = instant_from_subject(subject, place)
    return place, inst, sky_mod.build(place, inst, SCHEME)


def instant_from_subject(subject: Subject, place):
    from skurious.time import instant_from_jd
    return instant_from_jd(subject.jd_ut, place)


def initials(names: str) -> str:
    """A forwarded card shows initials, never names. The plan's privacy rule.

    Returned as bare letters ("PA") because they travel in a query string, and a
    separator that needs percent-encoding is a separator that will eventually be
    sent unencoded by something and 400.
    """
    marks = [part.strip()[0].upper() for part in names.split(",") if part.strip()]
    return "".join(m for m in marks if m.isalnum())[:4]


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    response = templates.TemplateResponse(request, "index.html", {"error": None})
    record(request, response, "visit")
    return response


@app.get("/geo")
async def geo_search(q: str = "", limit: int = 8):
    """Typeahead. Answers to Bombay as well as Mumbai, and to Devanagari."""
    q = q.strip()
    if len(q) < 2:
        return JSONResponse([])
    try:
        found = geo.search(q, limit=min(limit, 20))
    except SkuriousError:
        return JSONResponse([])
    return JSONResponse([
        {"id": p.id, "label": p.label, "tz": p.tz, "coords": p.coords}
        for p in found])


@app.post("/sky")
async def make_card(request: Request, date: str = Form(...),
                    time_: str = Form("", alias="time"),
                    place_id: str = Form(...), names: str = Form(""),
                    occasion: str = Form(""), approximate: str = Form("")):
    """Validate, pack the inputs into a link, and redirect to it.

    Nothing is written here. The redirect target contains the whole input, so
    the card can be redrawn from the URL alone for as long as the engine exists.
    """
    try:
        place = geo.by_id(int(place_id))
        inst = instant(date, time_ or "12:00", place)
        token = encode([Subject.from_instant(inst, place,
                                             approximate=bool(approximate))])
    except (SkuriousError, ValueError) as exc:
        response = templates.TemplateResponse(
            request, "index.html", {"error": str(exc)}, status_code=400)
        record(request, response, "error", ref=type(exc).__name__)
        return response

    # urlencode, not an f-string: names contain spaces and commas, and a
    # hand-built query string breaks on the first person called "Anne-Marie".
    pairs = {k: v for k, v in (("names", names), ("occasion", occasion)) if v}
    query = f"?{urlencode(pairs)}" if pairs else ""
    response = RedirectResponse(f"/s/{token}{query}", status_code=303)
    record(request, response, "result", token=token)
    return response


@app.get("/s/{token}", response_class=HTMLResponse)
async def result(request: Request, token: str, names: str = "",
                 occasion: str = ""):
    try:
        place, inst, sky = build_sky(token)
    except SkuriousError as exc:
        response = templates.TemplateResponse(
            request, "index.html", {"error": str(exc)}, status_code=404)
        return response

    marks = initials(names)
    card_query = f"?i={marks}" if marks else ""
    deva, iast = naming_syllable(sky.moon.lon_sid)
    context = {
        "token": token,
        "names": names,
        "occasion": occasion,
        "card_url": f"/c/{token}.png{card_query}",
        "svg_url": f"/c/{token}.svg{card_query}",
        "share_url": absolute(request, f"/s/{token}"),
        "og_image": absolute(request, f"/c/{token}.png{card_query}"),
        "place": place,
        "when": format_local(inst),
        "moon": sky.moon,
        "nakshatra": sky.moon.nakshatra_name,
        "syllable_deva": deva,
        "syllable_iast": iast,
        "phase": sky.moon_phase.name,
        "grahas": [b for b in sky.grahas if b.body not in ("rahu", "ketu")],
        "star_count": len(sky.stars),
        "footer": scheme_footer(inst, SCHEME),
    }
    response = templates.TemplateResponse(request, "result.html", context)
    record(request, response, "card_visit", token=token)
    return response


def render_card(token: str, marks: str) -> tuple[Path, Path]:
    """Draw the card, or serve the one already on disk.

    Cached by a hash of everything that changes the picture. A card that has
    been forwarded widely is drawn once.
    """
    key = hashlib.sha256(f"{token}|{marks}|{raster.resvg_version()}"
                         .encode()).hexdigest()[:20]
    svg_path, png_path = CACHE / f"{key}.svg", CACHE / f"{key}.png"
    if png_path.exists() and svg_path.exists():
        return svg_path, png_path

    place, inst, sky = build_sky(token)
    caption = sky_print.Caption(names=list(marks), occasion="", message="")
    svg = sky_print.render(sky, themes.get("pichwai"), CARD, caption,
                           mag_limit=4.6)
    CACHE.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg.to_string(), encoding="utf-8")
    raster.to_png(svg_path, png_path, dpi=raster.SCREEN_DPI)
    return svg_path, png_path


@app.get("/c/{token}.png")
async def card_png(token: str, i: str = ""):
    try:
        _svg, png = render_card(token, i)
    except SkuriousError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    return FileResponse(png, media_type="image/png",
                        headers={"Cache-Control": "public, max-age=31536000, immutable"})


@app.get("/c/{token}.svg")
async def card_svg(token: str, i: str = ""):
    try:
        svg, _png = render_card(token, i)
    except SkuriousError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    return FileResponse(svg, media_type="image/svg+xml",
                        headers={"Cache-Control": "public, max-age=31536000, immutable"})


@app.post("/e")
async def beacon(request: Request, type: str = Form(...),
                 token: str = Form(""), ref: str = Form("")):
    """Share and download counters. The Stage 2 gates are measured off this."""
    response = Response(status_code=204)
    if type in ("share_click", "card_download", "door_pdf", "door_astrologer"):
        record(request, response, type, token=token or None, ref=ref or None)
    return response


@app.get("/claims", response_class=HTMLResponse)
async def claims_page(request: Request):
    """The six Mahābhārata dates, evaluated live. The authority asset.

    This is the page that makes the site something other than a novelty
    generator: the same engine that draws a wedding sky says, out loud and with
    its working shown, which proposed dates the sky actually supports.
    """
    from pathlib import Path as P

    from skurious import claims as claims_mod

    directory = P(os.environ.get(
        "SKURIOUS_CLAIMS",
        P(sky_mod.__file__).resolve().parent.parent / "data" / "claims"
        / "mahabharata"))
    rows = []
    for claim in claims_mod.load_dir(directory):
        result = claims_mod.evaluate(claim)
        rows.append({"claim": claim, "result": result,
                     "instant": result.instants[claim.constraints[0].at]})
    response = templates.TemplateResponse(request, "claims.html", {"rows": rows})
    record(request, response, "claims_visit")
    return response


@app.get("/healthz")
async def healthz():
    return {"ok": True, "resvg": raster.resvg_version()}
