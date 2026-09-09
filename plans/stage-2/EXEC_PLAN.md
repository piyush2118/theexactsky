# Stage 2 Execution Plan

This is the active plan for driving `PROJECT_DONE.md` to completion.

It is updated by the loop runner as evidence changes. Keep it factual and current; do not use it as a speculative wishlist.

## Objective

Reach the Stage 2 release condition in `PROJECT_DONE.md` while preserving all hard gates in `QUALITY_SCORE.md`.

## Current repository state observed before this plan

The repository currently contains a strong Stage 0 engine and a working one-person web/claims surface:

- time/calendar/LMT/Delta-T handling;
- Swiss Ephemeris body calculations;
- sidereal `Scheme` and nakshatra/pada/rasi data;
- star/sky computation;
- historical claims DSL/evaluator/search;
- deterministic SVG/raster pipeline;
- stateless single-subject token;
- FastAPI sky/card/claims routes;
- engine/web tests and independent astronomical reconciliation;
- CI that installs pinned render/data inputs, tests both projects, reproduces canonical renders and checks determinism.

The current Stage 2 plan requires additional compatibility-specific work. The README/technical plan indicate that `kundali`, `kuta`, `band`, the Stage 2 pair card, and full compatibility flow are not yet complete.

## Baseline status

**Weighted baseline: UNSCORED**

**Hard-gate baseline: NOT YET ESTABLISHED FOR THIS BRANCH**

Do not replace these with assumed values. The first loop run must gather fresh evidence from the checked-out commit.

### Baseline procedure

1. Run:

```bash
python scripts/score-project.py
```

2. Run any specialist/full checks the score report marks incomplete.
3. Inspect current Stage 2 implementation against `PROJECT_DONE.md`.
4. Browser-review existing relevant flows when browser tooling is available.
5. Record hard-gate evidence and each 0–4 domain score below.

## Hard gates

| Gate | Status | Evidence / blocker |
|---|---|---|
| G1 Scientific ephemeris integrity | UNVERIFIED | establish with fresh reference run |
| G2 Time/calendar integrity | UNVERIFIED | establish with fresh time-suite run |
| G3 Explicit conventions | UNVERIFIED | inspect + targeted tests |
| G4 Claim epistemic integrity | UNVERIFIED | targeted claims run/review |
| G5 Deterministic/render integrity | UNVERIFIED | requires meaningful render run with `resvg` |
| G6 Privacy/statelessness | UNVERIFIED | token + web privacy run |
| G7 Single computation core | UNVERIFIED | architecture/static review |
| G8 Licensing/data provenance | UNVERIFIED | release dependency/data review |
| G9 Jyotish reconciliation | UNVERIFIED | Stage 2 kuta implementation/reconciliation not yet established |
| G10 Integrated release | UNVERIFIED | release-candidate CI required |

## Weighted rubric baseline

| Domain | Weight | Score | Evidence / gap |
|---|---:|---:|---|
| Scientific correctness | 16 | — | fresh evidence required |
| Time & historical astronomy | 7 | — | fresh evidence required |
| Jyotish implementation & provenance | 14 | — | Stage 2 implementation/reconciliation assessment required |
| Historical claim rigor | 6 | — | fresh evidence required |
| Engine architecture | 9 | — | architecture assessment required |
| Product completeness | 16 | — | compare implementation against `PROJECT_DONE.md` |
| UX & visual quality | 10 | — | browser review required |
| Render/output quality | 6 | — | meaningful render review required |
| Privacy & security | 6 | — | fresh evidence required |
| Reliability & operations | 5 | — | deployment/ops assessment required |
| Agent legibility / harness | 5 | — | assess after harness checks are usable |

## Workstream dependency map

```text
baseline / harness verification
          |
          v
      kundali domain
          |
          v
 north-standard-v1 rules
          |
          v
     kuta evaluator
          |
          v
  two-reference Jyotish reconciliation
          |
          +------------------+
          |                  |
          v                  v
     uncertainty band   pair-token evolution
          |                  |
          +---------+--------+
                    v
               kuta_card
                    |
                    v
             web match flow
                    |
          +---------+---------+
          |                   |
          v                   v
 share/download/OG       doors/waitlist/events
          |                   |
          +---------+---------+
                    v
             browser polish
                    |
                    v
          ops + release candidate
                    |
                    v
            full CI / rescore
```

## Planned workstreams

### W0 — Establish measurable baseline

Acceptance criteria:

- `scripts/score-project.py` produces a machine-evidence report;
- targeted/full commands can be run from a clean prepared development environment;
- every rubric domain has a defensible baseline score/evidence;
- hard gates are `PASS`, `FAIL`, or `UNVERIFIED` with reasons;
- no skipped independent check is called a pass.

### W1 — Kundali domain model

Goal: add the reusable chart object on which kuta/band/layouts depend.

Acceptance criteria:

- calculation lives in engine, not web/layout;
- Lagna/houses/bodies are scheme-aware;
- explicit house-system behavior;
- deterministic/reusable domain result;
- exact/boundary tests;
- independent Jyotish reconciliation fixture/workflow extended where needed.

### W2 — `north-standard-v1` rule data

Goal: encode sourced Stage 2 koota/dosha/cancellation conventions as versioned data.

Acceptance criteria:

- each table/rule has source/provenance;
- variant choices are explicit;
- structural tests cover all table dimensions/categories;
- no source-dependent table is buried in opaque code if it is naturally data.

### W3 — Kuta evaluator

Acceptance criteria:

- eight kootas with evidence and totals;
- doshas and cancellations as evidence-bearing findings;
- consumes charts/domain objects rather than recomputing astronomy;
- fixed regression vectors;
- symmetry/directional behavior tested where appropriate;
- no interpretation prose claiming scientific validity.

### W4 — Required Jyotish reconciliation

Acceptance criteria:

- 20 fixed pairs;
- results compared against two independent Jyotish programs/implementations;
- reconciliation artifact committed where licensing/privacy permits;
- disagreements documented and resolved through explicit sourced variants;
- G9 becomes `PASS` only after the comparison actually occurred.

This workstream may require a human/tool outside the repository. If so, the loop should stop on that specific gate rather than fabricate reference answers.

### W5 — Birth-time uncertainty band

Acceptance criteria:

- both approximate-time inputs supported as planned;
- sampling/interval semantics explicit;
- every required minute/window is covered;
- breakpoints/min/max or equivalent evidence is reproducible;
- property/boundary tests;
- output feeds the card and slider without duplicate web computation.

### W6 — Pair token

Acceptance criteria:

- two subjects round-trip;
- approximate bits/ruleset/version round-trip;
- CRC/integrity behavior preserved;
- names remain outside token;
- raw token remains outside analytics storage;
- compatibility/migration behavior for existing single-subject links is explicit;
- manual-coordinate mode, if retained, has an unambiguous versioned representation and tests.

### W7 — Compatibility card layout

Acceptance criteria:

- 1080×1350 share card;
- total + eight kootas + findings + uncertainty information + ruleset/scheme identity;
- deterministic SVG/PNG;
- intentional golden review;
- Devanagari/Indic text remains correctly shaped;
- card remains understandable at phone/share-preview sizes.

### W8 — Web match/result flow

Acceptance criteria:

- two-person input flow;
- place typeahead for both;
- approximate-time controls;
- validation/error behavior;
- stateless result route;
- band JSON/data endpoint;
- slider consumes engine-produced band data;
- result includes scheme/ruleset provenance;
- no astronomy/kuta calculation duplicated in templates/JS.

### W9 — Sharing, doors, waitlist and analytics

Acceptance criteria:

- WhatsApp/share action;
- image download;
- working OpenGraph image;
- PDF + astrologer doors;
- waitlist capture with door identity;
- expected event types recorded;
- raw tokens/names/birth details not persisted in analytics;
- hostile/unknown event types ignored/refused safely.

### W10 — Browser/product polish

Acceptance criteria:

- desktop and mobile journeys completed in a real browser;
- form, errors, result, slider, share, download, doors and waitlist inspected;
- no unexpected console errors;
- layout collision/overflow/accessibility issues addressed to >= 3/4 UX score;
- screenshots/evidence recorded in results/review where tooling supports it.

### W11 — Operations and release candidate

Acceptance criteria:

- rate limiting configured;
- backup path documented/automated;
- health/uptime path verified;
- secrets external to git;
- deployment docs/config match reality;
- full CI green;
- all gates `PASS`;
- weighted score >= 90 with no domain below 3;
- release decision recorded.

## Hill-climb task selection

At the beginning of each outer-loop iteration:

1. eliminate candidates blocked by unmet prerequisites;
2. never choose work that knowingly breaks a hard gate;
3. estimate for each viable candidate:
   - rubric points available;
   - confidence of gain;
   - effort;
   - regression risk;
4. prioritize approximately by:

```text
(rubric_points_available * confidence) / (effort * regression_risk)
```

5. choose one coherent change surface;
6. write concrete acceptance criteria before implementation.

Prerequisite/enabler work is allowed with no immediate score increase when it is explicitly tied to a named downstream rubric gap.

## Anti-thrashing rules

- Maximum three implementation/review cycles on one work item without measurable progress.
- If the same acceptance criterion fails twice, stop editing and diagnose the missing assumption, test, tool, data, documentation, or ownership boundary.
- If two coherent approaches fail to improve the target criterion, return the item to planning and record the blocker.
- Never weaken a hard gate, tolerance, privacy property, source label, test, or required scope to manufacture progress.

## Current next action

**W0 — establish the fresh baseline** is the first action after this harness lands.

After W0, select the next task using the dependency map and measured rubric gaps. Based on known architecture, `kundali` is expected to be an early prerequisite, but the loop must confirm this from the checked-out state rather than treating this sentence as a command to skip baseline measurement.

## Decisions log

- Current autonomous finish line is Stage 2, not Stage 3+.
- Existing one-person sky and historical claims remain supported and are not replacements for the Stage 2 compatibility flow.
- Hard gates dominate weighted scoring.
- Scientific evidence, Jyotish convention evidence, historical-source evidence, and visual/product evidence remain separate lanes.

## Blockers

None recorded yet. Populate only after a fresh baseline/attempt establishes a real blocker.
