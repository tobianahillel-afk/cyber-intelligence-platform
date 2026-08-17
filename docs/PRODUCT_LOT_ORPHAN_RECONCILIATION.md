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

| Historical residual | Audit result | Final owner | Required disposition |
| --- | --- | --- | --- |
| end-to-end privacy rights, rectification, objection/restriction, erasure and propagation | real unfinished product capability | **Lot 31** | dedicated implementation before controlled pilot |
| DNS-resolution pinning / DNS rebinding protection | real network hardening residual | **Lot 30** | mandatory outbound-network security gate |
| Starlette/TestClient deprecation and dependency migration | already assigned | **Lot 29 / issue #6** | keep open until dependency/release hardening closes it |
| isolated Chromium + download quarantine deferred by early lots | subsequently implemented | **SA-16** | do not reimplement; close historical issue #3 as completed/superseded |
| Lot 23 tracking issue #61 | implementation already merged via PR #62 | historical tracking only | close as completed |
| Lot 24 shown as planned in authoritative roadmap/README | stale documentation | current product docs | mark Lot 24 `IMPLEMENTED_VALIDATED`; next sequential product lot becomes Lot 25 |

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

## Why DNS hardening belongs to Lot 30

Lot 12 recorded DNS-resolution pinning as a future hardening topic. SA-16 added strong hostname/origin/path/request controls but did not explicitly make DNS-rebinding resistance a terminal certified capability.

Lot 30 already owns resilience, recovery, operational failure handling, and collection/runtime observability. The remaining DNS/address-safety property is therefore attached to Lot 30 rather than creating another out-of-sequence product lot.

Canonical amendment: `docs/lots/LOT_30_NETWORK_HARDENING_AMENDMENT.md`.

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

Disposition: **close as completed/superseded by SA-16**.

The issue must not stay open as if browser execution were absent. Any remaining DNS/address-safety work is tracked separately under Lot 30 and is not evidence that the browser runtime itself still needs reimplementation.

### Issue #5 — privacy rights and deletion propagation

Disposition: **keep open and rename/annotate as Lot 31 ownership**.

It becomes the implementation tracker for the dedicated Lot 31 privacy scope.

### Issue #6 — repository hardening / lockfiles / release provenance

Disposition: **keep open under Lot 29**.

The historical Starlette/TestClient deprecation warning is already attached to this dependency-hardening stream and is not orphaned.

### Issue #61 — Lot 23 governed research

Disposition: **close as completed**.

PR #62 merged Lot 23 with exact-head CI evidence. Keeping #61 open incorrectly suggests the product capability is still unfinished.

## Authoritative roadmap corrections

`docs/PROJECT_DELIVERY_PLAN.md` must reflect:

- Lots `00–24` are the contiguous `IMPLEMENTED_VALIDATED` product prefix;
- Lot 24 is not `PLANNED_LOCKED` anymore;
- Lot 25 is the next sequential normal product implementation lot;
- Lot 30 explicitly owns DNS pinning/rebinding and outbound address safety;
- Lot 31 is the dedicated privacy-rights/deletion-propagation lot, not a second browser implementation;
- Lot 32 depends on all mandatory Lots 00–31 and cannot use privacy rights merely as a pilot-time test for a capability that was never implemented.

The README/current-baseline summary should carry the same status truth.

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
