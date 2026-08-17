# Lot 31 — Privacy rights, lawful-basis operations, and deletion propagation

## Status

`PLANNED_LOCKED`

## Ownership amendment

Lot 31 was originally reserved for an isolated browser and download-quarantine runtime. That implementation scope was subsequently delivered through the merged SA-16 browser/authentication programme, including bounded Chromium execution, governed request interception, typed browser actions, screenshots, controlled downloads, quarantine, delegated identities, session reuse, OAuth/OIDC/SSO, and durable human checkpoints.

The original Lot 31 browser scope therefore no longer needs a second product implementation. Because Lot 31 was never completed as a product lot, this roadmap amendment reassigns its still-unimplemented product slot to the largest remaining normal-lot orphan discovered by the post-SA16 audit: end-to-end privacy rights and deletion/correction propagation.

This reassignment does not rewrite any completed lot number. Historical Lot 12 and old issue references remain audit evidence of the earlier deferral; `docs/PRODUCT_LOT_ORPHAN_RECONCILIATION.md` records the handoff.

## Primary business outcome

Make privacy rights operational end to end so a lawful request, correction, objection, restriction, or deletion is tracked, enforced, propagated, auditable, replay-safe, and unable to be silently undone by later ingestion, projection rebuild, export, cache refresh, or backup restoration.

## Dependencies

- Lots 01–02 for canonical persistence, retention, durable jobs, and replay;
- Lots 08–10 for identity, provider onboarding, source governance, and source runtime;
- Lots 20–22 for resolved entities, professional context, contacts, and conditional providers;
- Lots 26–30 for commercial operations, lineage/publication gates, repository controls, backup/restore, and operational recovery;
- deployment-specific legal and data-protection decisions for supported jurisdictions and channels.

## Deliverables

### Processing-purpose and lawful-basis registry

- machine-readable processing purposes and data categories;
- lawful-basis state by source, purpose, jurisdiction, and communication channel;
- documented legitimate-interest assessment references where that basis is used;
- retention, minimization, transfer, and recipient constraints;
- explicit handling for sources or fields whose licence or law restricts correction/export/deletion behavior.

### Rights-request workflow

- persisted request identity, type, scope, jurisdiction, received time, due time, owner, status, decision, and completion evidence;
- supported workflows for access, rectification, erasure, objection, restriction, and export/portability where legally applicable;
- proportionate requestor-verification state without storing unnecessary verification material;
- protected control-plane API and analyst/privacy-operator UI;
- SLA timers, escalation state, overdue reporting, and incident handoff.

### Suppression and non-resurrection

- stable privacy/suppression keys sufficient to prevent re-ingestion without retaining deleted personal content;
- suppression checks before ingestion, identity resolution, projection publication, export, and outreach-related use;
- correction propagation to canonical records and every derived projection;
- deletion or restriction propagation to PostgreSQL records, read models, search/index/cache layers, generated exports, CRM/engagement projections, and other product-owned copies when those components exist;
- invalidation/recomputation of derived signals, hypotheses, scores, opportunities, contact recommendations, and saved analyst views when their underlying personal data is corrected, restricted, or deleted;
- no deleted payload copied into audit logs, tombstones, dead letters, metrics, traces, or support artifacts.

### Provider and connector propagation

- connector-aware deletion/correction propagation where an approved provider contract supports it;
- local deny/suppression state when an upstream provider cannot be mutated;
- revocation and reauthorization interaction defined for account-bound sources;
- retry-safe propagation with durable per-destination status and no false global completion.

### Restore and replay safety

- suppression/rights state restored before ordinary collection resumes after backup recovery;
- deterministic reapplication of deletions and restrictions after restore;
- backfills, historical replay, re-resolution, or projection rebuilds cannot resurrect suppressed data;
- race handling when a deletion/correction overlaps an in-flight collection or worker transaction.

### Jurisdiction and audit operations

- explicit jurisdiction/channel matrix for supported deployments, including transfer constraints where applicable;
- request chronology and operator actions retained without preserving deleted personal payloads;
- measurable processing times and overdue state;
- operator runbooks for request handling, failed propagation, restoration, and privacy incidents;
- evidence sufficient to prove completion and destination status without reintroducing erased data.

## Required tests

- a deleted contact or person does not reappear after fresh ingestion, historical backfill, identity-resolution replay, projection rebuild, or backup restore;
- correction updates canonical and derived read models and invalidates stale outputs;
- restriction/objection prevents prohibited downstream use without inventing deletion when deletion was not requested;
- export, cache/index, engagement, and CRM-style projections are invalidated or updated consistently;
- concurrent collection and deletion cannot commit a resurrected current projection;
- partial downstream propagation remains visibly incomplete and retryable instead of reporting false success;
- suppression state is applied before workers resume after restore;
- audit records contain request/action metadata but not deleted personal payloads;
- deadlines, escalation, authorization, roles, and protected API/UI boundaries are enforced;
- provider revocation, unavailable deletion APIs, and retry exhaustion fail closed;
- full migration, architecture, backend, frontend, security, privacy, and regression gates pass on one exact final head.

## Non-goals

- inventing legal conclusions for unsupported jurisdictions;
- retaining extra identity documents merely to prove a request occurred;
- claiming deletion from an upstream provider when only local suppression was possible;
- weakening immutable technical provenance for non-personal records that can lawfully remain, provided deleted personal content is not retained;
- autonomous external communication.

## Exit gate

Lot 31 is complete only when a rights request can be accepted, tracked, decided, propagated across every applicable product-owned destination, verified, and closed; corrected/restricted/deleted personal data cannot silently reappear through ingestion, replay, restore, projection rebuild, cache/index refresh, export, or commercial workflow; and the audit trail proves what happened without retaining the deleted payload itself.
