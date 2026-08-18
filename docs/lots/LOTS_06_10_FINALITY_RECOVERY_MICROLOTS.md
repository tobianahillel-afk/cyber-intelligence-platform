# Lots 06–10 finality recovery micro-lots — version 3

Status: **PLANNED_LOCKED_AFTER_THIRD_PASS**  
Recovery overlay: **R02**  
Issue: **#175**  
Baseline: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`

## Mandatory implementation order

```text
R02-L01 ownership guard
  -> R02-L02 ATS identity binding + reversible dedup
  -> R02-L03 provider connectivity verification
  -> R02-L04 onboarding lifecycle/revision/expiry/rotation
  -> R02-L05 composed fail-closed execution authority
  -> R02-L06 source mutation capability + causal integrity
  -> R02-L07 durable backfill recovery
  -> R02-L08 truthful source quality semantics
  -> R02-L09 truthful source value/ablation
  -> R02-L10 adversarial exact-head qualification + closeout
```

These are recovery micro-lots, not normal product lot numbers.

---

## R02-L01 — executable ownership/no-orphan guard

Owns the machine-checkable recovery registry, not a product defect.

Create/extend architecture tests to enforce unique finding IDs, exactly one owner per finding, allowed dispositions, explicit later tracker for F06, no placeholder state, no duplicate Lot28–31/SA ownership, and no premature closeout.

Exit: YAML version 3 F01–F12 is executable as an architecture contract.

---

## R02-L02 — ATS canonical organization binding + durable reversible dedup

Owns: **F01, F07**.

Implement one public-job canonical grouping/application boundary:

- provider-native posting and organization identifiers stay immutable provenance;
- ATS tenant/board/company must bind to an existing Lot08-resolved canonical organization before organization-scoped aggregation;
- exact deterministic cross-provider duplicates may auto-group only after resolved-identity equality;
- ambiguous identity or duplicate similarity is review-required;
- durable group/member/decision/history with stable IDs and rule/version fingerprint;
- rejection and split/reversal survive replay;
- no destructive evidence merge;
- concurrency-safe membership in PostgreSQL.

Likely migration: duplicate group/member/decision audit plus a narrow ATS→canonical-organization binding record if no existing identity-claim table can express the association safely.

Tests: exact duplicates across all ATS pairs, ambiguous org, conflicting org, reviewed rejection, correction-induced split, replay order, concurrent arrivals, source evidence independence.

---

## R02-L03 — provider-specific verification before authenticated CONNECTED

Owns: **F02**.

Introduce an onboarding application port for bounded provider verification. Reference resolution alone is insufficient.

Requirements:

- policy before network;
- provider-approved minimal probe;
- credential/scope/connectivity typed results;
- strict timeout/size/redirect policy;
- missing verification implementation fails closed for authenticated providers;
- manual providers remain human checkpoint flows;
- auth-none public providers retain truthful network-free semantics where appropriate;
- no raw secret in DB/API/audit/logs.

Tests include rejected credential, wrong scope, timeout/outage, policy denial before fake transport, missing probe, secret redaction and successful verified connection.

---

## R02-L04 — one legal revision-bound onboarding lifecycle

Owns: **F03, F04**.

Implement a single explicit transition graph and one revision model for current authorization.

Verification validity must bind to:

- current secret-reference configuration revision;
- current provider-profile/verification-contract revision;
- successful provider verification outcome;
- current expiry/revocation state.

Changing secret refs, auth mode, required secret names, verification method/profile or relevant scope invalidates the prior verification. Illegal state transitions fail before mutation/audit. Rotation, expiry, revoke and reverification use the same state machine.

Concurrency tests: verify vs rotate, verify vs revoke, profile sync vs verify, exact expiry boundary, repeated operations, blocked provider escape attempt.

---

## R02-L05 — composed fail-closed source execution authority

Owns: **F05, F08**.

Replace bool-only fragmented truth with one typed eligibility decision used by scheduler, queued worker, priority/manual refresh and backfill.

Final decision composes:

- explicit Source Portfolio membership and executable state;
- runtime adapter/capability existence;
- current Provider Onboarding authorization state/revision where auth applies;
- portfolio authorization expiry;
- quota/cost blocking state;
- operational execution blocks.

Missing portfolio or required onboarding state fails closed. Startup validates both directions between executable catalog entries, adapters and schedules. Recheck eligibility at the last safe pre-network boundary so revoke/expiry after queueing cannot leak one more request.

Do not build Lot28 reconciliation here.

---

## R02-L06 — source mutation capability contract and causal integrity

Owns: **F09**.

### Goal

Make corrections/tombstones/retractions a real executable source-record contract rather than a permissive enum plus manifest flags.

### Required behavior

- mutation target exists;
- target belongs to same `source_id` and `source_record_key` (and compatible record type/adapter where required);
- mutation advances the current causal head or returns a typed stale/conflict outcome;
- concurrent competing mutations cannot silently fork current state;
- persistence maintains referential integrity for supersedes relationships where safe;
- reducer/replay validates causal history instead of ignoring supersedes;
- capability manifests are contract-tested against adapter behavior.

### ATS completion

For Greenhouse/Lever/SmartRecruiters:

- changed fingerprint after a known predecessor -> `CORRECTION` with predecessor ID;
- record present in prior complete checkpoint but absent from a new **complete successful** traversal -> `TOMBSTONE` with predecessor ID;
- partial/error/incomplete traversal -> never infer deletion;
- reappearance after tombstone follows an explicit deterministic resurrection/upsert rule;
- provider evidence/history never deleted.

### Migration/tests

Likely migration for supersedes FK/index/current-head protection or an equivalent normalized current-head table. Test cross-record supersedes rejection, unknown predecessor, stale branch, simultaneous corrections, tombstone race, replay order, deletion after complete traversal and no deletion after partial traversal.

Lot28 receives these valid mutations later; L06 does not propagate derived state globally.

---

## R02-L07 — durable backfill crash/partial-progress/circuit recovery

Owns: **F10**.

### Required architecture

Prefer reusing the collection orchestration lease/circuit primitives or extracting shared primitives rather than creating a second divergent reliability stack.

Backfill must have:

- durable lease owner and expiry or equivalent job ownership token;
- stale RUNNING recovery;
- PostgreSQL `SKIP LOCKED`/ownership-safe single claimant;
- retry `available_at` and bounded exponential backoff;
- circuit OPEN/HALF_OPEN behavior compatible with incremental collection;
- distinct retryable/non-retryable terminal semantics;
- safe partial-batch persistence for `AdapterPartialExecutionError`;
- cursor/progress checkpoint persisted atomically with source-local observations;
- no double-counting `records_written` on retry;
- pause/disable/revoke invalidates in-flight completion safely;
- execution authority rechecked immediately before provider network.

### Tests

Crash after claim; lease expiry/takeover; two workers; partial page succeeds then provider fails; retry resumes at partial cursor; circuit opens; backoff respected; pause/disable/revoke while running; lease lost on completion; migration upgrade/downgrade/upgrade.

---

## R02-L08 — truthful source-quality population/delta semantics

Owns: **F11**.

Extend `AdapterCollectionBatch` with a typed, provider-neutral run-quality profile rather than overloading `observations`.

Recommended data:

- `records_seen` / current provider population when knowable;
- `records_changed`;
- `records_removed`;
- page/window count;
- `traversal_complete`;
- schema fingerprints sampled from validated provider records;
- field-population summary;
- optional provider-declared totals;
- metric availability flags.

Quality baseline rules:

- population anomaly uses population metric, not immutable delta count;
- delta/change rate may have a separate baseline;
- partial/incomplete run never trains a healthy population baseline and never generates deletion inference;
- `not_modified` does not erase last truthful population state;
- schema/field health uses representative validated records rather than only changed rows where available;
- adapters unable to supply a metric report `unknown`, not zero.

Tests: 1000→1000 with one changed stays healthy; 1000→10 complete traversal flags anomaly; one changed in otherwise stable provider does not; incomplete traversal does not poison baseline; removal-only run; schema drift; 304/not-modified.

---

## R02-L09 — truthful source-value and ablation attribution

Owns: **F12**.

Create one value-event derivation contract shared by incremental and backfill completion.

Requirements:

- count accepted/persisted observations and source-owned canonical/commercial/identity outputs using one definition;
- do not hardcode backfill projections to zero;
- preserve `execution_mode` so historical outputs are distinguishable from fresh-trigger value;
- replay/idempotent event key remains unique;
- partial retries cannot double-count;
- source ablation summaries remain reproducible;
- if Lot28 later changes projection plumbing, value attribution consumes the canonical persistence result rather than duplicating reconciliation.

Tests use at least one real historical source path that produces commercial or identity output, not only the zero-output reference adapter.

---

## R02-L10 — final adversarial qualification and closeout

Owns terminal qualification only.

Before closeout, rerun the audit against the implemented code and add F13+ if a new historical residual is proven. No placeholder closure is allowed.

Exact-head gates:

- ownership manifest tests;
- ATS identity/dedup/mutation/replay/concurrency;
- provider verification/lifecycle/redaction;
- composed execution authority/no-network-after-deny;
- backfill lease/crash/partial/circuit PostgreSQL tests;
- quality semantics;
- value/ablation semantics;
- migration upgrade/downgrade/upgrade;
- architecture + backend full regression;
- frontend lint/type/test/build if UI touched;
- security gates;
- zero unresolved review threads;
- exact-head CI green.

Only L10 may create `LOTS_06_10_FINALITY_RECOVERY_CLOSEOUT.md`.
