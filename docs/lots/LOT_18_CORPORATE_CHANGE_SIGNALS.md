# Lot 18 — News, regulatory, corporate-disclosure, and change signals

## Status

`IMPLEMENTED_VALIDATED` for release `0.19.0`, subject to the exact final pull-request head passing every repository gate before merge.

## Objective

Lot 18 creates a source-aware corporate and regulatory change-intelligence layer for material public events that may later contribute to cybersecurity need analysis.

The lot deliberately separates raw public change evidence from service mappings, commercial needs, opportunities, contacts, and outreach.

```text
public mention
!= independent corroboration
!= official confirmation
!= service need
!= opportunity
!= authorization to contact
```

## Canonical material-change model

The domain represents:

- acquisitions;
- leadership changes;
- funding;
- restructuring;
- geographic expansion;
- cloud and digital programs;
- regulatory actions;
- public breach disclosures;
- audits;
- certifications;
- public security commitments;
- other material public changes that do not fit a narrower category.

Each event has a deterministic `event_key` and a current read projection backed by immutable claim history.

## Source and claim semantics

Source classes are explicit:

- official filing;
- regulator or public authority;
- company disclosure;
- media reporting;
- analyst commentary;
- other approved metadata sources.

Claim types are also explicit:

- confirmation;
- report;
- speculation;
- dispute;
- correction;
- retraction.

Only an active confirmation from an official filing, regulator, or company source can provide official confirmation in this lot. Media or analyst reporting never becomes official confirmation simply because it is repeated.

## Syndication and corroboration

Republished or syndicated copies retain a common syndication identity.

Independent-source counts therefore use a corroboration key that prefers the syndication group when present. Ten copies of the same wire story count as one corroboration lineage, not ten independent sources.

Separate sources without a common syndication lineage can count independently, but independence alone does not upgrade reporting or speculation to an official confirmation.

## Temporal semantics

The lot preserves distinct timestamps for:

- event time;
- publication time;
- provider modification time;
- expiry or staleness time;
- persistence time.

Historical backfill is explicitly distinguishable from current-capable evidence. An old event imported today cannot silently acquire current urgency simply because it was newly collected.

All domain times are timezone-aware UTC. Persistence hydration normalizes backend-returned timestamps before rebuilding domain objects.

## Corrections, supersession, and retraction

Every source revision is immutable.

A newer record can explicitly supersede an earlier source record. The earlier snapshot remains available for chronology and audit but is removed from the current reconciliation set.

The current event projection can therefore move among:

- `under_review`;
- `speculative`;
- `reported`;
- `confirmed`;
- `disputed`;
- `corrected`;
- `retracted`;
- `stale`.

Corrections and retractions do not erase historical evidence.

## Organization resolution boundary

Organization links are explicit:

- `exact`;
- `candidate`;
- `review_required`;
- `unresolved`;
- `rejected`.

An exact link requires an organization identifier. Conflicting exact organization identities converge to `review_required` rather than forcing a merge.

Name-only claims are not silently treated as exact organization matches.

## Copyright and content minimization

The canonical change model stores metadata and bounded excerpts, not full articles.

The hard excerpt limit is 500 characters in both provider contracts and the canonical domain.

The lot does not implement:

- full-article copying;
- paywall bypass;
- authentication bypass;
- private-source access;
- browser automation to defeat publisher controls.

## Service-family mappings

A change event can have separate analyst-maintained service-family mappings containing:

- service family;
- rationale;
- mapping confidence.

These mappings live in their own persistence table and do not mutate the immutable raw evidence history.

A mapping is not a need hypothesis, score, opportunity, or instruction to contact the organization.

## Persistence

Migration `20260807_0018` creates:

- `corporate_change_events`;
- `corporate_change_claim_snapshots`;
- `corporate_change_service_mappings`.

Claim snapshots are immutable and content-addressed. Replays are idempotent. Current event projections are recomputed from the current claim set while preserving every historical revision.

The migration is required to pass:

```text
upgrade head -> downgrade base -> upgrade head
```

on PostgreSQL 17.

## Protected API

The deployment-protected control-plane API exposes persisted data only:

- `GET /v1/corporate-changes`;
- `GET /v1/corporate-changes/{event_key}`.

Filters include:

- event status;
- event type;
- claim type;
- source kind;
- organization-link status;
- organization identifier;
- official-confirmation state;
- historical-only state;
- bounded text query;
- bounded pagination.

A request never performs collection, browsing, provider access, or contact enrichment.

## Analyst workspace

The `/corporate-changes` workspace provides:

- a filterable material-change inventory;
- explicit event and publication chronology;
- confirmation, speculation, dispute, correction, retraction, staleness, and historical-backfill context;
- organization-link state;
- claim and independent-source counts;
- immutable evidence revisions with source links and bounded excerpts;
- syndication identity;
- separate service-family mappings;
- permanent evidence-boundary messaging.

## Provider candidates

Lot 18 registers three governed source families:

- official corporate disclosures;
- official regulatory change notices;
- licensed corporate-news metadata.

Every checked-in entry is:

- `draft` in source governance;
- `candidate` in the source portfolio;
- unauthorized for automated collection;
- without approved hosts or paths;
- unscheduled;
- without a registered runtime adapter;
- `executable: false`.

The common runtime loads their governance metadata so they are auditable, but cannot execute them.

## Safety boundaries

The module contains no path for:

- autonomous web browsing;
- paywall, CAPTCHA, MFA, authentication, or access-control bypass;
- private portal or private social-network access;
- active scanning or probing;
- credential use;
- exploitation;
- victim-file or stolen-data retrieval;
- full copyrighted article storage;
- contact enrichment;
- automatic opportunity creation;
- autonomous outreach.

Architecture tests forbid network clients, source adapters, opportunity modules, contacts, and outreach imports from the corporate-change module.

## Validation scope

The lot tests:

- official confirmation versus media speculation;
- syndicated duplicate reporting versus independent sources;
- source-class distinctions;
- correction and retraction supersession;
- immutable replay behavior;
- stale and historical evidence;
- event time versus publication/update time;
- organization ambiguity and conflicting exact links;
- bounded excerpt enforcement;
- provider-schema chronology;
- non-executable source governance;
- persistence and service-mapping separation;
- protected API list/detail behavior;
- metadata registration;
- frontend type checking and production build;
- reversible PostgreSQL migration;
- full repository regression and branch-aware coverage.

## Lot 19 handoff

Lot 19 must start from the exact merged Lot 18 commit on `main`.

It will add temporal provider, customer, partner, supplier, integrator, auditor, insurer, MSSP, and other supply-chain relationships while preserving distinctions among claimed, observed, contracted, historical, and inferred relationships.
