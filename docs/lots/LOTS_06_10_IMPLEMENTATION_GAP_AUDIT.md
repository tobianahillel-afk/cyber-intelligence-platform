# Lots 06–10 implementation gap audit — third adversarial pass

Status: **THIRD_PASS_FINAL_AUDIT_COMPLETE_IMPLEMENTATION_PENDING**  
Recovery: **R02**  
Issue: **#175**  
Baseline: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`

## Audit method

This pass does not ask whether a feature name or test exists. It asks whether the historical invariant is enforced through the ordinary runtime and remains truthful under replay, correction, deletion, crash, concurrency, profile changes, health measurement and historical backfill.

A finding is retained only when it is distinct from an existing later owner and supported by current code. Suspicions disproven by deeper code inspection are recorded as non-findings.

---

## Lot06 — Greenhouse public hiring — #21

### Proven core

Greenhouse performs policy authorization before request, strict payload validation, duplicate-job rejection, a bounded 5,000-job board window, deterministic fingerprints and provider-scoped immutable observations/projections. An unchanged active job still receives a current commercial projection while its immutable observation is fingerprint-gated; an absent job stops being refreshed and ages out under the bounded commercial TTL.

### Third-pass nuance

The collector returns the full board response and validates the declared/observed count; no pagination truncation defect was found.

Lot06 itself did not require causal tombstone events. The later Lot10 capability manifest does claim tombstone/correction support for this adapter, and that stronger shared runtime contract is non-final under F09.

### Disposition

Historical Lot06 core remains terminal. Mutation-capability finality is owned by R02-F09/L06 because it is a Lot10 common-runtime promise.

---

## Lot07 — Lever + SmartRecruiters — #23

### Proven core

Both providers have strict public schemas, bounded complete pagination and deterministic current fingerprint maps. Lever advances `skip` until a short page; SmartRecruiters validates `offset` and `totalFound`, detects premature empty pagination and fetches validated detail records.

### R02-F01 — reversible inter-ATS dedup

The canonical model has a provider-independent exact candidate key and `exact_cross_provider_match()`, but no durable group/decision/rejection/split history. Historical `prudente et réversible` semantics therefore remain non-final.

Owner: **R02-L02**.

### R02-F07 — resolved organization binding before commercial aggregation

ATS registry IDs become `organization_key`; `CanonicalPublicJob.organization_id` derives a canonical UUID from that key; the mapper constructs an `Organization`; commercial persistence may upsert it and generate an opportunity. No enforced identity-resolution binding proves that the ATS tenant/board/company corresponds to a Lot08-resolved canonical organization first.

Owner: **R02-L02**.

### Boundary

L02 must preserve provider-native evidence and use Lot08's conservative identity authority. It must not implement fuzzy automatic organization merging or Lot28 downstream reconciliation.

---

## Lot08 — organization identity foundation — #25

### Proven core

The identity persistence model separates identities, identifiers, aliases, relationships, merge candidates and evidence claims. Official identifier normalized `exact_key` is globally unique in persistence, and the historical implementation had PostgreSQL migration/replay/architecture validation. No new internal Lot08 defect was proven by the third pass.

### Disposition

No new local Lot08 finding. F07 is the missing consumer-side enforcement at the ATS commercial boundary.

---

## Lot09 — provider onboarding and secret lifecycle — #27

### R02-F02 — provider-specific connectivity verification

Current authenticated verification can mark `CONNECTED` after secret references resolve, without provider-specific credential/scope/connectivity proof.

Owner: **R02-L03**.

### R02-F03 — legal transition graph

`_transition()` assigns the target state before audit and has no explicit previous→next legality policy.

Owner: **R02-L04**.

### R02-F04 — revision-bound expiry/rotation/reverification

The lifecycle contains `expires_at`, secret references and `last_verified_at`, but no complete revision binding. Third-pass code inspection adds an important case: `sync_provider_profiles()` may change auth mode, required secret names or human-action requirements on an existing row without necessarily invalidating a previous `CONNECTED` state.

Final verification must therefore be bound to:

- current secret-reference revision/fingerprint;
- current provider profile / verification method revision;
- current provider-specific successful verification outcome;
- current expiry/revocation state.

Owner: **R02-L04**.

---

## Lot10 — source portfolio/runtime/backfill/freshness/health/value — #29

### Historical contract

Lot10 explicitly required machine-readable capabilities, immutable source records, bounded resumable backfill, transactional checkpoints, corrections/tombstones/retractions, freshness/source health/circuits/quota/cost/schema drift, authorization expiry, protected lifecycle controls, commercial-value/ablation hooks and the end-to-end chain `catalogue -> onboarding -> backfill -> incremental -> source records -> freshness -> health -> disable`.

### R02-F05 — fail-open portfolio authority

`source_execution_allowed()` returns `True` when no `SourcePortfolioRecord` exists. Missing governance membership is therefore still an implicit allow path.

Owner: **R02-L05**.

### R02-F06 — later-owned downstream convergence

Correction/retraction/expiry/backfill changes are not guaranteed to converge through all downstream derived state. Lot28/#171 already owns the canonical cross-module reconciliation/outbox/invalidation architecture.

Disposition: **owned_by_existing_later_scope**.

### R02-F08 — split authorization truth

Onboarding and Source Portfolio persist separate authorization state. Runtime bootstrap synchronizes both independently, and target-dependent portfolio reconciliation can promote a source based on adapter presence. Execution guards consume portfolio/freshness state but not the current onboarding lifecycle.

Owner: **R02-L05**.

### R02-F09 — source mutation capability contract and causal integrity

The source model supports four mutation actions and a supersedes UUID, but the causal edge is not enforced end-to-end:

- `supersedes_observation_id` is not a same-record predecessor constraint in persistence;
- the reducer ignores the supersedes relation and resolves solely by time/key;
- invalid/forked/cross-record mutation graphs have no rejection path in the audited reducer;
- ATS capability manifests advertise corrections/tombstones while current ATS collectors emit changed records as default UPSERT and removals only as checkpoint absence.

Owner: **R02-L06**.

Required final behavior:

1. mutation target must exist and belong to the same source + source-record identity;
2. mutation must advance the current head or be explicitly classified as stale/conflicting;
3. concurrent competing mutations cannot silently fork current truth;
4. capability manifest support is executable and tested;
5. complete successful ATS traversal may emit causal TOMBSTONE for disappearance; partial traversal may never do so;
6. changed ATS record emits CORRECTION linked to current predecessor;
7. immutable history remains intact.

### R02-F10 — backfill is not durably crash-resumable

`BackfillPartitionRecord` has no lease owner/lease expiry/available-at. Claim sets a partition RUNNING and only PENDING/FAILED are later claimable; a process crash can strand RUNNING forever.

The backfill worker also catches `AdapterPartialExecutionError` through its parent type and discards the embedded partial batch/checkpoint, unlike incremental execution. Failed partitions are immediately reclaimable without incremental-style circuit/backoff.

Owner: **R02-L07**.

Required final behavior:

- durable ownership lease + stale RUNNING recovery;
- atomic partial observation/checkpoint/progress persistence;
- bounded backoff and shared/reused circuit semantics;
- retry after provider failure does not hammer upstream;
- pause/disable/revoke races invalidate ownership safely;
- PostgreSQL duplicate claims impossible;
- exact resumption from safe cursor after crash/partial response.

### R02-F11 — quality baseline measures delta emissions as source volume

`evaluate_quality()` computes `records_count = len(observations)` and updates EWMA volume/field/schema baselines. Delta adapters such as Greenhouse/Lever/SmartRecruiters fetch the full current provider set but emit immutable observations only for changed jobs.

Therefore source health can treat change count as provider population, producing false low-volume anomalies or misleading baselines.

Owner: **R02-L08**.

Final contract must separate:

- current records seen / authoritative population where provider supports it;
- changes emitted;
- removals observed;
- pages/windows traversed;
- traversal complete/incomplete;
- representative schema/field population;
- not-modified semantics.

Partial/incomplete traversals must not train a healthy-population baseline.

### R02-F12 — backfill value accounting is hardcoded to zero

Incremental value events count commercial and identity projections. Backfill value events unconditionally record `commercial_projections=0` and `identity_projections=0`, even when a batch persists derived source outputs. Existing historical value tests use a synthetic zero-projection batch and do not cover a real commercial/identity backfill.

Owner: **R02-L09**.

Final contract must count accepted/persisted outputs consistently and preserve execution mode so historical imports are not mistaken for fresh commercial triggers.

---

## Third-pass disproven hypotheses / non-findings

- **No general circuit finding:** collection orchestration has durable `CollectionCircuitRecord`, failure registration, OPEN/HALF_OPEN behavior and delayed retries. Backfill parity is F10.
- **No priority-refresh bypass:** priority refresh checks the shared execution authority and the worker checks again.
- **No portfolio sync pause reset:** normal sync preserves manual PAUSED/DISABLED state; runtime-managed activation only reinforces F08.
- **No Lot08 exact-ID uniqueness gap:** `OrganizationIdentifierRecord.exact_key` is unique.
- **No Lever/SmartRecruiters pagination gap:** bounded complete traversal is explicitly implemented.
- **No Greenhouse hidden pagination gap:** full board result is bounded and validated.

## Final registry

| ID | Severity | Owner | Status |
|---|---|---|---|
| F01 | high | R02-L02 | recovery_local |
| F02 | high | R02-L03 | recovery_local |
| F03 | high | R02-L04 | recovery_local |
| F04 | high | R02-L04 | recovery_local |
| F05 | critical | R02-L05 | recovery_local |
| F06 | critical | Lot28/#171 | owned_by_existing_later_scope |
| F07 | high | R02-L02 | recovery_local |
| F08 | critical | R02-L05 | recovery_local |
| F09 | high | R02-L06 | recovery_local |
| F10 | critical | R02-L07 | recovery_local |
| F11 | high | R02-L08 | recovery_local |
| F12 | high | R02-L09 | recovery_local |

There is no known ownerless residual after this third-pass ownership lock. R02-L10 remains authorized to discover F13+ only from the implemented code before closeout.
