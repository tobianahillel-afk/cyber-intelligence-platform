# Lots 06–10 implementation gap audit

Status: **FINAL_AUDIT_COMPLETE_IMPLEMENTATION_PENDING**  
Recovery: **R02**  
Issue: **#175**  
Baseline: `8d7184b8a6f494ceb407ab489d8971f4d015bab6`  
Second adversarial pass: **2026-08-18**

## Audit method

The second pass re-read issues #21/#23/#25/#27/#29 and historical PRs #22/#24/#26/#28/#30, then traced current runtime through ATS registries/mappers, canonical job mapping, commercial persistence, organization identity, provider onboarding, source portfolio health/catalog/execution, incremental worker, backfill worker and integration tests.

A helper, field or historical passing test is not terminal proof when the ordinary runtime does not enforce the corresponding invariant.

---

## Lot06 — Greenhouse public hiring signals — issue #21

### Result

**No local R02 finding.** The current Greenhouse path keeps the historical bounded-expiry/current-refresh semantics: unchanged active jobs can refresh current commercial projection without duplicating observations; absent jobs stop refreshing and age out. R02 does not invent an immediate source-specific tombstone requirement. Cross-module downstream withdrawal remains Lot28.

---

## Lot07 — Lever + SmartRecruiters + shared public-job contract — issue #23

### R02-F01 — durable/reversible inter-ATS dedup — HIGH — R02-L02

The exact-match helper exists, but no durable duplicate decision/group/rejection/split is materialized. Provider-native evidence remains correctly separate; the missing capability is the persistent analyst-current grouping decision required by `prudente et réversible`.

### R02-F07 — resolved organization identity before ATS commercial projection — HIGH — R02-L02

This is the key second-pass finding.

#### Proven current path

- Greenhouse `GreenhouseBoard`, Lever `LeverSite` and SmartRecruiters `SmartRecruitersCompany` registries carry provider-local identifiers and display metadata but no canonical organization identity decision/reference.
- Their mappers use the configured registry `id` as `CanonicalPublicJob.organization_key`.
- `CanonicalPublicJob.organization_id` is derived deterministically from `organization_key` and `map_canonical_public_job()` constructs an `Organization` using the configured canonical name.
- `persist_commercial_projections()` directly upserts `projection.organization`, then evidence/signal and opportunity projection.
- `tests/integration/test_greenhouse_commercial_projection.py` asserts that this route creates one `OrganizationRecord` and produces an opportunity for `Example Security` from registry configuration.

#### Why this is a defect

Lot08 established a conservative evidence-backed identity authority: official exact identifiers may auto-confirm; ambiguous/name-only identity must remain reviewable. The ATS commercial path does not prove that its configured `organization_key` has been resolved through that authority before it becomes a canonical organization and aggregation key.

This also makes F01 less trustworthy: cross-provider exact matching includes `organization_key`, so correct dedup can depend on operators independently choosing identical configuration IDs rather than on a canonical resolved legal identity.

#### Final ownership decision

Keep Lot08 internals terminal. Treat this as a **Lot07 integration defect** owned by R02-L02.

Required final architecture:

1. ATS source/tenant identity remains provider-native and immutable.
2. ATS configuration references a canonical `organization_id` only after exact official identity or explicit reviewed binding exists.
3. unresolved/ambiguous ATS organization binding is review-required and cannot silently mint a legal organization record for commercial aggregation.
4. cross-provider dedup first compares resolved canonical organization identity, then conservative job attributes.
5. source-native job/evidence history is never destroyed.
6. later propagation after a binding/merge changes remains Lot28, not R02.

---

## Lot08 — organization identity foundation — issue #25

### Result

**Internal module remains terminal.** The second pass does not find a reason to weaken the exact-ID/review boundary. The new F07 is specifically the missing enforcement of that authority in the ATS commercial path.

This distinction prevents two bad designs: reopening Lot08 as a broad fuzzy matching project, or letting every ingestion source mint canonical legal identities independently.

---

## Lot09 — provider onboarding and secret lifecycle — issue #27

### R02-F02 — provider-specific connectivity verification — HIGH — R02-L03

Current authenticated verification checks that required secret references exist and are resolvable. The integration test confirms that setting INPI username/password environment variables is sufficient for `verify` to return `connected`. No provider-specific connectivity/scope probe is required. This is below the historical acceptance text requiring a provider-specific connectivity port.

### R02-F03 — legal transition graph — HIGH — R02-L04

`_transition()` directly assigns the target state and then writes audit history. The historical contract explicitly requires illegal transitions to be refused. A route-level schema restriction is not a complete state graph.

### R02-F04 — expiry/rotation/reverification — HIGH — R02-L04

`expires_at` and `last_verified_at` are represented, but the ordinary flow lacks a complete revision-bound rotation/expiry/reverify contract. Rotation must invalidate the prior successful verification; expiry must change semantic authorization; failed reverify must not leave stale connected truth.

---

## Lot10 — source portfolio/runtime — issue #29

### R02-F05 — fail-closed portfolio membership — CRITICAL — R02-L05

`source_execution_allowed()` explicitly implements missing-record legacy allow. Both incremental and backfill execution paths use this function, so the correct fix is to make the shared authority fail closed after proving registry/portfolio completeness, not to add provider-specific guards.

### R02-F08 — onboarding authorization must participate in runtime execution authority — CRITICAL — R02-L05

#### Proven split

Provider onboarding owns one authorization lifecycle (`state`, `expires_at`, `last_verified_at`, secret refs, revoke/failure). Source Portfolio owns another execution/freshness representation (`status`, `authorization_expires_at`, health states). Portfolio sync derives authorization expiry from the machine-readable catalog/source governance entry, and `source_execution_allowed()` consults portfolio/health only. No bridge from current ProviderOnboardingRecord authorization state was found in the inspected catalog, health, service, worker or backfill path.

`run_worker_once()` checks `source_execution_allowed()` after claiming a queued job and before adapter lookup/collect. `_claim_partition()` in the backfill worker also checks it before selecting a partition. Therefore the gate is already the right architectural choke point; its input truth is incomplete.

#### Product consequence

A provider can be revoked, failed, expired or rotated-but-not-reverified in onboarding while the portfolio remains independently executable/current. The historical Lot10 contract explicitly says authorization expiry stops execution and its exit path includes onboarding.

#### Final ownership decision

R02-L04 defines valid onboarding authorization state. R02-L05 is the **single owner** of consuming that state for runtime execution. Do not add another global event bus/outbox; expose a composed execution eligibility decision.

Required composition:

`portfolio membership/status + current onboarding authorization + freshness/health + quota/cost + adapter/runtime availability -> typed execution decision`

All network-capable entry points must use it, and queued/claimed work must be revalidated at the last safe pre-network boundary so a concurrent revoke/expiry cannot be ignored.

### R02-F06 — global downstream convergence — CRITICAL — Lot28/#171

Still real and intentionally not implemented by R02. Backfill currently persists a narrower projection set than incremental collection; the platform-wide convergence/invalidation architecture is already owned by Lot28/#171.

---

## Test-depth conclusions

The second pass specifically rejects three tempting false conclusions:

- **“Tests are green, so Lot09 connectivity is complete.”** False: the existing API test encodes secret-reference availability as success and therefore proves the missing provider probe.
- **“Backfill bypasses source portfolio entirely.”** False: it calls the shared execution guard. The real defect is the guard's fail-open/incomplete authorization truth.
- **“Lot08 itself must be reopened.”** False: the defect is the ATS integration failing to require a resolved identity binding before commercial persistence.

## Final registry

| ID | Lot | Severity | Owner | Status |
|---|---:|---|---|---|
| R02-F01 | 07 | high | R02-L02 | recovery_local |
| R02-F02 | 09 | high | R02-L03 | recovery_local |
| R02-F03 | 09 | high | R02-L04 | recovery_local |
| R02-F04 | 09 | high | R02-L04 | recovery_local |
| R02-F05 | 10 | critical | R02-L05 | recovery_local |
| R02-F06 | 10 | critical | Lot28/#171 | owned_by_existing_later_scope |
| R02-F07 | 07 | high | R02-L02 | recovery_local |
| R02-F08 | 10 (cross-lot 09/10) | critical | R02-L05 | recovery_local |

There is no ownerless residual in the reviewed Lots 06–10 scope after this second pass. Future implementation discoveries must be registered as F09+ rather than silently absorbed.
