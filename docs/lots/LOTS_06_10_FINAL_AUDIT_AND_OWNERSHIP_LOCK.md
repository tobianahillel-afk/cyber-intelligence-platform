# Lots 06–10 final audit and ownership lock

Status: **FINAL_AUDIT_COMPLETE_IMPLEMENTATION_PENDING**  
Recovery: **R02**  
Tracking issue: **#175**  
Audited baseline: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`  
Second adversarial pass locked: **2026-08-18**

This document and `lots_06_10_recovery_findings.yml` are the authoritative pre-implementation ownership lock. This is **not** a runtime closeout.

## 1. Final result after second adversarial pass

### Active R02 implementation findings

| ID | Historical lot | Capability | Severity | Owner |
|---|---:|---|---|---|
| R02-F01 | 07 | durable/reversible cross-provider public-job dedup | high | R02-L02 |
| R02-F02 | 09 | provider-specific connectivity verification | high | R02-L03 |
| R02-F03 | 09 | legal onboarding transition graph | high | R02-L04 |
| R02-F04 | 09 | expiry/rotation/reverification lifecycle | high | R02-L04 |
| R02-F05 | 10 | fail-closed central source-portfolio membership/execution | critical | R02-L05 |
| R02-F07 | 07 | ATS commercial projection requires resolved canonical organization identity | high | R02-L02 |
| R02-F08 | 10 / integration 09→10 | onboarding authorization must participate in runtime execution authority | critical | R02-L05 |

### Existing later-owned residual

| ID | Historical lot | Capability | Severity | Owner | Disposition |
|---|---:|---|---|---|---|
| R02-F06 | 10 | global backfill/incremental/replay + correction/retraction/expiry derived-state convergence | critical | Lot28/#171 | owned_by_existing_later_scope |

### Historical cores retained

- Lot06 core remains terminal.
- Lot08 **internal identity foundation** remains terminal; F07 is the Lot07 integration that must consume it.

There is no ownerless residual in the reviewed scope after this lock.

## 2. Decisions that changed in the second pass

### Lot07 now has two defects, not one

The first audit correctly found missing durable/reversible inter-ATS dedup (F01), but treated the canonical `organization_key` as an already-safe identity input. The deeper trace disproves that assumption.

Greenhouse, Lever and SmartRecruiters registries provide local configuration IDs and names. Those IDs flow through their mappers into `CanonicalPublicJob.organization_key`; the canonical mapper derives an `organization_id` from that key and constructs an `Organization`; central commercial persistence then upserts it and can generate an opportunity.

The current path therefore lacks an enforced proof that an ATS tenant/board/company has been bound to a canonical organization through Lot08's safe identity rules.

**Decision:** F07 is HIGH and owned by the same R02-L02 as F01. Identity must be resolved/bound before cross-provider grouping or organization-scoped commercial aggregation. Lot08 itself is not reopened.

### Lot10 now has two local critical execution defects, not one

F05 remains the explicit `missing SourcePortfolioRecord -> True` legacy fail-open.

The deeper trace also proves separate authorization truths:

- Lot09 onboarding has `state`, `expires_at`, `last_verified_at`, secret references, failure and revocation;
- Lot10 portfolio has independent status/`authorization_expires_at`/health;
- `source_execution_allowed()` consumes the latter but not the former;
- both incremental and backfill workers rely on this gate before adapter network execution.

Historical Lot10 requires automatic stop at authorization expiry and explicitly composes onboarding into its exit chain.

**Decision:** F08 is CRITICAL and owned by R02-L05. Lot09 remains the credential/authorization source of truth; Lot10 remains the single execution authority; Lot10's verdict must compose the current Lot09 truth.

## 3. Exact ownership lock

### R02-L01

Owns only machine-checkable recovery ownership/no-orphan enforcement.

### R02-L02 — F01 + F07

Owns the public-ATS canonicalization boundary:

- source-native ATS organization/tenant identity preserved;
- explicit source→canonical organization binding through exact official or reviewed identity decision;
- unresolved identity cannot mint canonical org-scoped commercial state;
- durable conservative/reversible cross-provider job grouping;
- no fuzzy/name-only organization auto-merge;
- no destructive provider evidence merge.

Lot28 later consumes canonical changes for global downstream reconciliation.

### R02-L03 — F02

Owns provider-specific bounded connectivity verification before authenticated CONNECTED.

### R02-L04 — F03 + F04

Owns one legal provider onboarding state machine including expiration, reference rotation and re-verification. No parallel lifecycle.

### R02-L05 — F05 + F08

Owns one composed runtime execution authority:

`portfolio membership/status + onboarding authorization/current verification + freshness/health + quota/cost + adapter availability -> typed allow/deny`

It must govern scheduled, queued, incremental, backfill and manual network-capable execution, rechecking at the last safe pre-network boundary.

### R02-L06

Owns only final adversarial qualification/exact-head proof and eventual closeout.

### Lot28/#171 — F06

Sole owner of platform-wide derived-state reconciliation/invalidation and backfill/incremental/replay convergence. R02 must not duplicate it.

## 4. Evidence lock

### F01

`exact_cross_provider_match()` and candidate key exist, but no durable grouping decision/reversal is materialized.

### F02

`verify_provider_configuration()` resolves required references; existing INPI API test demonstrates that environment references becoming available are sufficient to reach `connected`. Provider connectivity/scope itself is not verified.

### F03/F04

`_transition()` writes target state directly. `expires_at` exists, but current ordinary routes/service do not provide a complete revision-bound rotation/expire/reverify lifecycle.

### F05

`source_execution_allowed()` explicitly returns true when no portfolio record exists.

### F07

The three public ATS mappers use registry-local ID as `organization_key`; canonical job mapping constructs an Organization; `persist_commercial_projections()` upserts it. Greenhouse integration test proves the behavior end-to-end.

### F08

Portfolio catalog/health use portfolio authorization metadata, not current onboarding record state. Both ordinary incremental worker and backfill worker call the shared portfolio execution guard; this makes a composed guard the correct fix and disproves the need for a separate backfill finding.

## 5. Explicit non-findings / anti-duplication

- No Lot06 immediate tombstone requirement beyond bounded expiry/current refresh.
- No Lot08 fuzzy matching project; internal exact/review identity foundation remains terminal.
- No F09 claiming backfill fully bypasses source portfolio: it already uses the shared guard.
- No reinterpretation of typed `CommercialProjection` as adapter-owned direct SQL.
- No second global outbox/reconciliation queue; Lot28 owns that.
- No supply-chain/release duplication (Lot29/#6).
- No DNS/address-safety duplication (Lot30/#169).
- No privacy non-resurrection duplication (Lot31/#5).
- No browser/CAPTCHA/MFA bypass.
- No synthetic live-provider proof duplication of Source Activation/SA20.

## 6. Required terminal proof

R02 cannot close until the same exact final SHA proves:

- registry/no-orphan architecture guard;
- F01/F07 identity binding + reversible job dedup under replay, correction and PostgreSQL concurrency;
- F02 provider auth/scope/connectivity verification with policy-before-network and redaction;
- F03/F04 legal transition matrix + exact expiry + rotation/reverify/revoke race safety;
- F05/F08 fail-closed composed execution authority across scheduler/queued worker/backfill/manual paths, with zero network after denial;
- F06 still uniquely handed to Lot28 unless independently completed there;
- reversible migrations where introduced;
- full backend and architecture gates;
- frontend gates when touched;
- security/redaction regression;
- no unresolved review threads;
- exact-head CI green.

Only then may `docs/lots/LOTS_06_10_FINALITY_RECOVERY_CLOSEOUT.md` be created and issue #175 closed.
