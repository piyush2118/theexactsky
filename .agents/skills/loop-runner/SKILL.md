---
name: loop-runner
description: Use when driving TheExactSky/Skurious Stage 2 toward completion across multiple engineering iterations. Establishes hard-gate/rubric baseline, selects the highest-value safe task, delegates investigation/review, implements one coherent change, verifies it, rescoring with evidence, and improves the harness when progress stalls.
---

# Stage 2 Loop Runner

Use this skill for substantial "continue/finish Stage 2", autonomous project-completion, hill-climb, or multi-iteration work.

Do not use it for a single narrowly specified edit that can be completed and verified directly.

## Governing files

Read these before selecting work:

1. `AGENTS.md`
2. `PROJECT_DONE.md`
3. `QUALITY_SCORE.md`
4. `plans/stage-2/EXEC_PLAN.md`
5. `plans/stage-2/RESULTS.md`
6. any task-specific skill, especially `scientific-change` when numerical/Jyotish/claim results can move

The user can override the milestone/scope. Otherwise Stage 2 is the finish line; do not start Stage 3 automatically.

## Mental model

The repository state is the candidate solution.

The optimization objective is:

```text
maximize weighted Stage 2 quality score
subject to every established hard gate remaining green
and all PROJECT_DONE.md scope being completed
```

A weighted-score gain never justifies a hard-gate regression.

## Three nested loops

### Inner loop — finish one coherent work item

```text
acceptance criteria
    -> inspect owner/tests
    -> implement
    -> targeted verification
    -> independent/specialist review
    -> fix
    -> broader verification
```

### Outer loop — hill-climb the milestone

```text
baseline/rescore
    -> find highest-value viable gap
    -> run inner loop
    -> rescore with evidence
    -> keep/revise/revert/block
    -> choose next gap
```

### Meta loop — improve the harness

When the agent repeatedly fails for the same reason, ask what capability was missing:

- invariant/documentation?
- test/eval?
- observable/browser/tool?
- source/reference data?
- task skill?
- ownership boundary?
- fast feedback command?

Improve the harness when that is the root cause. Do not merely add "be more careful" prose after every mistake.

## Procedure

### 1. Establish or refresh baseline

If the active plan does not contain fresh evidence for the checked-out commit, start with:

```bash
python scripts/score-project.py
```

Use specialist checks when required:

```bash
bash scripts/check-fast.sh
bash scripts/check-science.sh
bash scripts/check-render.sh
bash scripts/check-web.sh
```

For a release candidate:

```bash
bash scripts/check-full.sh
python scripts/score-project.py --strict
```

Do not infer green gates from test-file existence or historical prose.

Then score the weighted domains in `QUALITY_SCORE.md` from:

- machine evidence;
- code/architecture inspection;
- cited source/reconciliation evidence;
- real browser/product inspection for UX;
- actual CI for G10.

Update `plans/stage-2/EXEC_PLAN.md` with evidence, not optimistic guesses.

### 2. Build the candidate task set

Use `PROJECT_DONE.md`, rubric gaps, current blockers and dependency map.

Discard candidates that:

- are outside Stage 2;
- are blocked by an unmet prerequisite;
- knowingly break a hard gate;
- are speculative rewrites without a scored/prerequisite benefit.

Include required enablers even if they have no immediate weighted-score gain, but name the downstream criterion they unlock.

### 3. Prioritize the next safe uphill move

Estimate each viable candidate:

- rubric points available;
- confidence the task improves those points;
- effort;
- regression risk.

Use this as a rough ranking aid:

```text
priority = (rubric_points_available * confidence)
           / (effort * regression_risk)
```

Do not game estimates. Dependencies and hard gates dominate the formula.

Choose **one coherent change surface** for the writing phase.

### 4. Define acceptance criteria before editing

For the selected item, write down:

- exact user/product outcome;
- files/domain owner likely involved;
- rubric domain(s) targeted;
- hard gates that could be affected;
- targeted tests;
- independent/source/browser evidence required;
- explicit stop condition.

If the work can change scientific/Jyotish/historical results, invoke the `scientific-change` workflow as part of this inner loop.

### 5. Delegate investigation and review, not ownership chaos

When multi-agent tools are available, parallelize independent read-only work such as:

- codebase mapping;
- astronomy review;
- Jyotish source/convention review;
- test-gap analysis;
- UI/browser criticism;
- security/privacy review;
- final adversarial diff review.

Use one writer for one coherent change surface. Use separate worktrees/branches for genuinely independent writes.

Do not spawn agents to increase agent count.

### 6. Implement the smallest coherent change

Preserve repository ownership/invariants from `AGENTS.md`.

Avoid:

- opportunistic later-stage work;
- broad framework migrations;
- duplicated calculations;
- hidden convention defaults;
- tests that merely copy the implementation;
- premature golden regeneration.

### 7. Verify in layers

Run the narrowest test that can falsify the work first.

Then run the change-class specialist gate.

Then obtain the non-code evidence the criterion needs:

- independent astronomy reference;
- independent Jyotish reconciliation;
- primary historical source;
- browser/screenshots/console/network inspection;
- render/golden review;
- architecture/privacy review.

Before keeping a substantial change, run the appropriate broader/full checks.

A skip is a missing observation, not success.

### 8. Independent review

Before finalizing a high-impact work item, ask an independent reviewer/agent to look specifically for:

- wrong assumptions;
- duplicated computation;
- self-consistency masquerading as independent evidence;
- hidden tradition/scheme choices;
- source/status overclaiming;
- privacy regressions;
- unintended render changes;
- test gaps that would let the bug survive.

Address findings or record why they are not applicable.

### 9. Rescore only affected domains

Record actual evidence in `plans/stage-2/RESULTS.md`.

A task outcome is:

- **KEEP** — hard gates preserved and rubric improves, or it is a documented prerequisite for a named gap;
- **REVISE** — promising but acceptance criteria are not yet satisfied;
- **REVERT** — regression/risk exceeds benefit or gates fail;
- **BLOCKED** — genuine human/external/source/tool dependency prevents completion.

Do not increase a score because code volume increased.

### 10. Anti-thrashing rule

Maximum three implementation/review cycles on one work item without measurable progress.

If the same acceptance criterion fails twice:

1. stop editing;
2. diagnose missing assumption/tool/test/data/doc/owner;
3. improve the harness or re-plan;
4. only then attempt another implementation.

If two coherent approaches fail to improve the criterion, record a blocker/re-plan rather than entering an unbounded rewrite loop.

### 11. Stop condition

Stop the outer loop when `PROJECT_DONE.md` release condition is satisfied:

- every hard gate PASS;
- weighted score >= 90/100;
- no domain < 3/4;
- release-candidate CI green;
- required Jyotish reconciliation actually completed;
- representative desktop/mobile browser review completed;
- no unresolved release blocker.

Report Stage 2 as release-ready and stop.

Do not continue into practitioner/payments/muhurta/content stages without an explicit user decision.

## Completion report format

At the end of each substantial loop run, report:

1. starting -> ending commit/state;
2. work item completed;
3. hard-gate changes;
4. rubric score changes with evidence;
5. commands/references/browser reviews actually run;
6. skipped/unverified checks;
7. next highest-value gap or human blocker;
8. any harness improvement made because the agent struggled.
