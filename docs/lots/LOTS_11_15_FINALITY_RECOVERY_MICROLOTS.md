# Lots 11–15 finality recovery micro-lots

Status: **PLANNED_LOCKED_AFTER_DEEP_AUDIT**  
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

These are recovery micro-lots, not competing normal product lot numbers.

## R03-L01 — executable ownership/no-orphan guard

Owns no product defect. Add an architecture test reading `lots_11_15_recovery_findings.yml` and enforcing:

- unique finding IDs;
- exactly one owner per recovery-local finding;
- explicit tracker for every later handoff;
- no `later`, `future_hardening`, `manual`, `blocked`, `not_currently_called` or `works_in_test` terminal placeholders;
- no duplicate ownership with Lot19/Lot20/Lot28/Lot29/Lot30/Lot31/SA21;
- no premature closeout file.

Exit: registry is machine-enforced.

## R03-L02 — procurement causal revisions + sparse amendments

Owns: **F01, F02**.

Implement one causal effective-state contract for procurement revisions:

- source-native revision/notice/modification identifiers retained;
- deterministic causal predecessor/head, not content-hash chronology;
- equal-time ambiguity becomes conflict/review when provider sequence cannot resolve it;
- backfill old revision never steals current head;
- DECP amendment modeled as delta or applied to predecessor to materialize complete effective state;
- omitted field retains previous effective value;
- explicit source-supported clear remains possible;
- field-level provenance/date basis retained;
- cancellation/retraction is terminal/current-state semantics without deleting history.

Likely persistence work: source revision/predecessor/head metadata and field provenance or amendment-delta representation.

Tests: shuffled replay; equal timestamp; sparse title-only amendment; amount-only; duration-only; explicit clear; cancellation; retraction; two writers; migration up/down/up.

## R03-L03 — procurement identity + buyer canonical binding

Owns: **F03, F04**.

Create a local procurement identity decision boundary:

- native DECP/BOAMP/TED procedure/contract/publication IDs remain provenance;
- exact shared official identifiers/reference chains can converge deterministically;
- ambiguous candidate match is review-required;
- durable match/reject/split decision history and rule/version fingerprint;
- replay and concurrent arrivals converge;
- no fuzzy title/name auto-merge.

Buyer organization handling:

- exact official buyer identifier binds to existing Lot08 canonical organization;
- name-only buyer remains unresolved source-party evidence/review candidate;
- procurement history references resolved canonical organization only after binding;
- no source-local UUID becomes canonical merely by `upsert_organizations()`.

Tests across DECP↔BOAMP↔TED pairs, reviewed ambiguity, split/reversal, same buyer under multiple labels, exact SIREN/SIRET, concurrency and evidence independence.

## R03-L04 — public-footprint causal resource head + current claim set

Owns: **F05, F06**.

Implement:

- one causal current head per public resource;
- predecessor required for changed/tombstone head advancement unless explicitly historical import;
- stale/fork conflict outcome;
- PostgreSQL-safe head advancement;
- immutable resource-version history;
- claim assertions linked to supporting version;
- explicit claim current/withdrawn/superseded state or equivalent desired-set materialization;
- tombstone/current version withdraws claims no longer supported;
- current API defaults to current supported claims; historical endpoint/timeline remains complete.

Tests: changed page removes one claim; tombstone; redirect; two concurrent versions; same fetched time; older backfill after current; replay; claim reappearance.

## R03-L05 — vulnerability alias identity + lifecycle authority

Owns: **F07, F08**.

Identity:

- persist alias assertion with exact source/snapshot provenance and authority;
- authoritative exact bridge may converge two existing canonicals through a durable identity decision;
- ambiguous/conflicting bridge requires review;
- reversible merge/split/reject history;
- deterministic canonical display identifier without losing any source snapshots.

Lifecycle:

- authoritative namespace owner controls global lifecycle for that identifier;
- ecosystem/advisory withdrawal remains source-specific unless it owns the canonical identifier lifecycle;
- conflicts visible in API/read model;
- validate `superseded_by` target identity, prevent cycles/self-supersession and incompatible terminal states.

Tests: CVE.org active + OSV withdrawn; GHSA withdrawal; authoritative CVE reject; alias bridge after duplicate creation; concurrent alias bridge; split/replay; lifecycle correction.

## R03-L06 — incident authority, supersession and type conflicts

Owns: **F09, F10, F12**.

Authority:

- enforce claim-type↔source-kind matrix in domain/application boundary;
- secondary reporting never becomes official confirmation by claim label alone.

Supersession:

- source-local predecessor exists;
- same incident/source lineage;
- cross-key correction/retraction advances one causal head;
- stale/fork/cycle rejected visibly;
- immutable claim history preserved.

Type reconciliation:

- retain all type assertions and conflicts;
- distinguish alleged/observed/officially confirmed typing;
- canonical primary type uses authority/confidence/review, never fixed severity alone;
- low-authority severe allegation cannot silently upgrade official fact.

Tests: media mislabeled company confirmation, regulator/CERT matrix, cross-key correction/retraction, cycle, concurrent revisions, ransomware allegation vs company unauthorized-access confirmation.

## R03-L07 — reversible cross-source incident identity

Owns: **F11**.

Implement a local canonical incident identity service:

- source-native incident IDs preserved;
- exact external incident/reference identifiers can bind deterministically;
- reviewed organization + bounded event/time anchor may create an explicit identity decision;
- fuzzy similarity alone never auto-merges;
- durable merge/reject/split history;
- source independence remains intact after grouping for corroboration;
- contradiction and syndication calculations operate over canonical grouping without erasing source provenance.

Tests: same incident/different native IDs, same victim/two real incidents, reviewed merge/reject, correction-induced split, concurrent arrivals, replay.

## R03-L08 — threat-indicator causal supersession + clock expiry

Owns: **F13, F14**.

Supersession:

- apply cross-key `supersedes_record_key` to source-local lineage;
- validate predecessor indicator identity/source;
- cycle/fork/stale conflict handling;
- replay-safe current head.

Expiry/currentness:

- current state evaluated as-of a clock or maintained through a durable local expiration sweep;
- expired positive assertion stops contributing at exact boundary;
- another independent unexpired assertion may keep indicator active;
- new evidence reactivates without deleting historical expiry;
- analyst filters use time-correct state.

Lot28 consumes resulting canonical changes downstream; R03 does not build a second global sweep framework.

Tests: exact expiry boundary, no new ingestion, independent sources with different TTL, reactivation, cross-key retraction, replay and concurrent update/expiry.

## R03-L09 — canonical campaign/malware threat entities and analyst chronology

Owns: **F15**.

Complete the historical Lot15 product scope rather than merely wrapping opaque relation strings.

Implement one typed threat-entity model, at minimum:

- Campaign;
- MalwareFamily (or rigorously equivalent malware entity);
- typed aliases and source assertions;
- current/historical state and source timestamps;
- reversible identity/review decisions;
- typed temporal/provenanced relations: indicator↔campaign, indicator↔malware, campaign↔malware, threat entity↔vulnerability;
- relation confidence/source/snapshot and validity;
- STIX/TAXII mapping into source assertions without unsafe auto-identity;
- protected analyst list/search/detail/timeline API and UI if the existing Lot15 UI contract requires it;
- correction/retraction/expiry/supersession/replay support.

Do not actively validate IOCs or retrieve malware. This remains intelligence normalization, not active prospect scanning or payload acquisition.

Tests: same campaign aliases across sources, ambiguous campaign names, campaign split, indicator relation expires/retracts, historical timeline, malware-vulnerability relation provenance, API search/detail.

## R03-L10 — adversarial qualification and closeout

Owns terminal qualification only.

Reopen original Lots 11–15 contracts against the implemented branch. Add F16+ if new residuals are proven; do not force closure.

One exact SHA must pass:

- R03 ownership architecture guard;
- procurement amendment/order/identity PostgreSQL tests;
- footprint head/current-claim concurrency and replay;
- vulnerability alias/lifecycle authority tests;
- incident authority/identity/supersession/type tests;
- threat supersession/time expiry/campaign-malware tests;
- migrations upgrade/downgrade/upgrade;
- backend lint/type/full regression/coverage;
- frontend lint/type/test/build if touched;
- security/redaction/architecture gates;
- zero unresolved review threads;
- exact-head CI green.

Only R03-L10 may create `docs/lots/LOTS_11_15_FINALITY_RECOVERY_CLOSEOUT.md`.
