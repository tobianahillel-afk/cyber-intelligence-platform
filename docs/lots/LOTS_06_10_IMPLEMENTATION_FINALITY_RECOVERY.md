# Lots 06–10 implementation finality recovery

Status: **FINAL_AUDIT_COMPLETE_IMPLEMENTATION_PENDING**  
Recovery overlay: **R02**  
Tracking issue: **#175**  
Audited baseline: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`  
Second adversarial pass: **2026-08-18**

## Purpose

R02 reopens the original acceptance contracts of historical Lots 06–10 against the current ordinary runtime. Historical merge status and CI are evidence, not terminal proof. The second pass additionally traced adapter configuration through canonical mapping, central persistence, opportunity generation, onboarding state, source-portfolio authorization, incremental worker and backfill worker.

R02 is a recovery overlay; it does not renumber the normal product roadmap.

## Historical scope after the second pass

| Historical lot | Tracker | R02 disposition |
|---|---:|---|
| Lot06 | #21 | Historical core terminal; preserve bounded expiry/current refresh |
| Lot07 | #23 | Two local gaps: F01 durable reversible inter-ATS dedup; F07 resolved-organization binding |
| Lot08 | #25 | Internal identity foundation terminal; its authority must be consumed by Lot07 integration |
| Lot09 | #27 | Three local gaps: F02 connectivity, F03 legal transitions, F04 expiry/rotation/reverify |
| Lot10 | #29 | Two local critical gaps: F05 fail-closed portfolio, F08 onboarding→execution authority; F06 remains Lot28 |

## Final finding set

### R02-F01 — Lot07 durable/reversible inter-ATS dedup — HIGH — R02-L02

`CanonicalPublicJob.exact_cross_provider_match()` is only an in-memory exact predicate. The ordinary path does not persist a durable, reviewable, replay-stable duplicate decision/group/rejection/split. Lot07 explicitly requires prudent and reversible inter-ATS deduplication.

### R02-F02 — Lot09 provider-specific connectivity verification — HIGH — R02-L03

Authenticated verification currently proves that required secret references resolve, not that the provider accepts credentials/scope or is reachable under the approved verification contract. `CONNECTED` must require a bounded provider-specific verification success for authenticated providers.

### R02-F03 — Lot09 legal lifecycle transitions — HIGH — R02-L04

`_transition()` directly assigns the requested target. An explicit legal previous→next graph must reject invalid transitions before mutation and before a success audit entry.

### R02-F04 — Lot09 expiry/rotation/reverification — HIGH — R02-L04

`expires_at` and `last_verified_at` exist, but the control surface does not implement a complete rotation/expiry/reverification lifecycle bound to the current secret-reference revision. Rotation must invalidate old verification and expiry must remove current authorization semantics.

### R02-F05 — Lot10 fail-closed portfolio authority — CRITICAL — R02-L05

`source_execution_allowed()` explicitly returns `True` when `SourcePortfolioRecord` is absent. This legacy compatibility path contradicts the terminal architecture in which every executable source is governed by the central machine-readable portfolio.

### R02-F06 — Lot10 derived-state convergence residual — CRITICAL — Lot28/#171

This is real but already owned by Lot28: global backfill/incremental/replay convergence plus correction/retraction/expiry propagation. R02 must not build a second outbox/reconciliation system.

### R02-F07 — Lot07 ATS identity-authority integration — HIGH — R02-L02

The second pass proves an integration defect, not a Lot08-internal defect:

1. Greenhouse/Lever/SmartRecruiters registries carry a provider-local `id` plus canonical display name but no resolved Lot08 organization binding.
2. Mappers pass that local `id` as `CanonicalPublicJob.organization_key`.
3. `CanonicalPublicJob` derives a canonical `organization_id` from that key and constructs an `Organization` from the configured name.
4. `persist_commercial_projections()` upserts that `Organization`, persists evidence/signal and can generate an opportunity.
5. The Greenhouse integration test deliberately demonstrates this path by creating `Example Security` from the board registry.

This means the ordinary ATS path has no enforced proof that the organization used for aggregation/dedup/opportunity generation is a safely resolved canonical identity.

**Final choice:** ATS configuration must reference an existing resolved canonical organization or an explicit identity-resolution binding/decision. A provider tenant/board/company identifier may remain source identity but may not silently mint legal organization identity. Ambiguous identity remains review-required. No fuzzy auto-merge is introduced.

### R02-F08 — Lot09/Lot10 authorization split-brain — CRITICAL — R02-L05

Provider onboarding and Source Portfolio currently maintain independent authorization state:

- onboarding owns state, secret references, `expires_at`, `last_verified_at`, failure/revocation;
- portfolio owns execution status, its own `authorization_expires_at`, freshness/quota/cost;
- incremental and backfill workers call `source_execution_allowed()` before `collect()`;
- that gate consults portfolio state, not the current onboarding authorization record.

Historical Lot10 explicitly requires the composed chain `catalogue -> onboarding -> ... -> disable` and automatic stop at authorization expiry.

**Final choice:** keep onboarding as credential/authorization truth and portfolio as the single runtime execution authority, but make the portfolio verdict consume the current onboarding authorization state. Every network-capable execution path must deny revoked/expired/failed/rotated-but-unverified authorization and revalidate eligibility immediately before provider network. This is an execution-authority bridge, not a Lot28-style global event/reconciliation framework.

## Explicit non-findings

### Lot06 immediate tombstones are not invented

Active unchanged jobs refresh their mutable projection/TTL while observations stay fingerprint-gated. Removed jobs stop refreshing and age out. Global downstream withdrawal finality belongs to Lot28.

### Lot08 internals remain terminal

The identity module remains conservative and evidence-bound. R02-F07 says the ATS path fails to prove it consumed that authority; it does not weaken Lot08 or reopen it as a fuzzy matching project.

### Backfill does use the common execution guard

The second pass inspected `run_backfill_once()` and `_claim_partition()`: backfill calls `source_execution_allowed()`. Therefore R02 does not invent a separate finding claiming that backfill totally bypasses portfolio gating. F05/F08 instead require that the shared gate be correct and revalidated before network.

### Typed CommercialProjection is not a direct-write violation

Adapters may construct typed projection values; central orchestration/persistence owns database writes. F07 concerns identity authority at that central boundary, not adapter-owned SQL.

## Ownership boundary

- R02-L01 — executable finding/ownership registry guard.
- R02-L02 — F01 + F07: public-job duplicate decisions and resolved organization binding.
- R02-L03 — F02: provider-specific connectivity verification.
- R02-L04 — F03 + F04: one legal onboarding lifecycle including expiry/rotation/reverification.
- R02-L05 — F05 + F08: one fail-closed execution authority composing portfolio + onboarding truth.
- R02-L06 — adversarial exact-head qualification and eventual closeout.

Existing owners remain Lot28/#171, Lot29/#6, Lot30/#169, Lot31/#5 and SA20 for their already assigned capabilities.

## Terminal closeout gate

`docs/lots/LOTS_06_10_FINALITY_RECOVERY_CLOSEOUT.md` must not be created yet. It is allowed only after runtime fixes are implemented and one exact final SHA proves:

1. all eight findings have exactly one disposition/owner;
2. F01 durable/reversible conservative dedup works under replay/concurrency/correction;
3. F07 ATS projection cannot mint canonical organization identity without a resolved/reviewed binding;
4. F02 authenticated CONNECTED requires provider verification;
5. F03/F04 legal transitions, rotation, expiry and reverify are enforced;
6. F05 missing portfolio state fails closed everywhere;
7. F08 revoked/expired/failed/rotated-unverified onboarding state blocks every network execution path, including already queued work;
8. F06 still points solely to Lot28 unless Lot28 has independently completed it;
9. migrations, architecture, backend, frontend when touched, security, replay/concurrency and full regression gates are green on the same head;
10. unresolved review threads are zero and exact-head CI is green.
