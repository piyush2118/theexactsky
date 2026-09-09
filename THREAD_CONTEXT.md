# TheExactSky — New-Thread Context

Use this file to quickly recover the decisions already made about the Codex harness and current engineering target. For detailed rules, read the linked files rather than expanding this document.

## Current target

The autonomous engineering finish line is **Stage 2: the forwardable two-person compatibility card** from `technical-plan.md`.

Do not automatically continue into Stage 3+.

Stage 2 requires, at a high level:

```text
kundali
  -> north-standard-v1 sourced rules
  -> kuta + doshas/cancellations
  -> reconciliation against 2 independent Jyotish programs on 20 fixed pairs
  -> birth-time uncertainty band
  -> two-person stateless token
  -> deterministic 1080x1350 compatibility card
  -> match/result web flow + slider
  -> WhatsApp/share/download + OpenGraph
  -> PDF/astrologer doors + waitlist/events
  -> browser polish + ops + release gates
```

Exact scope and stop condition: `PROJECT_DONE.md`.

## Core architecture decision

> **One engine, many faces. The engine computes; it does not interpret.**

Keep four evidence lanes separate:

1. **Astronomy/science** — numerical correctness, time, ephemeris, eclipses, conjunctions, uncertainty.
2. **Jyotish convention** — explicit sourced rules/variants such as ayanamsa, koota tables, node/house choices.
3. **Historical attribution** — what a source actually states and whether citation/date status is verified.
4. **Product/presentation** — render, web UX, sharing, analytics, privacy.

JPL agreement does not prove a Jyotish convention. A claim meeting its encoded constraints does not prove a historical date.

## Existing engine ownership

- `time.py` owns local date/time/place -> `Instant`.
- `sidereal.py` owns `Scheme` and sidereal arithmetic/rule-table access.
- `ephem.py` is the single body-position path through Swiss Ephemeris.
- `sky.py` builds `SkyState`, which layouts consume.
- `claims/` evaluates encoded claims without historical verdicts.
- `render/` is deterministic SVG/PNG.
- `token.py` owns stateless share-token encoding.
- `web/` consumes the engine and must not duplicate astronomy/Jyotish calculations.

## Existing correctness properties to preserve

- independent astronomy reconciliation against JPL DE421 / Hipparcos / Lahiri anchor / historical eclipse dates;
- detection of silent Swiss -> Moshier fallback;
- explicit Julian/Gregorian/BCE/LMT/timezone/Delta-T handling;
- deterministic renders and Devanagari shaping checks;
- historical `citation_status` / `date_status` labels;
- raw names and birth-detail tokens are not stored in analytics;
- damaged tokens fail instead of producing a plausible wrong sky.

## Harness files finalized

- `AGENTS.md` — repo-wide operating rules and verification map.
- `.agents/skills/scientific-change/SKILL.md` — workflow for scientific/Jyotish/claim changes.
- `.agents/skills/loop-runner/SKILL.md` — Stage 2 hill-climb/project-completion loop.
- `PROJECT_DONE.md` — bounded Stage 2 definition of done.
- `QUALITY_SCORE.md` — hard gates + weighted 100-point rubric.
- `plans/stage-2/EXEC_PLAN.md` — active dependency/workstream plan.
- `plans/stage-2/RESULTS.md` — evidence/history log.

## Feedback tooling

From repo root:

```bash
python scripts/score-project.py   # objective gate evidence; does not invent UX scores
bash scripts/check-fast.sh        # quick engineering feedback
bash scripts/check-science.sh     # science/reference path
bash scripts/check-render.sh      # deterministic/render path; requires resvg
bash scripts/check-web.sh         # web tests
bash scripts/check-full.sh        # heavy release-candidate local gate
```

Skipped independent/reference/render checks are **UNVERIFIED**, not PASS.

## Release rule

Stage 2 is release-ready only when:

```text
all hard gates PASS
weighted quality >= 90/100
no quality domain < 3/4
release-candidate CI green
required 2-program Jyotish reconciliation completed
representative desktop + mobile browser review completed
no unresolved release blocker
```

## Loop rule

For each outer iteration:

```text
measure current state
  -> choose highest-value safe rubric gap
  -> define acceptance criteria
  -> implement one coherent change
  -> targeted verification
  -> independent review/evidence
  -> broader verification
  -> rescore with evidence
  -> KEEP / REVISE / REVERT / BLOCKED
```

If the same criterion fails twice, stop editing and diagnose the missing harness element (test, tool, source, doc, observable, skill, or ownership boundary). Do not thrash or weaken gates to increase score.

## Current immediate next step

After the harness PR lands, run **W0 baseline establishment** in `plans/stage-2/EXEC_PLAN.md` on the checked-out commit.

Do not assume a baseline score from roadmap text or historical test counts.

## Current harness PR

The harness work is being integrated through PR #1 (`harness/agents-scientific-skill`). Check the exact PR/CI state before beginning implementation work.
