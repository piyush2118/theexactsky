# Project Done — Stage 2 Forwardable Compatibility Card

This file defines the current bounded engineering milestone for autonomous/agentic work on TheExactSky / Skurious.

It is intentionally **not** the whole multi-year roadmap. A loop that is told to "finish the project" must stop at this milestone unless the user explicitly selects a later stage.

## Target

Ship the roadmap/technical-plan **Stage 2 forwardable compatibility card** as a release-grade public feature, while preserving the existing one-person sky and historical-claims capabilities.

The Stage 2 product answers a two-person compatibility query using the same astronomical engine, explicit Jyotish rules, and a birth-time uncertainty band, then produces a forwardable 1080×1350 card and a reproducible stateless result link.

## In scope

### Engine

Stage 2 is not complete until all of these exist and are integrated:

- `kundali` computation as a reusable engine/domain result;
- `kuta` / Ashtakoota using a versioned `north-standard-v1` rule set;
- doshas and applicable cancellations represented with evidence;
- `band` computation for approximate birth-time uncertainty;
- a `kuta_card` deterministic layout showing:
  - guna total;
  - all eight koota rows;
  - doshas;
  - applicable cancellations;
  - uncertainty-band result/curve;
  - URL/product identity;
  - rule-set/scheme identity.

Astronomical computation must continue to flow through the existing `Instant` / `Scheme` / ephemeris paths. Product-specific code must not become a second astronomy implementation.

### Jyotish provenance and reconciliation

Before Stage 2 is release-ready:

- every source-dependent koota/dosha/cancellation table is versioned and cited;
- regional/source variants are not silently merged;
- `north-standard-v1` has fixed regression vectors;
- the planned reconciliation against **two independent Jyotish programs/implementations** on 20 fixed input pairs has actually been performed and recorded;
- any disagreement is resolved as an explicit sourced convention, not hidden in code;
- astronomy-reference agreement is not presented as a substitute for Jyotish-convention reconciliation.

### Stateless pair token

The public compatibility result must be reproducible without a chart database.

The pair-token design must support:

- two subjects;
- each subject's UTC minute and place identity;
- approximate-time flags;
- rule-set/version information;
- integrity checking so damaged/tampered tokens fail loudly;
- the current privacy property that names are not encoded in the token.

If the Stage 2 manual-coordinate form from the technical plan is retained, its quantized-coordinate representation must be explicitly versioned/tested rather than ambiguously overloading a place id.

### Public web flow

The release must provide the Stage 2 flow, whether route names remain exactly as planned or are intentionally versioned/migrated:

- a two-person form with date, time, place typeahead, and an "approximate time" control for each person;
- validation that refuses ambiguous/nonexistent local times rather than guessing;
- a reproducible stateless result URL;
- results page with the compatibility card and uncertainty-band interaction;
- a card PNG endpoint suitable for OpenGraph/WhatsApp previews;
- machine-readable band data for the interactive slider;
- share/download actions;
- OpenGraph metadata whose image resolves successfully;
- the existing health endpoint or equivalent operational health check.

Existing `/sky`, `/s/...`, `/claims`, and other working features may remain. They do not substitute for the pair-compatibility flow and should not be broken by Stage 2 work.

### Forwardability and product instrumentation

The Stage 2 release must include:

- WhatsApp/share flow with the result URL;
- card download flow;
- result/card/share/download event instrumentation;
- two instrumented product doors (PDF and named-astrologer review);
- waitlist capture for the selected door;
- analytics keyed by session and **token hash**, not raw birth-detail token;
- no IP logging added by the application;
- analytics failures must not take down the result experience.

### Operations

Before release:

- Docker Compose/Caddy deployment remains reproducible;
- per-IP rate limiting is configured at the appropriate edge/proxy layer;
- SQLite backup procedure is documented/automated as planned;
- uptime/health monitoring can exercise `/healthz` or its replacement;
- secrets remain outside git;
- data retention/storage behavior matches the current Stage 2 stateless design.

## Out of scope for this milestone

Do **not** expand the autonomous loop into later roadmap stages unless explicitly requested.

Out of scope includes:

- practitioner second-opinion checkout/order/upload workflow;
- persistent hospital-record or reading storage;
- payments/webhooks for Stage 3;
- `panchanga` / `muhurta` planner products;
- planner subscriptions;
- content/CMS/blog infrastructure;
- mobile apps;
- frontend-framework migration for its own sake;
- accounts or a chart database;
- Kubernetes/microservices;
- generic AI-written astrological interpretation.

## Hard release gates

All hard gates in `QUALITY_SCORE.md` must be `PASS`.

A hard-gate failure blocks release regardless of the weighted score.

## Quality release condition

Stage 2 engineering is complete only when all of the following are true:

1. all hard release gates pass;
2. weighted quality score in `QUALITY_SCORE.md` is **>= 90/100**;
3. no scored quality domain is below **3/4**;
4. repository CI is green on the release candidate;
5. required independent-reference and Jyotish reconciliation checks were actually performed rather than skipped;
6. visual browser review covers the primary desktop and mobile compatibility journeys;
7. no unresolved blocker in `plans/stage-2/EXEC_PLAN.md` prevents a real public release.

## Business gates are measured after engineering release

The roadmap's market gates remain important, but they are not a reason for an engineering loop to fabricate traffic or keep coding indefinitely.

After release, measure separately:

- 1,000 results in 30 days;
- share rate > 20%;
- 100 users on the astrologer waitlist door;
- PDF vs astrologer-door demand.

Failure of a market gate should change the product/roadmap decision; it should not be "fixed" by silently altering the measurement definition.

## Stop rule

When the release condition above is satisfied, the autonomous engineering loop stops and reports Stage 2 as release-ready.

It does not begin Stage 3 automatically.
