# Skurious — Technical Plan

Companion to [roadmap.md](roadmap.md). The roadmap says *what* and *when*; this says *how*, in enough detail that each stage can be started without further design.

**Thesis.** One Python library computes the sky for any instant and place, derives the sidereal quantities (nakshatra, pada, rasi, lagna), scores a match, finds a muhurta, and evaluates a historical dating claim. Every product in the roadmap is a layout over that one computation or a web route in front of it. The engine computes; it never interprets. Interpretation is text a named person writes.

---

## 1. Principles

1. **One engine, many faces.** Prints, cards, worksheets, calendars, and plates are layouts over the same `SkyState` and `Chart` objects (§5). No product gets its own maths.
2. **The engine never interprets.** Code produces numbers, tables, pass/fail evidence, and pictures. Prose that judges a match or a date is authored by the practitioner under their name. This is the roadmap's brand/person split, enforced in the architecture.
3. **Deterministic.** Same inputs → byte-identical SVG. Renders are cached by a hash of their inputs; a customer's file can be regenerated years later.
4. **Rules are data.** Nakshatra tables, koota tables, dosha cancellations, muhurta rules, and dating claims are versioned YAML with a source citation on every rule. Outputs print the rule-set id they were computed under.
5. **Scheme-aware.** Ayanamsa, nakshatra boundary scheme, calendar, and time-scale are explicit parameters printed on the output. Never a hidden default.
6. **Stateless where the roadmap allows.** Card links encode their inputs. The first store of personal data is the Stage 3 upload, and its retention rule is written before the first upload.
7. **AGPL from day one.** Everything that links to Swiss Ephemeris is public. Customer data, orders, the practitioner's letters, and brand assets live in a separate private repo.

## 2. Stack

| Concern | Choice | Why |
|---|---|---|
| Language | Python 3.12 via `uv` (machine has 3.10; `uv python pin 3.12`) | Roadmap assumes Python; `pyswisseph` is mature and AGPL |
| Ephemeris | `pyswisseph` + Swiss Ephemeris `.se1` files covering −6000 … +2400 (14 planet + 14 Moon files, ~25 MB, vendored in-repo under the same AGPL) | Built-in Moshier fallback stops at 3000 BCE; the plate needs 5561 BCE. Long-term precession (Vondrák) is built in |
| Star catalogue | Yale Bright Star Catalogue BSC5 (9,110 stars, public domain) converted to Swiss `sefstars.txt` | Stars then get the same rigorous precession + proper motion path as planets |
| Images | SVG built in code → `resvg` (pinned version) → PNG; JPEG via Pillow | resvg shapes Devanagari correctly; cairosvg does not |
| Documents | Typst (pinned) embedding the SVGs | Multi-page worksheets, letters, calendars; single binary; Indic fonts work |
| Fonts | EB Garamond (Latin) + Tiro Devanagari Sanskrit (OFL, vendored) | Print-grade serif; correct conjunct shaping |
| Web | FastAPI + Jinja2 + vanilla JS, SQLite (WAL), Caddy, Docker Compose, one small VPS | One page, one process, ~₹500/month |
| Geocoding | GeoNames `cities500` (~200k places, includes timezone) in SQLite FTS5; `zoneinfo` for historical offsets | Indian birthplaces are often towns under 15k people; `cities15000` would miss them |
| Email | Resend (or Postmark) with DKIM on the domain | Waitlist confirmations, intake links, deliveries |
| Payments | Razorpay (INR), Paddle or Dodo (international, merchant of record), Etsy (Stage 1) | Per roadmap; Stripe is invite-only in India |
| Video | Frame renderer + `ffmpeg` | Stage 5 only |
| CI | GitHub Actions: pytest, golden-SVG diff, golden-PNG diff with pinned resvg + fonts | Pinning is what makes image diffs stable |
| Licence | AGPL-3.0 for `engine/` and `web/` | Astrodienst treats a network service as distribution. The CHF 750 professional licence (~₹75K) exceeds the whole Stage 2 budget, so AGPL is the only option that fits the roadmap |

Install once: `brew install resvg typst ffmpeg`, `uv python install 3.12`. Optional for vector PDF downloads: `cargo install usvg svg2pdf-cli`.

## 3. Accounts and services (not code, but each stage blocks on one)

| Needed by | Item |
|---|---|
| Stage 0 | Domain; Cloudflare DNS; GitHub org with public `skurious` and private `skurious-ops`; sole proprietorship + GSTIN started |
| Stage 1 | Etsy shop (GSTIN verified), Payoneer, Gelato account linked to Etsy |
| Stage 2 | VPS (Hetzner CX22 or equivalent), Resend with DKIM, object storage bucket for backups (Cloudflare R2 free tier) |
| Stage 3 | Razorpay live keys, Paddle or Dodo account (KYC takes 1–3 weeks; start during Stage 2), practitioner agreement |
| Stage 5 | YouTube channel, Zenodo account for the DOI |

## 4. Repository layout

```
skurious/                        # public, AGPL
  engine/
    skurious/
      time.py                    # date/time/place → Instant; calendars; LMT mode; ΔT and σ(ΔT)
      geo.py                     # place search (FTS5), Place objects, timezone resolution
      ephem.py                   # planets, Moon, nodes: tropical + sidereal lon/lat/speed; equatorial; alt/az
      sidereal.py                # ayanamsa modes; nakshatra, pada, lord; rasi; pure functions
      stars.py                   # BSC5 → sefstars.txt; star positions for an instant
      sky.py                     # SkyState; stereographic projection
      kundali.py                 # lagna, houses, planets by rasi; North/South chart data
      kuta.py                    # Ashtakoota, doshas, cancellations → KutaResult with evidence
      band.py                    # birth-time uncertainty sweep
      dasha.py                   # Vimshottari (only if the founder is the practitioner; see Stage 1)
      panchanga.py               # tithi, nakshatra, yoga, karana, vara, sunrise/sunset, Rahu kala
      muhurta.py                 # rule sets → candidate windows; scoring inside a venue slot
      claims/                    # dating-claim DSL, evaluator, conjunction + eclipse search
      render/
        svg.py                   # tiny SVG builder, units in mm, floats rounded to 3 dp
        themes.py                # palettes + fonts
        layouts/                 # sky_print, birth_print, kuta_card, plate6, calendar
        raster.py                # resvg wrapper: size presets, DPI, bleed, JPEG export
        docs.py                  # Typst wrapper: worksheet, letter, calendar, window report
      cli.py                     # `sk ...` (typer)
    data/
      ephe/                      # seplm60…seplm06, sepl_00…sepl_18; semom60…semo_18; sefstars.txt
      rules/                     # nakshatra.yaml, kuta/north-standard-v1/*.yaml, muhurta/vivaha-north-v1.yaml,
                                 # naming_syllables.yaml, deltat_sigma.yaml
      claims/                    # mahabharata/*.yaml, bethlehem.yaml
      geo/places.sqlite          # built from cities500 by scripts/build_geo.py
      fonts/
    tests/
  web/                           # Stage 2+: app/, templates/, static/, Dockerfile, Caddyfile, compose.yaml
  scripts/                       # fetch_ephe.py (with checksums), build_stars.py, build_geo.py
  docs/

skurious-ops/                    # private, separate repo, cloned as a sibling
  orders/<etsy_order_id>.yaml    # Stage 1 intake
  jobs/                          # Stage 3 (on the VPS, not in git; this holds templates only)
  listing/                       # mockups, photos, copy
  letters/                       # practitioner's templates
```

The engine reads `SKURIOUS_OPS_DIR` from the environment; nothing private is ever imported by the public code.

## 5. Data model

```python
Place(id, name, admin, country, lat, lon, tz)                      # tz is an IANA name or "LMT"
Instant(jd_ut, jd_tt, delta_t, delta_t_sigma, calendar, source_local_iso)
BodyPosition(body, lon_trop, lon_sid, lat, speed, retrograde, ra, dec, alt, az, nakshatra, pada, rasi)
Star(hr, name, ra, dec, alt, az, mag)
SkyState(place, instant, scheme, bodies: list[BodyPosition], stars: list[Star],
         moon_phase, ecliptic_path, sunrise, sunset)
Chart(place, instant, scheme, lagna_sid, houses, bodies)          # kundali inputs for a person
KutaResult(a: Chart, b: Chart, ruleset, kootas: dict[name → (points, max, evidence)],
           total, doshas: list[Finding], cancellations: list[Finding])
Finding(rule_id, applies: bool, evidence: dict, text, source)
BandResult(minutes: list[int], totals_a_varying, totals_b_varying, joint_min, joint_max, breakpoints)
Scheme(ayanamsa="lahiri", nakshatra_boundaries="equal", house_system="whole_sign", calendar="auto")
```

Every layout takes one of these plus a theme and a size. Nothing else is passed in.

## 6. Engine design

### 6.1 Time (`time.py`)
- Inputs: local date, time, `Place`, `calendar` (`gregorian` | `julian` | `auto` = Julian before 1582-10-15), `timescale` (`zone` | `lmt`).
- BCE dates use astronomical year numbering internally (5561 BCE = −5560); every output prints both forms.
- Conversion: local → UTC via `zoneinfo` (historical offsets included; ambiguous DST folds raise and the CLI asks). Before zones existed, Local Mean Time = UTC + lon/15.
- `jd_ut` from `swe.julday(y, m, d, h, cal)`; `jd_tt = jd_ut + swe.deltat_ex(jd_ut)`.
- σ(ΔT): Swiss Ephemeris gives no uncertainty. Encode the Stephenson–Morrison–Hohenkerk 2016 error curve as a small table in `deltat_sigma.yaml` (interpolated); values before its range are extrapolated and flagged. Any render before 500 CE prints σ in the footer. At −3000, ΔT is roughly 20 hours and σ is on the order of an hour: enough to move what is rising, not enough to move a planet's nakshatra.

### 6.2 Positions (`ephem.py`, `stars.py`)
- `swe.set_ephe_path(data/ephe)`; `swe.calc_ut(jd, body, SEFLG_SWIEPH | SEFLG_SPEED [| SEFLG_SIDEREAL])` after `swe.set_sid_mode`. Bodies: Sun, Moon, Mercury–Saturn, mean and true node, Ketu = node + 180°; Uranus–Neptune for the sky only.
- Ayanamsa modes exposed: `lahiri` (default), `true_chitra`, `raman`, `krishnamurti`, `j2000`.
- Stars: `scripts/build_stars.py` writes `sefstars.txt` from BSC5 (name `HRnnnn`, J2000 RA/Dec, proper motions, magnitude; zero for missing parallax/RV). Positions from `swe.fixstar2_ut` with `SEFLG_EQUATORIAL`, then `swe.azalt`. 9,110 calls per instant is well under a second; cached per instant. Round-trip check: Sirius and Spica from the generated file must match the stock `sefstars.txt` to 1″.
- Alt/az from `swe.azalt`; refraction off for prints (the sky is drawn geometrically).

### 6.3 Sidereal arithmetic (`sidereal.py`, pure functions, table-driven)
```
nakshatra = floor(sid_lon / (360/27))          # 0..26
pada      = floor(sid_lon / (360/108)) % 4 + 1
rasi      = floor(sid_lon / 30)
tithi     = floor(((moon - sun) % 360) / 12) + 1
yoga      = floor(((sun + moon) % 360) / (360/27)) + 1
karana    = floor(((moon - sun) % 360) / 6) + 1
```
`nakshatra.yaml` holds per nakshatra: names (Devanagari, IAST), lord, gana, yoni, nadi, and the four naming syllables per pada. Rasi tables hold varna, vashya group, and lord.

### 6.4 Sky and projection (`sky.py`)
- Zenith-centred stereographic disc: `r = R_h · tan(z/2)`, north up, east on the left (as seen from below, the convention every star-map buyer already knows).
- Layers, in order: ground, star field (mag ≤ 5.5, radius by magnitude), Milky Way omitted (v1), optional constellation lines (d3-celestial data, BSD-3), ecliptic arc with nakshatra ticks, horizon ring with N/E/S/W, planets with glyphs, Moon drawn with its true phase.
- Outer annulus: the sidereal **nakshatra ring**, 27 sectors labelled in Devanagari and IAST, each planet marked at its sidereal longitude, the Moon's nakshatra filled. This ring is the product's signature and appears on every layout.
- Below the disc: names/occasion, date in local time, place, coordinates, and a footer line with scheme id (e.g. `Lahiri · equal nakshatras · Julian`) and, when applicable, σ(ΔT).

### 6.5 Kundali and kuta (`kundali.py`, `kuta.py`)
- Lagna and cusps from `swe.houses_ex(jd, lat, lon, b'W', SEFLG_SIDEREAL)`; whole-sign houses by default, house system in `Scheme`.
- Ashtakoota, max 36, one YAML table each under `rules/kuta/north-standard-v1/`:

| Koota | Max | Basis | Table |
|---|---|---|---|
| Varna | 1 | Moon rasi class | 4 classes, comparison rule |
| Vashya | 2 | Moon rasi group | 5 groups, 5×5 with fractional scores |
| Tara | 3 | Nakshatra count mod 9, both directions | 9 taras, good/bad, 3 / 1.5 / 0 |
| Yoni | 4 | Animal of birth nakshatra | 14×14 |
| Graha Maitri | 5 | Friendship of Moon-sign lords | 7×7 friend/neutral/enemy → 5/4/3/1/0.5/0 |
| Gana | 6 | Deva / Manushya / Rakshasa | 3×3 |
| Bhakoot | 7 | Moon-sign distance | 2/12, 5/9, 6/8 → 0 else 7 |
| Nadi | 8 | Adi / Madhya / Antya | same → 0 else 8 |

- **Variant policy.** These tables differ by region and text. Pick one published source per table, cite it in the YAML, and reconcile the implementation against two independent programs (Jagannatha Hora and one open-source Jyotish library) on a fixed set of 20 input pairs before Stage 2 goes live. Where they disagree, the YAML records the choice. A South Indian 10-porutham rule set is a later, separate directory, not a flag.
- Doshas as `Finding`s: Nadi, Bhakoot, Manglik (Mars in 1, 2, 4, 7, 8, 12 from Lagna, from Moon, and from Venus, each reported separately with the house number as evidence).
- Cancellations are YAML rules whose predicate is a conjunction of named booleans the evaluator computes (`same_moon_rasi`, `same_moon_nakshatra`, `same_pada`, `rasi_lords_friends`, `both_manglik`, `mars_in_own_or_exalted_sign`, …):

```yaml
- id: nadi.same_rasi_different_nakshatra
  koota: nadi
  text: "Nadi dosha does not apply when both Moons occupy the same rasi in different nakshatras."
  source: "<text, chapter/verse>"
  when: {same_moon_rasi: true, same_moon_nakshatra: false}
```
Every rule's `applies` and evidence are returned, whether or not it fires. That is what lets the Stage 3 letter list "every applicable cancellation" without a human re-deriving them.

### 6.6 Uncertainty band (`band.py`)
- For each partner, sweep birth time at 1-minute steps over ±30 min with the other partner fixed (61 evaluations each, well under a second). Also compute the joint 61×61 grid for min and max.
- Report the exact minutes at which the Moon's nakshatra, Moon's rasi, or Lagna changes, and which findings flip. The card shows the per-partner curve; the results page adds an interactive slider driven by the precomputed JSON.

### 6.7 Panchanga and muhurta (`panchanga.py`, `muhurta.py`)
- Sunrise/sunset via `swe.rise_trans`; vara starts at sunrise; Rahu kala, Yamaganda, Gulika from the day's sunrise–sunset split. Everything is per *place*, not per timezone, because sunrise differs by city.
- Rule set `vivaha-north-v1.yaml`: allowed nakshatras, forbidden tithis, forbidden months (Kharmas, adhika masa), Venus/Jupiter combustion windows, Rahu kala exclusion, Chandra bala and Tara bala for each partner. Regional presets are separate files.
- `calendar(year, place)` → list of windows with the reasons each passes. `window(slot, place, a, b)` → 15-minute steps inside the slot, each scored against the rule set with evidence; output is a Typst document the practitioner signs.

### 6.8 Claims DSL (`claims/`)
```yaml
id: example-3067
source: "<full citation of the dating proposal>"
calendar: julian                         # proleptic Julian, astronomical year numbering
scheme: {ayanamsa: lahiri, nakshatra_boundaries: equal}
observer: kurukshetra                    # data/geo/places.yaml
events:
  war_day1: {date: -3066-11-22, time: sunrise}
constraints:
  - {id: c1, type: planet_in_nakshatra, body: saturn, nakshatra: rohini, at: war_day1, tol_deg: 6.67}
  - {id: c2, type: retrograde,          body: mars,   near_nakshatra: jyeshtha, at: war_day1, tol_deg: 13.33}
  - {id: c3, type: eclipse_pair, first: lunar, second: solar, max_gap_days: 14, within_days_of: war_day1, window_days: 45}
  - {id: c4, type: conjunction, bodies: [jupiter, saturn], max_sep_deg: 1.0, within_days_of: war_day1, window_days: 365}
```
- Constraint types for v0 (Stage 0, enough for the plate): `planet_in_nakshatra`, `retrograde`, `eclipse_pair` (via `swe.lun_eclipse_when` / `swe.sol_eclipse_when_glob`). Added in Stage 5: `conjunction`, `solstice_relative`, `visible_at`, `moon_phase_on`.
- Each claim records its own calendar and scheme; the evaluator can re-run a claim under another scheme to show how much of the argument depends on it.
- The evaluator returns computed values next to each pass/fail, and the plate prints them. The renders do the arguing; the code makes no verdict.

### 6.9 Rendering pipeline (`render/`)
- Physical units. Layouts are authored in mm; a size preset sets the page and the DPI sets pixels.

| Preset | mm | px @ 300 DPI (+3 mm bleed) | Use |
|---|---|---|---|
| 8×10 in | 203×254 | 2400×3000 (2471×3071) | Etsy small |
| 12×16 in | 305×406 | 3600×4800 (3671×4871) | Etsy mid |
| 18×24 in | 457×610 | 5400×7200 (5471×7271) | Etsy large, the sample |
| A4 / A3 / A2 | 210×297 / 297×420 / 420×594 | 2480×3508 / 3508×4961 / 4961×7016 | UK/EU buyers |
| card | — | 1080×1350 | WhatsApp |
| reel | — | 1080×1920 | Instagram |

- Export: SVG → `resvg --dpi --use-fonts-dir data/fonts` → PNG (print files to Gelato, sRGB). JPEG q90 via Pillow for digital downloads. Optional vector PDF: `usvg` (outlines text) → `svg2pdf`.
- Etsy digital downloads allow 5 files of ≤20 MB each. The digital bundle is therefore JPEGs at three aspect ratios (4:5, 3:4, 2:3) plus A-series, each under 20 MB, generated by `sk order render --digital`.
- Theme tokens live in `themes.py`. Starting values for `pichwai`, to be tuned on the printed sample: ground `#0F1B3D`, ivory ink `#F3E9D2`, gold `#C9A227`, kumkum accent `#B23A48`, muted `#6B7A99`. A 2% monochrome noise layer over the ground prevents banding in the indigo.
- Determinism: floats rounded to 3 dp, sorted element order, no timestamps in the SVG. CI hashes each golden render twice.

### 6.10 CLI
```
sk geo search "Edison"                                            # → Place ids
sk render sky     --date 2019-02-14 --time 19:30 --place 5097529 --size 18x24 --theme pichwai
sk render birth   --date ... --time ... --place ... --size 12x16   # nakshatra, pada, naming syllables
sk kuta           --a "1994-05-03 05:40 @<place>" --b "..." --ruleset north-standard-v1 --band 30 --card
sk plate mahabharata --claims data/claims/mahabharata           # the six-panel plate
sk claims check   example-3067 [--scheme true_chitra]
sk conj find      --bodies jupiter,saturn --from -0007-01-01 --to -0005-12-31 --place jerusalem
sk muhurta calendar --year 2027 --places us-uk-ca.yaml --ruleset vivaha-north-v1
sk muhurta window --slot "2027-06-12T14:00/20:00" --place <id> --a ... --b ...
sk order render   <etsy_order_id> [--proof | --digital]         # reads $SKURIOUS_OPS_DIR/orders/<id>.yaml
sk worksheet <job_id>   |   sk deliver <job_id>                  # Stage 3
sk frames --from ... --to ... --step 1d --place <id> --out frames/   # Stage 5
```

## 7. Build sequence, mapped to roadmap stages

### Stage 0 — engine and three pictures (weeks 1–2)
Scope is exactly the three renders. Kundali, kuta, and the web wait for Stage 2.

| Days | Deliverable | Done when |
|---|---|---|
| 1–2 | `time`, `geo`, `ephem`, `sidereal`; `scripts/fetch_ephe.py` with checksums; `build_geo.py` | Lahiri ayanamsa at J2000 = 23°51′ ± 1′; Moon nakshatra and pada match two reference programs on 20 inputs; Julian/Gregorian/year-zero/DST/LMT tests pass |
| 3–4 | `stars`, `sky`, projection | 50 bright stars agree with Stellarium to 0.1° for a 2024 instant; Sirius/Spica round-trip within 1″; −3000 star field renders without error |
| 5–7 | SVG builder, `pichwai` theme, `sky_print` layout, resvg pipeline, size presets | **Render 1** at 18×24 in, 300 DPI; two runs produce identical bytes; क्ष and ज्ञ shape correctly; footer shows scheme id |
| 8–10 | `claims` v0 (three constraint types, eclipse search), `plate6` layout | **Render 2**: six panels over Kurukshetra (5561, 3138, 3105, 3067, 1478, 1198 BCE), each at the claim's stated event time (sunrise if unstated), the same constraint list evaluated on each panel, σ(ΔT) and scheme in the footer |
| 11–12 | Conjunction finder, `bethlehem` theme | **Render 3**: the finder locates the three Jupiter–Saturn minima of 7 BCE on its own; regression test on the 2020-12-21 conjunction (separation ≈ 0.1°) |
| 13–14 | Proof/mockup export, Gelato sample | One Gelato 18×24 sample ordered from a generated file; CI green; `README` reproduces all three renders with one command each |

### Stage 1 — Etsy orders (weeks 2–8)
- **Intake.** Etsy's personalization box is 256 characters of free text. Each order becomes `orders/<id>.yaml`:
  ```yaml
  id: "3141592653"
  listing: sky_print            # sky_print | birth_print | digital
  occasion: wedding
  event: {date: 2019-02-14, time: "19:30", place_id: <from sk geo search>}
  names: ["Priya", "Arjun"]
  message: "Under this sky"
  size: 18x24
  theme: pichwai
  proof_sent: null
  approved: null
  gelato_order: null
  ```
  `sk order render --proof` echoes the parsed date, local time, timezone, and place back and makes a 1080-px watermarked proof. Send the proof through Etsy messages and wait for a reply before printing. This one step prevents most refunds (wrong year, AM/PM, wrong city).
- **Fulfilment.** Gelato imports the Etsy order; hold it, upload the rendered PNG to the line item, release. Manual until 30 orders a month; Etsy's v3 API needs app approval and is not worth it before that.
- **Birth print.** `birth_print` layout adds nakshatra, pada, and the naming syllables from `nakshatra.yaml`.
- **Digital.** `--digital` writes the JPEG bundle under 20 MB per file for Etsy's made-to-order digital delivery.
- **Listing assets.** A Pillow script drops a render into four room photos; Gelato's mockups cover the rest.
- **Data.** Record occasion and buyer city per order in the YAML. This becomes the Stage 4 planner target list.
- **If the founder is the practitioner** (roadmap Stage 3 fold-in): add `dasha.py` (Vimshottari from the Moon's nakshatra, ~60 lines) and a `reading` Typst worksheet (chart, current mahadasha/antardasha, Jupiter and Saturn transits to the 7th from Lagna and Moon) so the fourth listing can be delivered in three days. Skip entirely otherwise.

### Stage 2 — the forwardable card (weeks 6–12)
- **Engine.** `kundali`, `kuta` with `north-standard-v1` reconciled per §6.5, `band`, `kuta_card` layout (guna total, eight koota rows, doshas, applicable cancellations, band curve, URL, rule-set id).
- **Routes.**
  ```
  GET  /                 form (two people: date, time, place typeahead, "time is approximate" tick)
  GET  /geo?q=           typeahead JSON from places.sqlite
  POST /match            validate → 302 /r/<token>
  GET  /r/<token>        results page: card image, slider, doors, share buttons, OpenGraph tags
  GET  /c/<token>.png    the 1080×1350 card, cached on disk by token hash
  GET  /c/<token>.json   band data for the slider
  POST /e                event beacon
  POST /waitlist         email + door
  GET  /healthz
  ```
- **Token.** No database is needed to reproduce a card. Pack: version (1 B), two UTC minutes-since-1900 (4 B each), two place ids (4 B each), flags (rule set, ordering, approximate-time bits; 1 B), CRC-16 (2 B) → 20 bytes → 27 characters base64url. Manual lat/lon replaces a place id with quantized coordinates (0.01°, 4 B) under a flag bit. Names are not in the token; the card shows initials entered on the form, so a forwarded link never leaks names.
- **Forwardability.** Two paths, both instrumented: a WhatsApp deep link (`https://wa.me/?text=<url>`) whose link preview is the card via `og:image`, and a download button for people who forward the image itself. The slider on the results page is what the Reel screen-records; no separate animation tool is needed.
- **Fake doors.** Two buttons → a modal with an email field and the door name → `waitlist(email, door, token_hash, ts)`. The roadmap's ₹299 pre-sale, if the PDF door wins, is a Razorpay payment link with no code.
- **Events.** `events(ts, session, type, token_hash, ref)` with types `result`, `card_download`, `share_click`, `card_visit`, `door_pdf`, `door_astrologer`, `waitlist`. Session is a first-party cookie; IPs are not stored.
- **Ops.** Docker Compose (uvicorn + Caddy), per-IP rate limit, nightly `sqlite3 .backup` to R2, uptime ping, secrets in `.env` outside git.

### Stage 3 — practitioner second opinion (months 3–5)
- **Flow.** `POST /order/second-opinion` → `jobs(id, status, email, region, amount, created)` → Razorpay order or Paddle/Dodo checkout → webhook with signature verification and idempotent update → status `paid` → email an intake link → upload page (birth details for both, family astrologer's verdict, birth records; PDF/JPEG/PNG ≤10 MB each) → status `ready` → practitioner queue page behind basic auth.
- **Cap.** Paid jobs in the calendar month ≥ 20 → checkout shows next month's opening date.
- **Worksheet.** `sk worksheet <id>` → Typst PDF: both charts (North and South), koota table, every dosha and cancellation with evidence and citation, band curves, and a blank letter section. Nothing in it is prose the engine wrote.
- **Letter and delivery.** The practitioner writes the letter in a Typst template in `skurious-ops/letters/`. `sk deliver <id>` composes worksheet + letter, stamps the footer with practitioner name, rule-set id, and the PDF's SHA-256, emails a signed URL that expires in 7 days, and sets status `delivered`. Delivery email includes a referral code so the follow-on gate can be measured.
- **Data.** Uploads encrypted at rest (Fernet, key in `.env`), stored outside the repo, deleted 90 days after delivery by a cron job. This is the first personal-data store; the retention rule is written and tested before the checkout route is deployed.

### Stage 4 — muhurta (months 4–8)
- `panchanga` and `muhurta` per §6.7, rule set `vivaha-north-v1` reviewed by the practitioner before publication.
- `sk muhurta calendar --year 2027 --places us-uk-ca.yaml` → one Typst PDF with a page per city (10 cities across US, UK, Canada, chosen from Stage 1 order data) and an ICS per city. This is the free lead magnet.
- `sk muhurta window` → scored windows inside a venue slot, a Typst report the practitioner signs. Sold at $150–300 through the Stage 3 checkout with a second product id.
- Planner subscription: at three to six planners, invoice manually through Paddle or Razorpay; no subscription code until there are more than ten.

### Stage 5 — the verification tool as media (months 6–12)
- Full claims DSL (§6.8); `sk claims check` and `sk claims render` for every encoded proposal; a claim can be evaluated under each ayanamsa scheme in one table.
- A local-only `/lab` page in the same web app: date, time, and place controls that re-render the SVG live. This is what gets screen-recorded; a CLI table is not watchable.
- `sk frames` + ffmpeg for time-lapses (1080p at ~1 s/frame; a 60-second clip renders in under an hour).
- Open-source packaging: `README` with one-command reproduction of the plate, `CITATION.cff`, Zenodo DOI, tagged releases. This is the citation asset.
- In November: `sk render sky --theme bethlehem` for the Etsy listing, framed as astronomy.

### Stage 6 — content
Static pages rendered by the same FastAPI app only where a route already exists (calculator, calendar, claims). No CMS.

## 8. How each roadmap gate is measured

| Gate (roadmap) | Source | Query or method |
|---|---|---|
| Stage 1: 10 sales, 5 reviews ≥ 4.8 in 60 days | Etsy dashboard | none |
| Stage 2: 1,000 results in 30 days | `events` | `count(type='result')` |
| Stage 2: share rate > 20% | `events` | distinct sessions with `share_click` or `card_download` ÷ distinct sessions with `result` |
| Stage 2: 100 on the astrologer door | `waitlist` | `count(door='astrologer')`; compare with `door_pdf` clicks to decide the pre-sale |
| Stage 3: 10 paid readings in 30 days | `jobs` | `count(status in (paid, ready, delivered))` |
| Stage 3: follow-on > 20% | `jobs`, referral codes, Etsy | customers (email hash) with a second job, an Etsy order using their code, or a referred job ÷ delivered customers |
| Stage 4: 5 calls, 2 paying planners | spreadsheet | none |
| Stage 5: 1,000 subscribers in 90 days | YouTube | none |

## 9. Verification strategy
- **Golden tests** for every pure function; golden SVGs for every layout; golden PNGs for one size per layout with pinned resvg and fonts.
- **Reference reconciliation**: positions against `swetest`; alt/az against Stellarium for a modern instant; Moon nakshatra, pada, Lagna, and full Ashtakoota against Jagannatha Hora and one open-source Jyotish library on 20 fixed input pairs; eclipse pairs against the NASA canon after −2000; the 2020-12-21 conjunction for the finder.
- **Property tests**: longitude wraparound, nakshatra/pada boundaries, Tara symmetry, Bhakoot symmetry, band sampling covers every minute.
- **Time tests**: US DST births, pre-1945 India offsets, Nepal +5:45, Julian/Gregorian switch, year 0, LMT mode, ambiguous fold.
- **Rendering tests**: Devanagari shaping snapshot; determinism (hash twice); pixel dimensions per preset; digital bundle files under 20 MB.
- **Web tests**: token round-trip, OG tags present, rate limit, webhook signature rejection, retention cron deletes.

## 10. Risks with technical answers

| Risk | Answer |
|---|---|
| ΔT is uncertain by about an hour at −3000; it shifts what is rising, not planetary longitudes | σ(ΔT) printed on ancient plates; rising/setting constraints carry a tolerance; longitude constraints do not need one |
| Scholars disagree on nakshatra boundaries and ayanamsa | `Scheme` is explicit and printed; claims can be evaluated under each scheme in one table |
| Koota tables have regional variants; one wrong cell is a public embarrassment | One cited source per table; reconciliation against two programs on 20 inputs before Stage 2 goes live |
| Devanagari breaks in the rasteriser | resvg only, pinned; shaping snapshot in CI |
| Banding in dark print backgrounds | Noise layer; judged on the Stage 0 sample before listing |
| Wrong personalization details cause refunds | Proof echo-back and buyer approval before printing |
| Birth data and hospital records are personal data (DPDP Act 2023) | Stateless cards; no names in tokens; nothing stored until Stage 3; encryption at rest; 90-day deletion tested |
| Swiss Ephemeris licence | AGPL for all linked code, web app included; interpretation, customers, and brand stay private |
| Etsy API approval lag | Manual order pipeline until 30 orders a month |
| Reference programs disagree with each other | The YAML records the chosen variant with its source; the footer prints the rule-set id so a dispute is about a cited rule, not a bug |

## 11. Do not build
Accounts. A charts database. A mobile app. A frontend framework. A CMS. Kubernetes or microservices. Separate Hindu and Christian sites. Etsy automation before 30 orders a month. Subscription billing before ten planners. A PDF product without a pre-sale. Any prose generated by the engine.

## 12. This week
1. Register the domain; create the two repos; `uv init engine && uv python pin 3.12 && uv add pyswisseph pyyaml typer pillow`; `brew install resvg typst`.
2. `scripts/fetch_ephe.py` (files −6000 … +2400 with checksums), `build_stars.py` (BSC5 → `sefstars.txt`), `build_geo.py` (cities500 → `places.sqlite`).
3. Ship `time.py`, `geo.py`, `ephem.py`, `sidereal.py` with the tests in §9.
4. Render the wedding sky over the first city you would sell to, at 18×24 in, and order the sample.
