# Lots 01–05 — Implementation Finality Recovery

## Status

`PLANNED_LOCKED_CORRECTIVE_OVERLAY`

Tracker: issue #173 — `Lots 01–05: implementation finality recovery`.

Audit/recovery baseline: `8d7184b8a6f494ceb407ab489d8971f4d015bab6` (`main`, 2026-08-17).

This recovery does **not** renumber, reopen, or rewrite the historical `IMPLEMENTED_VALIDATED` status of Lots 01–05. It is a corrective implementation overlay that owns residual finality gaps discovered after those historical validations.

The authoritative numbered product sequence remains Lot 25 -> 26 -> 27 -> 28 -> 29 -> 30 -> 31 -> 32. This recovery must be implemented as a focused corrective programme and must not create a competing product-lot number.

## Purpose

The historical first five lots established the platform foundations:

- Lot 01 — modular core, PostgreSQL persistence, provenance, retention and migrations;
- Lot 02 — durable scheduler/worker/checkpoint/retry/recovery mechanics;
- Lot 03 — first evidence-backed opportunity engine and analyst Inbox;
- Lot 04 — TED European public-procurement acquisition;
- Lot 05 — BOAMP French public-procurement acquisition and executable architecture gates.

A later finality audit found that those outcomes contain several concrete residuals that matter for production correctness, completeness, auditability and measurable commercial quality.

The goal of this recovery is therefore not to add unrelated features. It is to prove that the capabilities promised by Lots 01–05 are complete enough to serve as trustworthy foundations for the later platform.

## Recovery invariant

```text
historical Lots 01–05 capability
-> adversarial requirement/runtime audit
-> one explicit finding record
-> exactly one owner/disposition
-> local implementation when the defect belongs here
-> named handoff when a later canonical owner already exists
-> executable proof
-> final no-orphan audit
```

A finding is not closed because a helper function exists, because a happy-path unit test passes, because an error is visible, or because a later document vaguely mentions hardening.

## Terminal finding dispositions

Every finding discovered before closeout must end as exactly one of:

1. `IMPLEMENTED_PROVEN_HERE`: implementation is part of this corrective recovery, deterministic tests and applicable PostgreSQL/integration tests exist, failure/recovery behavior is proven, and the exact final SHA passes the complete repository gate.
2. `OWNED_BY_EXISTING_LATER_SCOPE`: a named later product lot or Source Activation increment is already the correct owner; the exact contract handed over is documented; this recovery proves it has not created a competing mechanism; the later owner has a measurable acceptance gate.
3. `TERMINAL_ALREADY_PROVEN`: the audit traced the runtime and tests and found the historical capability already complete for the intended boundary; evidence is recorded rather than silently assuming completeness from the historical status.
4. `EXPLICITLY_EXCLUDED`: product/security/legal decision removes the requirement; rationale and effect on product claims are documented.

The following are **not** terminal dispositions: `later`, `future hardening`, `manual for now`, `blocked`, `not currently called`, `works in a test`, `provider limit exceeded`, or `will be handled by retry` without a durable recovery path.

## Confirmed finality gaps on the baseline

### F01 — Long-running collection does not drive the existing lease heartbeat

**Historical owner:** Lot 02.  
**Disposition:** `IMPLEMENT_HERE`.  
**Recovery owner:** R01-L02.

The durable queue already has lease ownership and a `heartbeat_job(...)` primitive. The ordinary worker claims a job, leaves the claim transaction, calls potentially long-running `adapter.collect(...)`, then opens a new transaction to complete the job. It does not renew the lease during that collection interval.

This creates a correctness gap when collection duration can exceed `lease_seconds`: another worker may recover/reclaim the job while the original worker is still performing provider work. The eventual `LeaseLostError` prevents some stale completion, but it does not prevent duplicate external collection work or guarantee controlled cancellation of the stale execution.

### F02 — Scheduled jobs do not preserve schedule revision provenance

**Historical owner:** Lot 02, with Lot 01 provenance principles.  
**Disposition:** `IMPLEMENT_HERE`.  
**Recovery owner:** R01-L03.

`SourceSchedule` currently contains source/adapter, interval, lease and retry values but no stable schedule identity, schedule revision or canonical configuration fingerprint. `CollectionJob` persists the resolved execution parameters and `scheduled_for`, but not enough provenance to reconstruct which exact schedule definition produced a historical job after configuration changes.

### F03 — TED collection is page-1 bounded and can miss more than 100 current results

**Historical owner:** Lot 04.  
**Disposition:** `IMPLEMENT_HERE`.  
**Recovery owner:** R01-L04.

The TED client currently submits `paginationMode=PAGE_NUMBER`, `page=1`, `limit=100`, and exposes no page/cursor parameter. The collector calls the client once and uses only the latest publication number as its checkpoint. This is not a safe completeness contract for a result set larger than one page.

### F04 — TED discovery/relevance is a duplicated static query with title-only admission

**Historical owner:** Lot 04.  
**Disposition:** `IMPLEMENT_HERE`, with calibration explicitly left to Lot 25.  
**Recovery owner:** R01-L05.

The TED transport owns a large static cyber keyword query while canonical service taxonomy already owns service-family vocabulary. The mapper then gates a notice using only `matched_procurement_terms(title)` and classifies contract services from `notice.title()`.

The recovery must remove duplicated hidden business vocabulary and create a versioned provider-aware procurement discovery/relevance contract that can use the selected TED metadata available to the adapter without turning this recovery into a new scoring engine.

### F05 — BOAMP dense result windows fail instead of being adaptively consumed

**Historical owner:** Lot 05.  
**Disposition:** `IMPLEMENT_HERE`.  
**Recovery owner:** R01-L06.

BOAMP correctly paginates 100-record pages but defaults to five pages. When a query window contains more than the bounded page budget, it raises `BoampSourceWindowError`; the application adapter maps that to non-retryable `source_window_exceeded`.

The safety budget is correct. The terminal behavior is not: a dense legitimate time window must be decomposed into smaller bounded windows, checkpointed and replay-safe rather than left uncollected.

### F06 — Lot 03 lacks a durable labelled ground-truth/evaluation foundation

**Historical owner:** Lot 03.  
**Disposition:** split responsibility.  
**Recovery owner:** R01-L07.  
**Canonical future owner for calibration:** Lot 25.

The current score value object is deterministic, componentized and versioned. The repository audit found no implemented labelled ground-truth/calibration corpus or evaluation contract that can objectively measure whether the historical opportunity engine ranks real positives above negatives/ambiguous cases.

The authoritative roadmap already assigns calibration datasets, offline evaluation, analyst outcome feedback, service/segment calibration, drift and false-positive monitoring to Lot 25. This recovery therefore owns only the **evaluation foundation and handoff contract** needed to make the historical Lot 03 claim auditable. It must not implement a competing calibration engine.

## Existing later owners that this recovery must preserve

### Lot 25 — scoring/calibration/feedback

This recovery may add stable labelled fixtures/contracts and baseline evaluation expectations. It must not implement final service-specific calibration, analyst-feedback learning, drift monitoring or score-version optimization.

### Lot 28 / issue #171 — derived-state finality

This recovery must not introduce another event bus, canonical-change outbox, graph/hypothesis reactor or cross-module desired-state framework. Lot 28 owns that platform-wide derived-state mechanism.

### Lot 30 / issue #169 — network/address safety and broad resilience

This recovery may test collection-worker lease correctness. It must not duplicate the future shared DNS/address-safety policy or the broader operational resilience programme.

### Lot 31 / issue #5 — end-to-end privacy rights/deletion propagation

Lot 01 retention/provenance primitives remain foundations. Rights requests, deletion propagation, suppression/non-resurrection and lawful-basis operations remain Lot 31 scope.

### SA-20 — source activation/live completeness

Where the remaining issue is controlled real-provider live proof rather than deterministic runtime correctness, Source Activation remains the owner. This recovery improves TED/BOAMP mechanics; it does not falsely promote source activation state without the required controlled live proof.

## Recovery micro-lot order

```text
R01-L01  exhaustive gap registry and ownership freeze
   -> R01-L02  lease heartbeat integration and lease-loss stop semantics
   -> R01-L03  schedule identity/revision provenance
   -> R01-L04  TED bounded complete pagination/resume
   -> R01-L05  TED versioned discovery/relevance completeness
   -> R01-L06  BOAMP adaptive dense-window partition/recovery
   -> R01-L07  Lot 03 labelled evaluation foundation + Lot 25 handoff
   -> R01-L08  cross-lot adversarial qualification and no-orphan closeout
```

R01-L02 and R01-L03 may be implemented in either order after L01 because they touch different aspects of collection orchestration. R01-L04 and R01-L05 should be sequential on the same TED adapter to avoid conflicting checkpoint/query revisions. R01-L06 may proceed after L01 independently. R01-L07 must be finalized before L08. L08 is terminal and may not be skipped.

## Global implementation rules

Every micro-lot must:

- start from the latest merged predecessor head;
- keep one coherent objective per PR;
- reuse existing domain/application primitives before adding new abstractions;
- avoid provider-specific direct writes to later commercial/graph state;
- keep network-free deterministic unit tests;
- use PostgreSQL tests for lease/concurrency/migration semantics;
- maintain >=90% global line and branch coverage and target >=95% on changed deterministic orchestration/connector logic;
- preserve source/effective/published/collected time distinctions;
- maintain exact source provenance and deterministic identities;
- update documentation and rollback instructions in the same change;
- pass exact-head CI after the final documentation change.

## Required final proofs

R01-L08 must prove at minimum:

1. a collection lasting longer than its original lease remains single-owner while heartbeat succeeds;
2. heartbeat/lease loss stops stale completion and cannot advance checkpoint as success;
3. a crashed worker stops heartbeating and the job becomes safely reclaimable after lease expiry;
4. a historical job exposes the exact schedule identity/revision/fingerprint that produced it;
5. TED can consume a deterministic fixture spanning at least three pages without gaps or duplicates;
6. TED can resume after interruption on a page boundary and converge to the same canonical observations as uninterrupted collection;
7. TED relevance covers all canonical service families through versioned discovery rules without copying a second hidden taxonomy into the adapter;
8. BOAMP can consume a deliberately over-budget dense interval by bounded partitioning and resume safely after interruption;
9. shuffled/replayed provider pages do not create duplicate canonical observations/opportunities;
10. the Lot 03 labelled evaluation corpus distinguishes positive, negative and ambiguous cases and produces reproducible baseline metrics without claiming Lot 25 calibration is complete;
11. all accepted limitations have one named owner and acceptance gate;
12. no recovery change introduces a competing Lot 25, Lot 28, Lot 30, Lot 31 or Source Activation mechanism.

## Exit gate

This corrective recovery may close only when F01–F06 have terminal dispositions with executable evidence; the final adversarial audit has re-read code, policies, migrations, tests and runtime wiring for Lots 01–05 rather than trusting this initial finding list; every newly discovered problem is added to the finding registry before closure; all recovery-local problems are implemented and proven; all later-owner handoffs are explicit and non-duplicative; the exact documentation-complete final SHA passes the standard repository CI; and issue #173 contains the final matrix with no finding remaining `unknown`, `later`, `manual`, `blocked`, or ownerless.
