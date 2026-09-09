---
name: scientific-change
description: Use for changes that can alter astronomical, sidereal, historical-claim, or Jyotish-rule results in TheExactSky/Skurious. Guides source inspection, explicit assumptions, independent verification, provenance, and result reporting.
---

# Scientific Change Skill

Use this skill when a task can change any computed sky result, historical-claim evaluation, time/calendar behavior, sidereal/Jyotish convention, astronomical search, or sourced rule data.

Typical triggers:

- edits to `engine/skurious/time.py`, `sidereal.py`, `ephem.py`, `stars.py`, `sky.py`, or `claims/`;
- edits to `engine/data/rules/` or `engine/data/claims/`;
- adding a new astronomical body/result, ayanamsa, house-system choice, rule table, eclipse/conjunction behavior, historical constraint type, or ancient-date behavior;
- a bug report where a chart, nakshatra, conjunction, eclipse, historical plate, or scheme-dependent result is wrong;
- any refactor that claims to preserve numerical outputs in those areas.

Do not use this skill for copy-only changes, ordinary CSS changes, generic deployment plumbing, or unrelated documentation edits unless they alter scientific/provenance meaning.

## Goal

Produce a change whose correctness can be explained in terms of **independent evidence and explicit assumptions**, not merely "the tests pass".

The repository has four different evidence lanes. Identify which one(s) apply before editing:

1. **Astronomical/numerical evidence** — independent ephemeris/catalogue/anchor/event data.
2. **Jyotish convention evidence** — a cited rule source plus explicit variant/scheme, sometimes requiring independent Jyotish software or human reconciliation.
3. **Historical attribution evidence** — what a source actually states and whether citation/date status is verified.
4. **Regression/behavior evidence** — boundary tests, deterministic output, end-to-end behavior.

Do not use evidence from one lane to overclaim another. JPL can validate planetary positions; it cannot establish a Jyotish convention or a historical proposal's truth.

## Procedure

### 1. Locate the existing owner

Before writing code, inspect the relevant code and tests.

Use these ownership rules:

- local date/time/place -> `Instant`: `engine/skurious/time.py`;
- ayanamsa/sidereal arithmetic/scheme: `engine/skurious/sidereal.py`;
- body positions/rise-set: `engine/skurious/ephem.py`;
- star positions: `engine/skurious/stars.py`;
- layout-facing computed sky: `engine/skurious/sky.py`;
- historical claim model/evaluation/search: `engine/skurious/claims/`;
- sourced convention tables: `engine/data/rules/`;
- historical proposal data: `engine/data/claims/`.

Do not create a second implementation in web/templates/render code for behavior already owned by the engine.

### 2. Write down the assumptions that can move the answer

For the specific task, explicitly identify the relevant subset of:

- calendar (`julian`, `gregorian`, `auto`);
- astronomical year numbering for BCE dates;
- timezone vs Local Mean Time;
- Delta-T and whether uncertainty matters;
- geocentric/topocentric choice;
- tropical/sidereal coordinates;
- apparent/mean convention if relevant;
- ayanamsa;
- nakshatra-boundary scheme;
- house system;
- mean vs true lunar node;
- observer/place;
- search window/tolerance;
- rule-set/tradition/source.

If an assumption is currently implicit but can move the result, prefer making it explicit rather than adding another hidden default.

### 3. Classify the change

Use one or more of these classes:

#### A. Time/calendar change

Risks include day shifts, DST folds/gaps, BCE year errors, historical offsets, sunrise/day-boundary errors, and ancient Delta-T effects.

Required mindset:

- time is a scientific input, not presentation;
- do not re-derive Julian days downstream;
- ambiguous/nonexistent local times must not be guessed;
- ancient tests should include actual ancient inputs.

Primary tests:

```bash
cd engine
uv run pytest -q tests/test_time.py
```

Add downstream claim/ephemeris tests if the change can move computed sky positions or event dates.

#### B. Ephemeris / body / star change

Risks include wrong flags, process-global sidereal mode, silent Swiss fallback, coordinate-system confusion, wrong azimuth convention, and duplicated calculations.

Required checks:

- compute through the existing ephemeris path;
- preserve `FLG_SWIEPH` usage;
- do not accept a self-consistency test as the only evidence;
- compare against independent reference data where practical.

Primary tests:

```bash
cd engine
uv run pytest -q tests/test_ephem.py tests/test_stars_sky.py tests/test_reference.py -rs
```

If `test_reference.py` skips because reference files are absent, report that as **not independently verified locally**. Do not phrase skipped tests as a pass.

#### C. Sidereal / Jyotish convention change

Risks include hidden tradition choices and treating convention as astronomy.

Required checks:

- put source-dependent/tabular rules in versioned data when appropriate;
- identify the source and variant;
- add exact-boundary/structure tests;
- preserve the `Scheme` mechanism for choices that move numbers;
- if two traditions disagree, model both or explicitly choose the requested one; never silently merge them.

Primary tests:

```bash
cd engine
uv run pytest -q tests/test_sidereal.py
```

If the change affects positions, also run the ephemeris/reference tests.

When independent Jyotish-program reconciliation is required, say whether that human/external check was actually performed. The existing `tests/fixtures/jyotish_reconciliation.tsv` workflow exists precisely because JPL does not settle Jyotish convention.

#### D. Historical claim / claim-DSL change

Risks include converting an encoded proposal into an endorsement, comparing incomparable assumptions, using placeholder dates as facts, or making the evaluator adjudicate truth.

Required checks:

- preserve the stated/computed/evidence split;
- keep scheme and tolerances explicit;
- `citation_status: verified` requires actual source checking;
- `date_status: stated` requires evidence the source states that date;
- a result such as `3 of 4 constraints met` is acceptable; "therefore this date is true" is not engine output.

Primary tests:

```bash
cd engine
uv run pytest -q tests/test_claims.py
```

If a constraint/search change depends on astronomy, also run the relevant reference tests.

### 4. Build a test that would catch the actual failure

Before or alongside the fix, add/identify a test whose failure mode matches the bug or requirement.

Prefer:

- exact boundary cases;
- known external events;
- independent implementations/catalogues;
- deliberately awkward real-world inputs;
- a "guard on the guard" when the verification itself could accidentally become vacuous.

Avoid:

- expected values generated by the same function under test;
- copying implementation arithmetic into the test and calling that independent;
- loosening tolerances until a failing result becomes green;
- regenerating goldens before deciding whether output change is intended.

### 5. Implement the smallest coherent change

During implementation:

- keep one source of computation;
- preserve domain objects (`Instant`, `Scheme`, `BodyPosition`, `SkyState`, claim result objects) rather than passing loose parallel values;
- surface assumptions/provenance in data or result evidence where readers need them;
- do not opportunistically implement roadmap features outside the task.

### 6. Verify in layers

Run targeted tests first, then the broader gates required by the change.

For a substantial numerical change, a strong local sequence is:

```bash
cd engine
uv run pytest -q tests/test_time.py tests/test_sidereal.py tests/test_ephem.py tests/test_claims.py
uv run pytest -q tests/test_reference.py -rs
```

Run rendering tests too if the changed values appear in canonical outputs:

```bash
uv run pytest -q tests/test_render.py -rs
```

Run web tests if the changed result is exposed through the site:

```bash
cd ../web
uv run pytest -q
```

The repository CI is the final integrated gate for substantial changes because it sets up pinned data/renderer inputs and re-renders the canonical outputs twice for determinism.

### 7. Report the result with epistemic precision

At completion, report these four items when applicable:

1. **What changed.**
2. **Which assumptions/convention are now in force.**
3. **What evidence was run** — targeted tests, independent reference, source check, reconciliation, render/browser check.
4. **What remains unverified** — skipped reference data, unperformed human/Jyotish reconciliation, unverified citation, unresolved historical uncertainty, etc.

Use wording such as:

- "matches JPL DE421 within the existing tolerance" rather than "scientifically proven";
- "implements the cited Lahiri/equal-boundary convention" rather than "astrology is correct";
- "the proposal meets 2 of 3 encoded constraints" rather than "the proposed date is true";
- "citation remains unverified" when it has not been checked.

## Stop conditions

Do not mark the task complete if any of these are true and material to the requested change:

- a hidden scheme/calendar/node/tradition choice was introduced;
- a numerical change lacks a meaningful regression test;
- required independent-reference tests were skipped and this is not disclosed;
- a historical citation/date was promoted to verified/stated without source checking;
- a Jyotish convention was presented as an astronomical fact;
- the web/render layer now contains a duplicate calculation that belongs in the engine;
- a golden was updated without establishing that the output change was intended.
