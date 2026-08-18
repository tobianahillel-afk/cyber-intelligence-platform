# Lots 06–10 finality recovery micro-lots

Status: **PLANNED_LOCKED_AFTER_SECOND_AUDIT**  
Recovery overlay: **R02**  
Tracking issue: **#175**  
Baseline audited: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`

## Mandatory order

```text
R02-L01 ownership registry / anti-orphan guard
  -> R02-L02 ATS identity binding + durable reversible inter-ATS dedup
  -> R02-L03 provider-specific connectivity verification
  -> R02-L04 legal onboarding lifecycle / expiry / rotation / reverify
  -> R02-L05 composed fail-closed runtime execution authority
  -> R02-L06 adversarial exact-head qualification / closeout
```

R02 micro-lots are corrective overlays, not new normal product lot numbers.

---

## R02-L01 — executable ownership registry and anti-orphan gate

### Owns

The recovery registry itself; no runtime defect is closed here.

### Required

Create `tests/architecture/test_lots_06_10_recovery_ownership.py` and enforce:

- unique `R02-Fxx` IDs;
- exactly one owner for every unresolved finding;
- local owners are only valid R02 micro-lots;
- later-owned findings name a real existing owner/tracker;
- F01/F07 → R02-L02 exactly once;
- F02 → R02-L03 exactly once;
- F03/F04 → R02-L04 exactly once;
- F05/F08 → R02-L05 exactly once;
- F06 → Lot28/#171 exactly once;
- no forbidden placeholder disposition;
- no premature closeout document/proof.

No migration.

---

## R02-L02 — resolved ATS organization binding + durable/reversible cross-provider job dedup

### Owns

- R02-F01;
- R02-F07.

### Why they share one owner

A cross-provider job comparison is only trustworthy after all provider-native postings refer to the same resolved canonical organization. Implementing F01 without F07 would preserve a hidden dependency on operators choosing matching `organization_key` strings; implementing F07 separately inside Lot08 would duplicate identity authority.

### Required architecture

Introduce one public-job canonicalization boundary with two stages:

1. **organization binding**
   - every configured Greenhouse board, Lever site and SmartRecruiters company keeps its provider-native source identity;
   - commercial projection must resolve that source identity to an existing canonical `organization_id` through exact official identity or an explicit reviewed binding;
   - unresolved/ambiguous binding is persisted as review-required and cannot silently create a canonical legal organization for aggregation;
   - display names remain source evidence, not identity authority.
2. **job duplicate decision**
   - compare only jobs already bound to the same canonical organization;
   - exact conservative rules may auto-group;
   - ambiguous similarity remains review-required;
   - persist stable group/member/decision, rule/version/fingerprint and reviewer/audit metadata;
   - preserve every provider-native SourceRecord/RawObservation/Evidence;
   - split/reject/reversal is durable and replay-stable.

Do not use fuzzy organization-name auto-merge. Do not create a Lot28-style downstream reconciliation engine here.

### Primary code surfaces

- `src/cip/adapters/sources/canonical_jobs.py`;
- Greenhouse/Lever/SmartRecruiters registries + mappers;
- `src/cip/modules/opportunities/infrastructure/projections.py` or a preceding application boundary that prevents unresolved organizations reaching canonical persistence;
- Lot08 organization identity query/application contracts for safe binding, without moving ownership into adapters;
- new narrowly owned public-job binding/dedup domain/application/persistence if no existing bounded context fits;
- migration(s) for source→organization binding and duplicate decisions if durable schema is absent.

### Required tests

- ATS local id cannot mint canonical organization without binding;
- exact official/resolved organization binding permits projection;
- ambiguous organization identity becomes review-required and emits no organization-scoped commercial aggregation;
- two ATS local identifiers can bind to the same canonical organization;
- exact duplicate across providers groups deterministically;
- same title/different organization never groups;
- same organization/title but materially different location/department remains separate or review-required per explicit rule;
- provider evidence remains independent;
- correction can split/re-group;
- reviewed reject/split survives replay;
- concurrent identical arrivals are race-safe in PostgreSQL;
- shuffled replay/backfill order yields same decision fingerprint;
- rollback removes only derived binding/grouping schema and never source history.

### Exit

Lot07's `prudente et réversible` requirement is demonstrated on resolved canonical organization identity, not config-string coincidence.

---

## R02-L03 — provider-specific connectivity verification before CONNECTED

### Owns

R02-F02.

### Required

Add an onboarding application port such as `ProviderVerificationPort`, backed by provider-specific bounded implementations. For authenticated providers:

- secret resolution is runtime-only;
- policy/authorization check occurs before network;
- no verifier implementation means verification-required/fail-closed, not success;
- provider-specific minimal probe validates credential and required scope;
- strict timeout/redirect/response-size rules;
- typed normalized errors for auth, scope, rate-limit, outage, policy, malformed response/config;
- no raw secret in DB/API/audit/logs;
- manual provider remains human/provider-approval flow;
- auth-none public sources retain truthful automatic behavior where the profile explicitly defines verification as not required.

### Tests

Resolvable secret + rejected credential/wrong scope/outage/missing verifier cannot become CONNECTED; successful probe sets current verification; policy denial precedes transport; raw secret redaction is proven end-to-end.

---

## R02-L04 — one legal onboarding state machine with expiry/rotation/reverification

### Owns

- R02-F03;
- R02-F04.

### Required

Define one explicit previous→next graph for every onboarding state and force every service operation through it. Illegal transitions fail before mutation and before success audit.

Rotation/expiry must be part of the same lifecycle:

- successful verification is bound to the current non-secret reference-set revision/fingerprint;
- replacing a reference invalidates prior verification;
- `now >= expires_at` is non-current authorization;
- failed reverify cannot preserve stale CONNECTED truth;
- revoke invalidates current authorization deterministically;
- blocked/quarantined controls cannot be bypassed by alternate transitions;
- unknown credential expiry stays unknown, not fabricated as infinite validity;
- concurrency verify↔rotate/revoke is safe under PostgreSQL.

Expose operator API/UI controls only where needed to make lifecycle actions operable and auditable.

### Exit

The domain transition graph, service behavior, API and runtime-consumed authorization view all describe the same lifecycle.

---

## R02-L05 — composed fail-closed source execution authority

### Owns

- R02-F05;
- R02-F08.

### Architecture decision

Do **not** choose between onboarding and portfolio by deleting one. They own different truths:

- Provider Onboarding = credential/authorization truth.
- Source Portfolio = single runtime execution decision authority.

The portfolio decision must compose onboarding instead of duplicating it.

### Required decision contract

Replace a boolean-only conceptual model with a typed eligibility result sufficient for observability:

```text
source portfolio membership/status
+ current provider onboarding authorization (when required)
+ authorization expiry / verification revision
+ freshness / circuit / quota / cost
+ runtime adapter capability/availability
= allow | deny(reason)
```

Required behavior:

- missing portfolio row => deny;
- candidate/planned/disabled => deny;
- authenticated source missing current CONNECTED verification => deny;
- revoked/failed/expired/rotated-but-unverified => deny;
- quota/cost/health block => deny;
- adapter unavailable/mismatched => deny;
- auth-none source may run only when its explicit portfolio/source-governance contract is executable;
- reverse startup validation proves every executable adapter/schedule/manual/backfill target has governed portfolio ownership;
- no implicit auto-promotion of unknown adapters;
- queued/claimed incremental jobs and claimed backfill partitions are revalidated at the last safe pre-network boundary;
- denial produces typed/observable reason and zero provider network.

### Concurrency/race tests

- revoke after queue but before collect => no network;
- expiry at exact boundary => no network;
- rotate after queue but before collect => no network until new verification;
- pause/disable after queue => no network;
- backfill sees same outcomes as incremental;
- missing portfolio record never restores legacy execution;
- startup catches runtime source without portfolio entry;
- explicit approved source remains executable after bootstrap.

### Boundary with Lot28

R02-L05 may synchronize/consult onboarding state only to make the execution decision. It must not build a generalized downstream outbox, entity invalidation bus or derived-state projector; those remain Lot28.

---

## R02-L06 — adversarial exact-head qualification and closeout

### Required re-audit

Re-read issues #21/#23/#25/#27/#29 and inspect the implemented code, migrations and tests rather than trusting this plan. Any new historical residual becomes R02-F09+ with exactly one owner before closeout.

### Adversarial matrix

- Lot06 active refresh/removed ageing semantics preserved.
- F07 unresolved ATS identity cannot mint canonical org/opportunity.
- F01 exact duplicates converge only after resolved identity; ambiguity and corrections remain reversible.
- F02 secret availability alone never proves authenticated connectivity.
- F03/F04 illegal transition, exact expiry, rotate/reverify/revoke races fail safely.
- F05 unknown/candidate/disabled source cannot execute.
- F08 onboarding revoke/expiry/failure/reference rotation blocks queued incremental/backfill/manual network calls.
- F06 remains solely Lot28-owned.
- no raw secrets, active scanning, auth bypass, fuzzy identity auto-merge or destructive source-history merge introduced.

### Exact-head gates

One final SHA must pass architecture, unit/integration, PostgreSQL concurrency, migration upgrade→downgrade→upgrade, lint/type/coverage/full backend regression, frontend checks when touched, security/redaction tests, review-thread zero check and exact-head CI.

Only then create `LOTS_06_10_FINALITY_RECOVERY_CLOSEOUT.md` and close #175.
