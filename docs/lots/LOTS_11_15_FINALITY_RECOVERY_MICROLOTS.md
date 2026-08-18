# Lots 11–15 finality recovery micro-lots

Status: **AUDIT_SIGNED_OFF_IMPLEMENTATION_PENDING**  
Recovery: **R03**  
Issue: **#177**  
Baseline: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`

## Mandatory order

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

These are recovery micro-lots, not competing normal product lot numbers. No micro-lot may move an unresolved defect into vague `later`/`future hardening` wording.

## R03-L01 — executable ownership/no-orphan guard

Owns no product finding.

Create `tests/architecture/test_lots_11_15_recovery_ownership.py` that reads `docs/lots/lots_11_15_recovery_findings.yml` and enforces:

- unique finding IDs;
- exactly one owner per `recovery_local` finding;
- every owner is a declared R03 micro-lot;
- every later-scope handoff has an exact tracker;
- no forbidden terminal placeholder;
- F07/F08/F16 are all owned by L05;
- no accidental duplicate ownership with Lot19/Lot20/Lot28/Lot29/Lot30/Lot31/SA21;
- no closeout document exists before L10 qualification.

**Exit:** registry becomes executable architecture truth.

## R03-L02 — procurement causal revisions and sparse amendments

Owns **F01, F02**.

### Implement

1. Add explicit procurement source-revision lineage:
   - source-native revision/notice/modification ID;
   - lineage key;
   - predecessor/current-head state;
   - optional source-native sequence/version;
   - conflict state/reason when equal-time revisions have no order.
2. Make current-head advance PostgreSQL-safe (row lock/CAS/unique-current constraint).
3. Replace `revision_key`/content-hash chronology fallback.
4. Model DECP amendments as typed deltas with `ABSENT`, `SET`, and source-supported `EXPLICIT_CLEAR` semantics.
5. Materialize a full effective contract state by applying a delta to the causal predecessor.
6. Preserve field-level provenance/basis and inherited-vs-modified state.
7. Cancellation/retraction changes current state without deleting immutable publication history.
8. Add deterministic data rebuild/backfill for existing histories.

### Migration

Likely new revision-lineage/current-head fields/table and amendment/field-provenance metadata. Migration must be reversible and include deterministic data backfill.

### Tests

- equal timestamp with opposite lexical hash ordering;
- shuffled replay;
- old backfill after current;
- title-only, amount-only, duration-only, titular-only amendment;
- explicit clear vs omission;
- cancellation/retraction;
- concurrent writers;
- migration upgrade/downgrade/upgrade.

**Exit:** no current procurement fact depends on write order/hash or sparse-null overwrite.

## R03-L03 — procurement identity and Lot08 buyer binding

Owns **F03, F04**.

### Implement

1. Persist source-native procurement identifiers/reference chains independent of canonical procurement ID.
2. Create durable `ProcurementIdentityDecision`/equivalent:
   - candidate canonical group;
   - exact evidence;
   - rule/version fingerprint;
   - `matched / rejected / review_required / split` states;
   - actor/reason/time audit where human review applies.
3. Auto-merge only strong exact official references; fuzzy/title/name similarity is candidate evidence only.
4. Preserve each DECP/BOAMP/TED source-local publication lineage after grouping.
5. Introduce procurement source-party evidence for buyers.
6. Resolve exact SIREN/SIRET/other governed official identifiers through Lot08 organization identity port.
7. Name-only/conflicting buyer identity remains unresolved/review-required.
8. Procurement canonical projection references a canonical organization only after binding.

### Tests

DECP↔BOAMP↔TED exact duplicates, false near-duplicates, reviewed match/reject/split, exact buyer IDs, same-name conflicts, replay and PostgreSQL concurrent arrivals.

**Exit:** procurement and buyer identity are explicit reversible decisions, not mapper-local UUID truth.

## R03-L04 — public-footprint causal resource head and desired current claim set

Owns **F05, F06**.

### Implement

1. One protected causal current head per resource.
2. Incremental changed/tombstone versions must point to the current predecessor; historical import has an explicit non-current mode.
3. Reject/record stale/fork attempts; same-time order is predecessor-driven.
4. Link claim assertions to supporting resource versions.
5. On head advance, compute desired current claims and reconcile:
   - retained;
   - superseded/changed;
   - withdrawn because no longer supported;
   - reappeared.
6. Tombstone current head withdraws its current claim set without deleting history.
7. Current list/search/filter/count uses only current supported claims; detail/history exposes immutable chronology.
8. Head/claim reconciliation is transactional.

### Migration

Likely resource-current-head and claim-currentness/support-version metadata. Backfill current heads from unambiguous lineages; ambiguous historic branches must be explicitly flagged rather than guessed.

### Tests

Removal, tombstone, reappearance, two concurrent versions, same fetched time, stale predecessor, older backfill, replay and current-vs-history query semantics.

## R03-L05 — vulnerability identity, lifecycle authority and provider-record head cardinality

Owns **F07, F08, F16**.

### Implement identity/provenance

1. Add source-level alias assertions bound to source snapshot/provider record.
2. Add durable canonical vulnerability identity decisions with merge/reject/split/review history and rule version.
3. Permit authoritative exact alias bridge to converge previously distinct canonicals without deleting source evidence.
4. Preserve former canonical IDs as aliases/history after merge.

### Implement lifecycle authority

5. Add identifier-namespace/source authority policy.
6. Preserve all lifecycle assertions and conflicts.
7. Advisory withdrawal/rejection remains advisory-local unless that source owns the relevant identifier lifecycle.
8. Validate `superseded_by`, prevent self/cycle/incompatible terminal transitions.

### Implement F16 current-set semantics

9. Replace one-`source` hydration with one current head per `(vulnerability_id, source, source_record_key)` or equivalent provider-record lineage key.
10. Reconcile **all** current provider-record heads for the canonical vulnerability.
11. Update/withdraw one GHSA/OSV record without suppressing sibling records from the same provider.
12. Add causal same-time/fork handling per provider record.

### Migration

Likely alias-assertion/identity-decision tables and provider-record lineage/current-head metadata. Existing canonical alias rows must be backfilled without fabricating their source provenance; where provenance cannot be reconstructed, mark it legacy/unknown rather than guessing.

### Tests

- alias bridge after duplicates and concurrent bridge;
- CVE active + OSV/GHSA withdrawn;
- authoritative CVE rejection/supersession;
- two distinct GHSAs sharing one CVE both contribute current data;
- two OSV records sharing one CVE;
- withdraw/update one sibling only;
- replay/same timestamp/concurrency;
- migration reversibility.

## R03-L06 — incident authority, causal supersession and type conflict semantics

Owns **F09, F10, F12**.

### Implement

1. Central claim-type↔source-kind authority matrix.
2. `confirmed_at` and official status require compatible source authority.
3. Persist source-local claim lineage with predecessor/head semantics and cross-key supersession.
4. Reject cycles, self-supersession, stale predecessor, cross-source/cross-incident predecessor and concurrent forks.
5. Preserve all incident-type assertions with source, confidence, confirmation status and history.
6. Replace fixed severity primary selection with authority/confidence/review policy.
7. Expose conflicts/alternative asserted types in read models.

### Tests

Media/provider mislabeled official, valid company/regulator/CERT combinations, A→B cross-key correction/retraction, cycle/fork/stale/race, ransomware allegation versus official unauthorized-access confirmation, replay.

## R03-L07 — reversible cross-source incident identity

Owns **F11**.

### Implement

1. Native provider incident IDs remain source evidence.
2. Add canonical incident identity assertion/decision/group persistence.
3. Deterministic exact shared event/reference IDs may bind automatically.
4. Organization + bounded event/time similarity can only propose/review, not silently merge.
5. Persist `merge / reject / split / review_required` history and rule version.
6. Reconciliation, corroboration, contradiction and independence operate over canonical group while retaining source independence.
7. Identity changes produce local canonical change events for Lot28 downstream; do not create a second global outbox.

### Tests

Same incident/different IDs, same victim/two incidents, reviewed merge/reject/split, correction-induced split, syndicated vs independent sources, replay and concurrency.

## R03-L08 — threat-indicator causal supersession and clock expiry

Owns **F13, F14**.

### Implement supersession

1. One source-local IOC record lineage keyed by provider record and canonical indicator identity.
2. Cross-key predecessor/head semantics.
3. Cycle/fork/stale/cross-identity/cross-source rejection.
4. Replay-safe same-time resolution by lineage, not insertion order.

### Implement time truth

5. Define `is_effective(as_of)`/equivalent for indicator assertions.
6. At `expires_at`, expired positive assertion stops contributing even without ingestion.
7. Multiple independent source expiries compose independently.
8. Fresh evidence may reactivate without rewriting historical snapshots.
9. API list/filter/count/detail current state is clock-correct.
10. Integrate local expiry transition with Lot28’s time-driven reconciliation mechanism; do not build a competing platform-wide scheduler.

### Tests

No-write time passage, exact boundary, independent TTLs, reactivation, cross-key correction/retraction, race between update and expiry, replay.

## R03-L09 — canonical Campaign/Malware threat entities and analyst chronology

Owns **F15**.

### Implement

1. Add canonical `Campaign` and `MalwareFamily` or rigorously equivalent threat-entity types.
2. Add immutable source assertions/snapshots, aliases, source timestamps, current/history state.
3. Add reversible identity decisions and review/split semantics; no name-only auto-merge.
4. Typed relation assertions:
   - indicator↔campaign;
   - indicator↔malware;
   - campaign↔malware;
   - campaign/malware↔vulnerability;
   - optional phishing-kit/infrastructure where supported.
5. Relation retains source snapshot/native target, confidence, valid-from/to, correction/retraction/expiry.
6. Add protected analyst campaign/malware list/search/detail/timeline API.
7. Add frontend views only if required to complete the existing threat-intelligence workspace contract; they must use protected server-side access and no client token exposure.
8. Map STIX/TAXII/provider objects conservatively.
9. Explicitly forbid IOC probing, active validation, malware download or binary execution.

### Tests

Cross-source aliases, ambiguous same-name campaigns, reviewed split/reject, relation expiry/retraction, campaign timeline, malware-vulnerability provenance, auth/search/detail, replay and migration reversal.

## R03-L10 — adversarial runtime qualification and closeout

Owns terminal qualification only.

Reopen original Lots11–15 issues/PRs/reports **again** against the implemented branch. Add `R03-F17+` if new residuals are proven; do not force closure.

One exact implementation SHA must pass:

- R03 ownership/no-orphan architecture guard;
- all affected unit/integration suites;
- PostgreSQL race/locking/fork tests;
- shuffled replay and late-backfill convergence;
- migration upgrade/downgrade/upgrade;
- time-only expiry tests without ingestion;
- truth/authority boundary tests;
- backend lint/type/full regression/coverage;
- frontend audit/type/test/build if touched;
- security/redaction/secret gates;
- zero unresolved review threads;
- exact-head CI green.

Only R03-L10 may create `docs/lots/LOTS_11_15_FINALITY_RECOVERY_CLOSEOUT.md`.
