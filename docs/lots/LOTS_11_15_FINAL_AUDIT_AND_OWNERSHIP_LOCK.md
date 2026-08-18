# Lots 11–15 — final audit and ownership lock

Status: **AUDIT_SIGNED_OFF_IMPLEMENTATION_PENDING**  
Recovery: **R03**  
Audit date: **2026-08-18**  
Baseline: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`  
Tracking issue: **#177**  
Draft PR: **#178**

This document and `lots_11_15_recovery_findings.yml` are the authoritative pre-implementation ownership lock. The sign-off is an audit/reviewer attestation, **not a cryptographic Git signature and not a runtime closeout**.

## 1. Final recovery-local register

| ID | Lot | Severity | Owner | Locked correction |
|---|---:|---|---|---|
| F01 | 11 | HIGH | L02 | causal procurement revision ordering |
| F02 | 11 | **CRITICAL** | L02 | sparse amendment effective-state merge |
| F03 | 11 | HIGH | L03 | cross-source procurement identity |
| F04 | 11↔08 | HIGH | L03 | Lot08-safe buyer organization binding |
| F05 | 12 | HIGH | L04 | current claim withdrawal/reconciliation |
| F06 | 12 | HIGH | L04 | one causal public-resource head |
| F07 | 13 | HIGH | L05 | alias bridge convergence + source assertion provenance |
| F08 | 13 | HIGH | L05 | lifecycle source/namespace authority |
| **F16** | 13 | HIGH | L05 | current head per provider record, not one snapshot per provider |
| F09 | 14 | HIGH | L06 | official confirmation authority matrix |
| F10 | 14 | HIGH | L06 | cross-key claim supersession |
| F11 | 14 | HIGH | L07 | reversible cross-source incident identity |
| F12 | 14 | HIGH | L06 | authority-aware incident typing |
| F13 | 15 | HIGH | L08 | cross-key IOC supersession |
| F14 | 15 | HIGH | L08 | clock expiry/reactivation |
| F15 | 15 | HIGH | L09 | canonical Campaign/Malware analyst model |

**Final count: 16 findings.**

There is no known ownerless local residual in audited Lots11–15 after the final adversarial pass. If implementation reveals another defect, L10 must add F17+ rather than force closure.

## 2. Why F16 is separate

F07 answers **which canonical vulnerability** a source record belongs to. F08 answers **which lifecycle assertion has authority**. F16 answers **how many distinct current source records from one provider continue contributing after grouping**.

A perfect F07 merge can still lose facts if hydration keeps only one GitHub/OSV record per provider. A perfect lifecycle policy cannot restore scores/ranges/references from a sibling provider record that was dropped before reconciliation. Therefore F16 has its own invariant and proof, while sharing L05 because the persistence/reconciliation surfaces are tightly coupled.

## 3. Existing later ownership preserved

| Capability | Owner |
|---|---|
| procurement incumbent/renewal relationship context | Lot19/#52 |
| global corporate/entity graph identity | Lot20/#54 |
| downstream derived-state routing/invalidation/time/replay convergence | Lot28/#171 |
| release/supply-chain/repository hardening | Lot29/#6 |
| DNS/address safety and resilience | Lot30/#169 |
| privacy deletion/non-resurrection | Lot31/#5 |
| provider/source activation | SA21/#158 |

R03 may expose more truthful local canonical change events to Lot28. R03 must not implement a competing global outbox, scheduler or reconciliation architecture.

## 4. One-owner map

```text
L01: registry / no-orphan process
L02: F01 F02
L03: F03 F04
L04: F05 F06
L05: F07 F08 F16
L06: F09 F10 F12
L07: F11
L08: F13 F14
L09: F15
L10: terminal qualification only
```

## 5. Mandatory terminal proofs by micro-lot

### L02

- equal-time revisions do not use hash/write chronology;
- sparse amendments preserve omitted facts;
- explicit clear differs from omission;
- shuffled replay/backfill/concurrent heads converge.

### L03

- cross-source exact duplicate procurement converges;
- near-duplicate remains separate;
- merge/reject/split/review is durable/reversible;
- exact buyer ID binds Lot08; name-only does not silently canonicalize.

### L04

- one resource current head under race/replay;
- claim removal/tombstone withdraws current support;
- old evidence remains historical;
- current filters/counts cannot match withdrawn-only claims.

### L05

- exact alias bridge may safely converge prior duplicates;
- source-level alias provenance remains visible;
- advisory withdrawal cannot globally withdraw authoritative CVE;
- authoritative reject/supersede behaves correctly;
- **two distinct current GHSA/OSV records resolving to one CVE both remain in current reconciliation**;
- changing/withdrawing one provider record does not erase its sibling;
- replay/concurrency/same-time provider-record heads converge.

### L06

- claim type + source kind authority enforced;
- true cross-key correction/retraction works;
- cycles/forks/stale mutation rejected;
- weak severe allegation cannot upgrade authoritative incident type.

### L07

- different native IDs can safely corroborate the same event;
- same-victim separate incidents remain separate absent explicit identity evidence/review;
- split/reject/replay/concurrency proven;
- source independence preserved.

### L08

- IOC cross-key supersession works;
- expiry changes truth with no new write;
- independent TTLs compose;
- fresh evidence reactivates;
- analyst filters are clock-correct.

### L09

- Campaign/Malware exist as searchable canonical analyst concepts;
- source-native aliases/targets remain provenance;
- typed temporal relations retain source/confidence/validity;
- ambiguity/review/split/retraction/expiry/replay covered;
- campaign search/detail/timeline exit gate is real.

### L10

All migrations, PostgreSQL races, shuffled replay, time-only tests, architecture, security, backend/full regression, frontend gates when touched, review-thread audit and exact-head CI pass on one implementation SHA.

## 6. Locked non-findings

Do not reopen without new evidence:

- search/archive result → governed retrieval/review boundary is already safe;
- provider activation is SA21 ownership;
- Lot11 incumbent/renewal context is Lot19 ownership;
- Lot15 relation rows do retain source snapshot provenance;
- Lot28 remains the single owner for downstream propagation/invalidation after local canonical truth changes.

## 7. Sign-off and closeout rule

The audit scope is signed off for implementation start. Runtime corrections remain unimplemented/unproven.

Do not create `docs/lots/LOTS_11_15_FINALITY_RECOVERY_CLOSEOUT.md` until R03-L10 proves every local finding on one exact implementation SHA. Issue #177 remains open until then.
