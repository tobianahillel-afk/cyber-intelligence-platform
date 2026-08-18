# Lots 11–15 — ultra-deep implementation gap audit

Status: **AUDIT_SIGNED_OFF_IMPLEMENTATION_PENDING**  
Recovery: **R03**  
Baseline: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`  
Issue: **#177**  
PR: **#178**

This audit distinguishes historical test success from semantic finality. Every local finding below has one recovery owner, an exact correction contract and terminal proof. “Works in a happy-path test”, “deterministic”, “manual refresh exists”, “later”, or “future hardening” are not terminal dispositions.

## R03-F01 — procurement revision causal ordering

**Lot:** 11  
**Severity:** HIGH  
**Owner:** R03-L02

### Expected contract

The current contract/procedure head must follow source/provider causal revision semantics. Replay order, database insertion order and a content-derived hash must not choose business chronology.

### Current behavior / root cause

`procurement_history.infrastructure.projections._publication_is_newer()` compares effective timestamps and, when equal, falls back to `candidate.revision_key >= current.revision_key`. `revision_key` is an immutable identity/deduplication key, not a source sequence or predecessor proof.

### Failure scenario

Two genuine source revisions share the same published/effective timestamp. The newer business revision has a lexically smaller revision hash/key. The older record remains current even though both rows are stored immutably. Shuffled replay can therefore produce a current state selected by a non-causal property.

### Exact correction

- add explicit source-native revision sequence/version/notice identifier where available;
- persist predecessor/current-head relationship for a source-local procurement lineage;
- if the source provides no order and two changed revisions are equal-time, record an explicit conflict/review state rather than inventing chronology;
- historical/backfill rows may be inserted without stealing the current head;
- current-head advance must be atomic/race-safe in PostgreSQL.

### Required proof

Equal-time opposite lexical hashes, shuffled replay, stale backfill, duplicate replay and two concurrent head candidates all converge to the same justified outcome.

### Not acceptable

Replacing `revision_key` with another arbitrary hash/UUID or relying on insertion time.

---

## R03-F02 — sparse DECP amendments overwrite valid fields

**Lot:** 11  
**Severity:** CRITICAL  
**Owner:** R03-L02

### Expected contract

A sparse amendment modifies only fields actually amended. Omission means “unchanged” unless the source explicitly represents a clear/removal.

### Current behavior / root cause

For a modification, `DecpContract.duration_months()` reads only `dureemoismodification`; `amount_value()` reads only `montantmodification`. Missing values return `None`. `map_decp_contract()` builds a complete `ProcurementContractProjection`, derives dates from those values, and `_upsert_contract()` overwrites every current field via `_contract_values()`.

### Failure scenario

A modification changes only title, procedure wording or titular information. Because amount/duration modification fields are absent, the resulting current contract can lose amount, end date and renewal date even though the source never cancelled those facts.

### Exact correction

- represent amendment field state as at least `ABSENT / SET(value) / EXPLICIT_CLEAR` or an equivalent typed delta;
- map DECP modification payload to an amendment delta, not to a synthetic complete snapshot;
- load the causal predecessor effective state and apply only explicit delta fields;
- materialize the new complete effective state after merge for read performance;
- retain field-level source publication/provenance and basis for inherited vs changed values;
- distinguish explicit cancellation/retraction from field omission;
- backfill existing amendment history in deterministic causal order to rebuild correct effective state.

### Required proof

Title-only, amount-only, duration-only, titular-only, explicit clear, cancellation and multi-amendment chains preserve unaffected facts. Migration up/down/up and replay produce the same effective state.

### Not acceptable

`value or old_value` shortcuts that cannot distinguish legitimate zero/empty/explicit-clear semantics.

---

## R03-F03 — procurement cross-source identity is source-prefixed

**Lot:** 11  
**Severity:** HIGH  
**Owner:** R03-L03

### Expected contract

The same real procurement published by DECP, BOAMP and/or TED can resolve to one canonical procedure/contract history while source-native publications remain independent immutable evidence.

### Current behavior / root cause

Mappers construct source-local canonical keys (for example `decp:procedure:*`, `decp:contract:*`, with analogous BOAMP/TED source namespaces). Persistence keys procedures/contracts by those values. Multi-source history therefore occurs only when mappers already happen to agree on the same canonical key, which the source prefix prevents for the same cross-channel event.

### Exact correction

- persist native source identifiers/reference chains separately from canonical procurement ID;
- create a deterministic/reviewed `ProcurementIdentityDecision` (or equivalent) with rule/version, evidence, state, decision history and reversible merge/reject/split semantics;
- auto-bind only strong exact shared official references/identifiers;
- name/title/amount/date similarity may rank candidates but must not silently merge;
- canonical procurement lookup occurs before aggregation/projection;
- preserve every source publication and source-local lineage after grouping.

### Required proof

DECP↔BOAMP, DECP↔TED and BOAMP↔TED duplicate cases converge; near-duplicates do not. Review, reject, split, replay and concurrent arrivals are durable and reversible.

---

## R03-F04 — procurement buyer bypasses Lot08 identity authority

**Lot:** 11↔08  
**Severity:** HIGH  
**Owner:** R03-L03

### Expected contract

Procurement buyer aggregation references the canonical organization only after exact/reviewed organization identity binding.

### Current behavior / root cause

DECP creates `Organization(id=uuid5(..., "decp:buyer:..."))` directly; other procurement sources have analogous mapper-local identity material. The procurement record then treats that UUID as the buyer identity. A source-local mapping choice can therefore become canonical organization identity without the Lot08 authority/review path.

### Exact correction

- introduce a procurement source-party assertion with source, native buyer IDs/name/address evidence;
- resolve exact SIREN/SIRET/official identifier through the Lot08 organization identity service/port;
- name-only or conflicting identifiers remain unresolved/review-required;
- persist a durable source-party→canonical-organization binding decision;
- procurement projection references canonical organization only after binding; otherwise keep unresolved party evidence without inventing organization truth.

### Required proof

Same SIREN/SIRET across differently labelled buyers binds one canonical org; same name without exact evidence does not. Conflicting identifiers force review. Reversal/replay/concurrency preserve evidence.

---

## R03-F05 — public-footprint claims remain current after evidence removal

**Lot:** 12  
**Severity:** HIGH  
**Owner:** R03-L04

### Expected contract

Immutable claim history remains, while the analyst “current” claim set equals claims supported by the current causal resource head.

### Current behavior / root cause

`persist_public_footprint_projections()` only upserts claims present in `projection.claims`. It never reconciles claims that existed on the predecessor but are absent on the new version/tombstone. Query filters and counts can match historical rows.

### Failure scenario

A company page removes a technology/security claim or returns 404/410. The old claim remains visible/countable as though supported now.

### Exact correction

- link every claim assertion to supporting version(s);
- materialize explicit currentness/validity or derive a desired current claim set from the protected head;
- on head advance, reconcile previous current claims against new desired claims: retained, superseded, withdrawn, reappeared;
- tombstone head produces an empty current claim set unless another independent current resource supports an equivalent claim;
- current list/filter/search defaults must use current support only;
- historical/detail timeline remains complete.

### Required proof

Claim removal, tombstone, reappearance, correction, replay and concurrent head advance all produce correct current vs historical results.

---

## R03-F06 — public-footprint versions do not have one protected causal head

**Lot:** 12  
**Severity:** HIGH  
**Owner:** R03-L04

### Current behavior / root cause

`supersedes_version_id` is optional. `_validated_predecessor()` validates a supplied predecessor but accepts no predecessor. Reads infer “latest” by `fetched_at DESC, created_at DESC` rather than a persisted current-head invariant.

### Exact correction

- add one protected current-head reference per resource or equivalent uniqueness-enforced head table;
- changed/tombstone incremental versions must advance from the current predecessor unless explicitly marked historical import;
- reject/record stale and fork attempts before head mutation;
- historical import does not become current merely because fetched later;
- head advance and version insert must be one transaction with row lock/CAS/unique guard;
- same-time ambiguity uses causal predecessor, not created_at.

### Required proof

Two writers, same fetched time, stale predecessor, branch attempt, replay and late backfill all preserve one justified head.

---

## R03-F07 — vulnerability alias bridge cannot converge existing canonicals safely

**Lot:** 13  
**Severity:** HIGH  
**Owner:** R03-L05

### Current behavior / root cause

`_resolve_vulnerability()` queries canonical/alias matches and raises if more than one `VulnerabilityRecord` matches. The historical validation report explicitly treated this as validated behavior. Alias rows are canonical-global rather than source assertion history; hydration injects canonical aliases into every source snapshot.

### Exact correction

- persist `VulnerabilityAliasAssertion` (or equivalent) with source, source record, snapshot, asserted alias/canonical identifier, authority and timestamp;
- introduce durable canonical vulnerability identity decisions with merge/reject/split/review states and rule version;
- an authoritative exact bridge can converge existing canonical records without deleting source snapshots;
- conflicting/ambiguous bridges require review;
- canonical identifier selection remains deterministic but does not erase former identifiers;
- identity reversal/split restores correct grouping without rewriting source evidence.

### Required proof

Bridge after duplicate creation, concurrent bridges, false/ambiguous bridge, split/reject, replay and source-provenance display.

---

## R03-F08 — vulnerability lifecycle authority is source-agnostic

**Lot:** 13  
**Severity:** HIGH  
**Owner:** R03-L05

### Current behavior / root cause

`reconcile_vulnerability_snapshots()` chooses status via a fixed `_STATUS_PRIORITY`, independent of which source owns the identifier lifecycle. OSV/GHSA mappers set `WITHDRAWN` for their advisory withdrawal, which can globally withdraw a canonical CVE.

### Exact correction

- model lifecycle as source assertions plus identifier-namespace authority policy;
- CVE.org/CNA-authoritative lifecycle controls CVE rejected/published/superseded semantics; advisory withdrawal remains advisory-local unless the advisory identifier itself is canonical without stronger authority;
- expose source conflicts rather than flattening them;
- validate `superseded_by` target existence/identity where required, prevent self/cycle/incompatible terminal states;
- preserve status history and policy/rule version used for canonical selection.

### Required proof

CVE active + OSV withdrawn, CVE active + GHSA withdrawn, authoritative CVE rejection/supersession, later correction and policy replay.

---

## R03-F16 — vulnerability hydration drops additional current records from the same provider

**Lot:** 13  
**Severity:** HIGH  
**Owner:** R03-L05

### Expected contract

After canonical convergence, **all distinct current provider records** that still assert facts about the canonical vulnerability contribute to current truth.

### Current behavior / root cause

`latest_vulnerability_snapshots()` orders rows by `source, modified_at DESC` and keeps only `latest[source]`. GitHub and OSV adapters use provider-native record keys (`GHSA-*`, OSV IDs); multiple distinct records can share the same exact CVE alias and resolve to one canonical vulnerability. Only the most recently modified record from that provider survives hydration.

### Failure scenario

Two GitHub advisories map to the same CVE and both remain valid, one carrying package range A and another range B. The more recently modified GHSA becomes the sole GitHub snapshot in reconciliation; the other still-current advisory’s ranges/references/scores disappear from current canonical truth.

### Exact correction

- define source-local lineage identity as `(vulnerability_id, source, source_record_key)` or an explicit provider-record lineage key;
- compute one current head per **source record**, not one per source;
- feed all current source-record heads into canonical reconciliation;
- if a provider record changes, its own predecessor lineage advances without suppressing sibling records;
- withdrawal/retraction of one provider record retires only that record’s contribution;
- add same-modified-time/fork handling using causal semantics, not insertion order.

### Required proof

Two GHSA records and two OSV records sharing one CVE all contribute; updating/withdrawing one does not erase the sibling; replay/concurrent ingestion/same timestamp converge.

### Not acceptable

Changing the dictionary key from `source` to another value that still conflates distinct native records.

---

## R03-F09 — incident official confirmation lacks source-kind binding

**Lot:** 14  
**Severity:** HIGH  
**Owner:** R03-L06

### Current behavior / root cause

`is_official_confirmation` checks membership in `_OFFICIAL_CLAIM_TYPES` and `active`; it does not require `COMPANY_CONFIRMATION` to come from `COMPANY`, regulator notice from `REGULATOR`, or CERT notice from `CERT`.

### Exact correction

- central domain/application authority matrix for allowed `(claim_type, source_kind)` combinations;
- validate at construction/mapping/persistence boundary before a claim can contribute to official status;
- incompatible input remains a lower-authority assertion or is rejected/quarantined with typed reason; never silently upgrades;
- `confirmed_at` additionally requires compatible authority.

### Required proof

Media/provider/ransomware source mislabeled as official does not confirm; company/regulator/CERT valid combinations do; corrections retain history.

---

## R03-F10 — incident cross-key supersession is stored but ignored

**Lot:** 14  
**Severity:** HIGH  
**Owner:** R03-L06

### Current behavior / root cause

`_latest_claim_revisions()` reduces by `(source_id, source_record_key)` and latest `modified_at`. `supersedes_record_key` never participates. Existing integration tests retract the **same** record key, so they do not prove cross-key semantics.

### Exact correction

- persist source-local claim lineage with predecessor pointer/head state;
- allow correction/retraction record B to supersede source record A when the provider says so;
- validate same source/incident lineage and compatible identity;
- reject cycles, self-supersession, stale predecessor and concurrent fork;
- same modified timestamp requires lineage, not write order;
- immutable predecessor snapshots remain queryable.

### Required proof

A→B cross-key correction/retraction, invalid cross-source predecessor, cycle, fork, stale write, replay and concurrent attempts.

---

## R03-F11 — incident grouping trusts provider-native `incident_key`

**Lot:** 14  
**Severity:** HIGH  
**Owner:** R03-L07

### Current behavior / root cause

`reconcile_incident_claims()` groups directly by `claim.incident_key`; mappers pass provider payload `incident_key` through. Independent providers normally use different native IDs, so corroboration/contradiction cannot reliably meet on one canonical incident.

### Exact correction

- preserve native incident identifier as evidence;
- create a canonical incident identity decision/group service;
- deterministic binding only on strong exact shared event/reference identifiers;
- reviewed match may use canonical organization + bounded event/time anchors with explicit human decision;
- fuzzy similarity alone never merges;
- persist merge/reject/split/review history and rule version;
- independence/syndication calculations run after grouping without collapsing provenance.

### Required proof

Same real incident/different IDs merges safely; same victim/two separate incidents remain separate; review/reject/split/replay/concurrency all work.

---

## R03-F12 — incident type uses “most severe wins”

**Lot:** 14  
**Severity:** HIGH  
**Owner:** R03-L06

### Current behavior / root cause

`_TYPE_PRIORITY` selects the maximum incident type across claims, irrespective of source authority/confidence. A low-confidence attacker allegation can therefore make the canonical type `ransomware` while an official source confirms only unauthorized access/service disruption.

### Exact correction

- retain typed incident-type assertions per claim/source;
- select primary type by source authority, confirmation state, confidence and explicit review policy;
- expose conflicts/alternative asserted types;
- low-authority severe allegations remain allegations, not canonical fact;
- retain policy/rule version in decision history.

### Required proof

Ransomware allegation + company unauthorized-access confirmation results in authoritative primary type plus visible ransomware allegation, not silent ransomware upgrade.

---

## R03-F13 — IOC cross-key supersession is stored but ignored

**Lot:** 15  
**Severity:** HIGH  
**Owner:** R03-L08

### Current behavior / root cause

`latest_indicator_snapshots()` reduces by `(source_id, source_record_key)` and never follows `supersedes_record_key`. Existing reclassification test reuses the same key.

### Exact correction

Implement source-local indicator record lineage equivalent to F10: predecessor/head, cross-key correction/retraction, same indicator identity/source validation, cycle/fork/stale protection, replay determinism and immutable history.

### Required proof

Cross-key retraction, cross-key correction, invalid identity/source predecessor, cycle/fork, same-time concurrency and replay.

---

## R03-F14 — IOC expiry is metadata, not clock truth

**Lot:** 15  
**Severity:** HIGH  
**Owner:** R03-L08

### Current behavior / root cause

`_reconcile_indicator()` considers `snapshot.active` but not `expires_at <= now`; queries do not receive `now` and filter the stored `active` column. Existing historical test manually sets `active=False`, so it does not prove automatic expiration.

### Exact correction

- define current assertion semantics `is_effective(as_of)` where expiry boundary is explicit;
- either make read/reconcile paths clock-aware plus schedule next transition, or integrate a durable **local** expiry reconciliation trigger with Lot28’s global time-driven mechanism;
- expired positive assertion stops contributing exactly at boundary;
- independent unexpired evidence may keep canonical indicator active;
- fresh evidence may reactivate without deleting expired history;
- API filters and counts must be time-correct.

### Required proof

No-write passage of time, exact boundary, multiple source TTLs, reactivation and concurrent update/expiry.

---

## R03-F15 — Lot15 campaign/malware capability stops at opaque relation targets

**Lot:** 15  
**Severity:** HIGH  
**Owner:** R03-L09

### Expected contract

An analyst can search and understand an indicator **or a campaign**, including typed chronology/provenance across indicator↔campaign↔malware↔vulnerability.

### Current behavior / root cause

`TelemetryRelation` contains only `relation_type`, `target_key`, `confidence`. The protected router exposes `/v1/threat-indicators` list/detail only. No canonical Campaign/Malware identity, source assertion history, review/split or dedicated analyst timeline exists in this bounded context.

### Exact correction

- add canonical `Campaign` and `MalwareFamily` (or rigorously equivalent threat-entity types);
- persist source-native aliases/assertions and reversible identity decisions;
- add source/current/history timestamps and correction/retraction/expiry semantics;
- replace opaque-only relations with typed relation assertions referencing canonical entity when resolved while retaining native target string as provenance;
- relation metadata includes source snapshot, confidence and validity interval;
- add protected analyst list/search/detail/timeline APIs and frontend workspace if required by the existing product UI contract;
- map STIX/TAXII/provider metadata conservatively; no name-only unsafe merge;
- never actively validate IOCs or retrieve malware binaries.

### Required proof

Cross-source campaign aliases, ambiguous same-name campaigns, split/reject, relation expiry/retraction, campaign timeline, malware↔vulnerability provenance, auth/search/detail and replay.

---

## Final audit conclusion

The final adversarial pass has **16 recovery-local findings**. F01–F16 each have one owner in R03-L02 through R03-L09, except L01/L10 which are process/qualification micro-lots. No known local residual is ownerless after this pass.

This audit is signed off as scope-complete for implementation start. It does **not** assert that any finding is fixed in runtime. R03-L10 must reopen the contracts again after implementation and may add new findings instead of forcing a closeout.
