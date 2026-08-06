# Project Delivery Plan

## Purpose

This document is the authoritative production roadmap for Cyber Intelligence Platform.

The product is a standalone cyber revenue-intelligence and commercial-operations system. Its purpose is not to accumulate the largest possible volume of OSINT records. Its purpose is to discover organizations with evidence-backed cybersecurity needs, explain why they may need a service or product, identify the correct professional context, and let analysts manage the opportunity inside the platform.

A lot is complete only when one final commit passes every applicable backend, frontend, architecture, migration, security, privacy, source-governance, data-quality, documentation, and rollback gate.

## Status vocabulary

- `IMPLEMENTED_VALIDATED`: implementation passed its complete exit gate.
- `IN_PROGRESS`: implementation is active but not finally validated.
- `PLANNED_LOCKED`: scope, dependencies, non-goals, and exit criteria are defined; code has not started.
- `BLOCKED`: an external authorization, legal, product, or technical dependency prevents execution.
- `DEFERRED`: intentionally postponed without blocking later lots that explicitly exclude it.

## Delivery rules

- Lot numbers are continuous and never reused.
- Completed lot numbers are immutable.
- Each lot has one primary business outcome.
- Code for a new lot starts from the merged `main` commit of the previous implemented lot.
- Source governance and provider onboarding must be positive before network access.
- A source catalog entry is not an executable adapter.
- Provider payloads never write directly to company, score, alert, or opportunity tables.
- Evidence, claims, observations, resolved facts, service mappings, signals, hypotheses, and analyst decisions remain distinct.
- Global vulnerability knowledge never proves that an organization uses an affected product or is exposed.
- An attacker allegation, public incident claim, or IOC never independently proves that an organization was compromised.
- Duplicate reporting increases corroboration; it does not duplicate entities, incidents, signals, alerts, or opportunities.
- Corrections, retractions, suppression, deletion, and authorization expiry propagate to derived data.
- Historical backfills must not flood the current analyst Inbox.
- Public or licensed data is minimized. Credentials, victim files, private communications, private-life data, active prospect scanning, and access-control bypasses are excluded.
- Every commercial lot covers the canonical service taxonomy rather than treating SIEM or SOC as the default need.
- Any later commit invalidates an earlier validation result; the final pull-request head must pass all gates.

## Product delivery stages

- **Stage A — foundations and explicit intent:** lots `00–11`.
- **Stage B — broad company and cyber evidence:** lots `12–19`.
- **Stage C — resolution, professional context, and conditional sources:** lots `20–23`.
- **Stage D — commercial intelligence and analyst operations:** lots `24–27`.
- **Stage E — production assurance:** lots `28–32`.

## Status overview

| Lot | Outcome | Status |
| ---: | --- | --- |
| 00 | Product, legal, and source-governance foundation | `IMPLEMENTED_VALIDATED` |
| 01 | Modular core, persistence, provenance, and retention | `IMPLEMENTED_VALIDATED` |
| 02 | Durable scheduler, worker, checkpoints, and recovery | `IMPLEMENTED_VALIDATED` |
| 03 | Evidence-backed opportunity engine and analyst Inbox | `IMPLEMENTED_VALIDATED` |
| 04 | TED European procurement signals | `IMPLEMENTED_VALIDATED` |
| 05 | BOAMP French procurement and executable architecture gates | `IMPLEMENTED_VALIDATED` |
| 06 | Greenhouse public cyber hiring signals | `IMPLEMENTED_VALIDATED` |
| 07 | Lever and SmartRecruiters multi-ATS expansion | `IMPLEMENTED_VALIDATED` |
| 08 | French and European organization identity foundation | `IMPLEMENTED_VALIDATED` |
| 09 | Official provider onboarding and secret lifecycle | `IMPLEMENTED_VALIDATED` |
| 10 | Source portfolio runtime, backfill, freshness, and source health | `IMPLEMENTED_VALIDATED` |
| 11 | Procurement history, providers, contracts, and renewal timing | `IMPLEMENTED_VALIDATED` |
| 12 | Corporate public footprint, documents, search, and archives | `IMPLEMENTED_VALIDATED` |
| 13 | Vulnerability knowledge and exploitation-state reconciliation | `IMPLEMENTED_VALIDATED` |
| 14 | Live incidents, ransomware claims, and official confirmation | `IMPLEMENTED_VALIDATED` |
| 15 | Malicious infrastructure, phishing, IOC, and attack telemetry | `IMPLEMENTED_VALIDATED` |
| 16 | Passive exposure and technographic observations | `PLANNED_LOCKED` |
| 17 | Vendor advisories, product versions, and applicability | `PLANNED_LOCKED` |
| 18 | News, regulatory, corporate-disclosure, and change signals | `PLANNED_LOCKED` |
| 19 | Providers, customers, partners, and supply-chain relationships | `PLANNED_LOCKED` |
| 20 | Entity resolution and temporal corporate knowledge graph | `PLANNED_LOCKED` |
| 21 | Professional organization maps, contacts, and public community signals | `PLANNED_LOCKED` |
| 22 | Conditional, premium, LinkedIn, Discord, and BrixHub integrations | `PLANNED_LOCKED` |
| 23 | Analyst research and governed OSINT catalog orchestration | `PLANNED_LOCKED` |
| 24 | Signal fusion, need hypotheses, and commercial taxonomy | `PLANNED_LOCKED` |
| 25 | Advanced scoring, calibration, explainability, and feedback | `PLANNED_LOCKED` |
| 26 | Native commercial operations, alerts, tasks, and engagement | `PLANNED_LOCKED` |
| 27 | Complete company intelligence and analyst workspace | `PLANNED_LOCKED` |
| 28 | Data quality, reconciliation, lineage, and publication gates | `PLANNED_LOCKED` |
| 29 | Supply-chain, release provenance, and repository protection | `PLANNED_LOCKED` |
| 30 | Observability, performance, resilience, and recovery | `PLANNED_LOCKED` |
| 31 | Isolated browser and download-quarantine runtime | `DEFERRED` |
| 32 | Controlled pilot and production gate | `PLANNED_LOCKED` |

## Lot 00 — Product, legal, and source-governance foundation

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Executable source policies control owner, purpose, hosts, paths, data categories, automation, quota, retention, attribution, raw storage, review, authorization, and quarantine before any collector can use the network.

## Lot 01 — Modular core, persistence, provenance, and retention

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Modular domain boundaries, PostgreSQL persistence, reversible migrations, canonical organizations, evidence, observations, suppression, retention, UTC timestamps, and provenance envelopes are implemented.

## Lot 02 — Durable scheduler, worker, checkpoints, and recovery

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Versioned schedules, durable jobs, leases, transactional checkpoints, retries, circuits, dead letters, interruption recovery, and source-health metrics prevent duplicate collection and false success.

## Lot 03 — Evidence-backed opportunity engine and analyst Inbox

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Evidence-backed commercial signals, need hypotheses, explainable scores, analyst reviews, score overrides, API contracts, and an Inbox workspace support human qualification without autonomous outreach.

## Lot 04 — TED European procurement signals

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Governed TED Search API collection produces deterministic procurement observations, evidence, service-classified signals, and opportunities with replay-safe checkpoints and provenance.

## Lot 05 — BOAMP French procurement and executable architecture gates

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** BOAMP procurement expands French coverage while executable rules enforce module boundaries, complexity, file sizes, duplicate definitions, release consistency, and deterministic unit tests.

## Lot 06 — Greenhouse public cyber hiring signals

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** An explicit company-board registry drives bounded Greenhouse collection, canonical job observations, evidence, service-family classification, commercial signals, and opportunities.

## Lot 07 — Lever and SmartRecruiters multi-ATS expansion

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Lever and SmartRecruiters extend the public hiring path with registry-bound targets, strict schemas, deterministic mapping, replay safety, and cross-ATS deduplication contracts.

## Lot 08 — French and European organization identity foundation

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Recherche d'entreprises, GLEIF, and BODACC support legal units, establishments, groups, exact identifiers, aliases, source claims, conflicts, parent relationships, and review candidates without unsafe fuzzy merges.

## Lot 09 — Official provider onboarding and secret lifecycle

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Provider onboarding states, reviewed authorization, capability checks, secret references, audit history, revocation, rotation, expiry, and control-plane APIs govern official or licensed integrations.

## Lot 10 — Source portfolio runtime, backfill, freshness, and source health

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** A machine-readable source portfolio controls executable capability, historical partitions, incremental collection, freshness, quota, cost, quality, health, ablation value, and runtime reconciliation.

## Lot 11 — Procurement history, providers, contracts, and renewal timing

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** DECP, TED, and BOAMP records produce canonical procedures, publications, contracts, parties, service classifications, chronology, and renewal context without treating historical awards as current buying intent.

## Lot 12 — Corporate public footprint, documents, search, and archives

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Governed public-web collection provides immutable resources, versions, tombstones, bounded parsing, exact scope enforcement, quarantined search leads, protected APIs, and a Research workspace while real targets and search/archive providers remain separately authorized.

## Lot 13 — Vulnerability knowledge and exploitation-state reconciliation

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Version `0.14.0` provides canonical vulnerability records, exact aliases, immutable provider snapshots, CVSS and EPSS history, CWE, affected ranges, independent exploitation dimensions, reversible persistence, protected APIs, and a Vulnerabilities workspace. CISA KEV projects transactionally through the existing governed worker; additional provider mappings remain non-executable candidates. Global vulnerability data alone cannot infer organization exposure or create an opportunity.

## Lot 14 — Live incidents, ransomware claims, and official confirmation

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Version `0.15.0` provides canonical incident records, immutable source claim revisions, explicit allegation/report/official-confirmation/denial/correction/retraction states, independent-source and syndication controls, reviewable organization links, separated occurrence/discovery/publication/confirmation times, reversible persistence, protected APIs, and an Incidents workspace. Official, public-reporting, and licensed-ransomware schemas are installed behind non-executable source candidates. No threat-actor interaction, victim content, compromised credential, private communication, autonomous opportunity creation, or outreach path is included.

## Lot 15 — Malicious infrastructure, phishing, IOC, and attack telemetry

**Status:** `IMPLEMENTED_VALIDATED`

**Primary business outcome:** Normalize lawful public or licensed technical threat telemetry into time-bounded infrastructure and campaign context that supports defensive-service hypotheses without scanning prospects or treating an IOC as proof of compromise.

**Dependencies:** Lots 01–03, 10, 13, and 14.

**Deliverables:**

- canonical indicators, infrastructure observations, campaigns, malware families, confidence, first/last seen, expiration, and source history;
- IOC types for domains, IPs, URLs, hashes, certificates, email infrastructure, phishing kits, and C2 metadata;
- passive/provider telemetry only, with source-specific licences and retention;
- distinction among malicious, suspicious, historical, sinkholed, shared-hosting, and unknown states;
- campaign and malware links with explicit provenance;
- no active connection to malicious infrastructure and no malware download;
- protected search and timeline views;
- signal eligibility rules that require organization-specific authorized evidence before any company conclusion.

**Required tests:**

- indicator normalization and collision prevention;
- shared infrastructure and CDN false-positive handling;
- first/last seen and expiration;
- correction, sinkhole, and benign reclassification;
- duplicate feed convergence;
- no prospect scanning or direct malicious-host connection;
- backfill/incremental idempotence;
- migration, API, UI, and full regression gates.

**Exit gate:** Technical telemetry is searchable, historical, source-aware, and safe, but cannot independently label an organization compromised or exposed.

## Lot 16 — Passive exposure and technographic observations

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Build organization-linked passive exposure and technology observations from approved providers so analysts can identify reviewable product, cloud, certificate, DNS, ASN, and service context without active scanning.

**Dependencies:** Lots 08, 10, 13, 15, and organization identity contracts.

**Deliverables:**

- passive asset, hostname, certificate, DNS, ASN, cloud, service, port, product, and technology observations;
- exact observation time, provider, confidence, expiry, and historical state;
- organization-link confidence and review workflow;
- explicit distinction among technology mention, passive observation, version observation, affected version, and verified exposure;
- authorized provider adapters and cost/quota controls;
- suppression and opt-out handling;
- no active probes, exploitation, credential use, or access-control bypass;
- asset and technology views with provenance and freshness.

**Required tests:**

- shared hosting, CDN, reseller, subsidiary, and abandoned-domain false matches;
- certificate and DNS chronology;
- passive observation expiration;
- technology without version and version without vulnerability applicability;
- provider correction/deletion;
- organization-link review;
- no live-network unit tests or active scans;
- migration, API, UI, and full regression gates.

**Exit gate:** Passive observations are useful and reviewable while every exposure conclusion remains bounded by evidence, time, identity confidence, and source authorization.

## Lot 17 — Vendor advisories, product versions, and applicability

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Reconcile vendor advisories, product naming, version ranges, support status, fixes, mitigations, and applicability so vulnerability knowledge can be compared with organization-specific technology evidence without unsafe automatic conclusions.

**Dependencies:** Lots 13 and 16.

**Deliverables:**

- vendor, product, edition, component, platform, version, branch, support lifecycle, advisory, fix, and mitigation models;
- vendor PSIRT and official advisory sources;
- CPE, package, ecosystem, and vendor alias reconciliation;
- range-evaluation semantics with unknown and ambiguous states;
- superseded advisories and corrected ranges;
- applicability assessments that cite both vulnerability and organization technology evidence;
- review-required state for weak product/version matches;
- no active validation against prospect systems.

**Required tests:**

- product aliases and false product merges;
- inclusive/exclusive and open-ended version ranges;
- unknown versions and backported fixes;
- vendor correction and supersession;
- operating-system/distribution/package distinctions;
- evidence expiration and applicability withdrawal;
- no exposure conclusion without organization evidence;
- migration, API, UI, and regression gates.

**Exit gate:** Applicability is explainable and reversible, with exact evidence for the vulnerability side and the organization-technology side.

## Lot 18 — News, regulatory, corporate-disclosure, and change signals

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Detect material public changes that may create cyber needs while distinguishing original disclosures, regulation, reporting, commentary, and speculation.

**Dependencies:** Lots 08, 10, 12, 14, and 17.

**Deliverables:**

- canonical change events for acquisitions, leadership, funding, restructuring, geographic expansion, cloud or digital programs, regulatory action, breaches, audits, certifications, and public security commitments;
- source and article identity, publication/update times, syndication groups, quotes/excerpts within copyright bounds, and provenance;
- official filing, regulator, company, media, and analyst-source distinctions;
- contradiction, correction, and retraction processing;
- organization and event candidate links;
- service-family mappings kept separate from raw events;
- protected event search and timelines.

**Required tests:**

- syndicated duplicate stories;
- speculation versus official disclosure;
- correction/retraction propagation;
- event-date versus publication-date separation;
- company-name ambiguity;
- bounded excerpts and retention;
- historical backfill versus current urgency;
- migrations, API, UI, and regression gates.

**Exit gate:** Analysts can trace every corporate or regulatory change to original evidence and understand whether it is confirmed, reported, disputed, or stale.

## Lot 19 — Providers, customers, partners, and supply-chain relationships

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Build temporal, evidence-backed business and technology relationships that explain incumbents, dependencies, partners, customers, suppliers, integrators, auditors, insurers, and MSSPs.

**Dependencies:** Lots 08, 11, 12, 14, 16, and 18.

**Deliverables:**

- typed organization relationships with direction, role, start/end, confidence, source, and review state;
- provider/product/customer evidence from contracts, case studies, partner directories, disclosures, certificates, and approved sources;
- distinction among claimed, observed, contracted, historical, and inferred relationships;
- duplicate and contradiction handling;
- incumbent and renewal context for commercial analysis;
- no scraping of private customer portals or personal networks;
- relationship graph and chronology APIs/UI.

**Required tests:**

- direction and role correctness;
- historical versus active relationship;
- marketing claim versus contract evidence;
- parent/subsidiary and reseller ambiguity;
- contradiction and correction;
- false relationship prevention;
- migrations, API, UI, and full regression gates.

**Exit gate:** Relationship context is temporal and explainable and never presented as current fact without adequate evidence.

## Lot 20 — Entity resolution and temporal corporate knowledge graph

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Reconcile organizations, establishments, groups, brands, domains, products, incidents, assets, providers, and relationships into a temporal graph with reversible merge/split decisions.

**Dependencies:** Lots 08 and 11–19.

**Deliverables:**

- graph identifiers, node/edge types, temporal validity, source claims, and lineage;
- deterministic exact matching followed by explainable probabilistic candidates;
- analyst merge, reject, split, and override workflows;
- identity-conflict queues and blast-radius previews;
- propagation of corrections and suppression;
- graph read models without making the graph database the system of record by default;
- performance and consistency contracts.

**Required tests:**

- exact identifiers and alias chains;
- homonyms, rebrands, mergers, spin-offs, and reused domains;
- merge/split rollback;
- temporal edges and historical queries;
- correction propagation;
- false-merge benchmark fixtures;
- migrations, API, UI, and regression gates.

**Exit gate:** Every resolved entity and relationship exposes why it exists, when it was valid, and how to reverse an incorrect decision.

## Lot 21 — Professional organization maps, contacts, and public community signals

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Identify relevant professional roles, teams, public business contact channels, and consented community context without building private-life profiles or bypassing platform rules.

**Dependencies:** Lots 08, 12, 19, and 20 plus privacy controls.

**Deliverables:**

- professional role, team, reporting-line claim, business email pattern, switchboard, contact form, and public professional profile references;
- relevance to service families and opportunities;
- source, freshness, confidence, and employment-history transitions;
- lawful-basis, minimization, suppression, correction, and deletion handling;
- public community signals only through approved exports, APIs, or administrator-installed integrations;
- no private messages, friend graphs, personal addresses, or sensitive private-life data;
- organization map and contact review UI.

**Required tests:**

- same-name people and job transitions;
- stale employment and role changes;
- business versus personal contact separation;
- suppression and deletion propagation;
- public/community consent boundaries;
- no unauthorized LinkedIn or Discord automation;
- migrations, API, UI, and regression gates.

**Exit gate:** Analysts can find relevant professional context with source and freshness while privacy rights and platform authorization remain enforceable.

## Lot 22 — Conditional, premium, LinkedIn, Discord, and BrixHub integrations

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Provide a controlled framework for sources whose use depends on licence, account scopes, administrator consent, customer-provided access, or written authorization.

**Dependencies:** Lots 09, 10, 21, privacy controls, and repository hardening.

**Deliverables:**

- per-provider approval dossier covering method, scopes, fields, purpose, retention, licence, security, revocation, and cost;
- provider service identities and secret references;
- official LinkedIn API/licensed paths only;
- Discord administrator-installed connector, authorized export, or equivalent consented path only;
- BrixHub exact access-path and field review before any adapter exists;
- premium CTI and commercial providers through contract-bound capabilities;
- kill switch, quota, deletion, audit, and unique-value measurement;
- no fake accounts, copied cookies, CAPTCHA solving, ban evasion, or proxy rotation for bypass.

**Required tests:**

- missing/expired/revoked authorization;
- scope reduction and secret rotation;
- account isolation;
- deletion and correction propagation;
- quota and cost limits;
- provider outage and terms-change pause;
- unique commercial value against existing sources;
- migrations, API, UI, and regression gates.

**Exit gate:** A conditional source cannot execute until its exact approval dossier is positive, and disabling it immediately stops collection without corrupting existing provenance.

## Lot 23 — Analyst research and governed OSINT catalog orchestration

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Turn the broad OSINT catalog into human-operated, policy-aware research plans and evidence capture instead of unrestricted autonomous browsing.

**Dependencies:** Lots 10, 12–22.

**Deliverables:**

- research questions, plans, steps, allowed tools, budgets, approvals, results, and analyst decisions;
- source selection based on value, freshness, cost, quota, authorization, and risk;
- analyst links for search/dorks when automation is not approved;
- captured evidence through approved ingestion paths only;
- no unrestricted agent browsing, authenticated automation, or active probing;
- reproducible research history and handoff;
- orchestration UI with explicit manual-action states.

**Required tests:**

- denied tool before execution;
- budget and domain/path boundaries;
- analyst-link versus automated-provider distinction;
- evidence provenance and deduplication;
- interruption/retry without duplicate actions;
- no autonomous outreach or unsafe browsing;
- API, UI, and full regression gates.

**Exit gate:** Analysts can run reproducible governed research while every automated step remains bounded by an executable policy and authorization.

## Lot 24 — Signal fusion, need hypotheses, and commercial taxonomy

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Fuse independent evidence into explicit cybersecurity need hypotheses across the complete service taxonomy without collapsing weak observations into deterministic conclusions.

**Dependencies:** Lots 11–23 and the canonical service taxonomy.

**Deliverables:**

- executable service-family mappings and versioned rules;
- evidence independence and corroboration groups;
- contradiction, negative evidence, freshness, and expiry;
- need hypotheses with rationale, confidence, urgency, horizon, and applicable offers;
- separate raw evidence, signal, hypothesis, and analyst decision states;
- cross-service coverage beyond SIEM/SOC;
- explainable source contribution and ablation.

**Required tests:**

- positive, negative, ambiguous, stale, and contradictory fixtures;
- duplicate-source independence;
- multi-service classification;
- global vulnerability without organization applicability;
- historical incident without current urgency;
- rule-version replay and rollback;
- API, UI, and regression gates.

**Exit gate:** Every need hypothesis explains which independent evidence supports it, which evidence conflicts, and why a service family is or is not applicable.

## Lot 25 — Advanced scoring, calibration, explainability, and feedback

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Rank opportunities using calibrated, explainable, reviewable scores tied to measurable outcomes rather than opaque heuristics.

**Dependencies:** Lot 24 plus analyst outcomes from Lot 03.

**Deliverables:**

- versioned score components for intent, urgency, fit, confidence, freshness, corroboration, relationship, timing, and cost;
- calibration datasets and offline evaluation;
- analyst overrides and reasons;
- uncertainty and missing-data handling;
- service-specific and segment-specific calibration;
- drift, bias, and false-positive monitoring;
- score replay and comparison between versions.

**Required tests:**

- monotonic component behavior;
- contradictory and missing evidence;
- calibration and ranking fixtures;
- override audit and rollback;
- score-version reproducibility;
- no sensitive protected-class inference;
- API, UI, and regression gates.

**Exit gate:** A score is reproducible, calibrated against outcomes, decomposable into evidence-backed components, and overrideable by an analyst.

## Lot 26 — Native commercial operations, alerts, tasks, and engagement

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Manage the complete opportunity lifecycle inside the platform without requiring an external CRM and without autonomous outreach.

**Dependencies:** Lots 21, 24, and 25.

**Deliverables:**

- organizations, contacts, opportunities, stages, owners, teams, tasks, notes, reminders, alerts, assignments, and engagement history;
- saved searches and subscriptions;
- analyst-created outreach drafts and approval workflow;
- communication logging without sending automatically;
- SLA, snooze, reopen, rejection, duplicate, and closed-loop outcomes;
- role-based control-plane operations and audit history;
- reporting read models.

**Required tests:**

- state-machine transitions and permissions;
- duplicate opportunity handling;
- task/reminder chronology;
- engagement audit and deletion;
- no automatic send or contact enrichment bypass;
- concurrency and rollback;
- API, UI, and regression gates.

**Exit gate:** Analysts can operate an opportunity end to end with auditable human decisions and no autonomous external communication.

## Lot 27 — Complete company intelligence and analyst workspace

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Deliver Company 360 and analyst workflows that assemble identity, evidence, incidents, vulnerabilities, exposure, relationships, contacts, opportunities, and actions without losing provenance or uncertainty.

**Dependencies:** Lots 20–26.

**Deliverables:**

- Company 360 summary and timelines;
- identity, group, establishment, domain, asset, product, provider, incident, vulnerability, relationship, role, contact, signal, hypothesis, score, opportunity, task, and engagement sections;
- freshness, confidence, contradictions, review queues, and source lineage;
- analyst navigation from summary to exact evidence;
- bulk triage and saved workspace state;
- accessibility and responsive design;
- performance budgets for large companies.

**Required tests:**

- cross-module read consistency;
- stale and contradictory data presentation;
- permission and privacy boundaries;
- source-to-summary navigation;
- large-record performance;
- accessibility, typecheck, and production build;
- complete regression gates.

**Exit gate:** An analyst can understand one company and act on it without hidden provenance, duplicated facts, or unsupported certainty.

## Lot 28 — Data quality, reconciliation, lineage, and publication gates

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Prevent low-quality or inconsistent data from silently reaching analyst-facing projections.

**Dependencies:** Lots 20–27.

**Deliverables:**

- completeness, validity, uniqueness, consistency, timeliness, provenance, and contradiction metrics;
- source and field-level quality baselines;
- quarantine and publication gates;
- reconciliation queues and repair tools;
- lineage from source record to every derived projection;
- correction, deletion, suppression, and restore validation;
- data-contract dashboards and alerts.

**Required tests:**

- schema drift and malformed records;
- duplicate and conflicting data;
- quality-threshold publication blocking;
- correction/deletion lineage;
- restore and replay consistency;
- performance and regression gates.

**Exit gate:** Analyst-facing data has explicit quality status and traceable lineage, and failed quality gates cannot masquerade as current facts.

## Lot 29 — Supply-chain, release provenance, and repository protection

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Make builds and releases reproducible, reviewable, attestable, and protected against unauthorized repository changes.

**Dependencies:** Stable application and CI contracts from lots 00–28.

**Deliverables:**

- verified Python and npm lockfiles;
- deterministic clean installations;
- `npm ci` and locked Python installation in CI;
- Python and npm SBOMs;
- signed or attested release artifacts;
- dependency-update policy and lockfile review;
- protected `main`, required PR and checks, CODEOWNERS, resolved conversations, and force-push prohibition;
- secret scanning and available repository security controls;
- release, rollback, and secret-rotation runbooks.

**Required tests:**

- two clean builds resolve identical dependencies;
- lockfile tampering and dependency drift;
- SBOM generation;
- pinned GitHub Action SHAs;
- protected-branch behavior;
- release rollback rehearsal;
- full regression gates.

**Exit gate:** Every release has reproducible dependencies, provenance evidence, and repository protections preventing unreviewed changes.

## Lot 30 — Observability, performance, resilience, and recovery

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Operate collection, processing, APIs, and analyst workflows reliably under expected load and recover predictably from failure.

**Dependencies:** Lots 02, 10, 27–29.

**Deliverables:**

- structured logs, metrics, traces, dashboards, alerts, and SLOs;
- queue depth, lag, source freshness, error budgets, cost, quota, and projection latency;
- load and capacity baselines;
- backup, restore, disaster recovery, and suppression reapplication;
- worker crash, database interruption, provider outage, and partial-dependency recovery;
- runbooks and incident exercises;
- data-integrity checks after recovery.

**Required tests:**

- load and sustained scheduler/worker operation;
- lease expiry and crash recovery;
- database and provider interruption;
- backup/restore and suppression replay;
- alerting and SLO calculation;
- performance regressions;
- complete release gates.

**Exit gate:** Operational failure is observable, bounded, recoverable, and documented with measured recovery objectives.

## Lot 31 — Isolated browser and download-quarantine runtime

**Status:** `DEFERRED`

**Primary business outcome:** Provide a browser path only when approved structured APIs and bounded static HTTP cannot satisfy a reviewed source requirement.

**Dependencies:** Lots 09, 10, 23, 28–30 plus an approved browser-specific threat model.

**Deliverables:**

- isolated Chromium/Playwright workers;
- ephemeral profile and context per source/account;
- host/path allowlists and network interception;
- page, time, CPU, memory, and download budgets;
- login, MFA, CAPTCHA, anti-bot, and terms-change detection producing `manual_action_required`;
- quarantined downloads with MIME detection, hashes, size limits, archive controls, isolated parsing, kill switch, and cleanup;
- no CAPTCHA solving, copied cookies, fake accounts, proxy bypass, or ban evasion.

**Required tests:**

- local simulated application E2E;
- isolation between sources;
- network allowlist enforcement;
- challenge pause behavior;
- download quarantine and parser failure;
- browser crash and cleanup;
- complete security and regression gates.

**Exit gate:** The browser runtime remains disabled unless separately approved and cannot escape source, network, account, or download isolation.

## Lot 32 — Controlled pilot and production gate

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Validate the complete platform with a controlled set of authorized sources, organizations, analysts, and measurable commercial outcomes before general production use.

**Dependencies:** Lots 00–30 and Lot 31 only if explicitly activated.

**Deliverables:**

- pilot scope, users, organizations, sources, jurisdictions, and success metrics;
- data-protection, security, source-authorization, and operational sign-offs;
- analyst training and runbooks;
- precision, recall, false-positive, freshness, source-value, workflow, and commercial-outcome measurement;
- support, incident, rollback, and kill-switch procedures;
- final go/no-go review;
- controlled production configuration with no dormant candidate source activated accidentally.

**Required tests:**

- end-to-end authorized-source workflows;
- privacy rights and suppression;
- source revocation and kill switches;
- disaster recovery;
- role and permission tests;
- pilot metrics and acceptance thresholds;
- security, performance, and full regression gates.

**Exit gate:** Named owners approve a measured pilot result, all mandatory controls are operational, and production can be disabled or rolled back without data-integrity loss.

## Current release boundary

Version `0.16.0` includes lots `00–15`.

Lot 15 installs canonical threat-indicator knowledge, immutable source snapshots, explicit malicious/suspicious/benign/sinkholed/expired/historical/shared-infrastructure/unknown/retracted states, campaign and malware relations, reversible persistence, protected APIs, and the Threat Intelligence workspace. Selected STIX/TAXII, phishing, passive-DNS, certificate, and malware-metadata schemas are installed behind non-executable source candidates. The release does not authorize active prospect scanning, direct connections to suspicious infrastructure, malware or victim-file downloads, credential use, autonomous opportunity creation, or outreach. Global technical telemetry cannot independently label a named organization compromised or exposed.

Lot 16 must start from the merged Lot 15 `main` commit and must preserve the distinction among a technology mention, a passive observation, an observed version, vulnerability applicability, and verified exposure.
