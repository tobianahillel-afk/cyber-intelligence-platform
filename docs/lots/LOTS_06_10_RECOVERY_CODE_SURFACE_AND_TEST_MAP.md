# Lots 06–10 recovery code surface and test map

Status: **PLANNED_LOCKED**  
Recovery: **R02**  
Issue: **#175**

This file is the implementation navigation map for R02. Paths marked `existing` are present on the audited baseline. Paths marked `candidate` are recommended ownership locations and may be renamed only if the final implementation preserves the same bounded-context ownership.

## R02-L01 — ownership registry

### Existing

- `docs/lots/lots_06_10_recovery_findings.yml`
- `docs/lots/LOTS_06_10_IMPLEMENTATION_FINALITY_RECOVERY.md`
- `docs/lots/LOTS_06_10_IMPLEMENTATION_GAP_AUDIT.md`
- `docs/lots/LOTS_06_10_FINALITY_RECOVERY_MICROLOTS.md`
- this file
- `docs/lots/LOTS_06_10_FINAL_AUDIT_AND_OWNERSHIP_LOCK.md`

### Create

- `tests/architecture/test_lots_06_10_recovery_ownership.py`

### Test focus

Manifest uniqueness, allowed dispositions, owner presence, later-tracker presence, no placeholder values, exact Lot28 handoff and no premature closeout claim.

### Migration

None.

---

## R02-L02 — Lot07 cross-provider public-job duplicate decisions

### Existing source contract

- `src/cip/adapters/sources/canonical_jobs.py`
  - `CanonicalPublicJob`
  - `exact_match_candidate_key`
  - `exact_cross_provider_match`
  - source-native observation/projection mapping
- `src/cip/adapters/sources/greenhouse/`
- `src/cip/adapters/sources/lever/`
- `src/cip/adapters/sources/smartrecruiters/`
- collection orchestration projection/persistence boundary

### Candidate new/modified ownership

Prefer a domain/application contract named for public-job duplicate grouping, not a generic utility. For example:

- `src/cip/modules/professional_context/domain/job_duplicates.py` if that existing bounded context owns canonical job semantics; or
- a narrowly scoped `public_jobs` domain/application package if architecture tests show no existing bounded context is correct.

Do not place persistence logic inside provider adapters.

Likely infrastructure surfaces:

- SQLAlchemy records for duplicate group, member and decision/audit;
- repository/application service invoked after canonical public-job persistence;
- migration under the repository's Alembic migration path;
- read model/API only if required for analyst reversal/review.

### Required stored facts

At minimum:

- stable group id;
- source-native member identities;
- decision state;
- rule/version/fingerprint;
- creation/update time;
- review actor/time for manual override if supported;
- reversal/split history or equivalent immutable audit.

Never copy provider payloads into the dedup table.

### Tests to locate/extend

- canonical public job unit tests;
- Greenhouse/Lever/SmartRecruiters mapper/collector tests;
- PostgreSQL persistence integration tests;
- replay/idempotency tests;
- concurrency test for duplicate simultaneous arrival;
- architecture test proving adapter packages do not own dedup persistence.

### Migration strategy

New grouping rows should start empty for legacy data unless a deterministic controlled replay/backfill establishes them. Do not infer historical exact matches solely during schema migration.

### Rollback

Drop only duplicate-grouping projections introduced by R02. Preserve source records, raw observations, evidence and provider-scoped facts.

---

## R02-L03 — Lot09 connectivity verification

### Existing

- `src/cip/modules/provider_onboarding/application/service.py`
  - `verify_provider_configuration`
  - `_verification_result`
- `src/cip/modules/provider_onboarding/application/secrets.py`
- `src/cip/modules/provider_onboarding/application/runtime_secrets.py`
- `src/cip/modules/provider_onboarding/api/routes.py`
- provider onboarding domain/profile catalogue
- approved provider adapter/client infrastructure

### Candidate create

- `src/cip/modules/provider_onboarding/application/ports.py` or a dedicated existing ports module extension for `ProviderVerificationPort`;
- provider-specific verification adapters in infrastructure/provider packages;
- a registry that binds `source_id/auth_mode` to a verification capability without importing concrete clients into the domain/application core.

### Port requirements

The application-facing result must be typed and secret-free. Suggested result fields:

- status/result enum;
- normalized error code;
- provider verification method/version;
- verified_at supplied by application clock;
- optional bounded non-secret metadata needed for diagnosis.

Never return token/key/password values.

### Tests

- provider onboarding service unit tests with fake verification port;
- transport-specific tests fully network-free;
- policy-before-network architecture/integration test;
- error normalization tests;
- audit redaction test;
- API serialization test proving no secret material.

### Migration

Only if verification method/version must be persisted. Existing `last_verified_at`, error code/message and audit history should be reused where sufficient.

---

## R02-L04 — Lot09 transition/rotation/expiry lifecycle

### Existing

- `src/cip/modules/provider_onboarding/domain/models.py`
- `src/cip/modules/provider_onboarding/application/service.py`
  - `_transition`
  - register/verify/revoke operations
- `src/cip/modules/provider_onboarding/api/routes.py`
- `src/cip/modules/provider_onboarding/api/schemas.py`
- onboarding infrastructure model with state, secret references, `last_verified_at`, `expires_at`, errors and audit history
- source-portfolio freshness/authorization integration

### Candidate create/modify

- one domain transition policy/table, e.g. `domain/lifecycle.py`, if adding it to `models.py` would violate module-size/single-responsibility standards;
- explicit application operations for rotation and expiry/reverification if they cannot be expressed safely by existing registration/verify methods;
- API schemas/routes for operator-visible rotation/expiry actions only as needed;
- UI Sources onboarding controls/status if current frontend needs the lifecycle to be operable.

### Transition policy constraints

- total coverage of known states;
- no wildcard “any -> failed/connected” shortcut unless historically and semantically justified;
- blocked/quarantined terminal guards;
- idempotent same-state behavior defined explicitly rather than accidental;
- no state mutation before validation.

### Persistence/migration candidates

Reuse current columns first. Add only metadata required to bind a successful verification to the current secret-reference configuration, for example a non-secret reference-set fingerprint/revision.

No secret contents in fingerprints if that would derive sensitive material; fingerprint stable reference identifiers/configuration, not resolved secret values.

### Tests

- full transition-table parametrized tests;
- invalid-edge negative matrix;
- rotate/reverify/revoke lifecycle;
- exact expiry boundary;
- PostgreSQL race: rotate vs verify;
- API conflict status for invalid transitions;
- source-portfolio composed execution denial after expiry/revoke;
- audit ordering and redaction.

---

## R02-L05 — Lot10 fail-closed source-portfolio authority

### Existing

- `src/cip/modules/source_portfolio/application/execution.py`
  - `source_execution_allowed`
- `src/cip/modules/source_portfolio/application/catalog.py`
- `src/cip/modules/source_portfolio/application/service.py`
- `src/cip/modules/source_portfolio/application/backfill.py`
- `src/cip/modules/source_portfolio/application/backfill_worker.py`
- `src/cip/modules/source_portfolio/application/health.py`
- `src/cip/modules/source_portfolio/application/records.py`
- source-portfolio bootstrap/reconciliation startup path
- machine-readable source portfolio policy/catalogue
- collection scheduler/worker execution paths

### Required modifications

1. Replace `record is None -> True` with fail-closed semantics.
2. Introduce a typed deny/configuration reason rather than silently collapsing all denial causes where the caller needs observability.
3. Add reverse startup validation: executable adapter/schedule/runtime source -> exactly one portfolio ownership record.
4. Ensure queued jobs are rechecked at execution time.
5. Ensure backfill/manual refresh uses the same gate.
6. Keep candidates/non-executable sources unable to run even if an adapter exists.

### Data/bootstrap migration

Before default denial is activated, enumerate all existing executable sources and synchronize them from the machine-readable portfolio. Missing entries are configuration errors, not candidates for implicit auto-executable creation.

### Tests

- `source_execution_allowed` missing-record deny;
- startup reverse reconciliation;
- schedule validation;
- worker recheck after source disable;
- backfill/manual path equality;
- policy denial before provider call;
- candidate source with adapter still denied;
- authorized source works after bootstrap.

### No duplicate Lot28 work

Do not change R02-L05 into the Lot28 outbox/reconciliation implementation. The only R02-L05 concern is whether the source is allowed to execute and whether every execution path is governed by the same portfolio authority.

---

## R02-F06 / Lot28 handoff map

No R02 production code is authorized for this finding.

Canonical owner:

- Lot28 / issue #171;
- existing Lot28 recovery docs on `main`.

R02 tests may assert the ownership pointer, but may not create:

- a second transactional outbox;
- a second derived-state queue;
- provider-specific cross-module invalidation;
- a competing global reconciliation scheduler.

---

## Historical-preservation tests

### Lot06

Preserve:

- unchanged active job refresh without duplicate observation;
- bounded expiry;
- source governance before request;
- no candidate/private application data.

### Lot08

Preserve:

- official-identifier validation;
- no name-only auto-confirmation;
- ambiguous/conflicting review state;
- evidence/identity projection consistency;
- no private-person enrichment introduced by R02.

---

## Migration gate for the entire recovery

If R02-L02 or R02-L04 adds schema:

1. upgrade from current `main` schema succeeds;
2. existing rows remain truthfully interpretable;
3. no historical successful verification or duplicate decision is fabricated;
4. downgrade succeeds without deleting source-native evidence;
5. upgrade after downgrade succeeds;
6. PostgreSQL-backed migration tests run on the exact final code head.

## Security gate

R02 must preserve:

- no raw provider secret in API/DB/audit/logs/fixtures;
- no auth/CAPTCHA/MFA bypass;
- no active scanning;
- policy and portfolio checks before provider network;
- no weaker organization matching;
- no destructive source-history dedup.

## Final exact-head test matrix

The closeout SHA must run, as applicable:

```text
architecture
provider adapter unit tests
ATS canonical/replay tests
provider onboarding unit + PostgreSQL integration tests
source portfolio/backfill/worker integration tests
migration upgrade/downgrade/upgrade
backend lint/type/coverage/full regression
frontend lint/type/test/build when touched
security/secret-redaction tests
unresolved review-thread check
exact-head CI
```

A green subset is not finality proof.
