# Lots 06–10 final audit and ownership lock — third pass

Status: **THIRD_PASS_FINAL_AUDIT_COMPLETE_IMPLEMENTATION_PENDING**  
Recovery: **R02**  
Tracking issue: **#175**  
Audited baseline: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`

This document and `lots_06_10_recovery_findings.yml` version 3 are the authoritative pre-implementation ownership lock for R02. This is not runtime closeout.

## 1. Final result

### R02-local findings

| ID | Historical lot | Severity | Owner | Locked correction |
|---|---:|---|---|---|
| F01 | 07 | HIGH | L02 | durable/reversible inter-ATS duplicate decisions |
| F02 | 09 | HIGH | L03 | provider-specific verification |
| F03 | 09 | HIGH | L04 | legal transition graph |
| F04 | 09 | HIGH | L04 | revision-bound profile/credential expiry/rotation/reverify |
| F05 | 10 | CRITICAL | L05 | fail-closed central portfolio membership |
| F07 | 07↔08 | HIGH | L02 | resolved canonical organization binding before ATS aggregation |
| F08 | 09→10 | CRITICAL | L05 | onboarding authorization composed into runtime eligibility |
| F09 | 10 | HIGH | L06 | causal source mutations + truthful capability manifests |
| F10 | 10 | CRITICAL | L07 | leased/crash-safe/partial/circuit-aware backfill |
| F11 | 10 | HIGH | L08 | population-aware source quality semantics |
| F12 | 10 | HIGH | L09 | truthful historical source-value/ablation accounting |

### Existing later-owned residual

| ID | Lot | Severity | Owner | Disposition |
|---|---:|---|---|---|
| F06 | 10 | CRITICAL | Lot28/#171 | owned_by_existing_later_scope |

There is no known ownerless residual in the audited Lots06–10 scope after this third pass.

## 2. Third-pass architectural decisions

### Source mutation is upstream truth; propagation remains downstream

Lot10 already defines immutable source mutation actions. R02-L06 will make their causal lineage and capability manifests truthful. It may create correction/tombstone source events but must not directly invalidate every opportunity/hypothesis/read model. Lot28 consumes valid mutations through its one reconciliation architecture.

### Backfill reliability must converge on shared collection reliability primitives

The final product should not keep two incompatible reliability stacks. Incremental collection already has leases, expired-lease recovery and circuit/backoff. L07 should reuse or extract shared primitives so backfill has equivalent ownership/retry safety while preserving bounded partition semantics.

### Quality must distinguish state from change

For full-snapshot/delta-hybrid providers, provider population, traversal completeness and immutable changes are different measurements. L08 must represent them separately. `len(batch.observations)` cannot be the universal source-volume truth.

### Historical value is value, but not a fresh trigger

Backfill-derived commercial/identity outputs must be counted for source value/ablation. Their `historical_backfill` mode must remain explicit so they do not masquerade as fresh trigger volume or generate false historical alert value.

### Provider verification is revision-bound

A successful provider verification is proof about an exact configuration. Changing secret references or the provider profile/required auth contract invalidates that proof. L04 owns the single revision-aware lifecycle.

## 3. Evidence lock for new findings

### F09

- RawObservation mutation vocabulary exists.
- `supersedes_observation_id` is carried but not validated as the same-record current predecessor by the reducer.
- reducer ignores the supersedes edge and orders by time/key.
- ATS capability manifests claim corrections/tombstones.
- Greenhouse/Lever/SmartRecruiters changed postings are currently normal UPSERT observations; disappearance is checkpoint absence.

Decision: implement the capability rather than weakening the catalogue, because a correct explicit mutation stream makes the product more complete and gives Lot28 a precise upstream event contract.

### F10

- Backfill partition persistence lacks lease owner/expiry/next-available retry time.
- claim moves PENDING/FAILED to RUNNING; abandoned RUNNING has no recovery path.
- partial adapter batch is discarded in backfill exception handling.
- FAILED can be reclaimed immediately without the incremental circuit/backoff.

Decision: CRITICAL. A production backfill must survive process death and upstream failure without permanent wedging, refetch storms or lost safe progress.

### F11

- quality evaluator trains on `len(observations)`.
- ATS observations are delta emissions after full current-state traversal.

Decision: HIGH. Wrong quality telemetry can disable/trust the wrong sources and hides genuine population collapse while flagging healthy low-change runs.

### F12

- value event schema supports projection counts.
- incremental reports them.
- backfill hardcodes zeros.

Decision: HIGH because Lot10 explicitly uses value/ablation to evaluate source usefulness; systematically undercounting historical-source contribution can drive wrong source-portfolio decisions.

## 4. Non-findings locked by deeper inspection

Do not reopen these without new code evidence:

- Greenhouse, Lever and SmartRecruiters traversal completeness/pagination are bounded and currently defensible.
- Lot08 exact official identifier persistence has global uniqueness; no internal collision bug proven.
- incremental circuit breaker is real and durable; F10 concerns backfill parity.
- priority refresh is not a separate authority bypass.
- normal source-portfolio sync does not simply erase manual PAUSED/DISABLED state.
- construction of typed adapter projections remains distinct from forbidden adapter-owned database writes.

## 5. One-owner map

```text
L01: registry/no-orphan process
L02: F01 F07
L03: F02
L04: F03 F04
L05: F05 F08
L06: F09
L07: F10
L08: F11
L09: F12
L10: final qualification only
Lot28/#171: F06
```

No capability in this map has two runtime owners.

## 6. Mandatory terminal proofs

### L02
Resolved organization binding, exact conservative grouping, review ambiguity, reversal/split, replay and concurrent arrival.

### L03
Real provider verification, typed auth/scope/outage errors, policy before network, secret redaction.

### L04
Full transition matrix; rotation/profile-change invalidation; expiry/revoke; revision binding; races.

### L05
Missing membership deny; onboarding revoke/expiry deny; adapter/schedule reverse completeness; final pre-network recheck; no network after deny.

### L06
Same-record causal predecessor; invalid/forked mutation rejection; manifest executable tests; ATS correction/tombstone only after complete traversal; concurrent lineage safety.

### L07
Lease/crash takeover; partial cursor persistence; retry backoff/circuit; pause/disable/revoke race; no duplicate progress.

### L08
Population-vs-delta tests including stable 1000/1-change, real collapse, partial traversal, not-modified and schema/field drift.

### L09
Real historical commercial/identity output accounting, replay/partial retry idempotency and correct ablation summaries.

### L10
All migration, PostgreSQL, architecture, backend, frontend-if-touched, security, regression, review and exact-head CI gates on one SHA.

## 7. Closeout rule

Do not create `docs/lots/LOTS_06_10_FINALITY_RECOVERY_CLOSEOUT.md` before L10 has one exact implementation SHA proving all R02-local findings. Issue #175 remains open until then.
