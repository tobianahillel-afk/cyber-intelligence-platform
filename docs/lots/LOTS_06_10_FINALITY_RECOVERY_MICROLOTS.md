# Lots 06–10 finality recovery micro-lots

Status: **PLANNED_LOCKED**  
Recovery overlay: **R02**  
Tracking issue: **#175**  
Baseline audited: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`

## Execution policy

R02 is corrective implementation work over historical Lots 06–10. These micro-lots are not new normal product lot numbers and must not alter the normal Lots 25–32 sequence.

Implementation order is mandatory unless a later code-level dependency proves a narrower safe reordering:

```text
R02-L01 ownership guard
  -> R02-L02 public-job cross-provider dedup
  -> R02-L03 provider connectivity verification
  -> R02-L04 provider lifecycle/expiry/rotation
  -> R02-L05 fail-closed portfolio authority
  -> R02-L06 adversarial final qualification and closeout
```

R02-L03 and R02-L04 may share one migration if the final schema requires it, but they remain separately testable invariants.

---

## R02-L01 — executable ownership registry and anti-orphan gate

### Owns

The recovery process itself. No runtime finding is closed by L01.

### Objective

Turn `docs/lots/lots_06_10_recovery_findings.yml` into an executable architecture contract so future edits cannot silently remove a finding, assign multiple owners, use placeholder dispositions or create a duplicate later owner.

### Expected code/test surface

Create:

- `tests/architecture/test_lots_06_10_recovery_ownership.py`

The test should load the YAML with the repository's existing safe YAML mechanism and enforce:

1. unique finding IDs;
2. IDs belong to `R02`;
3. each active finding has exactly one owner;
4. `later_scope` findings include an explicit named owner and tracker where applicable;
5. terminal findings use only the allowed terminal dispositions;
6. forbidden placeholder states never occur;
7. `R02-F06` remains owned by Lot28/#171;
8. Lot29/#6, Lot30/#169, Lot31/#5 and SA20 handoffs remain unique;
9. closeout document is not required/present as proof until runtime implementation is complete.

### Migrations

None.

### Tests

- malformed/duplicate finding fixture rejected;
- missing owner rejected;
- placeholder disposition rejected;
- unknown recovery-local owner rejected;
- duplicate capability ownership rejected where it would create competing runtime implementations.

### Exit gate

The ownership test passes and the registry still contains every unresolved final-audit item.

---

## R02-L02 — durable and reversible cross-provider public-job dedup

### Owns

- `R02-F01`.

### Historical invariant

Lot07/#23 requires prudent and reversible deduplication across Lever, SmartRecruiters and the shared Greenhouse canonical contract. Ambiguous cases must never be automatically merged.

### Current boundary to preserve

Keep source-native evidence immutable and provider-scoped:

- each ATS posting keeps its own `RawObservation` lineage;
- each source-native source record remains independently replayable;
- provider updates/removals cannot erase another provider's evidence;
- dedup affects analyst-current grouping/commercial interpretation, not source history.

### Required design

Introduce one canonical public-job duplicate decision/group contract rather than provider-specific pairwise hacks.

Recommended shape:

- durable duplicate group/decision record with stable UUID;
- member identity `(source_id, site_id/source_record_key)`;
- decision state such as `exact_auto_grouped`, `review_required`, `rejected`, `split` as appropriate to existing enum conventions;
- rule/version/fingerprint that explains why a grouping exists;
- `created_at`, `updated_at`, reviewer/actor for reviewed decisions;
- immutable decision history or append-only audit sufficient to reconstruct a split/reversal;
- no destructive merge of evidence rows.

The exact-match candidate key may be reused only after validating its semantics against the historical acceptance boundary. Similarity/fuzzy name matching must **not** become an automatic merge rule.

### Candidate code surfaces

Audit/modify as required:

- `src/cip/adapters/sources/canonical_jobs.py`;
- Lever mapper/collector package;
- SmartRecruiters mapper/collector package;
- Greenhouse canonical mapping compatibility;
- collection orchestration projection/persistence boundary;
- a narrowly owned public-job dedup domain/application module if persistence cannot live cleanly in an existing bounded context;
- migration/model/repository for durable grouping decisions;
- analyst/read-model surface only if required to make reversal observable.

Do **not** add cross-module derived-state reconciliation here; Lot28 consumes canonical change/grouping state later.

### Migration

Likely required if no existing durable duplicate-decision table can represent the invariant.

Migration must be reversible and should:

- create group/decision and member tables or the smallest equivalent normalized structure;
- enforce unique active membership where required;
- retain provider/source keys rather than copying private payloads;
- avoid retroactive unsafe merging during migration.

Legacy rows should initially remain ungrouped unless a deterministic exact replay/backfill explicitly establishes a decision.

### Required tests

1. exact duplicate Greenhouse ↔ Lever groups deterministically;
2. exact duplicate Greenhouse ↔ SmartRecruiters groups deterministically;
3. replay creates no duplicate group/member/decision;
4. same title but different location remains separate;
5. same org/location but materially different title remains separate;
6. ambiguous organization identity never auto-groups;
7. provider-specific source records/evidence remain separately queryable;
8. one provider changes title/location: prior automatic grouping is reevaluated/reversible, not silently permanent;
9. reviewed rejection survives replay;
10. split/reversal restores independent analyst-current interpretation without deleting source history;
11. concurrent arrival of the same pair is race-safe in PostgreSQL;
12. backfill order/shuffled replay produces the same duplicate grouping fingerprint.

### Rollback

Rollback removes only the grouping projection/schema introduced by R02-L02. Source-native evidence and commercial source records remain intact, so disabling the dedup layer cannot destroy collected truth.

### Exit gate

The historical phrase `prudente et réversible` is demonstrated by persisted behavior, not merely by an equality helper.

---

## R02-L03 — provider-specific connectivity verification before CONNECTED

### Owns

- `R02-F02`.

### Historical invariant

Lot09/#27 requires both validation of secret references and a provider-specific connectivity test.

### Required architecture

Add an application port for bounded provider verification. The onboarding module should depend on the port, not on concrete HTTP/SFTP SDK implementations.

Suggested contract semantics:

```text
ProviderVerificationPort.verify(profile, resolved-runtime-secret-handle, context)
  -> success | typed failure
```

Requirements:

- no raw secret persisted in onboarding state, API response, audit details or logs;
- reference resolution occurs at runtime only;
- verification endpoint/operation is provider-approved and minimal (health/whoami/token metadata/list-one/etc. according to the provider contract);
- policy/authorization is checked before network;
- strict timeout, response-size and redirect rules;
- typed normalized failures: auth rejected, scope rejected, rate limited, provider unavailable, policy denied, malformed response, configuration error;
- a missing verification implementation for a provider that requires authentication cannot be interpreted as successful connectivity;
- manual providers remain human/provider-approval flows rather than synthetic network success;
- auth-none public sources may retain the historical automatic `CONNECTED` path if their profile contract intentionally requires no authentication verification.

### Candidate code surfaces

- `src/cip/modules/provider_onboarding/application/service.py`;
- new/extended onboarding application port module;
- provider-specific adapters/infrastructure verification implementations;
- provider profile/catalog capability metadata;
- `src/cip/modules/provider_onboarding/api/routes.py` only for error/status representation, not provider networking;
- tests and operator documentation.

### Migration

Prefer none if existing normalized error/last-verified fields are sufficient. If verification method/version must be persisted for auditability, add the minimum nullable fields with safe legacy semantics, for example verification capability/version and last verification outcome fingerprint. Do not fabricate historical successes during migration.

### Required tests

1. resolvable secret + rejected credential => not `CONNECTED`;
2. resolvable secret + wrong scope => not `CONNECTED`;
3. successful provider probe => `CONNECTED` and `last_verified_at` set;
4. timeout/provider outage => typed failure, no secret leak;
5. verification implementation missing => fail closed for authenticated provider;
6. policy denial happens before fake network transport is called;
7. raw secret absent from DB/audit/API/log capture;
8. manual provider stays in human/approval state;
9. auth-none public provider follows its intended automatic path;
10. replay of verification does not corrupt audit history.

### Rollback

Rollback may disable the new provider probes and return authenticated providers to a non-connected verification-required state; it must never restore an unsafe “reference exists therefore connected” claim as a production truth.

### Exit gate

`CONNECTED` means the exact configured provider verification contract succeeded, except for profiles explicitly defined as authentication-free/not-required.

---

## R02-L04 — legal onboarding transitions, credential expiry, rotation and reverification

### Owns

- `R02-F03`;
- `R02-F04`.

### Objective

Make the provider onboarding lifecycle one explicit state machine. Rotation/expiry must use that same state machine rather than a parallel set of booleans.

### Required transition contract

Define a single previous→next transition graph for every `OnboardingState` used by the current domain. It must cover at minimum:

- initial/not-required/not-configured;
- human-action/email/MFA/provider-approval checkpoints;
- ready-to-verify;
- connected;
- failed;
- revoked;
- blocked/quarantined semantics where present.

Every service operation must request a transition through one validator. Illegal transitions fail before persistence and before success audit creation.

### Expiry/rotation semantics

- expiry timestamp is explicit, timezone-aware and auditable where the provider/reference has a known validity boundary;
- `now >= expires_at` cannot remain semantically current/connected;
- rotation changes a reference/version marker, invalidates the prior verification, and requires verification before `CONNECTED` returns;
- replacing a secret reference never stores or logs its raw value;
- revocation clears/invalidates current authorization deterministically;
- failed re-verification must not preserve a stale successful current status;
- if a provider cannot expose credential expiry, represent that truthfully rather than inventing a date;
- source-portfolio authorization/freshness integration should consume the onboarding truth without duplicating the lifecycle.

### Candidate code surfaces

- `src/cip/modules/provider_onboarding/domain/models.py`;
- `src/cip/modules/provider_onboarding/application/service.py`;
- `src/cip/modules/provider_onboarding/api/routes.py` and schemas;
- onboarding persistence model/audit record;
- source-portfolio freshness integration if it currently reads onboarding authorization state;
- frontend Sources onboarding UI if rotation/expiry must be operable by an analyst/operator.

### Migration

Likely required only if existing fields cannot distinguish reference revision/rotation/reverification state.

Potential minimal additions:

- secret-reference revision/fingerprint metadata that cannot reveal secret value;
- `verification_revision` or equivalent binding of successful verification to current reference configuration;
- `expired_at`/expiry reason only if `expires_at` plus audit cannot express the required transition safely.

Migration rules:

- never mark historical connected rows as freshly reverified;
- existing `expires_at = NULL` means unknown/not declared, not infinite proof;
- existing reference values remain references only;
- downgrade must preserve audit/source safety.

### Required tests

1. each legal edge succeeds;
2. each forbidden edge fails before mutation;
3. failed transition emits no misleading success audit;
4. expired connected provider becomes non-current/non-executable through the composed control path;
5. rotation invalidates old verification;
6. replacement reference requires a new provider verification;
7. failed reverify cannot leave `CONNECTED` current;
8. revoke from legal states works and clears authorization metadata;
9. repeated revoke/rotate semantics are deterministic;
10. concurrent verify/rotate is race-safe in PostgreSQL;
11. timezone boundary exactly at expiry is deterministic;
12. no raw secret in API/database/audit/logs;
13. blocked/quarantined provider cannot be transitioned around the block.

### Rollback

Rollback must prefer a conservative state (`ready_to_verify`, `failed` or equivalent) over preserving an unprovable connected status.

### Exit gate

The lifecycle diagram and the executable transition validator describe the same behavior, and expiry/rotation cannot bypass it.

---

## R02-L05 — fail-closed central source-portfolio execution authority

### Owns

- `R02-F05`.

### Historical invariant

Lot10/#29 establishes the machine-readable source portfolio as the common authority for future source execution. Legacy source absence cannot remain an implicit allow condition in the terminal architecture.

### Required implementation

Change the final authority semantics so:

```text
missing SourcePortfolioRecord -> deny execution + typed/observable reason
non-executable status -> deny
blocking freshness/authorization/quota/cost state -> deny
explicit executable/current record -> allow
```

Before changing the default, prove that every ordinary executable adapter/source/schedule/backfill target is synchronized into the portfolio during bootstrap/deployment validation.

Add a reverse validation complementary to the existing “portfolio executable entry has adapter” check:

- every registered executable adapter/source that can be scheduled or manually invoked must have a portfolio entry;
- every schedule references a governed source identity;
- synthetic/test-only adapters are explicitly classified rather than relying on missing-record allow;
- candidate/non-executable catalogue rows remain non-executable;
- a source removed/disabled from portfolio cannot continue because an old queued job still exists.

### Candidate code surfaces

- `src/cip/modules/source_portfolio/application/execution.py`;
- portfolio bootstrap/catalog synchronization service;
- adapter registry reconciliation;
- scheduler/worker/backfill/manual execution entry points;
- startup validation;
- source portfolio tests and architecture tests.

### Migration

Usually no schema migration is needed. A data migration/bootstrap reconciliation may be required so all legitimate legacy executable sources have explicit portfolio records before fail-closed behavior becomes active.

Do not auto-promote unknown adapters to executable merely to preserve compatibility. Promotion must come from the machine-readable source catalogue/capability contract.

### Required tests

1. missing portfolio record => denied;
2. executable/current portfolio record => allowed;
3. candidate/planned/disabled record => denied;
4. authorization expired/quota/cost blocked => denied;
5. startup fails or reports a hard configuration error when registered executable adapter lacks portfolio ownership;
6. schedule referencing unknown source cannot enqueue an executable job;
7. already queued job is rechecked at execution time and denied after source disable/removal;
8. backfill and manual refresh use the same authority;
9. synthetic test adapter has explicit test catalogue status;
10. normal bootstrap synchronizes all approved production adapters before worker execution;
11. no network call occurs after a portfolio denial.

### Rollback

Rollback should restore service only through explicit portfolio records/configuration, not by reintroducing a permanent global fail-open path. A temporary emergency compatibility flag, if absolutely required, must be explicit, default-off, observable and removed before R02 closeout.

### Exit gate

No runtime source can execute because the catalogue “forgot” it. Absence means non-executable.

---

## R02-L06 — adversarial qualification, no-orphan closeout and exact-head proof

### Owns

Terminal qualification of R02. It does not absorb R02-F06 from Lot28.

### Adversarial matrix

#### Lot06 preservation

- unchanged active Greenhouse posting refreshes expiry without duplicate observation;
- removed posting is not refreshed;
- no R02 change invents immediate false tombstones or source-history deletion.

#### Lot07

- same exact posting arrives in different provider order;
- concurrent duplicate arrival;
- ambiguous title/location/org cases;
- provider correction causes reversible regroup/split;
- reviewed rejection survives replay;
- source-native evidence remains independent.

#### Lot08 preservation

- exact official identifier can remain the only safe auto-confirm path;
- name-only/homonym/conflicting identifier remains review-required;
- R02 introduces no weaker identity merge rule.

#### Lot09

- secret reference exists but provider rejects credential;
- wrong scope;
- provider outage/timeout;
- policy denied before network;
- illegal state jumps;
- expiration at exact boundary;
- rotate while verification is in progress;
- revoke/rotate/reverify races;
- blocked provider cannot escape block;
- no secret appears in DB/API/audit/logs.

#### Lot10

- unknown source scheduled, queued, backfilled and manually requested;
- disable after enqueue/before execution;
- candidate source with adapter present;
- approved source bootstrap;
- authorization/quota/cost block;
- no provider network after denial.

#### Ownership

- R02-F06 still points to Lot28/#171;
- no outbox/reconciliation duplicate is introduced;
- Lot29/30/31 and SA20 boundaries unchanged;
- findings manifest contains no placeholder.

### Full gates

Run on one exact final SHA:

- architecture suite;
- unit/integration suites for ATS, provider onboarding and source portfolio;
- PostgreSQL-backed concurrency/race tests where required;
- migration upgrade/downgrade/upgrade;
- backend lint/type/test/coverage gates;
- frontend lint/type/test/build gates for any touched UI;
- secret scanning/security tests already required by repository CI;
- full regression suite;
- dependency/architecture audit;
- unresolved PR review threads = zero;
- exact-head CI green.

### Closeout document

Only after all gates pass create:

`docs/lots/LOTS_06_10_FINALITY_RECOVERY_CLOSEOUT.md`

It must record:

- exact final SHA;
- every finding and terminal disposition;
- migrations and rollback proof;
- test commands/results;
- CI run identifiers;
- review-thread state;
- explicit statement that Lot28/#171 remains the owner of R02-F06 until Lot28 itself closes that invariant.

### Exit gate

Issue #175 may close only after this closeout exists and reflects the exact merge-qualified head.
