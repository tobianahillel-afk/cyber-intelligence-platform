# Product Lot Orphan Reconciliation

## Status

`OWNERSHIP_RECONCILED_PENDING_IMPLEMENTATION`

Audit date: 2026-08-17.

Baseline before this reconciliation: merged `main` commit `409e6ffedba931b749d5fb8140e4ded61ab817db`.

## Purpose

This document records the post-SA16 audit of normal product lots and prevents incomplete work from remaining hidden behind historical lot closeouts, generic "future hardening" language, stale roadmap status, or already-superseded issues.

The audit distinguishes:

1. a real unfinished product capability;
2. a technical hardening residual;
3. work already assigned to a later lot;
4. work subsequently implemented by the Source Activation programme;
5. stale issue/document tracking that no longer reflects runtime reality.

## Final ownership decisions

| Historical residual | Audit result | Final owner / tracker | Final disposition |
| --- | --- | --- | --- |
| end-to-end privacy rights, rectification, objection/restriction, erasure and propagation | real unfinished product capability | **Lot 31 / issue #5** | dedicated implementation before controlled pilot; issue kept open |
| DNS-resolution pinning / DNS rebinding protection | real network hardening residual | **Lot 30 / issue #169** | mandatory outbound-network security gate; issue open |
| Starlette/TestClient deprecation and dependency migration | already assigned | **Lot 29 / issue #6** | keep open until dependency/release hardening closes it |
| isolated Chromium + download quarantine deferred by early lots | subsequently implemented | **SA-16 / historical issue #3** | no reimplementation; issue #3 closed completed on 2026-08-17 |
| Lot 23 tracking issue #61 | implementation already merged via PR #62 | historical tracking only | issue #61 closed completed on 2026-08-17 |
| Lot 24 shown as planned in authoritative roadmap/README | stale documentation | current product docs | corrected to `IMPLEMENTED_VALIDATED`; next sequential product lot is Lot 25 |

## Why Lot 31 is reassigned

The original roadmap reserved Lot 31 for an isolated browser/download-quarantine runtime and marked it deferred. That product lot was never completed under its original number.

SA-16 later implemented and validated the browser/authentication acquisition layer as a separate Source Activation programme, including:

- sandboxed/disposable Chromium execution;
- static-to-browser fallback;
- governed request interception and host/path checks;
- bounded DOM/rendered JSON/XHR/script-state extraction;
- typed reviewed actions and form submission;
- screenshots;
- controlled downloads and private quarantine/parser reuse;
- delegated identities and secret references;
- reviewed username/secret login;
- session reuse/logout/revoke;
- OAuth2/OIDC/SSO with PKCE/state/nonce;
- durable human checkpoints for MFA/CAPTCHA/provider-security action;
- same-job restart/resume and replay safety.

Rebuilding those capabilities in normal Lot 31 would duplicate merged functionality and create competing security/runtime paths. Lot 31 is therefore reassigned, while still unimplemented, to the largest genuine normal-lot orphan: end-to-end privacy rights and deletion propagation.

No completed product lot number is changed or reused.

Canonical Lot 31 scope: `docs/lots/LOT_31_PRIVACY_RIGHTS_AND_DELETION_PROPAGATION.md`.

Implementation tracker: issue #5, renamed `Lot 31: privacy rights and deletion propagation` and deliberately kept open.

## Why DNS hardening belongs to Lot 30

Lot 12 recorded DNS-resolution pinning as a future hardening topic. SA-16 added strong hostname/origin/path/request controls but did not explicitly make DNS-rebinding resistance a terminal certified capability.

Lot 30 already owns resilience, recovery, operational failure handling, and collection/runtime observability. The remaining DNS/address-safety property is therefore attached to Lot 30 rather than creating another out-of-sequence product lot.

Canonical amendment: `docs/lots/LOT_30_NETWORK_HARDENING_AMENDMENT.md`.

Implementation tracker: issue #169, `Lot 30: DNS pinning and rebinding defense for outbound acquisition`.

Lot 30 must not close until static HTTP, browser-backed acquisition, authenticated flows, redirects/retries, and controlled downloads share an effective fail-closed address policy that prevents an authorized hostname from reaching a forbidden internal/non-public address through DNS change or interpretation tricks.

## Privacy handoff from historical issue #5

Issue #5 remains a real implementation backlog item. This reconciliation does not close it.

Its original requirements are now explicitly owned by Lot 31, including:

- processing-purpose and lawful-basis registry;
- legitimate-interest references by source/channel where used;
- rights request API/UI and operator workflow;
- correction, restriction/objection, and deletion propagation;
- PostgreSQL/read-model/cache/index/export/CRM-style destination handling;
- audit without retaining deleted payloads;
- non-resurrection after ingestion/backfill/replay;
- suppression reapplication after backup restore;
- measurable request deadlines;
- jurisdiction/channel/transfer matrix and operator runbooks.

Lot 28 still owns generic lineage/publication-quality mechanics and Lot 30 still owns restore/recovery mechanics. Lot 31 composes those capabilities into the end-to-end privacy-rights product workflow and is the single owner of completion.

## Historical issue disposition

### Issue #3 — isolated Chromium and download quarantine

Disposition: **closed as completed/superseded by SA-16** on 2026-08-17.

The browser capability is no longer represented as absent. The remaining DNS/address-safety work is tracked separately by Lot 30 / issue #169 and is not evidence that the browser runtime itself needs reimplementation.

### Issue #5 — privacy rights and deletion propagation

Disposition: **open under Lot 31**.

The issue was renamed `Lot 31: privacy rights and deletion propagation` and annotated with the canonical Lot 31 ownership handoff.

### Issue #6 — repository hardening / lockfiles / release provenance

Disposition: **open under Lot 29**.

The issue was annotated with the explicit Lot 29 ownership handoff. The historical Starlette/TestClient deprecation warning remains part of dependency-hardening scope and is not orphaned.

### Issue #61 — Lot 23 governed research

Disposition: **closed as completed** on 2026-08-17.

PR #62 had already merged Lot 23 with exact-head CI evidence. The open issue was stale tracking rather than unfinished implementation.

### Issue #169 — DNS pinning/rebinding

Disposition: **open under Lot 30**.

This new tracker owns the complete DNS/address-safety exit gate across static HTTP, browser-backed acquisition, authenticated flows, OAuth/token paths, redirects/retries/reconnects and controlled downloads.

## Authoritative roadmap corrections

`docs/PROJECT_DELIVERY_PLAN.md` now reflects:

- Lots `00–24` are the contiguous `IMPLEMENTED_VALIDATED` product prefix;
- Lot 24 is not `PLANNED_LOCKED` anymore;
- Lot 25 is the next sequential normal product implementation lot;
- Lot 29 explicitly owns the historical Starlette/TestClient dependency-maintenance path;
- Lot 30 explicitly owns DNS pinning/rebinding and outbound address safety;
- Lot 31 is the dedicated privacy-rights/deletion-propagation lot, not a second browser implementation;
- Lot 32 depends on all mandatory Lots 00–31 and cannot use privacy rights or DNS safety merely as pilot-time experiments for capabilities never implemented beforehand.

The README/current-baseline summary carries the same status truth and points provider activation claims to the separate Source Activation programme.

## Sequencing after reconciliation

Normal product implementation remains sequential:

```text
00–24  IMPLEMENTED_VALIDATED
  -> 25 advanced scoring/calibration
  -> 26 commercial operations
  -> 27 Company 360 / analyst workspace
  -> 28 data quality / reconciliation / lineage / publication gates
  -> 29 supply-chain / release provenance / repository protection
  -> 30 observability / resilience / recovery + DNS/address hardening
  -> 31 privacy rights / lawful-basis operations / deletion propagation
  -> 32 controlled pilot / production gate
```

Source Activation remains a separate execution/activation track. Its progress can satisfy or supersede a provider/runtime prerequisite, but it does not silently mark a normal product lot complete unless the product roadmap is explicitly reconciled as done here.

## No-orphan rule going forward

Every future closeout must classify each accepted limitation as exactly one of:

- owned by a named later product lot;
- owned by a named Source Activation lot;
- explicitly excluded by product/security/legal decision with rationale;
- terminally complete with evidence.

Phrases such as "future hardening", "later", "manual for now", "blocked", or "deferred" are not sufficient terminal ownership by themselves.

A lot closeout is not allowed to create a useful unfinished capability with no named owner, exit gate, and verification path.
