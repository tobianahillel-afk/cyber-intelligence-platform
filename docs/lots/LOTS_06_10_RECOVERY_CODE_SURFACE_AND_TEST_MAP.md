# Lots 06–10 recovery code surface and test map — third pass

Status: **PLANNED_LOCKED_AFTER_THIRD_PASS**  
Recovery: **R02**  
Issue: **#175**

This is the implementation navigation map. Candidate paths may be renamed when existing bounded-context conventions demand it, but ownership and invariants must remain unchanged.

## R02-L01 — ownership registry

Existing:
- `docs/lots/lots_06_10_recovery_findings.yml`
- all R02 docs.

Create/extend:
- `tests/architecture/test_lots_06_10_recovery_ownership.py`.

Enforce version 3 F01–F12, one owner each, F06 Lot28/#171, no placeholders, no premature closeout.

## R02-L02 — ATS identity binding + duplicate decisions

Existing:
- `src/cip/adapters/sources/canonical_jobs.py`
- `src/cip/adapters/sources/greenhouse/`
- `src/cip/adapters/sources/lever/`
- `src/cip/adapters/sources/smartrecruiters/`
- `src/cip/modules/organizations/infrastructure/identity_*`
- commercial projection persistence in opportunities/collection orchestration.

Candidate create/modify:
- public-job canonical duplicate decision domain/application service;
- ATS source-identity→canonical-organization binding contract using existing organization identity records where possible;
- normalized duplicate group/member/decision/audit persistence;
- migration and analyst review/reversal endpoint/read model if needed.

Tests: cross-provider exact, ambiguity, binding absent, binding reviewed, reversible split, replay, PostgreSQL concurrency, evidence preservation.

## R02-L03 — provider verification

Existing:
- `src/cip/modules/provider_onboarding/application/service.py`
- secrets/runtime secret resolution;
- provider profile registry;
- approved provider clients/adapters.

Create/extend:
- `ProviderVerificationPort` in onboarding application ports;
- provider verification registry and provider-specific bounded implementations;
- typed secret-free verification result/error model.

Tests: credential/scope/connectivity failure, timeout, policy-before-network, missing implementation, successful verification, redaction.

## R02-L04 — onboarding lifecycle and revision validity

Existing:
- onboarding domain models/service/API/persistence/audit;
- `sync_provider_profiles()` and `_refresh_record()`.

Modify/create:
- explicit domain lifecycle transition policy;
- non-secret secret-reference revision/fingerprint;
- provider-profile/verification-contract revision/fingerprint;
- verification revision binding;
- rotate/expire/reverify operations and API/UI controls as required.

Tests: complete transition matrix; illegal edge before mutation; profile change invalidates verification; required-secret/auth-mode change; verify/rotate/revoke/profile-sync races; exact expiry boundary; blocked provider.

## R02-L05 — composed execution eligibility

Existing:
- `src/cip/modules/source_portfolio/application/execution.py`
- `src/cip/modules/source_portfolio/application/catalog.py`
- `src/cip/modules/collection_orchestration/application/runtime.py`
- scheduler/worker/priority/backfill gates;
- onboarding persistence.

Modify/create:
- typed `SourceExecutionDecision`/deny reason;
- onboarding authorization reader/port consumed by Source Portfolio application layer without circular infrastructure coupling;
- reverse startup validation runtime adapter/schedule -> portfolio;
- final pre-network revalidation in incremental and backfill workers.

Tests: missing portfolio, revoked/expired/failed onboarding, rotated-unverified, candidate/paused/disabled, adapter absent, queued-before-revoke, no transport call after deny.

## R02-L06 — source mutation causal integrity

Existing:
- `src/cip/modules/raw_observations/domain/entities.py`
- `src/cip/modules/raw_observations/domain/reducer.py`
- `src/cip/modules/raw_observations/infrastructure/models.py`
- `src/cip/modules/collection_orchestration/infrastructure/repository_completion.py`
- `infra/migrations/versions/20260805_0008_source_portfolio.py`
- ATS collectors/mappers;
- `policies/source_portfolio.yml` capability flags.

Modify/create:
- mutation repository/application validator;
- referential predecessor constraint/current-head persistence if needed;
- explicit conflict/stale result;
- ATS correction/tombstone generation based on complete checkpoint diff;
- executable manifest-capability architecture tests.

Migration candidates:
- self-FK or normalized predecessor relation;
- current-head table/index/constraint required for race-safe single active lineage;
- check constraint/action enum hardening where consistent with project migration style.

Tests:
- unknown predecessor;
- cross-source/cross-key predecessor;
- stale mutation;
- concurrent corrections;
- complete-traversal deletion;
- no deletion after partial traversal;
- correction then tombstone then replay;
- manifest says supported iff executable contract test passes.

## R02-L07 — durable backfill recovery

Existing:
- `src/cip/modules/source_portfolio/application/backfill.py`
- `src/cip/modules/source_portfolio/application/backfill_worker.py`
- `src/cip/modules/source_portfolio/infrastructure/models.py::BackfillPartitionRecord`
- collection orchestration queue/lease/circuit modules;
- `AdapterPartialExecutionError` contract.

Modify/create:
- backfill lease owner/expiry/available-at and ownership token OR shared collection job primitive;
- stale RUNNING recovery;
- partial progress persistence;
- shared circuit/backoff application;
- race-safe state transition functions.

Migration required if partition table gains lease/retry fields.

Tests: PostgreSQL two-worker claim, crash recovery, lease loss, partial batch resume, retry backoff, circuit open/half-open, pause/disable/revoke race, no duplicate records/value.

## R02-L08 — source quality run profile

Existing:
- `src/cip/modules/collection_orchestration/application/ports.py::AdapterCollectionBatch`
- `src/cip/modules/source_portfolio/application/health.py`
- `src/cip/modules/source_portfolio/application/quality.py`
- `SourceQualityBaselineRecord`;
- ATS wrappers and collectors.

Modify/create:
- typed `SourceRunQualityProfile` or equivalent in shared adapter output;
- population/delta/traversal metrics;
- quality evaluator accepting the typed profile;
- optional separate delta baseline if valuable.

Migration may extend quality baseline with population and delta dimensions; do not reinterpret existing historical `expected_records_per_run` silently without a migration/backfill policy.

Tests: full-population stable low-delta, real population collapse, partial traversal, not-modified, removal-only, schema drift, field population.

## R02-L09 — source value attribution

Existing:
- `src/cip/modules/source_portfolio/application/value.py`
- incremental worker value event;
- backfill worker value event;
- `SourceValueEventRecord`.

Modify/create:
- one helper/result mapping persistence outcome -> value event;
- correct backfill commercial/identity/source-owned projection counts;
- partial retry idempotency;
- preserve execution mode and historical semantics.

Tests: real commercial backfill, identity backfill, replay, partial retry, ablation with/without source, no false fresh-trigger classification.

## R02-L10 — closeout

No production ownership beyond qualification.

Required suites on one exact SHA:
- architecture;
- ATS unit/integration;
- raw-observation mutation/reducer;
- onboarding unit/integration/PostgreSQL races;
- source portfolio/runtime/backfill/quality/value;
- migrations up/down/up;
- backend lint/type/coverage/full regression;
- frontend full gates if touched;
- secret/security gates;
- unresolved review threads;
- exact-head CI.

## Preserved boundaries

Do not add in R02:
- second global outbox/reconciliation engine (Lot28/#171);
- supply-chain release controls (Lot29/#6);
- DNS/address safety framework (Lot30/#169);
- privacy erasure/non-resurrection workflow (Lot31/#5);
- browser/MFA/CAPTCHA bypass;
- active prospect scanning.
