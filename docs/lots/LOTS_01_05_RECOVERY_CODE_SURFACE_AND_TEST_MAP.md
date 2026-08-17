# Lots 01–05 — Recovery Code Surface, Migration, and Test Map

## Status

`PLANNED_LOCKED`

Parent recovery: `LOTS_01_05_IMPLEMENTATION_FINALITY_RECOVERY.md`.  
Micro-lots: `LOTS_01_05_FINALITY_RECOVERY_MICROLOTS.md`.  
Tracker: issue #173.

## Purpose

Translate recovery requirements into concrete repository surfaces so implementation does not drift into broad refactors or duplicate later architecture. Paths are based on audited baseline `8d7184b8a6f494ceb407ab489d8971f4d015bab6`; every PR must re-read its merged predecessor before editing.

## Global ownership constraints

Reuse, do not replace:

- `collection_orchestration` owns queue/lease/checkpoint/retry/scheduling;
- `service_taxonomy` owns canonical service vocabulary;
- TED remains under `cip.adapters.sources.ted_search`;
- BOAMP remains under `cip.adapters.sources.boamp`;
- `opportunities` owns historical scoring/rule semantics.

Do not introduce here: a second queue/event bus; Lot28 canonical-change outbox/reactors; Lot25 production calibration/feedback; Lot30 DNS/address policy; Lot31 privacy-rights workflow; or Source Activation promotion without live proof.

## R01-L01 — audit/ownership registry

Documents:

```text
docs/lots/LOTS_01_05_IMPLEMENTATION_FINALITY_RECOVERY.md
docs/lots/LOTS_01_05_IMPLEMENTATION_GAP_AUDIT.md
docs/lots/LOTS_01_05_FINALITY_RECOVERY_MICROLOTS.md
docs/lots/LOTS_01_05_RECOVERY_CODE_SURFACE_AND_TEST_MAP.md
docs/lots/lots_01_05_recovery_findings.yml
```

Planned architecture test:

```text
tests/architecture/test_lots_01_05_recovery_ownership.py
```

Assertions: unique IDs; known states/dispositions; one owner per local finding; real later owner for handoffs; no forbidden terminal placeholder; no new numbered roadmap lot.

No production migration.

## R01-L02 — lease heartbeat

Existing surfaces:

```text
src/cip/modules/collection_orchestration/application/worker.py
src/cip/modules/collection_orchestration/application/ports.py
src/cip/modules/collection_orchestration/infrastructure/repository_queue.py
src/cip/modules/collection_orchestration/infrastructure/repository_common.py
src/cip/modules/collection_orchestration/infrastructure/repository_failures.py
src/cip/modules/collection_orchestration/infrastructure/models.py
```

`repository_queue.py` already owns `heartbeat_job(...)`; use it.

Optional new application file, only if needed to preserve code budgets:

```text
src/cip/modules/collection_orchestration/application/lease_guard.py
```

Possible responsibilities: heartbeat interval calculation, lifecycle/controller, monotonic cancellation token, repository operation injected by port/callable. No SQLAlchemy in the application/domain control contract.

If common `CollectionAdapter.collect(...)` needs cooperative cancellation, evolve the common typed contract once and mechanically update adapters. Do not add provider-specific heartbeat callbacks.

Default migration decision: none. Add `last_heartbeat_at` or fencing revision only if PostgreSQL concurrency analysis proves existing lease owner/expiry insufficient; then use additive reversible migration and metadata tests.

Tests: unit timing/cancellation; PostgreSQL owner renewal and concurrent claim; worker integration for >lease duration, forced loss, process disappearance, human checkpoint, retry/partial/dead-letter.

## R01-L03 — schedule provenance

Domain:

```text
src/cip/modules/collection_orchestration/domain/models.py
```

Add stable schedule identity/revision/fingerprint and origin/trigger semantics.

Loader/bundle:

```text
src/cip/modules/collection_orchestration/infrastructure/schedule_loader.py
src/cip/modules/collection_orchestration/infrastructure/schedule_bundle.py
```

Add stable ID/revision parsing, duplicate schedule-ID rejection across bundles, schema compatibility.

Scheduler:

```text
src/cip/modules/collection_orchestration/application/scheduler.py
```

Carry exact provenance through `CollectionJob.from_schedule(...)` while preserving idempotency.

Persistence:

```text
src/cip/modules/collection_orchestration/infrastructure/models.py
src/cip/modules/collection_orchestration/infrastructure/repository_queue.py
```

Expected fields or equivalent normalized model:

```text
trigger_kind
schedule_id
schedule_revision
schedule_fingerprint
```

Checked-in collection schedule YAML must gain stable identities consistently.

Expected migration: one additive reversible revision. Do not invent historic fingerprints; legacy rows are explicitly legacy/unknown.

Tests: loader/bundle, canonical fingerprint, scheduler idempotency, persistence round-trip, legacy hydration, revision chronology, migration cycle.

## R01-L04 — TED pagination

Application adapter:

```text
src/cip/modules/collection_orchestration/application/ted_adapter.py
```

Keep transport construction/error translation/checkpoint conversion; provider traversal belongs in collector.

Provider client:

```text
src/cip/adapters/sources/ted_search/client.py
```

Move from `fetch()` page 1 to explicit current-provider bounded page/cursor request. Keep content-type/size/host-method protections.

Provider collector:

```text
src/cip/adapters/sources/ted_search/collector.py
```

Own multi-page traversal, overlap/dedup, versioned scan checkpoint, budgets, partial execution, and L02 cooperative cancellation at page boundaries if available.

Schema:

```text
src/cip/adapters/sources/ted_search/schemas.py
```

Add only fields required by verified pagination contract.

Checkpoint: evolve JSON shape with backward compatibility from current `{latest_publication_number}`. No DB schema migration expected.

Fixtures should include page1/page2/page3, short/empty last page, duplicate boundary, schema drift, mutation/interruption cases. Integration must exercise worker checkpoint persistence, not collector return only.

## R01-L05 — TED discovery/relevance

Authoritative vocabulary:

```text
src/cip/modules/service_taxonomy/domain/models.py
src/cip/modules/service_taxonomy/domain/classifier.py
docs/CYBER_SERVICE_NEED_TAXONOMY.md
```

Do not duplicate `_SERVICE_TERMS` inside TED.

Possible provider plan module:

```text
src/cip/adapters/sources/ted_search/query_plan.py
```

It owns TED syntax/rendering/version/partitions, not canonical service definitions.

Relevance mapping:

```text
src/cip/adapters/sources/ted_search/mapper.py
src/cip/adapters/sources/procurement_signals.py
```

Assess reviewed fields beyond title. A pure `ProcurementRelevanceAssessment` may be shared only if TED/BOAMP genuinely share semantics; otherwise keep provider mapping narrow and reuse canonical classifier.

Audit selected TED schema fields before adding any new field; every added field needs governance purpose, strict schema, fixtures and minimization review.

Query-plan identity/version should be reconstructable from observations/checkpoint/run metadata without storing giant query text redundantly.

Tests: all 19 families, plan version stability, query partition dedup, multilingual terms, CPV/contract-title cases, physical-security negatives, multi-family notice, taxonomy-duplication guard.

## R01-L06 — BOAMP adaptive windows

Application adapter:

```text
src/cip/modules/collection_orchestration/application/boamp_adapter.py
```

Current `source_window_exceeded` non-retryable terminal mapping should remain only for genuine configured safety/operator intervention after adaptive limits are exhausted, not ordinary dense data.

Provider client:

```text
src/cip/adapters/sources/boamp/client.py
```

Before changes verify current provider support for upper date bounds, precision, `idweb` comparison/range and offset limits. Do not borrow syntax from another Opendatasoft generation.

Provider collector:

```text
src/cip/adapters/sources/boamp/collector.py
```

Likely split into small units: window planner, page consumer, partition splitter, checkpoint/frontier serializer, result dedup/accumulator. Avoid oversized recursion.

Checkpoint stays JSON and keeps current `latest_idweb`/`latest_publication_date` readable while adding versioned bounded frontier state. No DB migration expected.

Fixtures: sparse, >500 multi-day, >500 same-day, overlap boundary, later-partition failure, provider mutation during traversal. Integration proves worker partial progress and no downstream duplication.

## R01-L07 — opportunity benchmark foundation

Keep production score code free of labels:

```text
src/cip/modules/opportunities/domain/scoring.py
src/cip/modules/opportunities/domain/rules.py
src/cip/modules/opportunities/domain/fusion.py
```

Preferred fixtures:

```text
tests/fixtures/opportunity_benchmarks/v1/
```

Preferred evaluator/tests:

```text
tests/commercial_value/opportunity_benchmark.py
tests/commercial_value/test_lot03_opportunity_baseline.py
tests/commercial_value/test_opportunity_benchmark_contract.py
```

If evaluator is genuinely reusable domain logic for Lot25, a framework-free `src/cip/modules/opportunities/domain/evaluation.py` may be justified; otherwise keep it in test/commercial-value tooling.

No production label persistence required by recovery. Production analyst-label storage/feedback remains Lot25 unless an explicit architecture decision changes ownership.

CI emits safe deterministic metric summary; benchmark versions/thresholds are reviewed, not silently regenerated.

## R01-L08 — qualification

Preferred E2E split, respecting file-size limits:

```text
tests/end_to_end/lots_01_05/test_lease_and_schedule_finality.py
tests/end_to_end/lots_01_05/test_ted_finality.py
tests/end_to_end/lots_01_05/test_boamp_finality.py
tests/commercial_value/test_lot03_finality.py
```

Lease concurrency/migration tests use disposable PostgreSQL, not SQLite-only proof. Routine provider tests remain network-free with fake transports/fixtures; live proof stays Source Activation.

Final report created only after implementation:

```text
docs/lots/LOTS_01_05_FINALITY_RECOVERY_CLOSEOUT.md
```

It records exact SHA, CI, test count, coverage, migration head, finding matrix and later-owner trackers.

## Migration summary

| Micro-lot | Expected migration | Notes |
|---|---|---|
| L01 | none | docs/architecture contract |
| L02 | preferably none | only if heartbeat telemetry/fencing persistence proven necessary |
| L03 | yes | schedule/job provenance |
| L04 | none | JSON checkpoint evolution |
| L05 | none | query-plan/version contract unless persisted registry deliberately needed |
| L06 | none | JSON frontier evolution |
| L07 | none for recovery | production label persistence belongs Lot25 by default |
| L08 | none | qualification/closeout |

## Test summary

| Capability | Unit | Contract/fixture | PostgreSQL | E2E | Commercial value |
|---|---:|---:|---:|---:|---:|
| heartbeat/lease | yes | n/a | mandatory | mandatory | n/a |
| schedule provenance | yes | config | mandatory | mandatory | n/a |
| TED pagination | yes | mandatory | worker checkpoint | mandatory | later source value |
| TED relevance | yes | mandatory | optional | mandatory | coverage/FP fixtures |
| BOAMP adaptive windows | yes | mandatory | worker checkpoint | mandatory | later source value |
| Lot03 benchmark | yes | mandatory | no recovery DB requirement | baseline | mandatory |
| no-orphan gate | architecture | n/a | as needed | mandatory | verify handoff |

## Rollback discipline

- L02 rollback restores prior worker behavior without corrupting queue rows.
- L03 downgrade removes new provenance schema while preserving legacy fields.
- L04/L06 readers tolerate immediately previous checkpoint shapes through rollout/rollback.
- L05 rollback preserves old observations and does not silently reinterpret history.
- L07 rollback never mutates production scores.

## Final implementation rule

A helper/diff is never sufficient proof. `heartbeat_job` existing is not L02 completion until ordinary long jobs renew; a TED `page` argument is not L04 completion until collector traversal/resume is safe; a BOAMP splitter is not L06 completion until dense worker execution converges; benchmark fixtures are not L07 completion until evaluator catches an intentionally degraded rule scenario.
