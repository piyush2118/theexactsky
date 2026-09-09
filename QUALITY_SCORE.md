# Quality Score — Stage 2

This rubric is the optimization target for the Stage 2 engineering loop defined in `PROJECT_DONE.md`.

It has two layers:

1. **hard release gates** — binary constraints; any failure blocks release;
2. **weighted quality score** — used to hill-climb among otherwise safe states.

Do not trade a hard gate for weighted-score gains.

## 1. Hard release gates

Use `PASS`, `FAIL`, or `UNVERIFIED`.

`UNVERIFIED` blocks release just like `FAIL` when the gate is required for the changed/release surface.

| Gate | Requirement | Primary evidence |
|---|---|---|
| G1 Scientific ephemeris integrity | Swiss is using vendored `FLG_SWIEPH` data; relevant independent astronomical reconciliation passes | `engine/tests/test_reference.py`, CI data setup |
| G2 Time/calendar integrity | BCE numbering, calendar selection, LMT/timezone behavior, DST folds/gaps and ancient Delta-T handling remain explicit and tested | `engine/tests/test_time.py` |
| G3 Explicit conventions | Result-changing scheme/ruleset choices are explicit and reproducible; no hidden ayanamsa/node/calendar/house-system variant | `Scheme`, rule data, focused tests/review |
| G4 Claim epistemic integrity | Unverified/placeholder historical material stays labeled; evaluator reports evidence rather than historical verdicts | claim YAML + `test_claims.py` |
| G5 Deterministic/render integrity | Required render tests run with `resvg`; deterministic SVG/PNG and Devanagari shaping/golden checks pass | `test_render.py`, CI canonical renders |
| G6 Privacy/statelessness | Names/raw tokens/birth details are not persisted in Stage 2 analytics; damaged tokens fail loudly | `test_token.py`, web privacy tests |
| G7 Single computation core | Web/layout/product code does not become an independent astronomy/sidereal implementation | architecture review + static checks where available |
| G8 Licensing/data provenance | AGPL/current Swiss/data/font licensing and checksum/attribution assumptions remain compatible with the release candidate | license/dependency/data review |
| G9 Jyotish reconciliation | `north-standard-v1` is reconciled on the planned 20 fixed pairs against two independent Jyotish implementations/programs, with disagreements explicitly resolved | recorded reconciliation artifact + tests |
| G10 Integrated release | Full repository CI is green on the release candidate, including canonical render reproduction/determinism | GitHub Actions |

### Gate discipline

- A passing self-consistency test is not enough for G1.
- A skipped reference suite is `UNVERIFIED`, not `PASS`.
- A render suite skipped because `resvg` is absent is `UNVERIFIED`, not `PASS`.
- JPL/Skyfield agreement does not satisfy G9.
- Do not promote a historical citation/date status merely to make G4 green.
- Do not weaken test tolerances, privacy tests, or deterministic-output checks to improve a score.

## 2. Scoring scale

Every quality domain is scored 0–4.

| Score | Meaning |
|---:|---|
| 0 | absent, materially broken, or not started |
| 1 | rough/partial prototype; major requirements missing |
| 2 | happy path works but robustness, coverage, evidence, or polish is incomplete |
| 3 | robust, tested, integrated, and suitable for release with minor remaining polish |
| 4 | release-grade; edge cases/evidence/polish are strong and independent verification is present where the domain requires it |

Weighted contribution:

```text
contribution = domain_weight * domain_score / 4
```

The weighted total is out of 100.

## 3. Weighted Stage 2 rubric

| Domain | Weight | What earns 4/4 |
|---|---:|---|
| Scientific correctness | 16 | Numerical changes are independently reconciled where applicable; ephemeris integrity is proven; assumptions are explicit; no known scientific correctness gaps |
| Time & historical astronomy | 7 | Modern/ancient/calendar/timezone/LMT/Delta-T edge cases are robust and downstream day-boundary behavior is tested |
| Jyotish implementation & provenance | 14 | Kundali/kuta/dosha/cancellation rules are versioned, cited, boundary-tested and independently reconciled against the required Jyotish references |
| Historical claim rigor | 6 | Claims preserve source/date verification status, explicit schemes/tolerances and evidence-only evaluation; source-sensitive edits are verified |
| Engine architecture | 9 | One reusable computation core; clear domain objects; Stage 2 maths lives in engine; minimal duplication/coupling |
| Product completeness | 16 | Every in-scope item in `PROJECT_DONE.md` works end-to-end; no required Stage 2 flow is still a stub |
| UX & visual quality | 10 | Two-person flow, result, band slider, share/download and waitlist are polished and browser-reviewed on representative desktop/mobile sizes |
| Render/output quality | 6 | Compatibility card is deterministic, legible, typographically correct, share-ready, and has intentional/golden-reviewed output |
| Privacy & security | 6 | Stateless pair flow preserves token/name/privacy boundaries, hostile/invalid inputs fail safely, secrets/storage boundaries are appropriate |
| Reliability & operations | 5 | Deployment, rate limiting, health, backups, cache behavior and important failure paths are release-ready |
| Agent legibility / harness | 5 | Agents can locate owners, run fast/specialist/full checks, understand current milestone, score progress, and stop without reconstructing the project from chat |
| **Total** | **100** | |

## 4. Domain scoring notes

### Scientific correctness — 16

Score 4 requires more than a green unit suite. Relevant independent evidence must be available and actually run.

Downgrade when:

- reference tests are skipped;
- new numerical logic lacks independent comparison where one is practical;
- hidden coordinate/time/scheme assumptions exist;
- a tolerance was chosen for convenience rather than justified behavior.

### Time & historical astronomy — 7

Score 4 requires preservation of the repo's deliberate hard cases: BCE numbering, Julian/Gregorian handling, historical offsets/LMT, DST folds/gaps, Delta-T uncertainty and event-day correctness.

### Jyotish implementation & provenance — 14

Score 4 requires the Stage 2 reconciliation gate, not only well-written YAML/tests.

If `north-standard-v1` is implemented but the two-program 20-pair reconciliation is not completed, this domain cannot exceed **2/4** and G9 remains `UNVERIFIED`.

### Historical claim rigor — 6

Score 4 requires that claim/data changes remain attributable and epistemically precise. Existing unverified claims may remain unverified without lowering the score if the product truthfully exposes that state; falsely upgrading them is a gate failure.

### Engine architecture — 9

Score 4 means:

- `Instant` remains the time boundary;
- `Scheme`/versioned rules own convention choices;
- Stage 2 computations return reusable domain results;
- web/templates/layouts consume results rather than recomputing them;
- no speculative architecture migration is needed for release.

### Product completeness — 16

Use `PROJECT_DONE.md` as the checklist. A missing required Stage 2 subsystem prevents 4/4.

A polished one-person sky page does not compensate for a missing two-person compatibility flow.

### UX & visual quality — 10

Do not award 4 from source inspection alone.

Evidence should include real browser interaction/screenshots for at least:

- representative desktop width;
- representative mobile width;
- form validation/error path;
- result page;
- uncertainty-band interaction;
- share/download action;
- waitlist door/modal/confirmation;
- console/network sanity.

### Render/output quality — 6

Score 4 requires meaningful render checks with the intended renderer/fonts installed and intentional review of any golden/output changes.

### Privacy & security — 6

Score 4 means the Stage 2 pair flow maintains the current privacy architecture and relevant negative/hostile-input tests.

### Reliability & operations — 5

Score 4 requires a deployable release path, not merely local route tests.

### Agent legibility / harness — 5

Score 4 when an agent can:

- read the milestone and constraints;
- choose the right owner/module;
- choose the right verification lane;
- gather objective evidence;
- update the active execution plan/results;
- diagnose missing harness/tooling instead of thrashing;
- stop at Stage 2 when the release condition is satisfied.

## 5. Release threshold

Stage 2 is release-ready only if:

```text
all hard gates == PASS
weighted score >= 90/100
no domain < 3/4
CI == green
```

The weighted score is not a substitute for the gates.

## 6. Scoring evidence format

Do not write unsupported numbers such as `UX = 4/4`.

For every changed score, record:

```text
Domain:
Score: N/4
Evidence:
- command/check/source/review
- command/check/source/review
Known gaps:
- ...
Reviewed at:
Reviewer/agent:
```

Objective test evidence should come from `scripts/score-project.py`, specialist check scripts, or CI where possible.

Subjective/product evidence should cite the actual browser/source/review performed.

## 7. Baseline rule

Do not infer a baseline score merely from roadmap prose or from the existence of test files.

The active loop must establish the current baseline from the checked-out commit by:

1. running `python scripts/score-project.py` (or the equivalent commands if the script cannot run);
2. inspecting current Stage 2 code against `PROJECT_DONE.md`;
3. browser-reviewing any domain whose score depends on visual/product behavior;
4. recording the evidence and scores in `plans/stage-2/EXEC_PLAN.md`.

Until that is done, the baseline is **unscored**, not zero and not assumed green.

## 8. Hill-climb priority

Among states where all already-established hard gates remain green, prioritize candidate work approximately by:

```text
priority = (rubric_points_available * confidence_of_gain)
           / (effort * regression_risk)
```

This is a decision aid, not a reason to game estimates.

A change may also be accepted without immediate rubric gain when it is a clearly documented prerequisite/enabler for a named rubric gap.

## 9. Anti-gaming rules

Never increase the score by:

- deleting or weakening tests;
- loosening scientific tolerances without evidence;
- relabeling `unverified` data as verified;
- counting skipped checks as passing;
- hiding an assumption/default;
- removing required Stage 2 scope from `PROJECT_DONE.md` without an explicit user/product decision;
- awarding visual/product points without inspecting the product;
- adding code volume or agent count that does not improve a scored outcome or required prerequisite.
