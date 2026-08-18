# Lots 11–15 — implementation finality recovery

Status: **DEEP_AUDIT_COMPLETE_IMPLEMENTATION_PENDING**  
Recovery overlay: **R03**  
Tracking issue: **#177**  
Audited baseline: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`

## Purpose

Historical Lots 11–15 were closed after local validation, but the current product is held to a stronger implementation-finality standard: the original contract must still be true in ordinary runtime paths, under replay, corrections, sparse updates, concurrency, independent sources, time-only transitions and analyst queries.

This recovery does not erase the historical implementations. It isolates residual capabilities that were implemented too narrowly, whose integration stops too early, or whose truth boundary is weaker than the historical specification.

## Historical scope

| Lot | Historical issue | Historical PR | Capability |
|---|---:|---:|---|
| 11 | #31 | #33 | procurement contract history |
| 12 | #34 | #35 | corporate public footprint |
| 13 | #36 | #37 | vulnerability knowledge |
| 14 | #38 | #39 | incident intelligence |
| 15 | #40 | #41 | threat telemetry |

## Final deep-audit register

| Finding | Lot | Severity | Owner | Capability |
|---|---:|---|---|---|
| R03-F01 | 11 | HIGH | R03-L02 | procurement causal revision ordering |
| R03-F02 | 11 | CRITICAL | R03-L02 | sparse amendment effective-state merge |
| R03-F03 | 11 | HIGH | R03-L03 | cross-source procurement identity convergence |
| R03-F04 | 11 | HIGH | R03-L03 | Lot08-safe buyer organization binding |
| R03-F05 | 12 | HIGH | R03-L04 | public-footprint claim currentness/withdrawal |
| R03-F06 | 12 | HIGH | R03-L04 | resource-version causal head integrity |
| R03-F07 | 13 | HIGH | R03-L05 | vulnerability alias bridge convergence/provenance |
| R03-F08 | 13 | HIGH | R03-L05 | vulnerability lifecycle source authority |
| R03-F09 | 14 | HIGH | R03-L06 | official-confirmation authority binding |
| R03-F10 | 14 | HIGH | R03-L06 | incident claim cross-key supersession |
| R03-F11 | 14 | HIGH | R03-L07 | cross-source incident identity resolution |
| R03-F12 | 14 | HIGH | R03-L06 | authority-aware incident type conflicts |
| R03-F13 | 15 | HIGH | R03-L08 | indicator cross-key supersession |
| R03-F14 | 15 | HIGH | R03-L08 | clock-driven indicator expiry/reactivation |
| R03-F15 | 15 | HIGH | R03-L09 | canonical campaign/malware analyst capability |

## Architectural decisions

### Procurement revisions are state transitions, not content-hash elections

A hash may prove content identity; it cannot define chronology. Source revision sequence, provider modification identifiers, explicit predecessor relationships and bounded conflict/review state must determine the current effective revision. Same-time revisions cannot silently pick a winner based on lexical hash order or process order.

### Sparse amendment means patch unless the source explicitly declares a full replacement

DECP amendment fields such as modified amount/duration are optional. An omitted modified field cannot clear a still-valid prior value. R03-L02 must either model amendment deltas directly or materialize a complete effective contract state by applying the delta to the prior causal head. Explicit clearing requires an explicit provider semantic, not absence.

### Procurement identity is separate from source identity

DECP, BOAMP and TED native identifiers remain immutable provenance. A separate local procurement identity decision may converge exact shared official references. Ambiguous similarity remains review-required and reversible. Lot28 cannot repair three already-separate procurement aggregates after the fact.

### Lot08 remains the organization identity authority

Procurement mappers must not create source-local buyer UUIDs and thereby make those organizations canonical by persistence side effect. Exact official IDs bind to the Lot08 canonical organization; name-only buyer identity remains unresolved/reviewed until enough evidence exists.

### Public-footprint history needs an explicit head and an explicit current claim set

Immutable versions and claims remain historical evidence. Current analyst truth is the desired claim set supported by the current causal resource head. A claim missing from a later complete version, or from a tombstoned resource, is historical/withdrawn rather than silently current forever.

### Vulnerability identity/lifecycle is authority-aware

An exact alias bridge can be valid even if two aggregates were created before the bridge became known; this requires a durable merge/review/reversal decision, not ingestion failure. Likewise an advisory ecosystem source may withdraw its advisory without globally withdrawing an authoritative CVE record it does not own.

### Incident confirmation and incident type are source assertions

Claim type alone is insufficient to establish official confirmation. Company/regulator/CERT confirmation must be compatible with source authority. Incident type also cannot be selected by “most severe assertion wins”; weak allegations remain visible without upgrading the authoritative analyst summary.

### Supersession is causal across record keys

Both incident and threat-indicator models carry `supersedes_record_key`; storing it without applying it is not terminal implementation. Cross-key correction/retraction must advance one source-local causal lineage, reject stale/fork/cycle conflicts and converge under replay.

### Time expiry is truth

An indicator with expired source evidence cannot remain active merely because no new provider batch arrived. Local threat telemetry owns clock-aware currentness; Lot28 only owns downstream reaction to the resulting canonical change.

### Lot15 must actually model the campaign/malware side of its exit gate

Opaque `target_key` strings are acceptable source-native evidence but not a finished canonical analyst model. The target product must expose typed campaign/malware/threat entities, temporal/provenanced relations and searchable chronology without turning a relation hint into an unproven identity assertion.

## Preserved later ownership

- **Lot19/#52** — relationship inference plus evidence-backed incumbent/renewal context.
- **Lot20/#54** — platform-wide corporate/entity graph merge/split and temporal graph identity.
- **Lot28/#171** — downstream dependency routing, invalidation, time-driven derived-state sweeps and replay/backfill/current-state convergence.
- **Lot29/#6** — supply-chain/release/repository hardening.
- **Lot30/#169** — DNS/address safety and resilience.
- **Lot31/#5** — privacy deletion/non-resurrection.
- **SA21/#158** — source/provider activation finality.

R03 must not construct a second global event/reconciliation architecture or relabel activation debt as a bounded-context defect.

## Locked implementation sequence

```text
R03-L01 ownership/no-orphan guard
  -> R03-L02 procurement revision + sparse amendment finality
  -> R03-L03 procurement + buyer identity finality
  -> R03-L04 public-footprint causal/currentness finality
  -> R03-L05 vulnerability identity/lifecycle authority
  -> R03-L06 incident claim authority/supersession/type
  -> R03-L07 cross-source incident identity
  -> R03-L08 indicator supersession/expiry
  -> R03-L09 campaign/malware threat-entity completion
  -> R03-L10 adversarial exact-head qualification and closeout
```

## Non-findings / explicit handoffs

- Public search/archive discovery is not treated as confirmed footprint evidence: candidates are routed to governed retrieval or source review.
- Missing live provider activation belongs to SA21 where already tracked; it is not evidence that the bounded-context model itself is broken.
- Lot11 incumbent/renewal inference has an explicit Lot19 owner and is not an orphan R03 residual.
- Lot15 relation provenance is not entirely absent: relation rows belong to source snapshots. F15 concerns the missing canonical campaign/malware analyst model and resolution semantics, not a claim that source provenance is totally lost.
- Lot28 remains the owner of downstream propagation after local canonical truth changes.

## Terminal rule

Historical validation is not enough to close R03. Closeout requires one exact runtime SHA proving all local findings, reversible migrations, PostgreSQL concurrency/replay/order tests, time-only transitions, safe authority boundaries, full regression/security/typing/architecture gates, zero unresolved review threads and exact-head CI green.

Do not create `docs/lots/LOTS_11_15_FINALITY_RECOVERY_CLOSEOUT.md` before R03-L10 proves that state.
