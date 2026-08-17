# Lots 06–10 implementation gap audit

Status: **FINAL_AUDIT_COMPLETE_IMPLEMENTATION_PENDING**  
Recovery: **R02**  
Issue: **#175**  
Baseline: `8d7184b8a6f494ceb407ab489d8971f4d015bab6`

## Audit method

For each historical lot this document compares the original issue contract with the present implementation and separates four classes:

1. proven historical capability;
2. current implementation-finality defect owned by R02;
3. residual already owned by a named later lot;
4. tempting but incorrect reopening that R02 explicitly rejects.

A historical test or helper is not terminal proof if the ordinary runtime does not enforce the same invariant.

---

## Lot06 — Greenhouse public hiring signals — issue #21

### Historical contract

Lot06 required approved public Greenhouse boards, bounded GET-only acquisition, strict schemas, in-memory HTML conversion, local cyber relevance, per-job fingerprints, deterministic organization/evidence/observation/job signal projection, mutable idempotent signals, bounded expiry, refresh of still-active ads, transactional opportunity projection, source governance and full tests.

### Current implementation proof

`src/cip/adapters/sources/greenhouse/collector.py`:

- authorizes each configured board before collection;
- validates the provider response;
- bounds job count;
- builds a current fingerprint set per board;
- emits a `RawObservation` only when a fingerprint is new/changed;
- still emits the mapped current projection for each relevant currently returned job.

`src/cip/adapters/sources/greenhouse/mapper.py` converts through the shared canonical public-job path.

`src/cip/adapters/sources/canonical_jobs.py` gives a deterministic provider/source record key, evidence identity, signal identity and bounded signal TTL.

### Final disposition

**No local R02 finding.**

A currently published unchanged job continues to refresh the mutable projection/expiry while avoiding duplicate observations. A removed job no longer receives a projection/refresh and therefore expires under the bounded TTL. That is consistent with Lot06's historical contract.

An immediate global invalidation of every downstream hypothesis/opportunity on source withdrawal is a different composed property and is owned by Lot28/#171.

---

## Lot07 — Lever + SmartRecruiters — issue #23

### Historical contract

Lot07 required:

- Lever and SmartRecruiters public APIs;
- a shared canonical public-job contract;
- provider-specific strict schemas/mappers/pagination;
- common cyber taxonomy;
- checkpoints for provider/site/job;
- new/modified/unchanged/removed semantics;
- mutable idempotent signals;
- **prudente et réversible** cross-ATS deduplication;
- health/schema-drift behavior;
- no candidate/private data.

Acceptance explicitly requires that cross-ATS dedup never auto-merge an ambiguous case.

### Current implementation proof

The shared `CanonicalPublicJob` abstraction exists and the ATS adapters use the shared public-job mapping path.

The canonical model exposes:

- `exact_match_candidate_key` derived from normalized organization key/title/location/department/employment type;
- `exact_cross_provider_match(left, right)` which refuses same-source comparisons and compares that exact key.

Provider/source-native evidence remains traceable because `source_record_key`, evidence IDs and commercial signal IDs include the source/provider identity.

### Gap R02-F01

The historical requirement is stronger than an in-memory equality predicate. The current canonical mapping path creates provider-scoped commercial facts and does not itself materialize a durable, reviewable and reversible duplicate-group decision.

The recovery implementation must therefore create one explicit source-local/canonical duplicate-decision contract. It must not erase either provider observation/evidence and must not turn fuzzy similarity into automatic merging.

Owner: **R02-L02**.

### Boundary with Lot28

R02-L02 owns the durable duplicate grouping/decision semantics for public jobs. Lot28 owns propagation of canonical changes into all later derived state. R02-L02 must expose a contract Lot28 can consume rather than adding a second cross-module reconciliation engine.

---

## Lot08 — organization identity foundation — issue #25

### Historical contract

Lot08 required separate legal-unit/establishment/brand/group identity, official identifiers, SIREN/SIRET/LEI validation, aliases, statuses, group relations, explainable candidates, exact-ID-only auto-confirmation, human review for ambiguous matches, source-level provenance/conflict retention, minimization/non-diffusion safeguards, reversible migrations and APIs/tests.

### Current implementation proof

The audited organization identity domain/application layer preserves distinct `OrganizationIdentity`, merge candidates and evidence-backed `IdentityProjection` values. `IdentityProjection` enforces internal consistency, including that at most one candidate may be `AUTO_CONFIRMED` and that such a candidate must correspond to the attached organization.

The current resolver/identifier surface previously audited in this pass validates official identifiers and keeps non-exact/conflicting candidates review-required.

### Final disposition

**No local R02 finding.**

R02 explicitly refuses to invent a generic “fuzzy matching” defect where the current boundary is already conservative.

Broader temporal merge/split, graph and reverse-invalidation semantics are later architecture and must remain with their existing later owners, including Lot28 where the missing property is cross-module reactive finality.

---

## Lot09 — provider onboarding and secret lifecycle — issue #27

### Historical contract

Lot09 explicitly requires:

- provider/source onboarding catalogue;
- auth modes and lifecycle states;
- exact human-action checkpoints;
- secret references only, never raw secrets;
- **reference validation and provider-specific connectivity testing**;
- **rotation, expiration, revocation, last verification and normalized errors**;
- invalid lifecycle transitions refused;
- blocked/quarantined providers not activatable;
- auditable verification/revocation;
- API/UI and reversible migrations.

### Proven current capability

The service persists only secret references, keeps audit records, supports start/human-checkpoint/reference registration/verify/revoke flows, distinguishes auth modes and blocked state, and has bounded/redacted secret-reference types.

### Gap R02-F02 — reference availability is not provider connectivity

`verify_provider_configuration()` calls `_verification_result()`. For authenticated non-manual providers, `_verification_result()` checks required references and `SecretReferenceResolver.is_available()`. If all references are resolvable it returns `CONNECTED`.

That proves the deployment can resolve a reference. It does **not** prove the provider endpoint is reachable, credentials/scopes are accepted, or the configured provider-specific verification contract succeeds.

Owner: **R02-L03**.

### Gap R02-F03 — transition graph is not enforced

`_transition()` assigns `record.state = target.value`, updates the timestamp and appends an audit entry. There is no explicit previous→target legality graph in that primitive.

The audit trail is useful but cannot substitute for rejection of an invalid transition before mutation.

Owner: **R02-L04**.

### Gap R02-F04 — expiry/rotation lifecycle is modelled but not operationally complete

`expires_at` exists and is surfaced by the domain mapping. Revocation clears it. The ordinary API exposes start, checkpoint, secret-reference registration, verify and revoke, but no complete rotate/expire/reverify operation is present in that control path, and verification does not use an expiry guard to prevent a stale `CONNECTED` state by itself.

This must be solved together with the transition graph so that rotation does not create a second lifecycle mechanism.

Owner: **R02-L04**.

### Safety boundary

R02-L03/L04 must not implement browser bypass, CAPTCHA/MFA bypass or DNS pinning. Browser/authenticated acquisition already has its own SA16 history; DNS/address safety is Lot30/#169. Provider probes must be explicitly approved, bounded, typed and policy-gated before network.

---

## Lot10 — source portfolio and unified collection runtime — issue #29

### Historical contract

Lot10 required a machine-readable source catalogue, non-executable candidates, adapter capability manifests, historical/incremental/conditional/webhook/entity/priority modes, immutable source records, bounded resumable backfills, transactional checkpoints, corrections/tombstones/retractions, freshness/health/circuits/quota/cost/schema drift, authorization expiry, protected suspend/resume/disable controls, value hooks and no adapter-owned direct writes into commercial projections.

Its exit gate required the complete chain:

`catalogue -> onboarding -> backfill -> refresh incremental -> source records -> freshness -> health -> disable`

### Proven current capability

The `source_portfolio` module contains distinct application services for catalog, backfill, backfill worker, execution, health, quality, records, priority and service operations. Bootstrap synchronization/reconciliation exists in the normal application startup path; the central portfolio is therefore not merely documentation.

### Gap R02-F05 — missing portfolio record is explicitly executable

`source_execution_allowed()` implements:

```python
record = session.get(SourcePortfolioRecord, source_id)
if record is None:
    return True
```

The docstring labels this as legacy behavior. This is useful for migration compatibility but non-terminal for Lot10: a source absent from the central authority can still execute.

Final behavior must be fail closed, with explicit migration/bootstrap validation for all existing adapters/schedules so that changing the default does not silently strand legitimate sources.

Owner: **R02-L05**.

### Residual R02-F06 — later-owned convergence

Lot10 originally includes backfill/incremental convergence and corrections/tombstones/retractions. The later platform-wide finality audit in issue #171 identifies that the historical backfill worker and incremental worker do not yet share the complete downstream projection/reconciliation contract, and that correction/retraction/expiry can leave derived state stale.

This is a real historical Lot10 residual but **not an R02 implementation item**. It is already a canonical Lot28 responsibility.

Disposition: `owned_by_existing_later_scope` → **Lot28/#171**.

### Non-gap: typed projections are centrally persisted

Current provider adapters may construct typed `CommercialProjection` output, but the collection worker owns persistence. R02 does not reinterpret the historical “no direct adapter write” test as banning typed output values. Adapter-owned SQL/database writes or cross-module infrastructure access would be a violation; typed outputs centrally persisted are not by themselves one.

---

## Cross-lot final registry

| ID | Lot | Severity | Owner | Status |
|---|---:|---|---|---|
| R02-F01 | 07 | high | R02-L02 | recovery_local |
| R02-F02 | 09 | high | R02-L03 | recovery_local |
| R02-F03 | 09 | high | R02-L04 | recovery_local |
| R02-F04 | 09 | high | R02-L04 | recovery_local |
| R02-F05 | 10 | critical | R02-L05 | recovery_local |
| R02-F06 | 10 | critical | Lot28/#171 | owned_by_existing_later_scope |

Lot06 and Lot08 have no current local recovery finding after this audit.

## No-orphan rule

R02-L01 must make this registry machine-checkable. A finding may not disappear from documentation merely because implementation becomes inconvenient. It must be implemented/proven, moved only to an already existing named owner with an explicit contract, terminally proven, or explicitly excluded with product/security/legal rationale.
