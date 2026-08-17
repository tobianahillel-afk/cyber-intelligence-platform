# Lot 28 — Derived-state reconciliation and reactive invalidation recovery

## Status

`PLANNED_LOCKED` as a mandatory part of Lot 28.

Tracking issue: #171 — `Lot 28: derived-state reconciliation and reactive invalidation recovery`.

Audit baseline: merged `main` commit `3b7a3151ff17df59c1a18ac6fb1a7233063dfaf0`.

Current validated product release: `0.24.0`.

Target product release for this implementation: **`0.28.0`**. This planning amendment does not change the current package version.

## Purpose

This amendment closes a cross-module implementation-finality gap discovered after the bounded-context validation of Lots 13–24.

The individual modules contain substantial and generally sound domain models, immutable histories, reconciliation functions, persistence projections, protected APIs, and tests. However, the current runtime does not yet provide one durable mechanism that guarantees that a canonical change automatically reaches every affected derived layer and that a correction, retraction, expiry, suppression, deletion, or identity decision automatically invalidates every downstream result that is no longer justified.

The missing product property is therefore not another provider adapter and not a Source Activation lot. It is **derived-state convergence** across the normal product architecture.

The required invariant is:

```text
new or changed governed source data
  -> immutable observation / claim / evidence
  -> canonical current-state reconciliation
  -> affected derived projections
  -> corporate graph when applicable
  -> commercial signal synthesis when justified
  -> need-hypothesis reconciliation
  -> scoring / opportunity reconciliation
  -> publication-readiness decision
  -> analyst-facing current state
```

and, equally importantly:

```text
correction / retraction / expiry / suppression / deletion
identity merge / identity split / attribution change
rule / taxonomy / projector version change
  -> mark affected derived state dirty
  -> deterministic recomputation
  -> withdraw / expire / supersede unsupported output
  -> preserve history and analyst decisions where still meaningful
  -> prevent stale output from masquerading as current truth
```

## Why this belongs to Lot 28 and not SA-22

SA-21 already owns orphaned **source activation** work. Source Activation decides whether a provider is reviewed, entitled, authorized, executable, scheduled, live-tested, observable, and fully integrated.

The gap documented here exists even with synthetic or already persisted data and therefore cannot be solved by activating another source. It concerns:

- reconciliation queues;
- derived dependency ownership;
- invalidation semantics;
- current-state lifecycle;
- replay/backfill convergence;
- publication gates;
- lineage and freshness;
- failure visibility.

Those are exactly the production-assurance responsibilities already assigned to **Lot 28 — Data quality, reconciliation, lineage, and publication gates**.

No SA-22 is created for this work.

## Historical completion semantics

Lots 13–24 remain immutable completed product lot numbers. This amendment does **not** rewrite their historical closeouts.

Their `IMPLEMENTED_VALIDATED` status means that the bounded-context capability and the exit gate evaluated at the time were validated on their final heads. The later cross-lot audit found that several promises written in the system-level architecture and test strategy were not yet enforced by one platform-wide runtime.

The missing **cross-module finality** is therefore explicitly handed to Lot 28.

Lot 28 must not claim completion by pointing back to local Lot 13–24 tests. It must prove the composed behavior on one exact final head.

## Normative implementation findings

### 1. Collection currently persists local projection families only

The normal collection worker calls `persist_batch_projections(...)`. The current batch contract can persist identity, commercial, procurement, public-footprint, vulnerability, passive-exposure, incident, corporate-change, and threat-indicator projections.

It does not provide a platform-wide derived-reconciliation contract for:

- organization-specific vulnerability applicability;
- relationship intelligence derived from other canonical records;
- corporate-graph refresh;
- professional-context derived changes;
- generalized need-hypothesis reconciliation;
- generalized score/opportunity reconciliation.

**Required completion:** canonical writes must publish minimal durable change facts in the same database transaction. Derived modules must react through a separate reconciliation worker, not through provider-specific imports or ad-hoc calls inside adapters.

### 2. Vulnerability applicability is implemented but not production-reactive

Lot 17 contains deterministic applicability matching and immutable assessment history. `persist_assessment(...)` correctly advances the current projection when explicitly called.

The production collection path does not automatically identify and recompute affected assessments when:

- a passive technology/version observation changes;
- a technology observation expires;
- a vendor advisory revision is corrected or withdrawn;
- affected-version ranges change;
- an organization/asset attribution changes.

**Required completion:** add a scoped applicability reactor that derives the impacted `(organization, asset, product, vulnerability)` set and writes a new assessment snapshot or withdrawal/unknown state as appropriate.

### 3. Procurement-to-relationship conversion exists but is not wired to normal persistence

Lot 19 contains `relationship_bundle_from_procurement(...)`, including assertion/retraction, validity, renewal and service-context semantics.

The standard procurement persistence path updates procurement state but does not invoke that relationship projection bridge.

**Required completion:** procurement canonical changes must enqueue relationship reconciliation. Cancellation, amended provider parties, changed end dates, changed resolution and replay must all converge to the correct relationship state without a manual API call.

### 4. Corporate graph reconciliation is explicit rather than dependency-driven

Lot 20 can load organizations, relationships, passive observations, incidents, corporate changes and applicability into graph snapshots, and its domain reconciler is time-aware.

The production entry point is still an explicit graph refresh. The reconciler being correct when invoked is not equivalent to a guarantee that it is invoked when dependencies or time validity change.

**Required completion:** mark graph subjects dirty from upstream canonical changes and from due time transitions. Reconcile scoped nodes/edges automatically, while retaining the explicit administrative full rebuild as a repair operation rather than the normal correctness mechanism.

### 5. There is no single canonical-to-commercial-signal synthesis layer

`SignalType` already enumerates procurement, jobs, contracts, regulatory change, incidents, vulnerability applicability, passive exposure, technology change, corporate change, relationships, professional context and research discovery.

The current generic signal mapper does not synthesize all of those signal families from the corresponding canonical models. Historical automatic mapping is concentrated on earlier tender/hiring behavior, while other paths depend on a signal already having been constructed with appropriate commercial metadata.

**Required completion:** introduce versioned signal-synthesis projectors for each commercially legitimate canonical input. Every mapping must preserve the truth hierarchy and must be capable of producing supporting, contradicting, negative or no signal.

Professional context is normally a **reachability/decision enabler**, not independent evidence of need. A role must not become a high-priority need solely because the `PROFESSIONAL_CONTEXT` signal type exists.

### 6. Generalized need hypotheses are recomputed explicitly and lack desired-set invalidation

Lot 24 can fuse current non-expired `CommercialSignal` records into generalized need hypotheses.

The current recompute path upserts hypotheses that are produced. It does not reconcile the complete desired current set against previously active rows and therefore does not automatically withdraw an old hypothesis that is no longer produced.

The current `HypothesisStatus` model exposes `proposed`, `active`, and `dismissed`, but no explicit lifecycle for system-driven `expired`, `withdrawn` or `superseded` state.

**Required completion:** hypothesis generation becomes desired-set reconciliation. Existing current hypotheses absent from the desired result must transition to an explicit non-current system state with reason, timestamp, generation/rule version and preserved history.

### 7. The legacy SIEM/SOC opportunity path remains parallel to generalized Lot 24 fusion

The earlier `generate_siem_soc_opportunity(...)` path still creates a hypothesis, score and opportunity directly from tender/hiring signals. This remains useful historical behavior, but it creates a second orchestration path beside generalized Lot 24 hypothesis fusion and future Lot 25 scoring.

**Required completion:** migrate the direct path into the universal reconciliation pipeline. New commercial projections persist evidence/signals and mark the organization dirty; generalized hypothesis reconciliation becomes the canonical inference layer; Lot 25 owns advanced scoring/calibration; opportunity reconciliation consumes current eligible hypotheses without source-specific direct creation.

Existing analyst state and stable opportunity identity must be preserved during migration.

### 8. Opportunity lifecycle does not yet express system invalidation completely

Current opportunity states are analyst-workflow states such as `needs_review`, `qualified`, `rejected`, `snoozed`, and `enrichment_requested`.

Those states do not by themselves express that the underlying generated basis expired, was withdrawn, became contradictory, or is awaiting reconciliation.

List queries can therefore continue to expose stored opportunities unless another evaluation explicitly updates them.

**Required completion:** separate analyst workflow state from generated/current-basis state, or extend the model with an equivalent explicit system lifecycle. An analyst qualification must be preserved historically, but an opportunity whose evidence basis is no longer current must not silently remain current merely because the analyst once reviewed it.

### 9. Time-only transitions need a scheduler, not only event delivery

A transactional outbox handles database writes. It cannot, by itself, handle truth changes caused by the passage of time.

Examples include:

- signal `expires_at`;
- hypothesis `expires_at`;
- score/opportunity TTL;
- passive observation expiry;
- relationship `valid_until`, evidence expiry and renewal windows;
- corporate-change staleness;
- applicability based on expiring technology evidence;
- freshness/publication-quality thresholds.

**Required completion:** persist or derive a bounded `next_reconcile_at` and run a durable due-time sweep. Time-driven work uses the same idempotent projectors as write-driven work.

### 10. Incremental and backfill paths are not projection-equivalent

The incremental worker and historical backfill worker currently persist different projection families. The backfill path does not run the complete local/derived contract and cannot therefore prove that historical replay reaches the same current state.

A naive fix that simply generates an opportunity for every historical record is also wrong because backfill must not flood the current analyst Inbox.

**Required completion:** both modes share one canonical projection application contract. Historical records are persisted with their effective times; derived projectors calculate current state from effective chronology and freshness; only the final current eligible state is publishable.

### 11. Current tests describe stronger behavior than the runtime currently proves

`docs/TEST_STRATEGY.md` already requires:

- backfill/incremental convergence;
- signal-fusion and hypothesis invalidation;
- correction/retraction/deletion propagation;
- outbox delivery;
- idempotent consumers;
- derived-data invalidation;
- replay consistency;
- no duplicate opportunities after duplicate delivery or partial failure.

These remain mandatory requirements. Lot 28 must implement the runtime needed to make them true end to end rather than weakening the tests or documentation.

## Target architecture

### A. Transactional canonical-change outbox

Every canonical write that can affect derived truth records a minimal `CanonicalChangeEvent` in the same PostgreSQL transaction as the source-of-truth update.

The event contains only bounded routing and lineage metadata, for example:

- stable event ID and idempotency key;
- source module;
- aggregate/entity type;
- aggregate key or UUID;
- organization ID when resolved;
- change kind such as `created`, `revised`, `retracted`, `suppressed`, `deleted`, `identity_changed`, `expired_due`, `rule_changed`;
- effective/source timestamp;
- transaction occurrence timestamp;
- minimal dependency keys such as asset/product/vulnerability/relationship IDs;
- schema/event version.

The outbox must not duplicate raw provider payloads, secrets, private HTML, tokens, or unrestricted personal data.

### B. Durable reconciliation queue

Outbox dispatch creates or coalesces bounded reconciliation work.

Required properties:

- PostgreSQL durability;
- at-least-once delivery;
- deterministic idempotent consumers;
- dedupe/coalescing by projector and subject;
- leases and ownership;
- retry with bounded backoff;
- dead-letter state;
- operator replay/requeue;
- no false success if a projector fails;
- observable lag and oldest-pending age.

### C. Explicit dependency registry

Dependencies are code/config contracts, not hidden call chains.

Example:

```text
passive technology change
  -> vulnerability applicability
  -> corporate graph
  -> commercial signal synthesis
  -> need hypotheses
  -> score/opportunity current-basis state
  -> publication readiness

procurement contract change
  -> relationship intelligence
  -> corporate graph
  -> contract/relationship commercial signals
  -> need hypotheses
  -> score/opportunity current-basis state
  -> publication readiness

corporate incident/change revision
  -> corporate graph
  -> commercial signal synthesis
  -> need hypotheses
  -> score/opportunity current-basis state
  -> publication readiness
```

Not every input reaches every projector. The registry must encode legitimate dependencies and no-op cases explicitly.

### D. Application-level reconciliation ports

Provider adapters must not import downstream opportunity/scoring infrastructure.

Each derived bounded context exposes an application-level reconciliation port or service. The composition layer wires those ports to the durable reconciliation worker.

Cross-module infrastructure-to-infrastructure imports must not be introduced as a shortcut.

### E. Desired-state projectors

A projector computes what **should be current now** for its subject and reconciles stored current state to that desired result.

It must support:

- create;
- update;
- no-op/idempotent replay;
- withdraw/expire/supersede;
- contradiction/review-required state;
- lineage/fingerprint update;
- preservation of immutable snapshots/history.

A successful run that produces zero desired outputs is still meaningful and may need to retire previous outputs.

### F. Time-transition sweep

The scheduler periodically claims due derived subjects using persisted expiry/freshness/validity metadata.

The sweep must be bounded and incremental. It must not perform an unbounded full-table scan on every tick.

### G. Publication-readiness state

Analyst-facing projections expose whether the derived result is:

- `current`;
- `stale`;
- `reconciling`;
- `failed`;
- `suppressed/non_publishable` where applicable.

The exact persisted model may use enums/flags appropriate to each bounded context, but the platform-level semantics and API representation must be consistent.

A failed reconciliation never upgrades stale data to current.

### H. Rebuild and convergence fingerprint

Lot 28 must provide a controlled rebuild/reconciliation command or administrative job capable of regenerating derived current state from canonical persisted truth.

The rebuild produces deterministic counts and fingerprints so CI/operator validation can compare:

```text
incremental result
== backfill result
== shuffled replay result
== restore + rebuild result
```

for the same effective source history and configuration versions.

## Proposed module placement

The exact filenames may change during implementation, but ownership must remain clear.

Suggested new shared product module:

```text
src/cip/modules/derived_reconciliation/
  domain/
    events.py
    models.py
  application/
    dependency_registry.py
    ports.py
    service.py
    worker.py
    time_sweep.py
  infrastructure/
    models.py
    outbox.py
    queue.py
    projection_state.py
```

Composition code wires projectors from the existing bounded contexts. Domain code remains framework-free.

Do not place provider HTTP/browser logic in this module.

## Persistence model requirements

At minimum, migrations must support the equivalent of:

### `derived_reconciliation_outbox`

- immutable event identity;
- idempotency key;
- event/schema version;
- aggregate/module/change kind;
- bounded routing keys;
- effective and occurrence times;
- dispatch state/time.

### `derived_reconciliation_job`

- projector ID/version;
- subject type/key;
- coalescing fingerprint;
- state;
- attempt/max attempts;
- next attempt;
- lease owner/expiry;
- last error code;
- created/updated/completed times.

### `derived_projection_state`

- projector and subject identity;
- current input fingerprint;
- rule/config/taxonomy version;
- readiness state;
- last successful event/version;
- last reconciliation time;
- next reconciliation time;
- failure metadata safe for operator display.

Exact table names are implementation details; the behaviors are mandatory.

## Invalidation triggers

The reconciliation contract must cover at least:

- canonical create/update;
- correction;
- retraction/withdrawal/denial where semantically relevant;
- tombstone;
- suppression;
- product-owned deletion;
- source record supersession;
- source/organization attribution change;
- entity merge/split/reject/reversal;
- validity start/end;
- expiry/freshness transition;
- source authorization state where it changes publication legitimacy rather than merely future acquisition;
- mapper/rule/taxonomy/config version change;
- migration/rebuild request;
- restore/recovery validation.

Lot 31 remains the owner of end-to-end privacy-rights workflows and non-resurrection across personal-data destinations. Lot 28 provides the generic derived invalidation mechanics that Lot 31 composes.

## Backfill and replay semantics

Historical import must obey all of the following:

1. persist immutable historical observations/claims with source/effective time;
2. do not create one analyst notification/opportunity for every historical record;
3. reconcile current state from the full effective chronology;
4. preserve corrections/retractions and supersession order independent of ingestion order;
5. allow a deterministic rebuild after all partitions complete;
6. produce the same current canonical/derived result as an equivalent incremental history;
7. record the mode and lineage so operators can distinguish backfill work from live freshness.

## Interaction with Lots 25–27

### Lot 25

Lot 25 owns advanced scoring, calibration, explainability and feedback. It must expose deterministic scoring/re-score contracts callable by Lot 28 reconciliation. It must not create another source-specific scheduling system.

### Lot 26

Lot 26 owns commercial operations, alerts, tasks and engagement. It must distinguish an analyst lifecycle decision from the generated basis being withdrawn/stale. Lot 28 owns propagation of evidence-basis invalidation; Lot 26 owns the resulting workflow semantics and user actions.

### Lot 27

Lot 27 owns Company 360/read workflows. It must display freshness/reconciliation/readiness state and cannot hide a failed derived-data reconciliation behind a normal-looking current card.

Lots 25–27 may be implemented before Lot 28 in normal sequence, but they must remain compatible with this contract and cannot be used as evidence that Lot 28 is unnecessary.

## Interaction with Source Activation

Source Activation continues to own provider-specific authorization and live execution.

For sources that eventually produce relationship or professional-context canonical observations, the provider-specific adapter and entitlement remain in the appropriate SA lot. Lot 28 owns the common post-persistence change/reconciliation mechanism.

A source activation must not create its own private graph/hypothesis refresh path to compensate for Lot 28 being unfinished.

## Non-goals

Lot 28 does not:

- authorize or purchase provider access;
- bypass CAPTCHA, MFA, paywalls, provider security or account controls;
- perform active scanning or probing of prospects;
- create autonomous outreach;
- infer compromise from a global IOC;
- infer vulnerability applicability from a CVE alone;
- infer an active relationship from a weak directory mention alone;
- treat professional-role presence as a need by itself;
- replace the Lot 25 scoring-calibration business logic;
- replace Lot 31 privacy-right workflows;
- rebuild already correct bounded-context history models without a demonstrated convergence need.

## Required observability

Operators must be able to answer:

- which subject is stale or reconciling;
- which canonical change made it dirty;
- which projector/version owns the work;
- how long the work has been pending;
- whether retries are occurring;
- why it failed;
- whether analyst-facing publication is blocked;
- which downstream projections were changed/withdrawn;
- whether a full rebuild matches the incremental fingerprint.

## Required migration safety

Migrations must be reversible where repository policy requires it and must preserve existing analyst decisions.

The migration from the legacy direct SIEM/SOC path must not silently duplicate opportunities or discard:

- qualification/rejection/snooze state;
- analyst notes/reviews;
- score overrides where still semantically applicable;
- evidence lineage;
- stable organization/opportunity references.

## Required security and privacy properties

- outbox/job payloads contain routing metadata, not raw secrets or broad personal payloads;
- control-plane operations for replay/requeue/full rebuild are protected and audited;
- deletion/suppression cannot be undone by a stale reconciliation job;
- worker retries cannot bypass Source Governance or privacy suppression decisions;
- logs/errors remain redacted;
- no reconciler performs external network access unless that action belongs to a separately governed acquisition job.

## Required test families

Lot 28 must add deterministic tests for:

1. forward propagation from a changed canonical record;
2. correction propagation;
3. retraction propagation;
4. time-only expiry without a new source write;
5. suppression/deletion invalidation;
6. organization identity merge;
7. organization identity split/reversal;
8. rule/taxonomy/projector version rebuild;
9. duplicate outbox delivery;
10. worker crash after commit but before acknowledgement;
11. projector failure and dead-letter visibility;
12. concurrent updates and coalescing;
13. shuffled historical replay;
14. incremental versus backfill convergence;
15. restore plus rebuild convergence;
16. no historical Inbox flood;
17. stale/failed publication blocking;
18. preservation of analyst review state across rescore/reconciliation;
19. no false semantic upgrade such as CVE -> applicability or role -> need;
20. full source-to-current-opportunity and reverse-invalidation E2E scenarios.

Tests must respect repository size limits; split large matrices across focused files rather than creating a monolithic test file.

## Release gates

Lot 28 implementation cannot be called complete until:

- migrations apply and rollback as required;
- architecture rules pass without introducing forbidden cross-module dependency shortcuts;
- unit/property/integration/E2E tests cover both positive and negative reconciliation;
- PostgreSQL-backed outbox/lease/retry behavior is proven;
- incremental/backfill/replay/restore fingerprints converge;
- analyst-facing stale/failed state is exercised;
- backend combined branch-inclusive coverage remains at or above repository threshold;
- new deterministic critical reconciliation code targets at least 95% coverage;
- frontend typecheck/build and affected UI tests pass;
- security/privacy/retention gates pass;
- no tests or thresholds were weakened to obtain green CI;
- every check corresponds to the exact final PR head.

## Exit gate

Lot 28 cannot be marked `IMPLEMENTED_VALIDATED` while any analyst-facing derived result can remain apparently current solely because:

- a downstream projector was never triggered;
- a time-based transition occurred without a new source write;
- a recompute generated zero positive rows and failed to withdraw the old row;
- backfill skipped a projection family used by incremental collection;
- a duplicate/retried event created duplicate state;
- a correction/retraction/deletion did not reach all dependent projections;
- a reconciliation failure was hidden.

The final proof must demonstrate deterministic forward propagation **and reverse invalidation** from canonical evidence through the current commercial state on one exact final head.