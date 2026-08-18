# Lots 11–15 — implementation finality recovery

Status: **AUDIT_SIGNED_OFF_IMPLEMENTATION_PENDING**  
Recovery: **R03**  
Audit date: **2026-08-18**  
Audited baseline: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`  
Tracking issue: **#177**  
Draft PR: **#178**

> This document signs off the **audit scope**, not runtime implementation. The sign-off is a reviewer attestation recorded in repository documentation; it is **not a cryptographic Git commit signature** and must not be represented as one.

## 1. Purpose

Historical Lots 11–15 were previously reported `IMPLEMENTED_VALIDATED`. R03 reopens their original issues, PRs, validation reports and current runtime to test a stronger question: whether the promised product behavior is complete under ordinary execution, corrections, sparse updates, concurrent writes, replay/backfill, source disagreement, time passage and cross-source identity.

The audit covers:

- Lot 11 — procurement history and contract timing (#31 / PR #33);
- Lot 12 — corporate public footprint (#34 / PR #35);
- Lot 13 — vulnerability knowledge (#36 / PR #37);
- Lot 14 — incident intelligence (#38 / PR #39);
- Lot 15 — threat telemetry (#40 / PR #41).

Historical validation remains useful evidence. It is not terminal proof when the original tests encoded an incomplete semantic contract or did not exercise the adversarial case now identified.

## 2. Final finding register

| ID | Lot | Severity | Recovery owner | Required correction |
|---|---:|---|---|---|
| R03-F01 | 11 | HIGH | R03-L02 | causal procurement revision/head ordering |
| R03-F02 | 11 | **CRITICAL** | R03-L02 | sparse amendment → effective-state merge, not null overwrite |
| R03-F03 | 11 | HIGH | R03-L03 | reversible cross-source procurement identity |
| R03-F04 | 11↔08 | HIGH | R03-L03 | buyer source-party → Lot08 canonical organization binding |
| R03-F05 | 12 | HIGH | R03-L04 | current claim-set reconciliation / withdrawal |
| R03-F06 | 12 | HIGH | R03-L04 | one protected causal current resource head |
| R03-F07 | 13 | HIGH | R03-L05 | alias-bridge convergence with provenance and reversible identity decisions |
| R03-F08 | 13 | HIGH | R03-L05 | namespace/source-authoritative lifecycle reconciliation |
| R03-F16 | 13 | HIGH | R03-L05 | preserve every current provider-record head after canonical convergence |
| R03-F09 | 14 | HIGH | R03-L06 | official-confirmation claim/source authority matrix |
| R03-F10 | 14 | HIGH | R03-L06 | causal cross-record-key correction/retraction lineage |
| R03-F11 | 14 | HIGH | R03-L07 | reversible cross-source incident identity resolution |
| R03-F12 | 14 | HIGH | R03-L06 | authority-aware incident-type conflict resolution |
| R03-F13 | 15 | HIGH | R03-L08 | causal cross-record-key IOC supersession |
| R03-F14 | 15 | HIGH | R03-L08 | clock-correct IOC expiry and reactivation |
| R03-F15 | 15 | HIGH | R03-L09 | canonical Campaign/Malware analyst model and chronology |

**Final audited local residual count: 16.**

There is no known ownerless residual in the audited local Lots 11–15 scope after the final adversarial pass. That statement is an audit conclusion only; implementation remains pending.

## 3. Highest-risk defects

### Lot 11 — sparse amendments can destroy valid current state

`DecpContract.duration_months()` and `amount_value()` select modification fields whenever `is_modification()` is true. When an amendment omits those fields, they become `None`. `map_decp_contract()` materializes a complete contract projection and `_upsert_contract()` writes every value returned by `_contract_values()`. A title-only or party-only amendment can therefore clear amount, duration-derived end date and renewal date that remain valid in source semantics.

The correction must model amendment omission separately from explicit clearing and materialize an effective contract state from the prior causal head plus the amendment delta.

### Lot 12 — immutable versions exist, but “current truth” is not explicit

A changed resource can create immutable versions and tombstones, but `persist_public_footprint_projections()` only upserts claims that are present. Claims missing from the new head are not retired. Queries then search/count claim rows across the resource history. Separately, a version may have no predecessor and the read path derives latest by timestamps/write order.

The correction must separate immutable history from a protected current resource head and reconcile the desired current claim set against that head.

### Lot 13 — canonical identity and lifecycle lose provider-record semantics

An exact alias bridge that touches two existing canonical rows raises rather than creating a controlled merge/review decision. Canonical status uses a source-agnostic severity priority, so advisory withdrawal can globally withdraw a CVE it does not authoritatively own. The final audit also found R03-F16: `latest_vulnerability_snapshots()` keeps only one current row per `source`, even though GitHub/OSV can have several distinct still-current provider record keys that resolve to the same CVE.

The correction must retain alias assertions and current source-record heads with source+record provenance, then reconcile identity and lifecycle through explicit authority rules.

### Lot 14 — incident semantics are locally safe but incomplete

Claim type alone can qualify a claim as official; `supersedes_record_key` is not used by reconciliation; provider `incident_key` is treated as canonical grouping; and canonical type is selected by a fixed severity priority. These mechanisms preserve history but can misstate present truth or prevent real corroboration.

### Lot 15 — IOC history exists, but time and campaign intelligence are incomplete

IOC supersession is reduced by `(source_id, source_record_key)` rather than causal predecessor lineage. `expires_at` is not evaluated by reconciliation or queries, so passage of time alone cannot make an active IOC expire. Campaign and malware relations exist only as typed relation labels to opaque `target_key` strings; there is no complete canonical Campaign/Malware analyst bounded context or protected campaign search/detail/timeline API.

## 4. Mandatory recovery order

```text
R03-L01
 -> R03-L02
 -> R03-L03
 -> R03-L04
 -> R03-L05
 -> R03-L06
 -> R03-L07
 -> R03-L08
 -> R03-L09
 -> R03-L10
```

These are recovery micro-lots, not new normal-product lot numbers.

- **L01** machine-enforces the finding/owner/no-orphan registry.
- **L02** fixes procurement revision chronology and sparse amendment semantics.
- **L03** fixes procurement identity and Lot08 buyer binding.
- **L04** fixes public-footprint causal heads and desired current claim sets.
- **L05** fixes vulnerability alias identity, lifecycle authority and provider-record current-set cardinality.
- **L06** fixes incident authority, causal claim supersession and type conflict semantics.
- **L07** fixes cross-source incident identity.
- **L08** fixes IOC supersession and clock expiry/reactivation.
- **L09** completes Campaign/Malware canonical analyst capability.
- **L10** performs a new adversarial runtime audit and exact-head qualification; it may add findings instead of forcing closure.

## 5. Preserved later ownership

R03 must not duplicate existing owners:

- Lot19/#52 — evidence-backed incumbent/renewal relationship context;
- Lot20/#54 — platform-wide corporate/entity graph identity and graph merge/split;
- Lot28/#171 — cross-module derived-state propagation, invalidation, time/replay/backfill convergence and publication readiness;
- Lot29/#6 — release/supply-chain/repository hardening;
- Lot30/#169 — DNS/address safety and resilience;
- Lot31/#5 — privacy rights, deletion propagation and non-resurrection;
- SA21/#158 — provider/source activation finality.

R03 owns the **local canonical truth** defects above. Lot28 consumes resulting canonical changes downstream; R03 must not create a competing global event bus or reconciliation engine.

## 6. Locked non-findings

Do not reopen without new code evidence:

- search/archive metadata remains discovery evidence routed to governed retrieval or source review; it is not directly promoted into confirmed public-footprint claims;
- source activation omissions already assigned to SA21 are not local Lots11–15 model defects;
- Lot11 incumbent/renewal relationship inference has explicit Lot19 ownership;
- Lot15 relation rows do retain their source snapshot provenance; F15 concerns missing canonical Campaign/Malware concepts, identity and analyst chronology, not total loss of relation provenance.

## 7. Documentation set

- `LOTS_11_15_IMPLEMENTATION_FINALITY_RECOVERY.md` — scope and final register;
- `LOTS_11_15_IMPLEMENTATION_GAP_AUDIT.md` — deep gap analysis;
- `LOTS_11_15_FINALITY_RECOVERY_MICROLOTS.md` — locked correction sequence;
- `LOTS_11_15_RECOVERY_CODE_SURFACE_AND_TEST_MAP.md` — implementation navigation;
- `lots_11_15_recovery_findings.yml` — machine-readable ownership registry;
- `LOTS_11_15_FINAL_AUDIT_AND_OWNERSHIP_LOCK.md` — ownership/finality lock;
- `LOTS_11_15_AUDIT_EVIDENCE_AND_CORRECTION_MATRIX.md` — per-finding evidence and exact corrective contract;
- `LOTS_11_15_AUDIT_SIGNOFF.md` — audit attestation.

## 8. Runtime-finality rule

The audit is signed off. **The runtime is not.**

Do not create `docs/lots/LOTS_11_15_FINALITY_RECOVERY_CLOSEOUT.md` until R03-L10 has one exact implementation SHA proving all local findings with reversible migrations, PostgreSQL concurrency tests, replay/order tests, time-only transition tests, truth-boundary tests, affected frontend gates, security/typing/full regression, zero unresolved review threads and exact-head CI green.
