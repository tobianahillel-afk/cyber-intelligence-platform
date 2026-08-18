# Lots 11–15 — implementation gap audit

Status: **DEEP_AUDIT_COMPLETE_IMPLEMENTATION_PENDING**  
Recovery: **R03**  
Issue: **#177**  
Baseline: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`

## Audit method

For each historical lot this audit compares:

1. original issue/spec and validation report;
2. source mappers and provider-native keys;
3. domain invariants;
4. persistence/current-head rules;
5. local reconciliation;
6. analyst queries/API;
7. replay/order/concurrency/time-only semantics;
8. later-lot ownership to prevent duplicate architecture.

A residual is retained only when current code proves a local capability gap and no existing later owner already covers the exact responsibility.

---

## Lot11 — procurement contract history

### R03-F01 — HIGH — procurement revision causal ordering

**Observed implementation**

- Procedure current state accepts an equal `effective_at` replacement, so process order can decide current state.
- Contract publication ordering uses `revision_key` as a tie-break at equal effective time.
- `revision_key` is a deterministic content identity, not provider chronology.
- DECP exposes date-granularity publication/modification fields, so equal timestamps are not theoretical.

**Gap**

Determinism is not the same as causal correctness. A lexically larger hash can beat a genuinely later source revision, while procedure state can depend on replay order.

**Required correction**

Persist source revision sequence/predecessor/version metadata where available; establish one causal head; surface true same-time ambiguity as typed conflict/review; keep backfilled older revisions historical without stealing the head.

### R03-F02 — CRITICAL — sparse DECP amendment state loss

**Observed implementation**

DECP modification helpers prefer modification-only fields. On an amendment:

- amount reads modified amount only;
- duration reads modified duration only;
- derived end/renewal dates are recalculated from amendment fields;
- absent amendment values become `None`;
- procurement persistence then overwrites the materialized current contract columns from that projection.

**Gap**

An amendment that changes only one dimension can erase still-valid fields from the original contract. Existing integration tests use fully populated amendment snapshots and do not prove sparse patch semantics.

**Required correction**

Represent amendment deltas or materialize a complete effective state by applying a sparse delta to the valid predecessor. Omission must not clear. Preserve field-level provenance and explicit-clear semantics.

### R03-F03 — HIGH — duplicate official procurement publications remain source-isolated

**Observed implementation**

Native canonical keys are source-prefixed (`decp:*`, `boamp:*`, `ted:*`). Historical API tests can show multiple publications under one procedure only because the test manually supplies the same canonical procedure key.

**Gap**

The runtime mappers do not guarantee that the same procurement event published in several official channels becomes one procedure/contract history, despite the historical duplicate-publication acceptance case.

**Required correction**

Create a local procurement identity layer with exact official reference assertions, durable match/reject/split decisions and review for ambiguity. Never fuzzy-auto-merge by title/name alone.

### R03-F04 — HIGH — buyer organization identity bypasses Lot08

**Observed implementation**

DECP/BOAMP/TED construct `Organization` values using source-local UUID derivation. Generic organization persistence upserts by UUID and does not reinterpret these source-local IDs through Lot08 identity resolution.

**Gap**

One real buyer can become several canonical organizations, and name-only buyer data can be made canonical by mapper side effect.

**Required correction**

Bind exact official buyer IDs to Lot08 canonical identity. Name-only buyer observations remain source-party evidence and review candidates until resolved.

**Existing handoff**

Incumbent/renewal relationship inference is explicitly owned by Lot19/#52 and is not duplicated in R03.

---

## Lot12 — corporate public footprint

### R03-F05 — HIGH — stale claims survive newer versions/tombstones

**Observed implementation**

Projection persistence inserts/updates claims that are present in the incoming projection. It does not close or withdraw claims absent from a newer current version. Query paths list persisted claims without restricting them to the claim set of the current resource head.

**Gap**

A claim such as “uses vendor X” can remain analyst-visible after the page removes that evidence or after the resource is tombstoned.

**Required correction**

Retain immutable claim assertion history while materializing an explicit current validity/withdrawal state tied to the current resource head. Current APIs default to currently supported claims; history remains separately queryable.

### R03-F06 — HIGH — resource versions lack a mandatory single causal head

**Observed implementation**

`supersedes_version_id` is optional. Persistence validates predecessor compatibility only when a predecessor is supplied. A changed version can therefore be inserted as a parallel branch; claim update ordering then relies heavily on fetch time/write sequence.

**Gap**

Version chronology is not protected against silent forks or same-time race ambiguity.

**Required correction**

Introduce one current resource-head contract, explicit stale/fork conflict semantics and PostgreSQL-safe advancement. Historical backfill may insert an older historical revision without becoming current.

**Non-finding**

Search/archive discovery correctly routes a candidate toward a governed target or source review and does not directly upgrade search lead text into a confirmed footprint claim.

---

## Lot13 — vulnerability knowledge

### R03-F07 — HIGH — exact alias bridge cannot converge existing canonicals

**Observed implementation**

If the aliases of an incoming snapshot resolve to more than one existing vulnerability record, persistence raises an error. Alias values are then stored on the canonical vulnerability and reused when hydrating all source snapshots, losing the exact assertion provenance of which source established which alias.

**Gap**

A legitimate authoritative alias discovered after two records were independently created cannot converge safely; ingestion stops instead of producing a reviewed/reversible identity decision.

**Required correction**

Persist source/snapshot alias assertions, authority and decision history. Support deterministic exact union where safe, review otherwise, and reversible merge/split/reject decisions while preserving all source snapshots.

### R03-F08 — HIGH — canonical lifecycle is source-agnostic

**Observed implementation**

Canonical status chooses the highest lifecycle severity (`REJECTED`, `WITHDRAWN`, `SUPERSEDED`, etc.) across source snapshots. Existing integration tests explicitly demonstrate an OSV withdrawn snapshot making the entire canonical vulnerability `withdrawn`.

**Gap**

An ecosystem advisory can globally withdraw/reject an authoritative CVE it does not own. Other fields already have source precedence, but lifecycle does not.

**Required correction**

Make lifecycle namespace/source-authority aware. Retain source-specific withdrawal as a source fact; only the authority for the canonical identifier may authoritatively withdraw/reject it. Validate supersession targets and prevent cycles/conflicting terminal state.

---

## Lot14 — incident intelligence

### R03-F09 — HIGH — official confirmation is claim-type-only

**Observed implementation**

The domain considers company confirmation, regulator notice and CERT notice official when the claim type matches and the claim is active. It does not require the corresponding source kind.

**Gap**

A mapping error or future adapter could label media/provider/attacker content as a company/regulator/CERT claim type and create an official confirmation.

**Required correction**

Enforce a domain authority matrix before persistence: company confirmation↔company source, regulator notice↔regulator, CERT notice↔CERT, plus only explicitly approved equivalents. Secondary reporting remains secondary.

### R03-F10 — HIGH — cross-key supersession is ignored

**Observed implementation**

Claims contain `supersedes_record_key`, but reconciliation selects the latest revision independently for each `(source_id, source_record_key)` and does not apply the supersedes relationship. Historical tests retract by reusing the same key, masking the gap.

**Required correction**

Apply source-local causal supersession across record keys; validate predecessor/incident/source, reject cycles/stale forks, preserve immutable history and converge under shuffled replay/concurrency.

### R03-F11 — HIGH — incident grouping depends on provider-native key equality

**Observed implementation**

Provider payload `incident_key` flows directly into the canonical claim and reconciliation groups by that key. Independent sources with distinct native incident IDs therefore cannot reliably corroborate or contradict each other.

**Required correction**

Add a reversible local canonical incident identity decision using strong exact external incident references and reviewed organization/event anchors. Preserve each source-native incident ID and independence key; ambiguous similarity is review-required.

### R03-F12 — HIGH — most severe incident type wins

**Observed implementation**

Canonical incident type uses a fixed type-priority ordering. A weak ransomware/supply-chain allegation can therefore set the canonical type even if official sources only confirm a less severe class.

**Required correction**

Keep type as source assertions with conflicts. Select authoritative/confirmed analyst summary using authority/confidence/review, not severity. Weak claims remain visible without silently upgrading official fact.

---

## Lot15 — threat telemetry

### R03-F13 — HIGH — cross-key indicator supersession ignored

**Observed implementation**

Indicator snapshots carry `supersedes_record_key`; local selection still groups independently by `(source_id, source_record_key)`. Tests cover same-key correction/retraction only.

**Required correction**

Implement one source-local causal indicator lineage supporting cross-key correction/retraction, stale/fork/cycle rejection, deterministic replay and PostgreSQL concurrency safety.

### R03-F14 — HIGH — expiry is metadata rather than current-state truth

**Observed implementation**

Snapshots have `expires_at`, but reconciliation derives active state from `snapshot.active` and has no `now` parameter. Persistence only reconciles on writes; queries do not clock-filter active state. Historical tests explicitly set expired examples to inactive rather than proving automatic expiry.

**Gap**

An `active=True` IOC can remain active after its expiry until another provider write happens.

**Required correction**

Make local currentness clock-aware through as-of reconciliation and/or a durable local expiry sweep. One expired source assertion stops contributing; another unexpired independent source can keep the indicator active. Fresh evidence can reactivate it.

### R03-F15 — HIGH — campaign/malware capability stopped at opaque relation strings

**Historical requirement**

Lot15 requires indicator↔campaign↔malware↔vulnerability relations with provenance and an analyst ability to search/understand an indicator **or a campaign**.

**Observed implementation**

The bounded context contains canonical indicator records and snapshot-owned relation rows whose targets are opaque strings. The protected API exposes `/v1/threat-indicators` list/detail only; no canonical campaign/malware entity, identity, timeline or campaign endpoint exists.

**Gap**

The indicator side was implemented; the campaign/malware analyst side of the historical exit gate was not developed to the same depth.

**Required correction**

Add canonical threat entities (Campaign, MalwareFamily or a rigorously typed equivalent), immutable source assertions, alias/review decisions, typed temporal relations to indicators/vulnerabilities, current+historical timelines and protected search/detail API/UI. Source-native relation strings remain provenance until safely resolved.

---

## Ownership conclusion

No R03-local finding above has a valid existing later owner. Known later responsibilities remain intentionally outside R03:

- Lot19 relationship/incumbent/renewal context;
- Lot20 global corporate/entity graph;
- Lot28 cross-module downstream reconciliation/invalidation;
- Lot29/30/31 hardening/privacy;
- SA21 live source activation.

The authoritative machine-readable owner mapping is `lots_11_15_recovery_findings.yml`.
