# Source Integration and Commercial Value Test Matrix

## Purpose

This document defines the mandatory test path for every new source family. Parser coverage alone is insufficient. A source is releasable only when collection, normalization, resolution, signal generation, analyst presentation, correction, and business-value behavior are all proven.

It complements [`TEST_STRATEGY.md`](TEST_STRATEGY.md) and is mandatory for roadmap lots 10 through 28.

## Release-gate sequence

Every source adapter must pass the following gates in order.

### Gate 1 — Catalog and governance

Prove that:

- the canonical source identity is stable;
- owner, terms, licence, purpose, allowed fields, prohibited fields, retention, attribution, quota, and access mode are recorded;
- expired, quarantined, blocked, or unauthorized sources are denied before DNS or network access;
- a catalog candidate cannot execute merely because it appears in OSINT Framework or another list;
- source changes, redirects, ownership changes, or licence changes return the entry to review.

### Gate 2 — Onboarding and secrets

Prove that:

- public sources connect without a fake secret;
- authenticated sources use only approved secret references;
- raw passwords, tokens, API keys, cookies, and MFA secrets never enter API responses, logs, fixtures, analytics, Git, frontend state, or application tables;
- invalid scopes and expired authorization block collection;
- rotation, revocation, and source disablement stop future jobs;
- anonymous visitors cannot access onboarding or source-control operations.

### Gate 3 — Transport and provider schema

Prove that:

- only approved hosts, paths, methods, and content types are reachable;
- redirects cannot escape the allowlist;
- response bytes, records, pages, date windows, concurrency, and time are bounded;
- 401, 403, 404, 409, 429, and 5xx failures are typed;
- retries obey `Retry-After`, backoff, circuit, and retry budgets;
- provider errors encoded as HTTP 200 are detected;
- strict schemas reject unexpected or prohibited fields;
- schema drift creates a health failure rather than silent partial data.

### Gate 4 — Backfill and incremental convergence

Prove that:

- historical partitions are bounded and resumable;
- a killed worker resumes from the last committed checkpoint;
- a replay produces the same canonical result;
- incremental cursor, timestamp, ETag, Last-Modified, webhook, or delta modes converge with a complete backfill;
- mutable source records update instead of duplicating;
- tombstones, removals, corrections, and retractions propagate;
- historical imports do not create a burst of current alerts or duplicate opportunities.

### Gate 5 — Canonical mapping

Prove that:

- provider payloads remain inside adapter packages;
- source records are immutable and content-hashed;
- mapping is deterministic for identical input and mapper version;
- source time, event time, publication time, modification time, and retrieval time remain distinct;
- normalized output preserves provenance and source identifiers;
- prohibited fields are rejected before persistence;
- no adapter writes directly to opportunity, score, or company projection tables.

### Gate 6 — Entity and event resolution

Prove that:

- exact authoritative identifiers link deterministically;
- fuzzy matches create review candidates rather than silent merges;
- similar company names, subsidiaries, shared domains, CDN infrastructure, and renamed companies are represented in negative and ambiguous fixtures;
- incident victim matching handles aliases, groups, brands, countries, and ambiguous names;
- technology and provider aliases do not merge unrelated products;
- accepted merges and relationships can be reversed without losing history;
- false merges are measured and treated as more severe than missed automatic links.

### Gate 7 — Deduplication and contradiction

Prove that:

- repeated delivery from one source does not duplicate source records, observations, signals, alerts, or opportunities;
- several sources reporting one event increase corroboration rather than record count at the commercial layer;
- amendments update contract chronology;
- company denials, corrections, and retractions remain visible beside earlier claims;
- contradictory technology, role, provider, incident, and legal-status evidence is preserved;
- source independence is not inflated when several feeds copy the same upstream source.

### Gate 8 — Commercial signal and hypothesis

Prove that:

- each adapter output maps to documented commercial signal types or remains evidence-only;
- every signal includes evidence, dates, freshness, confidence, service fit, urgency, and explanation;
- stale evidence decays or expires;
- one source event cannot create several duplicate signals merely because it supports multiple services;
- weak public-community statements and unconfirmed actor claims cannot independently create a confirmed high-priority need;
- corrections and retractions recalculate or invalidate signals and need hypotheses;
- analyst overrides remain separate from generated baselines.

### Gate 9 — Opportunity behavior

Prove that:

- compatible hypotheses group into one commercial motion;
- evidence refresh preserves analyst stage, assignment, notes, and history;
- a material new event can reopen an appropriate alert without duplicating the opportunity;
- a source outage does not delete the last valid stored evidence;
- stale, disputed, retracted, and confirmed states affect priority correctly;
- suppression prevents a contact channel from being used in tasks, exports, or engagement workflows.

### Gate 10 — UI and analyst workflow

Prove loading, empty, partial, stale, conflicting, unavailable, unauthorized, suppressed, and success states for:

- Sources control plane;
- company timeline and evidence lineage;
- incident claims and confirmations;
- technology and vulnerability applicability;
- contract chronology and renewal estimate;
- public professional roles and contact channels;
- signal explanation and score components;
- source freshness and health;
- alert, task, and opportunity transitions.

The interface must not display raw provider payloads or secrets as a substitute for a canonical product experience.

### Gate 11 — Operational resilience

Inject:

- worker interruption;
- database restart;
- duplicate queue delivery;
- provider outage;
- quota exhaustion;
- malformed payload;
- parser version change during backfill;
- source record changing between pages;
- index failure;
- authorization expiry;
- partial projection failure.

Verify no lost checkpoint, false success, uncontrolled retry, duplicate opportunity, or corrupt published projection.

### Gate 12 — Commercial usefulness

Each source family needs a labelled benchmark measuring:

- organization-resolution rate;
- duplicate suppression rate;
- contradiction rate;
- stale-data rate;
- signal precision and recall;
- false-urgency rate;
- analyst acceptance, rejection, and snooze rates;
- unique accepted opportunities added beyond existing sources;
- cost per accepted opportunity;
- analyst time saved;
- conversion or downstream usefulness by signal type.

A source that adds volume but no reliable incremental value does not pass the product gate.

## Cross-source scenario matrix

### Procurement and contracts

Fixtures must cover:

- open notice followed by award;
- award followed by amendment;
- cancellation after publication;
- duplicate TED and national publication;
- buyer name without identifier;
- consortium and subcontractors;
- incumbent provider with uncertain end date;
- renewal estimate later corrected by an amendment;
- one contract containing several cyber service categories.

Expected outcome: one chronology, explicit current/historical states, and no duplicate opportunity.

### Corporate websites, documents, search, and archives

Fixtures must cover:

- sitemap and linked PDF containing the same statement;
- archived page contradicting a current page;
- changed job or technology page;
- canonical URL and tracking parameters;
- external CDN and third-party documentation host;
- public document with accidental secret-like content;
- unsupported file type or oversized response;
- robots or authorization state changing between runs.

Expected outcome: bounded evidence discovery, provenance, historical context, and no unrestricted mirroring or secret collection.

### Vulnerabilities and advisories

Fixtures must cover:

- CVE aliases across NVD, OSV, GitHub, CIRCL, and vendor advisory;
- conflicting CVSS;
- KEV addition and removal/correction;
- EPSS history;
- product family without exact version;
- exact affected, unaffected, and unknown ranges;
- superseded advisory;
- proof of concept without observed exploitation;
- observed scanning without confirmed compromise.

Expected outcome: precise vulnerability knowledge and qualified applicability, never an unsupported company vulnerability claim.

### Ransomware and incidents

Fixtures must cover:

- actor claim only;
- actor claim copied by several aggregators;
- company confirmation;
- company denial;
- regulator notice;
- victim alias matching a brand but not the legal entity;
- two companies with the same name;
- retracted or false attribution;
- old historical claim re-imported;
- published anonymized negotiation corpus.

Expected outcome: one event cluster with separate claims, confidence, chronology, and no victim files or private communications.

### IOC, phishing, and telemetry

Fixtures must cover:

- same IP or URL in multiple copied feeds;
- indicator reactivation;
- shared hosting;
- benign scanner classification;
- C2 expiration;
- BGP anomaly with no organization impact evidence;
- phishing domain targeting a brand;
- telemetry source with narrow sensor scope;
- source feed outage and late replay.

Expected outcome: contextual threat intelligence with expiry and scope, not automatic company compromise attribution.

### Passive exposure and technographics

Fixtures must cover:

- shared CDN or hosting IP;
- certificate covering unrelated tenants;
- stale service banner;
- product family versus exact version;
- provider disagreement;
- acquired domain;
- parked domain;
- asset ownership correction;
- observation disappearing on the next provider snapshot.

Expected outcome: time-bound hypotheses with ownership and version confidence.

### Professional roles and public communities

Fixtures must cover:

- current and former role conflict;
- two professionals with the same name;
- role mailbox versus personal email;
- suppression request;
- pseudonym with no public identity link;
- pseudonym explicitly linked by its owner to a professional profile;
- public product discussion without employer attribution;
- self-declared professional affiliation with independent corroboration;
- forum content copied across communities.

Expected outcome: professional context and weak leads without private-life profiling or unsupported employer technology claims.

### BrixHub and other conditional sources

Before executable tests exist, governance tests must prove the source remains disabled.

After approval, tests must cover:

- legitimate historical export import;
- partition resume;
- incremental delta convergence;
- provider schema drift;
- field allowlist and prohibited-field rejection;
- correction and deletion propagation;
- duplicate overlap with existing sources;
- source-specific commercial value compared with the existing portfolio;
- authorization and licence expiry.

## Required test artifacts per adapter

Every adapter pull request includes:

- source manifest;
- capability manifest;
- authorization fixture;
- minimum, representative, empty, pagination, drift, error, correction, and tombstone fixtures;
- golden canonical mapping;
- checkpoint and replay tests;
- cross-source duplicate fixtures where applicable;
- one source-to-signal scenario;
- one correction or retraction scenario;
- source health and freshness assertions;
- commercial value statement and benchmark plan;
- rollback and disablement instructions.

## CI placement

### Every pull request

- unit and property tests;
- parser fixtures and golden mappings;
- common adapter contracts;
- policy-before-network tests;
- migration cycle;
- architecture gates;
- line and branch coverage;
- frontend typecheck and build;
- dependency and secret scans.

### Main branch

- disposable PostgreSQL integration tests;
- end-to-end source-record-to-opportunity tests;
- frontend end-to-end workflows;
- complete deletion, correction, and suppression propagation;
- backfill and incremental convergence suites.

### Scheduled

- source-schema drift checks against approved sandboxes or published schemas;
- optional approved provider smoke tests;
- large backfill and performance benchmarks;
- source portfolio quality and incremental-value benchmarks;
- resilience and restore exercises;
- authorization-expiry and source-disablement drills.

## Definition of test-complete

A source lot is test-complete only when the final SHA proves:

- safe and authorized collection;
- deterministic canonical data;
- durable backfill and refresh;
- correct resolution, deduplication, conflicts, corrections, and retractions;
- explainable commercial signals and hypotheses;
- stable analyst workflows;
- measurable incremental client-finding value;
- complete repository quality gates.
