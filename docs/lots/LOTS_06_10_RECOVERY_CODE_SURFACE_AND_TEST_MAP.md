# Lots 06–10 recovery code surface and test map

Status: **PLANNED_LOCKED_AFTER_SECOND_AUDIT**  
Recovery: **R02**  
Issue: **#175**

This map records the code surfaces proven by the second audit and the intended implementation ownership. Candidate paths may be renamed if bounded-context ownership remains identical.

## R02-L01 — ownership registry

Existing docs:

- `docs/lots/lots_06_10_recovery_findings.yml`
- `docs/lots/LOTS_06_10_IMPLEMENTATION_FINALITY_RECOVERY.md`
- `docs/lots/LOTS_06_10_IMPLEMENTATION_GAP_AUDIT.md`
- `docs/lots/LOTS_06_10_FINALITY_RECOVERY_MICROLOTS.md`
- this file
- `docs/lots/LOTS_06_10_FINAL_AUDIT_AND_OWNERSHIP_LOCK.md`

Create `tests/architecture/test_lots_06_10_recovery_ownership.py` and validate F01–F08 ownership/dispositions plus no premature closeout.

---

## R02-L02 — ATS organization binding + cross-provider duplicate decisions

### Proven existing surfaces

- `src/cip/adapters/sources/canonical_jobs.py`
  - `CanonicalPublicJob.organization_key`
  - derived `organization_id`
  - `exact_match_candidate_key`
  - `exact_cross_provider_match`
  - `map_canonical_public_job()` constructs `Organization`, Evidence, CommercialSignal.
- `src/cip/adapters/sources/greenhouse/registry.py` / `mapper.py`
  - board `id` becomes `organization_key`.
- `src/cip/adapters/sources/lever/registry.py` / `mapper.py`
  - site `id` becomes `organization_key`.
- `src/cip/adapters/sources/smartrecruiters/registry.py` / `mapper.py`
  - company `id` becomes `organization_key`.
- `src/cip/modules/opportunities/infrastructure/projections.py`
  - `persist_commercial_projections()` upserts `projection.organization` before evidence/signal/opportunity generation.
- Lot08 organization identity application/infrastructure surfaces for exact/reviewed identity decisions.

### Existing proof tests to modify/extend

- `tests/integration/test_greenhouse_commercial_projection.py` currently proves a registry-derived organization can be created directly.
- canonical ATS mapper/collector tests under `tests/unit/adapters/`.
- Lot08 organization identity tests and `tests/integration/test_organization_identity_persistence_api.py`.

### Candidate implementation surfaces

Prefer a narrow public-job binding/dedup bounded context or an existing domain that can own both source→canonical organization binding and job duplicate decisions. Provider adapters must not own SQL persistence.

Likely schema:

- source ATS organization binding: provider/source tenant key → canonical organization id + decision state + evidence/rule/version + reviewer/audit;
- duplicate group/member/decision + decision history/reversal metadata.

Do not copy provider payloads into these tables and do not destructively rewrite source-native evidence.

### Required tests

- unresolved ATS binding blocks canonical org-scoped projection;
- exact/reviewed binding permits it;
- ambiguous/name-only binding never auto-confirms;
- same legal org across different ATS local IDs converges;
- exact cross-provider duplicate deterministic/replay-safe;
- ambiguity/review reject/split/correction reversible;
- PostgreSQL concurrent arrivals unique/race-safe;
- provider-native evidence independently queryable after grouping/split.

---

## R02-L03 — provider connectivity verification

### Existing

- `src/cip/modules/provider_onboarding/application/service.py`
- secret-reference resolver/runtime secret surfaces
- provider profile/catalogue
- `src/cip/modules/provider_onboarding/api/routes.py`
- approved provider client/transport infrastructure.

### Existing proof test

`tests/integration/test_provider_onboarding_api.py` currently sets INPI env references and expects `connected`; this must be changed so reference availability alone cannot prove connectivity.

### Candidate create

- onboarding `ProviderVerificationPort` and typed secret-free result;
- provider verifier registry;
- provider-specific minimal verification adapters.

Test rejected auth/scope, outage, timeout, missing verifier, policy-before-network, auth-none/manual semantics and complete redaction.

---

## R02-L04 — transition/expiry/rotation/reverify lifecycle

### Existing

- provider onboarding domain models;
- `application/service.py` including `_transition`, register/verify/revoke;
- API routes/schemas;
- persistence record with state, secret refs, `last_verified_at`, `expires_at`, error/audit fields;
- unit tests under `tests/unit/provider_onboarding/`;
- `tests/integration/test_provider_onboarding_api.py`.

### Candidate modifications

- one domain lifecycle/transition policy;
- reference-set non-secret revision/fingerprint binding successful verification to current configuration;
- explicit rotation/expiry/reverify application/API behavior;
- operator UI status/actions when needed.

Tests: full legal/illegal edge matrix; no audit on invalid jump; exact expiry; rotate→must reverify; failed reverify; revoke; blocked state; PostgreSQL verify↔rotate/revoke race; secret redaction.

---

## R02-L05 — composed fail-closed source execution authority

### Proven existing surfaces

- `src/cip/modules/source_portfolio/application/execution.py`
  - currently `record is None -> True`.
- `src/cip/modules/source_portfolio/application/catalog.py`
  - portfolio sync; `authorization_expires_at` comes from catalog entry.
- `src/cip/modules/source_portfolio/application/health.py`
  - computes authorization/quota/cost freshness blocks from portfolio state.
- `src/cip/modules/source_portfolio/application/service.py`.
- `src/cip/modules/provider_onboarding/application/service.py`
  - separate onboarding state/expiry/verification/revoke truth.
- `src/cip/modules/collection_orchestration/application/worker.py`
  - claims then calls `source_execution_allowed()` before `adapter.collect()`.
- `src/cip/modules/source_portfolio/application/backfill_worker.py`
  - `_claim_partition()` calls `source_execution_allowed()` before selecting a partition; collect occurs after claim.

### Existing tests

- `tests/integration/test_source_portfolio_execution_guards.py`
  - pause-after-queue cancellation;
  - portfolio `authorization_expires_at` block;
  - quota/cost block.
- `tests/integration/test_source_portfolio_backfill_worker.py`.
- `tests/integration/test_source_portfolio_runtime_reconciliation.py`.
- `tests/integration/test_source_portfolio_lifecycle.py`.
- `tests/integration/test_provider_onboarding_api.py`.

### Required modifications

1. replace missing-row allow with typed fail-closed decision;
2. compose current onboarding authorization for providers requiring onboarding;
3. define mapping source_id/provider profile ↔ portfolio source without duplicate identity tables;
4. reverse validate runtime adapters/schedules/manual/backfill targets against portfolio at startup;
5. recheck composed eligibility at last safe pre-network boundary for incremental and backfill work;
6. make denial observable and prove zero network call;
7. preserve auth-none public source semantics only when explicitly executable/governed.

### Required race/negative tests

- missing record deny;
- candidate/disabled deny even with adapter present;
- onboarding revoked/failed/expired deny;
- rotated reference without successful current-revision verification deny;
- revoke/expiry/rotate after queue/claim but before collect => zero network;
- incremental/backfill/manual parity;
- portfolio authorization expiry and onboarding expiry cannot contradict into an allow;
- startup hard-fails/reports executable runtime source without portfolio ownership;
- approved current source works after synchronization.

### Lot28 boundary

No global outbox/derived-state invalidation implementation here. F06 remains Lot28/#171.

---

## Historical-preservation gates

### Lot06

Preserve unchanged-active refresh, fingerprint-gated observations, bounded TTL, source governance and no applicant/private data.

### Lot08

Preserve exact official-identifier safety, ambiguity review, conflicting identifier retention and evidence provenance. F07 must **consume**, not weaken or replace, this authority.

## Migration gate

If R02-L02/L04/L05 adds schema or reference revisions:

- upgrade from current main succeeds;
- no historical identity binding/dedup/verification success is fabricated;
- legacy rows default to conservative unresolved/reverify-required state where truth is absent;
- downgrade preserves source-native evidence and secret safety;
- upgrade-after-downgrade succeeds on PostgreSQL.

## Final exact-head matrix

```text
architecture ownership + adapter boundaries
ATS unit/integration + replay/concurrency
organization identity integration
provider onboarding unit/integration + secret redaction
source portfolio scheduler/worker/backfill/manual execution guards
PostgreSQL race tests
migration upgrade/downgrade/upgrade
backend lint/type/coverage/full regression
frontend lint/type/test/build when touched
security/policy-before-network
unresolved review-thread check
exact-head GitHub CI
```

A green subset is not R02 finality proof.
