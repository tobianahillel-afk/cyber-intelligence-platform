# Lot 28 — Implementation-finality gap audit

## Status

`AUDITED_HANDOFF_TO_LOT_28`.

Audit date: 2026-08-17.

Audited merged baseline: `3b7a3151ff17df59c1a18ac6fb1a7233063dfaf0`.

Current validated package version on that baseline: `0.24.0`.

Implementation tracker: issue #171.

Canonical recovery plan: `LOT_28_DERIVED_STATE_RECONCILIATION_RECOVERY.md`.

## Audit question

After Lots 13–24 had each been validated, does the merged product guarantee that any material canonical change automatically converges every affected derived projection, including reverse invalidation and time-only transitions, without relying on a manual refresh/recompute endpoint or an adapter-specific shortcut?

**Audit answer: no.**

The bounded contexts contain meaningful implemented functionality. The missing property is a durable platform-level reconciliation runtime joining them.

## Method

The audit traced runtime call paths rather than relying on roadmap status alone.

It inspected:

- collection adapter batch contracts;
- incremental worker persistence;
- historical backfill persistence;
- applicability matcher/persistence/API usage;
- procurement and relationship mapping/persistence;
- graph loaders/reconciliation/refresh API;
- commercial signal mapping and persistence;
- generalized need-hypothesis generation/persistence/query behavior;
- legacy SIEM/SOC opportunity generation;
- opportunity current query/lifecycle state;
- professional-context runtime shape;
- system-level integration architecture and test strategy.

The audit distinguishes:

- **local capability implemented**;
- **cross-module trigger missing**;
- **negative reconciliation missing**;
- **time-driven transition missing**;
- **replay/backfill convergence missing**;
- **documentation/test requirement already exists but implementation proof does not**.

## Finding register

### G01 — No durable cross-module outbox/reconciliation runtime

**Severity:** critical production-finality gap.

**Current evidence:**

- collection work is durable, but there is no `outbox`-named implementation in the merged source tree;
- `run_worker_once(...)` completes the collection job, calls `persist_batch_projections(...)`, records source health/value, and commits the session;
- no platform derived-event dispatch follows as a durable independent stage.

**Why it matters:**

A canonical DB commit and a downstream derived recompute are currently not linked by a durable at-least-once correctness mechanism.

**Required owner:** L01–L02.

---

### G02 — `AdapterCollectionBatch`/worker persistence covers local projection families, not the complete derived chain

**Severity:** high.

**Current evidence:**

`persist_batch_projections(...)` persists:

- identity projections/claims;
- commercial projections;
- procurement;
- public footprint;
- vulnerability snapshots;
- passive snapshots;
- incident claims;
- corporate-change claims;
- threat indicators.

The batch/runtime does not itself represent the derived reconciliation stages for:

- vulnerability applicability;
- relationship derivation;
- graph refresh;
- generalized need-hypothesis reconciliation;
- generalized scoring/opportunity reconciliation.

Professional-context data is also outside the current collection batch contract.

**Important constraint:** the fix is **not** to put graph/hypothesis/opportunity objects into provider batches. Derived state must be triggered from canonical changes through Lot 28.

**Required owner:** L01–L03.

---

### G03 — Incremental and historical backfill projection behavior diverge

**Severity:** critical data-convergence gap.

**Current evidence:**

The normal worker calls the common incremental projection persistence path.

The historical backfill success path independently persists a narrower set:

- observations;
- procurement organizations/projections;
- public footprint;
- vulnerability snapshots;
- passive snapshots;
- incident claims;
- threat indicators.

It does not apply the same full set as incremental collection and records `commercial_projections=0` and `identity_projections=0` in its source-value event.

**Why it matters:**

A history ingested incrementally and the same history imported by backfill are not guaranteed to produce the same canonical dirty events or derived current state.

**Required owner:** L03, terminal proof in L12.

---

### G04 — Lot 17 applicability works when called but is not automatically recomputed from changing dependencies

**Severity:** critical semantic-finality gap.

**Current evidence:**

- applicability domain matcher exists;
- `persist_assessment(...)` preserves immutable snapshots and advances current projection;
- API exposes read/list behavior rather than a production reconciliation worker;
- integration fixtures explicitly construct `TechnologyEvidence` and `VulnerabilityEvidence`, call the matcher, then call `persist_assessment(...)`.

**Missing production triggers:**

- passive technology/version revision;
- passive technology expiry;
- advisory/range revision or withdrawal;
- organization/asset attribution change;
- rebuild/rule-version change.

**Required owner:** L04 + L10.

---

### G05 — Procurement-to-relationship bridge is implemented but not wired into procurement persistence

**Severity:** high.

**Current evidence:**

`relationship_bundle_from_procurement(...)` exists and models:

- provider/subcontractor relationship roles;
- assertion versus cancellation/retraction;
- historical state;
- contract validity;
- renewal context;
- service context.

`persist_procurement_projections(...)` updates procurement procedures, publications, contracts, parties and service classifications but does not invoke the relationship bridge.

Relationship tests seed `persist_relationship_evidence(...)` directly.

**Required owner:** L05.

---

### G06 — Corporate graph is correctly reconcilable but normal correctness depends on explicit refresh

**Severity:** high.

**Current evidence:**

`refresh_corporate_graph(...)` loads:

- organizations;
- relationships;
- passive exposure;
- incidents;
- corporate changes;
- applicability;

and persists graph nodes/edges plus resolution candidates.

The API exposes `POST /v1/graph/refresh`, and integration tests invoke that endpoint before checking refreshed state.

**Nuance:** this is not a claim that graph reconciliation is fundamentally broken. The graph domain reconciler is time-aware and can recalculate currentness when invoked. The missing property is a durable dependency/time trigger that guarantees invocation.

**Required owner:** L06 + L10.

---

### G07 — Several local reconcilers are time-aware but are refreshed primarily on writes

**Severity:** high.

**Current evidence:**

Relationship reconciliation evaluates:

- current validity;
- staleness;
- historical state;
- contract-backed current state;
- renewal dates.

Corporate-change reconciliation evaluates fresh versus stale claims using `now`.

Graph reconciliation evaluates node/edge validity/expiry using `now`.

Their stored current projections are refreshed when persistence/refresh functions run. Passage of time by itself does not create a database write.

**Why it matters:**

A correct domain function can still leave the persisted read model stale if no job invokes it after a deadline passes.

**Required owner:** L10.

---

### G08 — Signal types are broad, but canonical-to-signal synthesis is not a complete general pipeline

**Severity:** critical commercial integration gap.

**Current evidence:**

`SignalType` includes:

- public tender;
- job posting;
- contract lifecycle;
- regulatory change;
- incident;
- vulnerability applicability;
- passive exposure;
- technology change;
- corporate change;
- relationship;
- professional context;
- research discovery.

The generic signal mapper mainly fills historical tender/hiring mappings when the signal is already being stored. It is not a registry of projectors that creates current signals from every corresponding canonical module.

**Why it matters:**

A correct incident, applicability assessment or relationship can exist without automatically becoming a current commercial input.

**Required owner:** L07.

---

### G09 — Generalized Lot 24 hypotheses rely on explicit recompute

**Severity:** critical.

**Current evidence:**

`POST /v1/need-hypotheses/organizations/{organization_id}/recompute` calls `generate_need_hypotheses(...)`.

`generate_need_hypotheses(...)` correctly ignores expired commercial signals and stores generated hypotheses.

Integration tests explicitly seed evidence/signals, call generation and separately exercise the recompute endpoint.

**Missing property:** no platform dependency reactor guarantees recompute when relevant signals/canonical state change.

**Required owner:** L08.

---

### G10 — Hypothesis persistence is positive-upsert oriented, not complete desired-set reconciliation

**Severity:** critical stale-state gap.

**Current evidence:**

`store_need_hypothesis(...)` upserts generated hypotheses and replaces their signal links.

When a new fusion run no longer generates an old hypothesis, the generation path does not reconcile the previously current hypothesis set and mark missing results non-current.

`HypothesisStatus` currently contains:

- `proposed`;
- `active`;
- `dismissed`.

It does not distinguish system-driven expiry/withdrawal/supersession from analyst dismissal.

Default hypothesis list queries also do not automatically filter by current `expires_at`.

**Required owner:** L08 + L10/L11.

---

### G11 — Opportunity analyst state and generated-basis currentness are not fully separated

**Severity:** high.

**Current evidence:**

`OpportunityState` currently models analyst workflow:

- `needs_review`;
- `qualified`;
- `rejected`;
- `snoozed`;
- `enrichment_requested`.

It does not express that the generated evidence basis is expired/withdrawn/stale/reconciling.

The opportunity list function receives `now` but does not use `expires_at` as a default currentness filter.

**Required owner:** L09–L11, with workflow semantics coordinated with Lot 26.

---

### G12 — Legacy SIEM/SOC direct generation remains a parallel inference/orchestration path

**Severity:** high architectural duplication.

**Current evidence:**

`persist_commercial_projections(...)` stores source-provided commercial projections and then invokes `generate_siem_soc_opportunity(...)` for touched organizations.

That generator directly evaluates tender/hiring signals and creates:

- a need hypothesis;
- an opportunity score;
- an opportunity.

Generalized Lot 24 separately supports service-taxonomy need fusion and explicit recompute.

**Why it matters:**

The product has two commercial orchestration paths with different triggers/lifecycle semantics.

**Required owner:** L09, coordinated with Lot 25.

---

### G13 — Professional context has no common collection-batch/reconciliation bridge yet

**Severity:** medium now, high before SA19/provider activation is called fully integrated.

**Current evidence:**

The professional-context module has domain/persistence/query/API functionality, but its API is read-oriented and the current `AdapterCollectionBatch` has no professional-context projection family.

**Ownership boundary:**

- SA19 owns legitimate provider/community/professional source activation;
- Lot 28 owns the common post-canonical persistence/change/reconciliation contract;
- Lot 21 domain logic remains the canonical bounded context.

**Required owner:** L01/L03/L07/L11 interfaces; provider-specific implementation remains SA19.

---

### G14 — Research discovery must join the common evidence path, not a private commercial shortcut

**Severity:** semantic safety requirement.

**Current architecture contract:**

The platform truth model says a research result is not evidence until canonical provenance is validated.

Lot 28 routing must therefore treat unpromoted research results as non-commercial discovery state and only route a result through commercial synthesis after it becomes validated canonical evidence of a known type.

**Required owner:** L01/L07/L11 contract enforcement; Lot 23 remains the research workflow owner.

---

### G15 — System documentation/test strategy already requires behavior not yet proven end to end

**Severity:** critical release-truth gap.

**Existing documented requirements include:**

- a need hypothesis is recalculated when evidence changes;
- corrections/retractions invalidate derived outputs;
- backfill and live collection use the same normalization/projection contracts;
- backfill and incremental modes converge;
- outbox delivery;
- idempotent consumers;
- correction/retraction/deletion propagation;
- derived-data invalidation;
- replay consistency;
- duplicate queue delivery must not duplicate opportunities;
- a retracted claim cannot remain sole support for an active need hypothesis.

**Audit result:** those are valid desired properties, but the merged runtime does not yet contain one complete cross-module mechanism proving them.

**Required owner:** all Lot 28 micro-lots; terminal proof L12.

## Local capabilities that should be reused, not rewritten

The recovery must preserve strong existing work.

### Incident intelligence

Incident claims already preserve explicit allegation/report/confirmation/denial/retraction semantics and local reconciliation.

Lot 28 should react to the resulting canonical incident state; it should not flatten those semantics into a generic boolean incident flag.

### Corporate changes

Corporate-change claims already reconcile confirmation/report/speculation/dispute/correction/retraction and staleness logic.

Lot 28 needs due-time/downstream triggers, not a replacement event model.

### Relationships

Relationship evidence already supports assertion/dispute/correction/retraction, evidence classes, validity and current/historical reconciliation.

Lot 28 needs to wire canonical inputs/time transitions and downstream dirty routing.

### Corporate graph

Graph snapshots, temporal reconciliation, entity-resolution candidates, reversible analyst decisions and blast-radius fingerprints are valuable existing primitives.

Lot 28 needs automatic/scoped invocation and stale-job/version safety.

### Applicability

The existing matcher and immutable assessment history enforce the critical distinction between global vulnerability knowledge and organization applicability.

Lot 28 must preserve that separation while making recompute automatic.

### Need fusion

Generalized Lot 24 fusion already models source independence, corroboration, contradiction/negative evidence, service taxonomy and hypothesis classes.

Lot 28 must make it desired-state/reactive rather than replacing it with a second inference engine.

## Root cause classification

The gaps share a common pattern:

```text
local bounded-context domain model implemented
+ local persistence implemented
+ local API/tests implemented
- durable platform dependency routing
- negative desired-state reconciliation
- time-only scheduling
- replay/backfill parity
= locally correct modules that can become globally stale
```

This is why one cross-cutting Lot 28 recovery is safer than reopening and independently modifying every historical lot.

## Version and sequencing decision

- current validated release remains `0.24.0`;
- Lot 25 is still the next sequential implementation lot;
- Lot 26 follows Lot 25;
- Lot 27 follows Lot 26;
- this recovery is mandatory Lot 28 scope targeting `0.28.0`;
- Lots 25–27 must not introduce another reconciliation/event bus or hard-code source-specific triggers that Lot 28 would later have to remove;
- Lot 32 cannot treat this recovery as an optional pilot experiment.

## Completion disposition

Every finding G01–G15 must end the Lot 28 completion audit as exactly one of:

- **implemented and proven** with code/migration/test/runtime evidence;
- **explicitly excluded** by a documented product/security/legal decision with rationale;
- **owned by a named later product/source-activation lot** only where that later owner is genuinely distinct and the Lot 28 exit gate does not depend on pretending the capability exists now.

No finding may close as generic `later`, `future hardening`, `manual`, `blocked`, `not currently called`, or `works when explicitly recomputed`.