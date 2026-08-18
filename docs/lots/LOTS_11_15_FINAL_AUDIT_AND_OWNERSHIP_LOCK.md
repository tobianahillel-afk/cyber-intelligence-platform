# Lots 11–15 final audit and ownership lock

Status: **DEEP_AUDIT_COMPLETE_IMPLEMENTATION_PENDING**  
Recovery: **R03**  
Tracking issue: **#177**  
Audited baseline: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`

This document and `lots_11_15_recovery_findings.yml` are the authoritative pre-implementation ownership lock for R03. They are not a runtime closeout.

## 1. Recovery-local findings

| ID | Lot | Severity | Owner | Locked correction |
|---|---:|---|---|---|
| F01 | 11 | HIGH | L02 | causal procurement revision ordering |
| F02 | 11 | CRITICAL | L02 | sparse amendment effective-state merge |
| F03 | 11 | HIGH | L03 | cross-source procurement identity |
| F04 | 11↔08 | HIGH | L03 | canonical buyer organization binding |
| F05 | 12 | HIGH | L04 | claim currentness/withdrawal |
| F06 | 12 | HIGH | L04 | single causal resource head |
| F07 | 13 | HIGH | L05 | alias bridge convergence + provenance |
| F08 | 13 | HIGH | L05 | lifecycle source authority |
| F09 | 14 | HIGH | L06 | official confirmation authority matrix |
| F10 | 14 | HIGH | L06 | cross-key claim supersession |
| F11 | 14 | HIGH | L07 | cross-source incident identity |
| F12 | 14 | HIGH | L06 | authority-aware incident typing |
| F13 | 15 | HIGH | L08 | cross-key indicator supersession |
| F14 | 15 | HIGH | L08 | clock expiry/reactivation |
| F15 | 15 | HIGH | L09 | campaign/malware canonical analyst model |

There is no known ownerless residual in the audited local Lots11–15 scope after this deep pass.

## 2. Existing later ownership preserved

| Capability | Owner |
|---|---|
| procurement incumbent/renewal relationship context | Lot19/#52 |
| global corporate/entity graph identity | Lot20/#54 |
| downstream derived-state routing/invalidation/replay convergence | Lot28/#171 |
| release/supply-chain/repository hardening | Lot29/#6 |
| DNS/address safety and broad resilience | Lot30/#169 |
| privacy deletion/non-resurrection | Lot31/#5 |
| provider/source live activation | SA21/#158 |

R03 may expose better local canonical change truth to Lot28; it must not implement a competing global outbox/reconciliation engine.

## 3. Why the findings are not duplicates

### F01 vs F02

F01 is chronology/head selection. F02 is sparse amendment field semantics. A perfect causal head can still contain data loss if patch fields are interpreted as a complete snapshot; a perfect patch merger can still choose the wrong head.

### F03 vs F04

F03 resolves the procurement object across sources. F04 resolves the buyer organization through Lot08. A single procurement can still point to duplicate buyer organizations, and one buyer can participate in distinct procurements.

### F05 vs F06

F06 identifies the current resource version. F05 identifies which claims that version currently supports. A single correct head does not automatically withdraw omitted claim rows unless claim currentness is reconciled.

### F07 vs F08

F07 is vulnerability identity/alias authority. F08 is lifecycle status authority after identity is known.

### F09/F10/F12 vs F11

F09/F10/F12 make claim semantics truthful inside one canonical incident. F11 determines whether independent native incident identifiers belong to the same canonical incident at all.

### F13/F14 vs F15

F13/F14 complete indicator current-state semantics. F15 completes the historical campaign/malware analyst capability and typed threat relationships.

## 4. Mandatory terminal proofs

### L02

- sparse DECP amendment retains unmodified values;
- explicit clear is distinguished from omission;
- equal-time revisions use causal semantics;
- shuffled replay and two-writer races converge;
- old backfill does not steal current head.

### L03

- exact cross-source duplicate procurement converges;
- false similar procurement does not;
- review/reject/split is durable and reversible;
- exact buyer official ID binds Lot08 organization;
- name-only buyer does not silently canonicalize.

### L04

- one resource head under race/replay;
- removed claim becomes historical/withdrawn;
- tombstone withdraws current claim set;
- current vs historical query semantics are explicit.

### L05

- authoritative alias bridge can reconcile previous duplicates;
- alias assertion source provenance remains visible;
- OSV/advisory withdrawal cannot globally withdraw authoritative CVE;
- authoritative reject/supersede behaves correctly;
- identity and lifecycle conflicts are reviewable/reversible.

### L06

- claim-type/source-kind authority matrix enforced;
- cross-key correction/retraction works;
- cycles/forks/stale mutation rejected;
- weak severe allegation cannot upgrade official incident type.

### L07

- independent sources with different native IDs can safely corroborate the same incident;
- ambiguous same-victim events remain separate unless reviewed;
- split/reject/replay/concurrency are proven;
- source independence remains measurable.

### L08

- cross-key indicator supersession works;
- expiry changes currentness without new ingestion;
- independent TTLs compose correctly;
- fresh evidence reactivates;
- analyst filters are clock-correct.

### L09

- campaign/malware entities exist as canonical searchable analyst concepts;
- source-native aliases/targets remain provenance;
- typed temporal relations preserve source/confidence/validity;
- ambiguity/review/split/retraction/expiry/replay are covered;
- campaign analyst search/detail/timeline exit gate is real.

### L10

All migrations, PostgreSQL races, replay/order/time tests, architecture, security, backend/full regression, frontend gates when touched, review-thread audit and exact-head CI must pass on one SHA.

## 5. Deep-audit non-findings

Do not reopen without new code evidence:

- public search/archive results are discovery leads routed to governed retrieval or review, not automatically confirmed footprint claims;
- source activation omissions already tracked by SA21 are not local model defects;
- procurement incumbent/renewal inference has explicit Lot19 ownership;
- Lot15 relation rows do retain snapshot/source provenance, so F15 is not a claim that relation provenance is completely absent;
- Lot28 remains the correct owner for downstream propagation once local truth changes.

## 6. One-owner map

```text
L01: registry/no-orphan process
L02: F01 F02
L03: F03 F04
L04: F05 F06
L05: F07 F08
L06: F09 F10 F12
L07: F11
L08: F13 F14
L09: F15
L10: terminal qualification only
```

## 7. Closeout rule

Do not create `docs/lots/LOTS_11_15_FINALITY_RECOVERY_CLOSEOUT.md` before R03-L10 has one exact implementation SHA proving every R03-local finding. Issue #177 remains open until then.
