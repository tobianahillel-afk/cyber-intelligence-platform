# Lot 28 — Code surface, migration, and test map

## Status

`PLANNED_LOCKED`.

Parent scope: `LOT_28_DERIVED_STATE_RECONCILIATION_RECOVERY.md`.

Execution plan: `LOT_28_REACTIVE_RECONCILIATION_MICROLOTS.md`.

Tracking issue: #171.

Audit baseline: `3b7a3151ff17df59c1a18ac6fb1a7233063dfaf0`.

Current validated release: `0.24.0`.

Planned Lot 28 target release: `0.28.0`.

## Purpose

This document turns the Lot 28 recovery from an architectural requirement into an implementation map. For every micro-lot it identifies:

- existing code that must be reused or modified;
- new code surfaces that should be introduced;
- persistence and migration work;
- tests that must be extended or created;
- legacy paths that must be retired or deliberately preserved;
- architecture boundaries that must not be violated.

It is intentionally more concrete than the roadmap while remaining implementation-safe: exact helper names may change during coding, but ownership, dependency direction, migration sequencing, and exit behavior may not.

## Confirmed repository locations

Alembic is configured with:

```text
script_location = infra/migrations
```

so new schema revisions belong under:

```text
infra/migrations/versions/
```

The current backend package lives under:

```text
src/cip/
```

and existing runtime/reconciliation work relevant to this recovery is primarily under:

```text
src/cip/modules/collection_orchestration/
src/cip/modules/source_portfolio/
src/cip/modules/organizations/
src/cip/modules/procurement_history/
src/cip/modules/vulnerability_knowledge/
src/cip/modules/passive_exposure/
src/cip/modules/vulnerability_applicability/
src/cip/modules/incident_intelligence/
src/cip/modules/corporate_changes/
src/cip/modules/relationship_intelligence/
src/cip/modules/corporate_graph/
src/cip/modules/professional_context/
src/cip/modules/research_orchestration/
src/cip/modules/opportunities/
```

## Shared implementation principles

### One reconciliation mechanism

Do not introduce:

- one event bus for applicability;
- another queue for graph refresh;
- direct source-adapter calls into opportunities;
- a special backfill-only recompute path;
- an in-memory event dispatcher as the source of correctness.

Lot 28 owns one durable reconciliation mechanism shared by all derived projectors.

### PostgreSQL remains the durable handoff

A separate Kafka/RabbitMQ dependency is not required to close this gap. The system of record is PostgreSQL, so the minimum correct architecture is:

```text
canonical DB transaction
  -> transactional outbox row
  -> durable reconciliation job
  -> idempotent projector
  -> projection-state/readiness update
```

An external broker may only be introduced by a separate justified architecture decision and must not remove the transactional database handoff.

### Separate acquisition from derived work

Provider adapters should remain responsible for governed acquisition and source-native/canonical mapping. Derived projectors should run in a distinct reconciliation execution path.

A recommended process shape is:

```text
cip-scheduler / cip-worker              acquisition jobs
reconciliation scheduler / worker      derived-state jobs
```

The exact command names are not locked by this document. The important property is separate queue/lease semantics so a slow graph/hypothesis rebuild cannot block provider acquisition correctness.

### Preserve inward dependencies

Domain code remains framework-free. A derived reconciliation composition layer may know multiple application ports; one bounded context's infrastructure must not import another bounded context's infrastructure simply to shortcut orchestration.

---

# L01 — Canonical-change contracts and dependency registry

## Existing code to inspect/reuse

- `src/cip/modules/collection_orchestration/application/ports.py`
  - current typed `AdapterCollectionBatch` and source-native projection contract;
  - useful reference for bounded immutable dataclasses and validation style.
- domain identifiers/state models from:
  - `organizations/domain/`;
  - `procurement_history/domain/`;
  - `vulnerability_knowledge/domain/`;
  - `passive_exposure/domain/`;
  - `vulnerability_applicability/domain/`;
  - `incident_intelligence/domain/`;
  - `corporate_changes/domain/`;
  - `relationship_intelligence/domain/`;
  - `corporate_graph/domain/`;
  - `opportunities/domain/`.

## New code surfaces

Recommended module:

```text
src/cip/modules/derived_reconciliation/__init__.py
src/cip/modules/derived_reconciliation/domain/__init__.py
src/cip/modules/derived_reconciliation/domain/events.py
src/cip/modules/derived_reconciliation/domain/models.py
src/cip/modules/derived_reconciliation/application/__init__.py
src/cip/modules/derived_reconciliation/application/dependency_registry.py
src/cip/modules/derived_reconciliation/application/ports.py
```

The initial domain should define the semantic equivalent of:

- `CanonicalChangeEvent`;
- validated aggregate/module identity;
- validated `CanonicalChangeKind`;
- bounded routing/dependency keys;
- `ReconciliationProjectorId` + version;
- `ReconciliationSubject`;
- deterministic event/idempotency key calculation.

## Migration impact

None required for the pure L01 contract unless implementation deliberately lands the first persisted registry/version table here. Prefer keeping L01 domain/application-only and putting queue persistence in L02.

## Tests to add

Suggested focused files:

```text
tests/test_derived_reconciliation_events.py
tests/test_derived_reconciliation_registry.py
```

and extend architecture checks under `tests/architecture/` if necessary.

Required coverage:

- deterministic keys;
- invalid enum/routing data;
- bounded payload sizes;
- exact projector routing;
- explicit no-op routing;
- no CVE -> applicability promotion;
- no IOC -> compromise promotion;
- no professional-role -> need promotion;
- no raw research discovery -> evidence/need promotion;
- no SQLAlchemy/FastAPI import in domain.

## Do not duplicate

- do not replace `AdapterCollectionBatch` with a generic untyped event bag;
- do not move provider data-category/authorization concerns into derived reconciliation;
- do not create source-specific projector IDs inside adapters.

---

# L02 — Transactional outbox and durable reconciliation queue

## Existing code to inspect/reuse

### Collection transaction boundary

- `src/cip/modules/collection_orchestration/application/worker.py`
- `src/cip/modules/collection_orchestration/application/worker_persistence.py`

The current success path already persists job completion, canonical projections, source health, and source-value state inside one session/transaction. Canonical-change outbox rows must be created inside this same atomic boundary.

### Existing lease/retry conventions

Reuse patterns, not tables blindly, from:

```text
src/cip/modules/collection_orchestration/infrastructure/repository_queue.py
src/cip/modules/collection_orchestration/infrastructure/repository_failures.py
src/cip/modules/collection_orchestration/infrastructure/repository_completion.py
src/cip/modules/collection_orchestration/infrastructure/repository_common.py
```

The derived queue needs its own subject/projector semantics but should feel operationally consistent with the existing durable collection worker.

## New code surfaces

Recommended:

```text
src/cip/modules/derived_reconciliation/application/worker.py
src/cip/modules/derived_reconciliation/infrastructure/__init__.py
src/cip/modules/derived_reconciliation/infrastructure/models.py
src/cip/modules/derived_reconciliation/infrastructure/outbox.py
src/cip/modules/derived_reconciliation/infrastructure/queue.py
src/cip/modules/derived_reconciliation/infrastructure/repository_common.py
```

If process entry points are added, update `pyproject.toml` only after names are settled. Suggested human-readable roles are a reconciliation worker and reconciliation scheduler; exact executable names are not normative.

## Migration M1

Create one Alembic revision under:

```text
infra/migrations/versions/
```

for the equivalent of:

### `derived_reconciliation_outbox`

Required indexes/constraints should support:

- unique idempotency key;
- undispatched rows ordered by occurrence/ID;
- aggregate/subject lookup where required;
- bounded event/schema versions.

### `derived_reconciliation_job`

Required indexes/constraints should support:

- active job uniqueness/coalescing by `(projector_id, subject_type, subject_key)` or equivalent safe fingerprint;
- claimable `state + next_attempt_at` ordering;
- lease expiry recovery;
- projector/state metrics;
- dead-letter queries.

Do not add raw JSON provider payload copies. Routing payloads must remain bounded and reviewable.

## Tests to add

Suggested split:

```text
tests/integration/test_derived_outbox_atomicity.py
tests/integration/test_derived_reconciliation_queue.py
tests/integration/test_derived_reconciliation_worker_recovery.py
```

Use PostgreSQL-backed tests for locking/lease/atomicity behavior where SQLite cannot prove semantics.

Required scenarios:

- canonical transaction rollback -> no outbox;
- commit -> outbox atomically present;
- duplicate event -> one logical event/job;
- worker crash after commit before ack;
- expired lease reclaimed;
- retry/backoff;
- dead letter + explicit requeue;
- newer dirty event safely coalesces with existing job;
- stale job cannot overwrite newer projector generation.

## Do not duplicate

- do not make source collection jobs carry derived projector semantics;
- do not invoke graph/hypothesis work synchronously inside `adapter.collect()`;
- do not treat an in-process callback as durable delivery.

---

# L03 — Unified incremental/backfill/replay application contract

## Existing code to modify

```text
src/cip/modules/collection_orchestration/application/worker.py
src/cip/modules/collection_orchestration/application/worker_persistence.py
src/cip/modules/source_portfolio/application/backfill_worker.py
```

Also inspect current source-value/backfill records under:

```text
src/cip/modules/source_portfolio/application/
src/cip/modules/source_portfolio/infrastructure/
```

## New application service

Introduce one service used by both execution modes, conceptually:

```text
apply_collection_batch(session, batch, execution_context, now)
```

The exact function/class name is not locked.

It must own canonical persistence orchestration and canonical-change event emission, while source-specific health/job completion remains in the caller where appropriate.

## Required behavior changes

The backfill path must stop maintaining an independently curated subset of canonical projection calls.

Both modes must use the same canonical projection application contract for every projection present in `AdapterCollectionBatch`.

Do not add derived outputs to `AdapterCollectionBatch`; the common service emits canonical dirty events which L02 dispatches.

## Migration impact

Usually none beyond L02. Add source-value/backfill schema changes only if required to persist a deterministic reconcile/rebuild checkpoint or finalization state.

If a schema change is needed, keep it separate from M1 rather than continually editing the initial queue migration after review.

## Tests to update/add

Existing relevant tests:

```text
tests/integration/test_source_portfolio_backfill_worker.py
tests/integration/test_source_portfolio_backfill_recovery.py
tests/integration/test_source_portfolio_worker_vertical.py
tests/integration/test_sa16_l12_partial_retry.py
```

Add focused convergence tests, for example:

```text
tests/integration/test_collection_backfill_projection_parity.py
tests/integration/test_collection_replay_ordering.py
```

Required proof:

- identical effective history via live/incremental and backfill produces same canonical fingerprint;
- all batch projection families are honored consistently;
- reverse/shuffled historical order converges;
- partial retry is idempotent;
- historical import does not create one current Inbox item per old record.

## Do not duplicate

- no separate backfill-only canonical mapping rules;
- no backfill-only direct opportunity generation;
- no dependency on ingestion order when source/effective chronology is available.

---

# L04 — Vulnerability applicability reactor

## Existing code to reuse

```text
src/cip/modules/vulnerability_applicability/domain/matcher.py
src/cip/modules/vulnerability_applicability/domain/models.py
src/cip/modules/vulnerability_applicability/domain/enums.py
src/cip/modules/vulnerability_applicability/infrastructure/models.py
src/cip/modules/vulnerability_applicability/infrastructure/projections.py
src/cip/modules/vulnerability_applicability/infrastructure/queries.py
```

Inputs come from existing canonical persistence/query layers in:

```text
src/cip/modules/passive_exposure/
src/cip/modules/vulnerability_knowledge/
src/cip/modules/organizations/
```

## New code surfaces

Prefer application-level orchestration in Lot17's bounded context, for example:

```text
src/cip/modules/vulnerability_applicability/application/reconciliation.py
src/cip/modules/vulnerability_applicability/application/ports.py
src/cip/modules/vulnerability_applicability/infrastructure/impact_queries.py
```

The derived reconciliation worker calls an application port; it should not reach directly into applicability infrastructure internals.

## Identity audit before migration

Current assessment identity includes organization, asset, vulnerability and technology-snapshot identity. Before coding, verify whether a new technology snapshot creates a new current identity while leaving the previous assessment visible as current.

If yes, introduce a stable current subject key/current-selection model without deleting immutable assessment snapshots.

## Optional Migration M2a

Only if the identity audit proves it necessary, add a dedicated revision under `infra/migrations/versions/` for:

- stable applicability current-subject key;
- current-generation/current flag or equivalent;
- indexes on organization/asset/product/vulnerability impact lookup;
- uniqueness that prevents two current projections for one stable subject.

Do not alter immutable historical snapshot identity simply to make queries convenient.

## Tests to extend/add

Existing:

```text
tests/integration/test_vulnerability_applicability_api.py
```

Add:

```text
tests/integration/test_vulnerability_applicability_reactor.py
```

Split further if the file approaches repository test-size limits.

Required scenarios:

- passive technology arrives -> assessment automatically reconciles;
- advisory correction -> assessment changes;
- advisory withdrawal -> current support withdrawn/unknown;
- passive evidence expiry through L10 -> assessment changes without provider write;
- organization rebind -> old scope invalidated/new scope reconciled;
- duplicate dirty events no-op safely;
- global CVE alone never becomes organization applicability.

## Do not duplicate

- keep `assess_applicability(...)` as domain truth engine;
- do not implement a second matcher inside the queue worker;
- do not perform active validation or scanning.

---

# L05 — Relationship reactor

## Existing code to reuse/modify

```text
src/cip/modules/relationship_intelligence/application/procurement_adapter.py
src/cip/modules/relationship_intelligence/application/bundles.py
src/cip/modules/relationship_intelligence/domain/reconciliation.py
src/cip/modules/relationship_intelligence/domain/models.py
src/cip/modules/relationship_intelligence/infrastructure/projections.py
src/cip/modules/relationship_intelligence/infrastructure/queries.py
src/cip/modules/procurement_history/infrastructure/projections.py
```

## New code surfaces

Recommended:

```text
src/cip/modules/relationship_intelligence/application/reconciliation.py
src/cip/modules/relationship_intelligence/application/ports.py
src/cip/modules/relationship_intelligence/infrastructure/impact_queries.py
```

The procurement bounded context should emit a canonical contract-change event. The relationship application projector consumes that event and calls the existing mapping/persistence semantics.

Avoid making `procurement_history.infrastructure.projections` import `relationship_intelligence.infrastructure.projections` directly.

## Migration impact

Potentially none if current relationship identity/current projection can reconcile award/amend/cancel and time transitions safely.

Add a dedicated migration only if impact selection/current uniqueness needs additional indexes or persisted stable subject identity.

## Tests to extend/add

Existing:

```text
tests/integration/test_relationship_intelligence_api.py
tests/integration/test_procurement_history_boamp_worker.py
tests/integration/test_procurement_history_decp_worker.py
tests/integration/test_procurement_history_ted_worker.py
```

Add:

```text
tests/integration/test_procurement_relationship_reactor.py
```

Required proof:

- award -> relationship;
- amendment -> relationship update;
- cancellation -> retraction/historical state;
- provider/consortium/subcontractor change;
- org resolution change;
- renewal/end-date change;
- time validity transition;
- weak directory/case-study evidence retains weaker evidence class.

## Do not duplicate

- reuse `relationship_bundle_from_procurement(...)`;
- do not create one procurement-specific relationship table;
- do not let future source-activation adapters write graph/opportunity state directly.

---

# L06 — Corporate graph reactor

## Existing code to reuse

```text
src/cip/modules/corporate_graph/infrastructure/refresh.py
src/cip/modules/corporate_graph/infrastructure/projections.py
src/cip/modules/corporate_graph/infrastructure/relationship_adapter.py
src/cip/modules/corporate_graph/infrastructure/passive_adapter.py
src/cip/modules/corporate_graph/infrastructure/incident_adapter.py
src/cip/modules/corporate_graph/infrastructure/corporate_change_adapter.py
src/cip/modules/corporate_graph/infrastructure/applicability_adapter.py
src/cip/modules/corporate_graph/infrastructure/organization_adapter.py
src/cip/modules/corporate_graph/domain/reconciliation.py
src/cip/modules/corporate_graph/infrastructure/resolution_persistence.py
src/cip/modules/corporate_graph/infrastructure/candidate_generation.py
src/cip/modules/corporate_graph/api/routes.py
```

## New code surfaces

Recommended:

```text
src/cip/modules/corporate_graph/application/reconciliation.py
src/cip/modules/corporate_graph/application/ports.py
src/cip/modules/corporate_graph/infrastructure/impact_queries.py
```

Refactor existing full refresh internals so the same loader/reconciliation primitives can support scoped subjects without duplicating graph semantics.

## Required behavior change

`POST /v1/graph/refresh` remains a protected repair/full-rebuild operation.

Ordinary currentness must be maintained by dirty events from:

- relationships;
- passive observations;
- incidents;
- corporate changes;
- applicability;
- organization identity decisions;
- due-time transitions.

## Migration impact

Prefer no new graph history tables. Add indexes/current-generation columns only if scoped desired-set reconciliation cannot be implemented efficiently with current schema.

Any graph schema migration should be separate from the queue migration.

## Tests to extend/add

Existing:

```text
tests/integration/test_corporate_graph_api.py
```

Add:

```text
tests/integration/test_corporate_graph_reactor.py
tests/integration/test_corporate_graph_rebuild_equivalence.py
```

Required proof:

- upstream relationship/passive/incident/change/applicability update appears without HTTP refresh;
- disappearing desired node/edge becomes non-current correctly;
- time expiry updates graph;
- merge/split/reversal is version-safe;
- stale job cannot overwrite newer analyst resolution decision;
- full rebuild fingerprint == scoped incremental fingerprint.

## Do not duplicate

- do not replace temporal graph snapshots;
- do not bypass blast-radius/version checks;
- do not make graph itself infer commercial need from weak data.

---

# L07 — Canonical-to-commercial signal synthesis

## Existing code to reuse

```text
src/cip/modules/opportunities/domain/signal_entities.py
src/cip/modules/opportunities/domain/signal_mapping.py
src/cip/modules/opportunities/infrastructure/signals.py
src/cip/modules/opportunities/infrastructure/models.py
src/cip/modules/service_taxonomy/domain/classifier.py
src/cip/modules/service_taxonomy/domain/models.py
```

Canonical inputs are read from the existing bounded contexts, not from raw provider payloads.

## New code surfaces

Do not put every mapping into one >400-line file. Split by family, for example:

```text
src/cip/modules/opportunities/application/signal_synthesis.py
src/cip/modules/opportunities/application/signal_projectors/__init__.py
src/cip/modules/opportunities/application/signal_projectors/procurement.py
src/cip/modules/opportunities/application/signal_projectors/incidents.py
src/cip/modules/opportunities/application/signal_projectors/corporate_changes.py
src/cip/modules/opportunities/application/signal_projectors/applicability.py
src/cip/modules/opportunities/application/signal_projectors/passive_technology.py
src/cip/modules/opportunities/application/signal_projectors/relationships.py
src/cip/modules/opportunities/application/signal_projectors/research.py
src/cip/modules/opportunities/application/signal_projectors/professional_context.py
```

Exact grouping may change to keep functions/files below repository limits.

## Required persistence change

`store_commercial_signal(...)` remains useful for deterministic upsert, but the application projector must reconcile the **desired current signal set** and retire signals that are no longer supported.

If current signal schema cannot express system withdrawal/current-generation clearly, add a dedicated migration before L08 rather than overloading `expires_at` alone.

## Optional Migration M2b

Potential fields/structures:

- current/system lifecycle or active-generation marker;
- withdrawal/supersession reason/time;
- projector/rule generation;
- input fingerprint;
- indexes for organization + current + expiry + mapping rule.

Do not remove immutable evidence linkage.

## Tests to add

Use multiple focused files rather than one huge mapping matrix, for example:

```text
tests/test_signal_synthesis_procurement.py
tests/test_signal_synthesis_incidents.py
tests/test_signal_synthesis_applicability.py
tests/test_signal_synthesis_relationships.py
tests/test_signal_synthesis_truth_boundaries.py
```

Required for every mapping family:

- positive mapping;
- explicit no-signal boundary;
- correction/retraction;
- expiry;
- unresolved organization;
- independence/corroboration semantics;
- deterministic mapping version;
- service taxonomy result;
- historical-only behavior.

## Do not duplicate

- do not let adapters hand-build opportunity rows;
- do not promote CVEs/IOCs/roles/research snippets beyond their evidence semantics;
- do not use graph adjacency alone as proof of need.

---

# L08 — Desired-set need-hypothesis reconciliation

## Existing code to modify/reuse

```text
src/cip/modules/opportunities/domain/entities.py
src/cip/modules/opportunities/domain/fusion.py
src/cip/modules/opportunities/infrastructure/fusion_generation.py
src/cip/modules/opportunities/infrastructure/hypotheses.py
src/cip/modules/opportunities/infrastructure/hypothesis_queries.py
src/cip/modules/opportunities/api/hypothesis_routes.py
src/cip/modules/opportunities/api/hypothesis_schemas.py
```

## New code surfaces

Recommended application service:

```text
src/cip/modules/opportunities/application/hypothesis_reconciliation.py
```

The current `generate_need_hypotheses(...)` logic can be refactored/reused internally, but the public application behavior must reconcile desired vs previously current hypotheses.

## Migration M3

Add a dedicated Alembic revision under `infra/migrations/versions/` for the minimum lifecycle needed to distinguish:

- analyst dismissal;
- system expiry;
- system withdrawal;
- superseded generation;
- current generation/readiness where appropriate.

Suggested persisted concepts:

- system lifecycle/currentness;
- lifecycle reason/time;
- generation/rule/taxonomy version;
- input fingerprint;
- current-scope uniqueness/indexes.

Exact column names are implementation details. Do not force analyst `dismissed` to mean system invalidation.

## Query/API changes

Default analyst lists should return current eligible hypotheses. Historical/non-current hypotheses remain queryable with explicit status/history filters.

The explicit recompute endpoint may remain as a protected repair/manual force-reconcile operation, but ordinary correctness cannot depend on it.

## Tests to update/add

Existing:

```text
tests/integration/test_need_hypothesis_api.py
tests/integration/test_need_hypothesis_persistence.py
```

Add:

```text
tests/integration/test_need_hypothesis_reconciliation.py
tests/integration/test_need_hypothesis_expiry.py
```

Required proof:

- new signal -> automatic hypothesis;
- independent corroboration updates one stable hypothesis;
- contradiction/negative evidence changes desired state;
- zero desired output retires previously current hypothesis;
- signal expiry retires it without a new positive signal;
- analyst dismissal is not overwritten as a system withdrawal;
- rule/taxonomy version rebuild preserves audit history;
- default current query excludes non-current rows.

## Do not duplicate

- reuse the generalized Lot 24 fusion engine;
- do not reintroduce one hypothesis algorithm per provider;
- do not delete old hypothesis history to get a clean current list.

---

# L09 — Score/opportunity reconciliation and legacy SIEM/SOC migration

## Existing code to modify/reuse

```text
src/cip/modules/opportunities/infrastructure/projections.py
src/cip/modules/opportunities/infrastructure/generation.py
src/cip/modules/opportunities/domain/rules.py
src/cip/modules/opportunities/domain/scoring.py
src/cip/modules/opportunities/infrastructure/queries.py
src/cip/modules/opportunities/infrastructure/reviews.py
src/cip/modules/opportunities/infrastructure/models.py
```

Future Lot 25 scoring/calibration contracts are authoritative for advanced scoring semantics.

## Historical path to retire as an orchestration trigger

Current flow in commercial projection persistence:

```text
store commercial signal
 -> generate_siem_soc_opportunity(...)
```

must become:

```text
store/reconcile commercial signals
 -> mark organization/hypothesis scope dirty
 -> generalized hypothesis reconcile
 -> Lot 25 score/re-score contract
 -> opportunity current-basis reconcile
```

The SIEM/SOC rule logic may remain as a rule input if still valuable; the private direct runtime trigger must not remain as a second correctness path.

## Migration M4

Add a dedicated migration if needed to separate:

### analyst workflow state

Existing states such as:

- needs review;
- qualified;
- rejected;
- snoozed;
- enrichment requested.

### generated-basis lifecycle/readiness

Equivalent semantics for:

- current;
- stale;
- reconciling;
- withdrawn/expired;
- failed/non-publishable.

Also add deterministic current commercial-motion identity/generation fields if required to keep one stable opportunity through rescore/rebuild.

## Data migration requirements

Existing opportunities must preserve:

- IDs where possible;
- analyst reviews;
- qualification/rejection/snooze state;
- review notes/reasons;
- score component overrides according to version policy;
- evidence links;
- future Lot26 task/engagement references.

The migration must not create duplicate opportunities simply because the canonical pipeline changed.

## Tests to update/add

Existing:

```text
tests/integration/test_opportunity_pipeline.py
tests/test_opportunity_api.py
```

Add:

```text
tests/integration/test_opportunity_reconciliation.py
tests/integration/test_opportunity_legacy_migration.py
```

Required proof:

- legacy SIEM/SOC fixture reaches same stable opportunity through new path;
- generalized hypothesis creates/updates opportunity;
- hypothesis withdrawal makes generated basis non-current;
- analyst workflow history survives;
- score TTL/version change triggers correct re-score/readiness;
- duplicate events do not duplicate opportunity;
- current Inbox does not silently show expired basis as normal current work.

## Do not duplicate

- Lot28 does not invent a second advanced scoring model beside Lot25;
- do not overload analyst `rejected` to mean system evidence withdrawal;
- do not discard manual review history during migration.

---

# L10 — Time, suppression, deletion, and identity invalidation

## Existing code to reuse

Scheduler/lease design reference:

```text
src/cip/modules/collection_orchestration/application/scheduler.py
src/cip/modules/collection_orchestration/infrastructure/repository_queue.py
```

Truth/currentness sources include:

```text
passive_exposure/*
vulnerability_applicability/*
relationship_intelligence/*
corporate_changes/*
corporate_graph/*
opportunities/*
organizations/*
data_governance/*
```

## New code surfaces

Recommended:

```text
src/cip/modules/derived_reconciliation/application/time_sweep.py
src/cip/modules/derived_reconciliation/infrastructure/projection_state.py
```

If scheduling is separated operationally:

```text
src/cip/modules/derived_reconciliation/application/scheduler.py
```

Use indexed due-time claims and bounded batches; do not full-scan all canonical tables every minute.

## Persistence evolution

This may share the L11 projection-state migration if `next_reconcile_at` was not introduced earlier.

Required indexed concept:

```text
(projector_id, readiness/current state, next_reconcile_at)
```

or an equivalent efficient due-work structure.

## Identity event integration

Integrate organization/entity-resolution merge/split/reject/reversal events so old and new organization scopes are both marked dirty.

Version/fingerprint checks must prevent older background work from restoring a superseded analyst resolution decision.

## Suppression/deletion boundary

Lot28 owns generic invalidation propagation. Lot31 owns legal/privacy request workflow and non-resurrection semantics for personal data.

A source merely being disabled for future acquisition is **not** automatically a deletion of valid retained historical evidence.

## Tests to add

```text
tests/integration/test_derived_time_sweep.py
tests/integration/test_derived_suppression_invalidation.py
tests/integration/test_derived_identity_rebinding.py
```

Required proof:

- expiry fires without source write;
- stale corporate/relationship state transitions;
- suppression invalidates dependent publication;
- old queued job cannot republish suppressed/deleted state;
- merge -> rebind -> split converges old/new organization projections;
- provider disablement stops future acquisition without erasing legitimate retained history.

## Do not duplicate

- do not encode each module's expiry semantics in the scheduler; invoke its application projector at due time;
- do not turn Lot28 into the Lot31 rights-request workflow.

---

# L11 — Projection readiness, lineage, observability, and publication gates

## Existing code to integrate

- existing protected APIs and `require_control_plane` dependency;
- source health/metrics patterns from `source_portfolio` and collection orchestration;
- current workspace/read APIs for graph, applicability, relationships, hypotheses and opportunities;
- Next.js application under `apps/web`.

## New backend code surfaces

Recommended:

```text
src/cip/modules/derived_reconciliation/application/service.py
src/cip/modules/derived_reconciliation/application/view_models.py
src/cip/modules/derived_reconciliation/infrastructure/projection_state.py
src/cip/modules/derived_reconciliation/infrastructure/queries.py
src/cip/modules/derived_reconciliation/api/routes.py
src/cip/modules/derived_reconciliation/api/schemas.py
```

Protect operator actions with control-plane auth and audit them.

## Migration M5

If not already created, add `derived_projection_state` or equivalent under `infra/migrations/versions/`.

Required persisted semantics:

- projector/version;
- subject type/key;
- input fingerprint;
- latest trigger/event version;
- config/rule/taxonomy generation when relevant;
- readiness state;
- last successful reconcile;
- next reconcile time;
- safe error code;
- lineage/output keys sufficient for operator diagnosis.

Indexes must support:

- stale/failed counts;
- due-time claim;
- subject lookup;
- projector backlog/health;
- oldest pending queries.

## Read/API behavior to update

Affected analyst read models should expose or consume common readiness semantics:

```text
current
stale
reconciling
failed
non-publishable/suppressed
```

Do not replace richer domain truth states with readiness. They are orthogonal.

## Frontend work

Update affected Company/workspace cards when Lot27 surfaces exist so an analyst can distinguish:

- current result;
- stale historical context;
- reconcile in progress;
- failed projector;
- publication blocked.

Do not silently hide degraded state if historical context remains useful; label it accurately.

## Tests to add/update

Backend:

```text
tests/integration/test_derived_reconciliation_api.py
tests/integration/test_derived_projection_readiness.py
```

Frontend: add focused tests beside affected views/components and keep each component under the repository 300-line limit.

Required proof:

- failed projector visible;
- stale != current;
- requeue clears failure only after successful reconcile;
- lineage resolves canonical change -> job -> projector -> output;
- operator endpoints require control-plane auth;
- logs/metrics contain no secret/raw personal payload;
- UI distinguishes readiness states.

## Do not duplicate

- source-health status and derived-projection readiness are related but not the same record;
- a healthy provider does not prove all downstream projections are current.

---

# L12 — End-to-end convergence qualification and closeout

## Existing test families to compose

Use the current integration fixtures for:

```text
tests/integration/test_vulnerability_applicability_api.py
tests/integration/test_relationship_intelligence_api.py
tests/integration/test_corporate_graph_api.py
tests/integration/test_need_hypothesis_api.py
tests/integration/test_need_hypothesis_persistence.py
tests/integration/test_opportunity_pipeline.py
tests/integration/test_source_portfolio_backfill_worker.py
```

Do not turn one existing test into a >650-line mega-suite.

## New E2E test decomposition

Recommended:

```text
tests/integration/test_reconciliation_e2e_passive_applicability.py
tests/integration/test_reconciliation_e2e_procurement_relationship.py
tests/integration/test_reconciliation_e2e_incident_change.py
tests/integration/test_reconciliation_e2e_identity_suppression.py
tests/integration/test_reconciliation_e2e_replay_convergence.py
tests/integration/test_reconciliation_e2e_queue_resilience.py
```

Each scenario must test both positive propagation and reverse invalidation where relevant.

## Required convergence fingerprint

Add a deterministic comparison utility/test helper that can compare material current state across:

- incremental ingestion;
- historical backfill;
- reverse/shuffled replay;
- restore + rebuild.

Fingerprint inputs should be stable normalized state, not volatile row insertion order or run IDs.

## Closeout documentation

Create at implementation completion:

```text
docs/lots/LOT_28_COMPLETION_AUDIT.md
```

It must map every G01–G15 finding and every L01–L12 exit gate to:

- implementation files;
- migration revision(s);
- deterministic tests;
- exact final SHA;
- CI/workflow evidence;
- runtime/operational proof;
- disposition.

No generic future/deferred/manual disposition is acceptable for a required exit condition.

## Exact-head gates

Before Lot28 can be marked complete:

- dependency/security audits pass;
- Ruff passes;
- strict Mypy passes;
- architecture/complexity/release/dependency contracts pass;
- every new migration upgrades/downgrades under repository policy;
- backend branch-aware combined coverage remains >=90%;
- new deterministic critical reconciliation/orchestration code targets >=95% coverage;
- frontend audit/typecheck/build and affected tests pass;
- no test/coverage threshold is weakened;
- no permanent skip hides a required projector/E2E case;
- reviews/threads have no unresolved blockers;
- all required workflows correspond to the exact final PR head.

---

# Recommended migration sequence

Do not create one giant migration spanning the entire programme. Preferred sequence:

| Migration | Micro-lot | Required purpose |
| --- | --- | --- |
| M1 | L02 | transactional outbox + reconciliation jobs + indexes/lease/coalescing constraints |
| M2a, only if needed | L04 | stable applicability current-subject/index support after identity audit |
| M2b, only if needed | L07 | commercial-signal system lifecycle/current-generation/fingerprint support |
| M3 | L08 | hypothesis system lifecycle/current-generation/supersession support |
| M4 | L09 | opportunity generated-basis/readiness separation and stable reconciliation identity |
| M5 | L10/L11 | projection state, next-reconcile scheduling, lineage/readiness indexes |

Every revision lives under `infra/migrations/versions/` and must follow the current repository migration-policy and round-trip tests.

Later implementation may combine adjacent revisions only if they land in the same reviewed micro-lot and remain reversible/understandable. Do not keep rewriting an already reviewed base migration merely to reduce revision count.

# Expected code ownership after Lot 28

The final dependency direction should look like:

```text
provider adapter
  -> canonical bounded-context application/persistence
       -> transactional canonical-change outbox
            -> derived reconciliation application worker
                 -> bounded-context application projector port
                      -> domain reconcile/fusion/matcher
                      -> bounded-context persistence
                 -> projection readiness/lineage
```

Not:

```text
provider adapter
  -> graph infrastructure
  -> opportunity infrastructure
  -> private recompute endpoint
```

and not:

```text
backfill worker
  -> a manually maintained different list of projectors
```

# Implementation handoff checklist

Before starting L01 code, the implementer should be able to answer all of the following from this documentation without repeating the audit:

- which current modules are canonical vs derived;
- where atomic outbox rows must be written;
- why PostgreSQL is sufficient for durable handoff;
- why time transitions need a scheduler in addition to outbox events;
- why applicability/relationship/graph projectors should reuse existing domain logic;
- why `CommercialSignal` synthesis needs reviewed per-family rules;
- why zero desired hypotheses must retire old current rows;
- why analyst workflow state must be preserved separately from generated-basis currentness;
- why backfill cannot use a smaller projection contract than incremental collection;
- why a full graph/hypothesis refresh remains a repair tool rather than normal correctness dependency;
- which migrations should land in which micro-lot;
- which existing test files should be extended and which new E2E suites should be created;
- which false semantic upgrades are forbidden;
- what exact proof Lot28 must provide before `IMPLEMENTED_VALIDATED` can be claimed.

If any implementation proposal contradicts those answers, it needs architectural review before merge.