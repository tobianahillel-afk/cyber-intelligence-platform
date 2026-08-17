# Lots 06–10 final audit and ownership lock

Status: **FINAL_AUDIT_COMPLETE_IMPLEMENTATION_PENDING**  
Recovery: **R02**  
Tracking issue: **#175**  
Audited baseline: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`

This document is the authoritative pre-implementation ownership lock for the Lots 06–10 recovery. If an earlier R02 document is less precise, this document and `lots_06_10_recovery_findings.yml` control.

It is **not** a runtime closeout. The code fixes R02-L01–L05 and the adversarial gate R02-L06 remain to be implemented/proven.

## 1. Final audit question

For each historical Lot 06–10, the audit asked:

> If the original issue were reviewed today against the current ordinary runtime—not only its historical merge evidence—what acceptance capability is still absent, only partially materialized, or now known to require an explicitly later owner?

The audit additionally rejected defects that would merely duplicate later architecture or reinterpret historical requirements more strictly than written.

## 2. Primary historical contracts

- Lot06 — issue #21 — Greenhouse cyber hiring signals.
- Lot07 — issue #23 — Lever + SmartRecruiters shared public-job model, source lifecycle and prudent/reversible inter-ATS dedup.
- Lot08 — issue #25 — French/European organization identity foundation.
- Lot09 — issue #27 — official provider onboarding and secret lifecycle.
- Lot10 — issue #29 — source portfolio runtime, backfill, freshness and source health.

## 3. Final result

### Active R02 implementation findings

| ID | Historical lot | Capability | Severity | Owner |
|---|---:|---|---|---|
| R02-F01 | 07 | durable/reversible cross-provider public-job dedup | high | R02-L02 |
| R02-F02 | 09 | provider-specific connectivity verification | high | R02-L03 |
| R02-F03 | 09 | legal onboarding transition graph | high | R02-L04 |
| R02-F04 | 09 | expiry/rotation/reverification lifecycle | high | R02-L04 |
| R02-F05 | 10 | fail-closed central source-portfolio execution authority | critical | R02-L05 |

### Existing later-owned historical residual

| ID | Historical lot | Capability | Severity | Owner | Disposition |
|---|---:|---|---|---|---|
| R02-F06 | 10 | backfill/incremental/replay + correction/retraction/expiry downstream convergence | critical | Lot28/#171 | owned_by_existing_later_scope |

### Historical cores not locally reopened

- Lot06 — terminal historical core retained.
- Lot08 — terminal historical core retained.

There is **no currently known ownerless residual** in the audited Lot06–10 scope after this ownership lock.

## 4. Evidence lock by lot

### Lot06 — terminal historical core

The original issue requires bounded expiration and refresh of active postings, not an immediate destructive tombstone on first absence.

Current Greenhouse collection:

- authorizes before request;
- produces a current board fingerprint map;
- emits observations only for changed/new fingerprints;
- maps every currently returned relevant posting to a current commercial projection;
- therefore refreshes mutable expiry for active postings while avoiding duplicate observations;
- no longer refreshes a posting absent from a later successful provider result.

The shared canonical job mapping uses bounded signal TTL.

**Decision:** do not create an R02 finding for immediate withdrawal. Global downstream withdrawal/reconciliation is a Lot28 property where applicable.

### Lot07 — one finality defect

The historical issue explicitly requires `déduplication inter-ATS prudente et réversible`.

Current canonical code supplies:

- a provider-independent exact-match candidate key;
- `exact_cross_provider_match()`;
- provider-scoped source record/evidence/signal identities that correctly preserve provenance.

What is not materialized by that path is the durable decision layer that makes a cross-provider group/rejection/split explainable and reversible across replay and provider corrections.

A pure equality helper is not the same acceptance capability as durable reversible deduplication.

**Decision:** R02-F01 → R02-L02.

The fix must preserve source-native evidence and must not auto-merge ambiguous/fuzzy cases.

### Lot08 — terminal historical core

The original issue requires exact official-identifier auto-confirmation and review for ambiguous cases.

The audited identity layer preserves evidence-bound identity projections and internal consistency. Automatic confirmation cannot attach multiple organizations in one projection, and the resolver/identifier boundary audited during this recovery retains exact official IDs as the safe auto-confirm route rather than name-only fusion.

**Decision:** no local R02 finding.

Do not move later graph merge/split/reactive invalidation into Lot08 recovery. Those capabilities already have later architecture ownership.

### Lot09 — three finality defects

#### Connectivity

Original issue text explicitly says:

`validation des références et test de connectivité via ports provider-specific`

Current `_verification_result()`:

- handles auth-none and manual modes;
- checks missing references;
- checks resolver availability;
- returns `CONNECTED` for authenticated providers when references are available.

It does not invoke a provider-specific verification port.

**Decision:** R02-F02 → R02-L03.

#### Transition legality

Original acceptance explicitly says invalid state transitions are refused.

Current `_transition()` directly writes the target state then emits audit history. Audit history records what happened but does not prove the requested edge was legal.

**Decision:** R02-F03 → R02-L04.

#### Rotation and expiry

Original scope explicitly includes rotation and expiration. Current persistence/domain exposes `expires_at`, and revocation clears it, but the ordinary API/service presents start/checkpoint/reference/verify/revoke without a complete operational rotation/expiry/reverification contract bound to the current reference configuration.

A model field by itself is not lifecycle finality.

**Decision:** R02-F04 → R02-L04.

R02-F03 and F04 share one owner so R02 does not create competing state machines.

### Lot10 — one local critical defect + one existing later handoff

#### Central authority is fail-open

The central `source_execution_allowed()` function says sources not yet represented in the Lot10 portfolio retain legacy behavior and implements `record is None -> True`.

The normal application does synchronize the portfolio at bootstrap; therefore the finding is **not** “there is no central catalogue.” The defect is narrower and stronger: the catalogue is not terminally authoritative because missing membership remains executable.

**Decision:** R02-F05 → R02-L05.

R02-L05 must add reverse adapter/schedule-to-portfolio completeness validation before switching to fail closed, preventing legitimate current sources from being silently stranded.

#### Backfill/current derived convergence

Lot10 historically requires backfill/incremental convergence and correction/tombstone/retraction behavior. The later derived-state finality audit has already proved and documented that full downstream convergence is missing across modules and assigned the canonical solution to Lot28/#171.

**Decision:** R02-F06 is real but is **not** implemented in R02. Disposition is `owned_by_existing_later_scope`.

## 5. Explicit anti-duplication decisions

R02 must not create any of the following:

- a second transactional outbox or global reconciliation queue — Lot28 owns it;
- provider-specific direct invalidation of every downstream module — Lot28 owns generalized propagation/invalidation;
- lockfile/SBOM/release provenance work — Lot29/#6;
- DNS pinning/rebinding architecture — Lot30/#169;
- privacy deletion/non-resurrection workflows — Lot31/#5;
- browser/CAPTCHA/MFA bypasses — prohibited/outside R02; browser historical implementation remains separate;
- synthetic controlled-live evidence — live provider proof remains Source Activation/SA20 ownership when activation is the missing property.

## 6. Non-gap decisions that future audits must preserve

### Typed CommercialProjection output

Adapters constructing typed `CommercialProjection` values is not by itself a violation of Lot10's no-direct-write acceptance test when the central worker owns database persistence. R02 does not ban typed output values.

### Greenhouse absence

Do not add a Greenhouse-specific immediate tombstone merely because the checkpoint no longer contains a removed job. Historical Lot06 requires bounded expiry/refresh semantics, which the current pattern provides. Later generalized invalidation remains separate.

### Lot08 conservative identity matching

Do not weaken or replace exact-identifier-first identity resolution with fuzzy auto-merge as part of R02.

## 7. Recovery implementation ownership

### R02-L01

Executable manifest/no-orphan architecture test.

### R02-L02

Durable conservative/reversible cross-provider public-job duplicate decisions.

### R02-L03

Provider-specific bounded connectivity verification application port and provider implementations.

### R02-L04

Single legal onboarding state machine including expiry/rotation/reverification.

### R02-L05

Fail-closed portfolio authority plus reverse completeness/startup validation and execution-time recheck.

### R02-L06

Adversarial qualification, migration/regression/full exact-head gates, no-orphan check and eventual closeout.

## 8. Required proof to close each finding

### R02-F01

Must prove:

- source evidence remains separate;
- exact duplicates converge deterministically;
- ambiguity does not auto-merge;
- decision is persisted;
- reviewed rejection/split is replay-stable;
- provider correction can reverse grouping;
- PostgreSQL concurrency does not create duplicate groups.

### R02-F02

Must prove:

- reference availability alone is insufficient for authenticated provider success;
- provider-specific verification is policy-gated before network;
- rejected credential/scope cannot be `CONNECTED`;
- provider outage is a typed non-secret failure;
- successful probe produces the current verification truth;
- manual/auth-none semantics remain truthful.

### R02-F03/F04

Must prove:

- full legal-transition matrix;
- every illegal edge fails before mutation;
- rotation invalidates old verification;
- expiry removes current-connected semantics at the boundary;
- new reference must reverify;
- revoke/rotate/verify races are safe;
- blocked providers cannot transition around controls;
- secret values never cross persistence/API/audit/log boundaries.

### R02-F05

Must prove:

- missing portfolio source cannot schedule/execute/backfill/manual refresh;
- approved current sources are synchronized explicitly before execution;
- adapter/schedule reverse completeness is validated;
- disable/removal after enqueue is respected by the worker;
- no provider network occurs after denial.

### R02-F06

R02 proof is only that ownership remains Lot28/#171 and no duplicate architecture was introduced. Functional terminal proof belongs to Lot28.

## 9. Final adversarial re-audit requirement

The current finding set is the final **pre-implementation** audit register. It does not exempt the corrected code from another adversarial examination.

R02-L06 must inspect the actual implementation and is authorized to discover R02-F07+ if implementation reveals a new historical residual. Any such finding must be added to the YAML registry with one owner before closeout.

This prevents documentation finality from becoming a reason to ignore defects discovered during implementation.

## 10. Closeout rule

Do not create `LOTS_06_10_FINALITY_RECOVERY_CLOSEOUT.md` now.

Create it only after one exact final implementation SHA proves:

- all R02-local findings implemented/proven;
- R02-F06 still correctly owned by Lot28 unless Lot28 has independently completed it;
- migrations upgrade/downgrade/upgrade;
- PostgreSQL race/replay tests;
- architecture/security/secret-redaction gates;
- backend full gates;
- frontend full gates when touched;
- full regression;
- no unresolved review threads;
- exact-head CI green.

Only then may issue #175 be closed as implementation-finality recovered.
