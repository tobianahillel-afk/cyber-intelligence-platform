# Lots 11–15 — audit evidence and correction matrix

Status: **AUDIT_SIGNED_OFF_IMPLEMENTATION_PENDING**  
Recovery: **R03**  
Baseline: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`

This matrix is the executable bridge from audit to implementation. Paths/functions are the current evidence surface; “target correction” is the required semantic outcome, not a mandate to preserve current file boundaries.

| Finding | Current evidence surface | What is wrong | Target correction | Data / migration | Terminal test proof | Owner |
|---|---|---|---|---|---|---|
| F01 | `procurement_history/infrastructure/projections.py::_publication_is_newer` | equal-time head chosen by `revision_key` | source-causal predecessor/sequence or explicit unresolved conflict; atomic head | likely lineage/head metadata | equal-time inverse hashes, replay, stale backfill, race | L02 |
| F02 | `decp/schemas.py::{duration_months,amount_value}`; `decp/mapper.py`; `_contract_values` | sparse amendment missing fields become `None` and overwrite effective state | typed amendment delta + predecessor merge + explicit-clear semantics + field provenance | lineage/delta/provenance and deterministic rebuild | sparse amendment matrix, clear vs omit, chain replay | L02 |
| F03 | DECP/BOAMP/TED source-prefixed procedure/contract keys | same official procurement can remain multiple canonicals | native-ID assertions + reversible canonical procurement identity decision | identity decision/group tables | source-pair duplicates vs near-duplicates; split/reject/race | L03 |
| F04 | procurement mappers construct buyer `Organization` with source-local UUID | mapper-local buyer may bypass Lot08 identity authority | source-party evidence + Lot08 exact/reviewed binding port | binding/audit records | exact SIREN/SIRET, name-only, conflicts, reversal | L03 |
| F05 | `public_footprint/.../projections.py::_upsert_claim`; queries `_claim_exists` | omitted/tombstoned claim remains current/searchable | desired current claim-set reconciliation tied to causal head | claim support/currentness metadata | removal, tombstone, reappearance, current/history filters | L04 |
| F06 | `_validated_predecessor` accepts none; queries sort by fetched/created | no unique causal current resource head | protected head + predecessor-required incremental advance + stale/fork outcome | current-head/lineage | two writers, same time, stale branch, late backfill | L04 |
| F07 | vulnerability `_resolve_vulnerability` raises on >1 record; aliases canonical-global | exact alias bridge cannot safely merge; source alias provenance blurred | source alias assertions + reversible identity decisions/merge/split | alias assertion + identity decision tables | bridge after duplicate, concurrent bridge, split/reject | L05 |
| F08 | vulnerability `_STATUS_PRIORITY`; OSV/GHSA map withdrawal | advisory lifecycle can globally override CVE authority | namespace/source authority policy + visible lifecycle conflicts | policy/decision metadata as needed | CVE active + OSV/GHSA withdrawn; authoritative reject | L05 |
| **F16** | `projection_hydration.py::latest_vulnerability_snapshots` keyed only by `source` | only newest provider row survives after several provider records converge to one CVE | one current head per source **record**; reconcile all sibling heads | source-record lineage/head | two GHSA/OSV siblings, withdraw one, replay/race/same-time | L05 |
| F09 | incident model `is_official_confirmation` claim-type only | incompatible source can become official if mislabeled | claim-type↔source-kind authority matrix and confirmed-at validation | usually model/policy; audit reason if quarantined | media/provider mislabeled official; valid company/reg/CERT | L06 |
| F10 | incident `_latest_claim_revisions` keyed `(source_id,source_record_key)`; ignores `supersedes_record_key` | cross-key correction/retraction leaves predecessor current | source-local claim lineage/head with cross-key predecessor | lineage/head metadata | A→B, cycle/fork/stale/cross-source/race | L06 |
| F11 | incident reconciler groups by provider `incident_key`; mappers pass through | different native IDs cannot reliably corroborate same incident | reversible canonical incident identity group/decision | identity assertion/decision tables | same event different IDs; same victim distinct events; split | L07 |
| F12 | incident `_TYPE_PRIORITY` max | weak severe allegation can overstate canonical type | source type assertions + authority/confidence/review primary decision | type-decision metadata if materialized | ransomware allegation vs official unauthorized access | L06 |
| F13 | IOC `latest_indicator_snapshots` keyed `(source_id,source_record_key)` | cross-key IOC supersession ignored | source-local indicator lineage/head | lineage/head metadata | A→B correction/retraction, cycle/fork/race/replay | L08 |
| F14 | IOC reconciler ignores `expires_at`; queries have no `now` | active IOC can remain active after TTL | clock-aware effective assertions + local time transition integration | optional next-expiry/current metadata | no-write time passage, exact boundary, multi-source TTL, reactivate | L08 |
| F15 | `TelemetryRelation(target_key)`; API only `/v1/threat-indicators` | campaign/malware are opaque relation targets, not complete analyst concepts | canonical Campaign/Malware entities, identity/history, typed temporal relations, protected search/detail/timeline | new entity/assertion/relation tables | aliases/review/split, relation expiry/retraction, API auth/timeline | L09 |

## Required migration principles

For every R03 migration:

1. **No fabricated provenance.** Legacy data that cannot be mapped to an exact source assertion must be marked legacy/unknown, not guessed.
2. **History remains immutable.** Migrations may add lineage/currentness/decision layers; they must not rewrite raw/source evidence to make the new model look cleaner.
3. **Deterministic backfill.** Rebuilding effective state or heads must be repeatable from the same source history.
4. **Ambiguity is explicit.** If historic rows cannot establish a unique causal head/identity, store review/conflict state rather than choose by UUID/hash/insertion time.
5. **Reversible schema.** `upgrade -> downgrade -> upgrade` must pass on PostgreSQL.

## Required concurrency principles

- current-head uniqueness enforced at database/application boundary;
- stale compare-and-swap/predecessor rejected visibly;
- no lost update through read-then-write without lock/version guard;
- identity merge/split decisions are serializable/idempotent;
- replaying the same immutable source record does not duplicate decisions or heads;
- late historical/backfill writes never steal present currentness.

## Required source-truth principles

- source-native identifier is provenance, not automatically canonical identity;
- hash/digest is identity/dedup evidence, not chronology;
- omission is not explicit clearing;
- advisory withdrawal is not automatically CVE withdrawal;
- claim label is not authority;
- more severe allegation is not more authoritative fact;
- IOC expiration is truth at the time boundary;
- opaque campaign/malware strings remain unresolved evidence until identity is established.

## Required L10 regression matrix

L10 must prove one exact SHA across:

- architecture/no-orphan registry;
- migration up/down/up;
- PostgreSQL race tests;
- shuffled replay + late backfill;
- current vs immutable-history read models;
- source authority/identity conflicts;
- no-write time passage;
- control-plane authentication on new/changed endpoints;
- frontend type/build/security gates when touched;
- full backend regression and coverage;
- zero unresolved review threads;
- exact-head CI green.
