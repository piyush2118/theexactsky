# TheExactSky / Skurious — Agent Operating Guide

These instructions apply to the whole repository unless a deeper `AGENTS.md` overrides them.

The user's explicit task controls scope and desired outcome. These repository rules define how to implement that task safely and consistently. If a task intentionally changes one of the invariants below, make that change explicit and update the relevant tests/docs rather than silently bypassing the invariant.

## 1. Project model

The repository is `theexactsky`; the Python package and current product name in code are `skurious` / Skurious. Do not rename either unless the task asks for a rename.

The core architectural rule is:

> **One engine, many faces. The engine computes; it does not interpret.**

Astronomy, Jyotish convention, historical attribution, and presentation are different kinds of truth. Keep them separate:

- **Astronomy / numerical science:** positions, time conversion, eclipses, conjunctions, projection, uncertainty.
- **Jyotish convention:** ayanamsa, nakshatra/pada/rasi rules, node choice, house system, sourced rule tables.
- **Historical claim attribution:** what a publication or tradition actually states, whether the citation/date has been checked, and which constraints are being tested.
- **Presentation/product:** SVG/PNG layout, web routes, copy, cards, caching, analytics, and UX.

A computed astronomical result does not validate an astrological interpretation. A faithfully encoded Jyotish convention is not an empirical scientific claim. A claim satisfying its own constraints is not a historical verdict.

## 2. Source-of-truth order

When sources disagree, use this order:

1. **Current code, tests, and CI** for what the repository does now.
2. **`README.md`** for the current product overview, subject to verification against the tree/tests.
3. **`technical-plan.md` and `roadmap.md`** for design intent and staged/planned work. They are plans, not proof that a module exists or is absent.
4. **Versioned YAML/data files** for the specific convention or historical claim they define.
5. External sources only when the task requires new/changed scientific, historical, licensing, or third-party facts.

Do not implement a planned feature merely because it appears in the roadmap or technical plan. Inspect the current tree and tests first. If documentation is stale relative to code, do not guess; preserve current behavior unless the task asks to change it, and update the affected documentation when appropriate.

## Active milestone, rubric, and loop

For autonomous/"finish the project" work, the current bounded finish line is defined in:

- `PROJECT_DONE.md` — exact Stage 2 scope and stop condition;
- `QUALITY_SCORE.md` — hard release gates plus the weighted 0–100 hill-climb rubric;
- `plans/stage-2/EXEC_PLAN.md` — current evidence, dependency map, workstreams, blockers, and next action;
- `plans/stage-2/RESULTS.md` — completed loop iterations and evidence.

Do not expand an autonomous loop into Stage 3+ unless the user explicitly changes the milestone.

Useful harness skills:

- `.agents/skills/scientific-change/SKILL.md` — use when numerical astronomy, sidereal/Jyotish conventions, historical claims, or sourced rule data can change;
- `.agents/skills/loop-runner/SKILL.md` — use for multi-iteration Stage 2 hill-climbing/project-completion work.

Preferred feedback commands from the repository root:

```bash
python scripts/score-project.py
bash scripts/check-fast.sh
bash scripts/check-science.sh
bash scripts/check-render.sh
bash scripts/check-web.sh
bash scripts/check-full.sh
```

`score-project.py` gathers objective hard-gate evidence; it intentionally does not fabricate the subjective weighted score. Browser/product review, architecture review, licensing review, Jyotish reconciliation, and exact release-candidate CI still require their real evidence.

## 3. Repository map and ownership

### Engine

- `engine/skurious/time.py` — the single local date/time/place -> `Instant` boundary; calendars, astronomical year numbering, zone/LMT conversion, Delta-T and its uncertainty.
- `engine/skurious/geo.py` — places, GeoNames lookup/search, named observers.
- `engine/skurious/sidereal.py` — `Scheme`, pure sidereal arithmetic, nakshatra/pada/rasi/tithi/yoga/karana, rule-table loading.
- `engine/skurious/ephem.py` — the single body-position path through Swiss Ephemeris; tropical, sidereal, equatorial, horizontal coordinates; nodes; rise/set.
- `engine/skurious/stars.py` — star positions.
- `engine/skurious/sky.py` — `SkyState`, the computed object layouts consume, plus projection.
- `engine/skurious/claims/` — machine-checkable historical-claim model, evaluator, eclipse/conjunction search.
- `engine/skurious/render/` — deterministic SVG/raster pipeline and layouts.
- `engine/skurious/token.py` — stateless share-link encoding/decoding.

### Data

- `engine/data/rules/` — versioned, cited convention/rule data.
- `engine/data/claims/` — historical proposals encoded as data; loading a claim is not endorsing it.
- Ephemeris, fonts, geo, and external reference data are fetched/built by `scripts/` and are checksummed where the repository requires it.

### Web

- `web/app/main.py` — FastAPI route layer. It consumes the engine; it must not become a second astronomy engine.
- `web/templates/`, `web/static/` — presentation.
- `web/tests/` — end-to-end route/privacy/card behavior.

### Verification / automation

- `engine/tests/` — unit, regression, rendering, and independent-reference tests.
- `.github/workflows/ci.yml` — pinned CI path, including data setup, engine/web tests, canonical renders, and determinism checks.
- `scripts/check-*.sh` — local feedback layers; `check-full.sh` is the heavy release-candidate approximation.
- `scripts/score-project.py` — machine evidence for the hard-gate rubric.

## 4. Hard invariants

### 4.1 One computational core

Do not duplicate astronomical or sidereal calculations inside `web/`, templates, render layouts, or product-specific code.

- Convert local input to an `Instant` once and pass it downstream.
- Compute bodies through `ephem.py` rather than calling Swiss independently elsewhere.
- Prefer `SkyState` or domain result objects as layout/UI inputs.
- If a new product needs new maths, add that maths to the engine and expose a reusable result object.

### 4.2 Scheme choices are explicit

`Scheme` owns choices that can move results: ayanamsa, nakshatra-boundary scheme, house system, calendar, and lunar-node convention.

- Do not introduce a hidden ayanamsa, calendar, node, or house-system choice.
- Preserve the scheme on results/outputs so a computation can be reproduced.
- Remember Swiss sidereal mode is process-global state; use the existing `Scheme.apply()` path rather than assuming prior state.
- If traditions disagree, model the disagreement as an explicit variant/scheme/ruleset; do not silently choose one.

### 4.3 Time is a scientific input, not formatting

Do not re-derive Julian days downstream of `time.py`.

Preserve these behaviors unless the task explicitly changes them:

- astronomical year numbering internally (`1 BCE == year 0`);
- explicit Julian/Gregorian handling;
- historical timezone behavior and Local Mean Time where applicable;
- refusal of ambiguous DST folds and nonexistent local times instead of guessing;
- Delta-T uncertainty for ancient dates and the extrapolation flag.

Ancient-time code needs tests at real edge cases, not only modern happy paths.

### 4.4 Ephemeris integrity and independent evidence

Production astronomy uses the vendored Swiss Ephemeris path. A silent Moshier fallback is a correctness failure.

- Do not weaken/remove the test that proves Swiss is using `FLG_SWIEPH` data.
- Do not loosen reference tolerances merely to make a change pass.
- Do not replace independent-reference tests with tests that compare two functions sharing the same implementation or ephemeris.
- For changes that can move astronomical results, use an independent authority/implementation where practical (the existing suite uses JPL DE421/Skyfield, Hipparcos, the Calendar Reform Committee anchor, and historical eclipse dates).
- If reference data are missing and tests skip, say so; a skipped reference suite is not independent verification.

### 4.5 Rules and Jyotish conventions are data with provenance

If a convention is naturally tabular or source-dependent, prefer versioned YAML under `engine/data/rules/` over hard-coded branches.

- Keep a rule-set id/source/note where the surrounding data format does so.
- Cite the source and identify the variant/tradition when disagreement is possible.
- Add structural/boundary tests for rule data.
- Do not describe a Jyotish convention as scientifically established.
- Where the plan requires reconciliation with independent Jyotish software or a human check, do not pretend an astronomy reference test settles that convention question.

### 4.6 Historical claims do not become verdicts

The claims subsystem records what a proposal asks for and what the computed sky did.

- Loading/evaluating a claim does not endorse it.
- Preserve `citation_status` and `date_status` semantics.
- Never change `unverified` -> `verified` or `placeholder` -> `stated` without actually checking the relevant primary/authoritative source.
- Do not make the evaluator decide whether a historical proposal is "true". Counts such as "N of M constraints met" are allowed; adjudication is not.
- Keep scheme/tolerance choices visible in claim data/result evidence.

### 4.7 Rendering is deterministic evidence

The rendering pipeline is intentionally reviewable and reproducible.

- Same inputs must remain byte-identical SVG and pixel-identical PNG unless an intentional output change is being made.
- Do not add timestamps, random ids, unstable attribute ordering, or environment-dependent layout behavior.
- Preserve the pinned/resolved font + `resvg` path and Devanagari shaping checks.
- Do not regenerate a golden merely because the golden test failed. First decide whether the visual change is intended and inspect the diff/output.

For an intentional golden change, the existing regeneration path is:

```bash
cd engine
SKURIOUS_UPDATE_GOLDEN=1 uv run pytest tests/test_render.py
```

Review the changed golden before treating the update as valid.

### 4.8 Web privacy/statelessness is an architecture property

Treat a card token as birth/time/place data.

Preserve these properties unless the task explicitly redesigns privacy/storage:

- names do not enter the encoded token;
- analytics do not store the raw token, names, or birth details;
- token references in analytics remain hashed;
- malformed/damaged tokens fail loudly instead of drawing a plausible wrong sky;
- analytics failures do not take the product page down.

Do not add persistent personal-data storage as a convenience refactor.

### 4.9 Scope and staging

The roadmap contains future modules/features. Do not build them opportunistically while solving an unrelated task.

For autonomous Stage 2 work, `PROJECT_DONE.md` is the scope contract. Prefer the smallest coherent change that improves a named rubric gap or is a documented prerequisite. Avoid speculative framework migrations or broad refactors unless they directly reduce risk or are requested.

### 4.10 Licensing/data provenance

The engine/web are currently AGPL-3.0-or-later and depend on Swiss Ephemeris licensing choices.

Do not change licensing, remove attribution/checksum machinery, or introduce data/dependencies with incompatible redistribution terms without an explicit licensing task and supporting evidence.

## 5. Working procedure

Before editing:

1. Read the target module and the nearest tests.
2. Identify which truth lane(s) the change touches: astronomy, Jyotish convention, historical attribution, presentation/privacy.
3. Find the existing owner of the behavior; do not create a second owner.
4. Identify what evidence decides correctness: unit/boundary tests, independent astronomical reference, cited rule table, primary historical source, golden render, or browser behavior.
5. For project-completion work, identify the exact rubric domain/gate and acceptance criteria before writing.

While editing:

- make the smallest coherent change;
- preserve public behavior not named by the task;
- prefer existing abstractions over parallel implementations;
- add tests that can fail for the intended bug/requirement, not tests that merely mirror the implementation;
- keep assumptions explicit in data/types/results.

After editing:

1. Run the narrowest meaningful tests first.
2. Run the broader suite required by the change class.
3. Review the diff for unintended architecture, source/provenance, privacy, or deterministic-output changes.
4. Report any skipped/unavailable independent checks instead of presenting them as passed.
5. For loop work, rescore only from actual evidence and record the outcome in `plans/stage-2/RESULTS.md`.

## 6. Verification matrix

Prefer the root check scripts for routine agent loops; the direct commands below are the underlying focused paths.

### Fast feedback

```bash
bash scripts/check-fast.sh
```

### Pure time/sidereal arithmetic

```bash
cd engine
uv run pytest -q tests/test_time.py tests/test_sidereal.py
```

### Ephemeris / stars / numerical astronomy

```bash
bash scripts/check-science.sh
```

or directly:

```bash
cd engine
uv run pytest -q tests/test_ephem.py tests/test_stars_sky.py tests/test_reference.py -rs
```

`test_reference.py` is an independent gate only when its reference data are present. If it skips, state that explicitly. The fetch command used by the repo is `uv run --project engine scripts/fetch_reference.py` from the repository root.

### Historical claims / eclipse / conjunction logic

```bash
cd engine
uv run pytest -q tests/test_claims.py
```

If the change can move astronomical results/search behavior, also run the relevant reference tests.

### Rendering / themes / SVG / raster

```bash
bash scripts/check-render.sh
```

or directly:

```bash
cd engine
uv run pytest -q tests/test_render.py -rs
```

`resvg` is required for the meaningful raster/Devanagari/golden checks. A skip because `resvg` is unavailable is not render verification.

### Token/privacy changes

```bash
cd engine
uv run pytest -q tests/test_token.py
cd ../web
uv run pytest -q
```

### Web routes/templates/static behavior

```bash
bash scripts/check-web.sh
```

For visual UI work, use a real browser/browser tool when available; a `200` response alone is not visual verification.

### Machine rubric evidence

```bash
python scripts/score-project.py
```

Use `--strict` only for a release-candidate gate, because Stage 2 development is expected to contain legitimate `UNVERIFIED` gates before it is complete.

### Full release-candidate local check

```bash
bash scripts/check-full.sh
```

This intentionally fails as `UNVERIFIED` when required reference data or `resvg` are unavailable. For substantial changes, CI in `.github/workflows/ci.yml` remains the final repository-level gate because it installs the pinned renderer/data and reproduces the canonical renders twice.

## 7. Multi-agent work

Parallelize **read-only investigation, source checking, and review** when that improves speed or quality.

For writes:

- one agent should own a coherent change surface at a time;
- use separate Git worktrees/branches for genuinely independent implementations;
- avoid multiple agents editing the same files concurrently;
- use an independent reviewer for high-impact astronomy, provenance, privacy, or rendering changes when agent tooling supports it.

For project-completion loops, use the task-selection/anti-thrashing rules in the `loop-runner` skill. Do not spawn agents merely to increase agent count.

## 8. Definition of done

For ordinary tasks, a change is done when:

- the requested behavior is implemented;
- relevant targeted tests pass;
- required broader/reference/render/web checks pass or any unavailable checks are explicitly disclosed;
- no hidden scheme/time/provenance assumption was introduced;
- no computation was duplicated across engine/web/layout layers;
- historical/Jyotish claims retain correct epistemic labels;
- privacy/statelessness is preserved unless intentionally changed;
- intentional render changes have been visually/diff reviewed;
- affected documentation is consistent with the resulting code when the task changes architecture or product status.

For autonomous Stage 2 project completion, the stricter release condition in `PROJECT_DONE.md` and `QUALITY_SCORE.md` controls completion. Stop when it is satisfied; do not continue into later roadmap stages automatically.
