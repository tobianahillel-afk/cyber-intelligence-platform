# Lots 06–10 implementation finality recovery

Status: **FINAL_AUDIT_COMPLETE_IMPLEMENTATION_PENDING**  
Recovery overlay: **R02**  
Tracking issue: **#175**  
Audited baseline: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`

## Purpose

This recovery applies the same implementation-finality method used for historical Lots 01–05 to historical Lots 06–10. A closed issue, merged PR, passing historical CI or an `IMPLEMENTED_VALIDATED` label is evidence, but it is not by itself proof that the original product invariant remains fully implemented in the current runtime.

The recovery therefore reopens the original acceptance contract and compares it against:

1. current domain contracts;
2. current adapter/runtime invocation paths;
3. persistence and migrations;
4. API/control-plane behavior;
5. replay, failure and concurrency semantics;
6. current tests and architecture boundaries;
7. later roadmap ownership already assigned to Lots 28–31 or Source Activation.

R02 is a recovery overlay. It does **not** renumber or replace the normal product roadmap.

## Historical scope

| Historical lot | Tracker | Original outcome | R02 disposition |
|---|---:|---|---|
| Lot06 | #21 | Greenhouse public cyber hiring signals | Historical core remains terminal; no local recovery finding |
| Lot07 | #23 | Lever + SmartRecruiters, shared public-job contract and reversible inter-ATS dedup | One local finality gap: R02-F01 |
| Lot08 | #25 | French/European organization identity foundation | Historical core remains terminal; no local recovery finding |
| Lot09 | #27 | Provider onboarding, secret-reference lifecycle and verification | Three local finality gaps: R02-F02–F04 |
| Lot10 | #29 | Central source portfolio/runtime, backfill, freshness and source health | One local critical gap R02-F05; one cross-module residual already owned by Lot28 as R02-F06 |

## Final finding set

### R02-F01 — Lot07 cross-provider public-job dedup finality

`CanonicalPublicJob` has an exact cross-provider comparison primitive and a provider-independent candidate key. However, the normal mapping path still creates source-record/evidence/signal identities scoped to the provider/source and the audited Lot07 surface does not materialize a durable duplicate-group decision, rejection or reversal contract.

The original Lot07 requirement was not merely “a helper can compare two jobs”; it required **prudente et réversible** inter-ATS deduplication.

Owner: **R02-L02**.

### R02-F02 — Lot09 provider-specific connectivity verification

The Lot09 issue explicitly requires both secret-reference validation **and** provider-specific connectivity testing. `verify_provider_configuration()` currently resolves required references and marks an authenticated provider `CONNECTED` when those references are available. That proves deployability of a reference, not provider connectivity or authorized scope.

Owner: **R02-L03**.

### R02-F03 — Lot09 legal lifecycle transitions

The historical acceptance criteria explicitly require invalid transitions to be refused. Current `_transition()` records previous/new state in audit history but directly assigns the requested target state. Auditability is present; transition legality is not a first-class invariant.

Owner: **R02-L04**.

### R02-F04 — Lot09 expiry/rotation/re-verification lifecycle

The historical scope explicitly includes rotation and expiry. `expires_at` exists in persistence/domain state and revocation clears it, but the ordinary service/API surface does not provide a complete rotate/expire/reverify workflow and does not make expiry itself a state-machine guard before a provider remains current/connected.

Owner: **R02-L04** together with R02-F03 because both are one provider-lifecycle invariant and must not be implemented as two competing state machines.

### R02-F05 — Lot10 central portfolio fail-open execution

The current central execution gate contains an explicit legacy compatibility path:

```python
record = session.get(SourcePortfolioRecord, source_id)
if record is None:
    return True
```

That contradicts the intended final state of Lot10: the machine-readable central source portfolio must be the authority for whether a source is executable. Bootstrap synchronization exists and is retained, but absence from the portfolio must not silently restore legacy execution.

Owner: **R02-L05**.

### R02-F06 — Lot10 cross-module convergence residual

Lot10 historically requires backfill/incremental convergence and correction/deletion/retraction behavior. A later cross-module audit proved that full downstream derived-state propagation/invalidation is still non-final. That residual is already explicitly assigned to **Lot28 / issue #171**.

R02 records this as `owned_by_existing_later_scope`; it must **not** implement another outbox/reconciliation architecture.

## Explicit non-findings

### Lot06 is not reopened for immediate tombstones

The Greenhouse collector fingerprints observations but still emits the current commercial projection for each active relevant posting. Therefore successful collection refreshes the mutable signal/expiry without duplicating the raw observation. A job absent from the provider result is no longer projected/refreshed and ages out under the bounded TTL.

That satisfies the Lot06 bounded-expiry/current-refresh contract. R02 does not invent an immediate Greenhouse-specific tombstone requirement. Cross-module withdrawal/invalidation finality remains Lot28 where applicable.

### Lot08 safe auto-confirmation is not reopened

The audited organization-identity foundation preserves identity/evidence linkage and guards automatic attachment. Exact official identifiers are the auto-confirm boundary; ambiguous/conflicting/name-only candidates remain review paths. R02 therefore does not invent a fuzzy-matching defect.

Later temporal corporate-graph merge/split/invalidation behavior remains owned by later identity/graph and Lot28 finality work, not by a duplicate Lot08 recovery mechanism.

### Lot10 adapter projection construction is not itself a direct-write violation

Historical Lot10 forbids adapters from writing companies/signals/scores/alerts/opportunities directly. Current adapters construct typed `CommercialProjection` values but persistence is performed centrally by collection orchestration. R02 interprets the original boundary as prohibiting adapter-owned database writes and cross-module infrastructure shortcuts, not prohibiting typed application output values.

If later architecture work replaces legacy commercial projection construction with canonical-change reconciliation, that is Lot28 ownership.

## Ownership boundary

R02 owns only the defects that can be corrected without duplicating a later canonical architecture:

- R02-L02 — cross-ATS duplicate decision/grouping contract;
- R02-L03 — provider-specific connectivity verification;
- R02-L04 — provider onboarding legal transitions + rotation/expiry/reverification;
- R02-L05 — fail-closed central portfolio authority;
- R02-L06 — adversarial terminal qualification.

R02-L01 is the executable ownership/audit guard that protects this registry.

Existing later owners remain:

- Lot28 / #171 — cross-module derived-state propagation, invalidation, desired-set reconciliation and backfill/incremental/replay convergence;
- Lot29 / #6 — lockfiles, SBOM, release provenance and repository protection;
- Lot30 / #169 — DNS/address safety and broader resilience;
- Lot31 / #5 — privacy rights, deletion propagation and non-resurrection;
- SA20/current activation successor — provider-specific controlled live proof when runtime implementation already exists and only activation proof is missing.

## Recovery rules

Every R02 finding must end with exactly one of:

- `implemented_proven_here`;
- `owned_by_existing_later_scope`;
- `terminal_already_proven`;
- `explicitly_excluded`.

The following are forbidden terminal dispositions:

- `later`;
- `future_hardening`;
- `manual`;
- `blocked`;
- `not_currently_called`;
- `works_in_test`.

## Terminal closeout gate

`docs/lots/LOTS_06_10_FINALITY_RECOVERY_CLOSEOUT.md` must **not** be created by this documentation-only scope lock.

It may be created only after the runtime corrections are implemented and R02-L06 proves on one exact final SHA:

1. the machine-readable finding registry has no orphan or placeholder;
2. cross-ATS dedup is conservative, deterministic, durable and reversible;
3. authenticated provider `CONNECTED` state requires the correct bounded verification contract;
4. illegal onboarding transitions fail before mutation;
5. expiration/rotation/reverification cannot leave stale authorization presented as current;
6. missing portfolio state fails closed for all execution entry points;
7. no R02 code duplicates Lot28–31 or SA20 ownership;
8. migrations are reversible;
9. architecture, backend, frontend, security, replay and regression suites pass on the same exact head;
10. unresolved review threads are zero and the final head is merge-qualified.
