# Cyber Intelligence Platform

Cyber Intelligence Platform is a standalone cyber revenue-intelligence and commercial-operations system. It collects approved public or licensed evidence, resolves it into reviewable company and cyber context, converts that evidence into explainable cybersecurity need hypotheses, and lets analysts investigate, qualify, assign, and track potential clients.

The product is not a Salesforce, HubSpot, or external-CRM extension. It owns company intelligence, evidence, alerts, saved searches, professional organization maps, contacts, opportunities, tasks, notes, assignments, engagement history, and reporting.

The product is evidence-first. A material statement must expose its source, event and observation times, confidence, freshness, claim type, contradictions, and review history. An attacker allegation is not an official confirmation. A technology mention is not proof of deployment. A passive observation is not proof of vulnerability applicability or verified exposure. A vulnerability record is not proof of an affected installation. A global indicator is not proof that a named organization was compromised or exposed. Search-result metadata is a discovery lead, not independent corroboration.

## Product objective

The platform should answer:

- Which organizations show a current or emerging cybersecurity need?
- What independent evidence supports or contradicts that need?
- Is the signal explicit buying intent, urgency, transformation, renewal timing, product risk, provider displacement, or only a weak lead?
- Which services or products fit the evidence?
- Which professional roles and lawful business contact channels are relevant?
- What should a human analyst do next?

The product covers strategy and vCISO, audit, GRC, pentest, red and purple teaming, vulnerability management, SOC and MDR, incident response, resilience, IAM and PAM, cloud security, AppSec and DevSecOps, network security, data protection, supply-chain security, OT security, awareness, product integration, and cyber-insurance readiness.

Source breadth is useful only when it improves reliable client discovery. Sources that add records without unique commercial value should be deprioritized or removed.

## Current validated baseline

The current validated release is version `0.24.0`, covering lots `00` through `23`.

Implemented and validated capabilities include:

- source governance, authorization, retention, suppression, and provenance;
- PostgreSQL persistence and reversible Alembic migrations;
- durable scheduler, worker, checkpoints, retries, circuits, dead letters, and recovery;
- evidence-backed opportunities with analyst review and explainable score components;
- TED and BOAMP procurement signals;
- Greenhouse, Lever, and SmartRecruiters public hiring signals;
- French and European organization identity using Recherche d'entreprises, GLEIF, and BODACC;
- official provider onboarding and secret-reference lifecycle;
- common source-portfolio runtime, backfill, freshness, health, cost, and controls;
- DECP, TED, and BOAMP contract history, providers, and renewal timing;
- governed corporate public-footprint resources, immutable versions, tombstones, quarantined search leads, protected APIs, and the Research workspace;
- canonical vulnerability knowledge with aliases, immutable source history, CVSS, EPSS, CWE, affected ranges, exploitation dimensions, protected APIs, and the Vulnerabilities workspace;
- canonical public incident records with immutable claims, explicit allegation/report/confirmation/denial/correction/retraction states, syndication controls, protected APIs, and the Incidents workspace;
- canonical defensive threat indicators with deterministic normalization, immutable source history, conflicting classifications, sensor scope, campaign/malware/CVE relations, protected APIs, and the Threat Intel workspace;
- canonical passive assets and technographic observations with immutable revisions, explicit attribution risks, protected APIs, and the Passive Exposure workspace;
- canonical vendor advisories, affected-version ranges, organization-specific vulnerability applicability, immutable assessment history, protected APIs, and the Vulnerability Applicability workspace;
- source-aware corporate and regulatory change intelligence with immutable claim history, syndication-aware corroboration, explicit confirmation/report/speculation/dispute/correction/retraction states, separate service mappings, protected APIs, and the Corporate Changes workspace;
- temporal provider, customer, partner, supplier, reseller, integrator, auditor, insurer, MSSP/MDR, cloud-provider, technology-vendor, and subcontractor relationship intelligence with immutable evidence history, explicit evidence classes, reversible chronology, protected APIs, and the Relationships workspace;
- temporal entity-resolution and corporate-graph intelligence with immutable node/edge history, exact alias/identifier/domain references, review-only probabilistic candidates, historical queries, reversible analyst decisions, versioned blast-radius previews, protected APIs, and the Graph workspace;
- governed professional-context intelligence with source-qualified people references, temporal roles and direct reporting lines, public business contact channels, consented community metadata, lawful-basis and retention controls, HMAC-backed erasure, protected APIs, and the Professional Context workspace;
- conditional-provider governance with immutable approval revisions, provider-method restrictions, persisted-state eligibility resolution, append-only pause/kill-switch controls, safe-default non-executable provider catalogues, source-value evidence, protected APIs, and the Conditional Integrations workspace;
- governed analyst research orchestration with persisted plans/revisions/decisions/steps/attempts/results, deterministic source ranking, exact runtime authorization/capability/quota/cost controls, explicit manual-link states, evidence-reference provenance validation, protected APIs, and the analyst Research workspace.

Lot `12` remains under an explicit activation boundary: merging the software does not authorize collection against a real organization. The checked-in public-web example is disabled, unauthorized, unscheduled, and non-executable. Search and archive providers remain disconnected until separately approved.

Lot `13` provides global vulnerability knowledge without asserting organization exposure. CISA KEV uses its existing governed runtime path. CVE.org, NVD, EPSS, OSV, GitHub Global Security Advisories, and CIRCL mappings remain non-executable candidates until their access, quota, authorization, retention, and scheduling contracts are approved.

Lot `14` provides public incident intelligence without contacting threat actors or handling victim data. An attacker allegation remains an allegation; only an active company confirmation, regulator notice, or CERT notice can provide official confirmation. Incident provider candidates remain non-executable, unauthorized, and unscheduled.

Lot `15` provides a global defensive telemetry layer without organization attribution. It normalizes public-safe indicators, preserves malicious, suspicious, benign, sinkholed, expired, shared-infrastructure, and retracted states, and exposes immutable source history. It performs no active connection, scan, binary download, compromise inference, opportunity creation, or outreach. All newly modeled telemetry providers remain non-executable candidates.

Lot `16` provides validated passive exposure and technographic observations without probing assets or verifying exposure. It normalizes public technical assets, preserves immutable provider revisions and supersession history, separates technology mentions from passive observations and observed versions, and represents organization attribution as exact, candidate, review-required, rejected, or unresolved with explicit risks. It performs no authentication, service connection, applicability assessment, opportunity creation, or outreach. All newly modeled passive providers remain unauthorized, unscheduled, and non-executable candidates.

Lot `17` provides explainable vulnerability applicability by reconciling organization-specific passive technology evidence with official advisory revisions and affected-version ranges. It preserves unknown and review-required outcomes, immutable assessment history, corrections, withdrawals, support lifecycle, fixes, and mitigations. Applicability is not active validation, verified exposure, compromise, an automatic opportunity, or authorization to contact an organization. All newly modeled advisory providers remain unauthorized, unscheduled, and non-executable candidates.

Lot `18` provides source-aware public corporate and regulatory change intelligence. It separates official filings, regulator notices, company disclosures, media reporting, analyst commentary, speculation, disputes, corrections, retractions, syndication, and staleness; preserves immutable revisions and distinct event/publication/update times; bounds stored excerpts; and keeps service-family mappings separate from raw evidence. A repeated report is not independent corroboration, reporting is not official confirmation, and a raw change event is not a need, opportunity, or authorization to contact. All newly modeled change-intelligence providers remain unauthorized, unscheduled, and non-executable candidates.

Lot `19` provides temporal, directed, evidence-backed organization relationships. It separates claimed, observed, contracted, historical, and inferred evidence; preserves source/target direction, endpoint identity review, validity, expiry, corrections and retractions; and keeps contract/product/service contexts separate from source evidence. Marketing claims are not contract evidence, historical or inferred relationships are not current incumbents, and relationship evidence is not a need, opportunity, or authorization to contact. New relationship providers remain unauthorized, unscheduled, and non-executable candidates.

Lot `20` provides a PostgreSQL-backed temporal corporate knowledge graph over previously persisted evidence. It preserves source lineage, evidence class, chronology, suppression and correction state; treats shared names, aliases, domains and identifiers as conflicts rather than automatic merges; separates deterministic exact resolution from review-only probabilistic candidates; and makes merge, reject, split, override and restore decisions append-only and reversible through versioned blast-radius previews. Graph membership is not an evidence upgrade, verified exposure, compromise, service need, opportunity, contact target, or outreach authorization.

Lot `21` provides source-aware professional organization context without building private-life profiles. It preserves source-qualified person references, temporal role/team and direct reporting-line claims, public business contact channels, authorized public-community metadata, lawful-basis and retention state, correction history, and HMAC-backed erasure. Same names are not automatic person merges, a professional role claim is not verified employment, a public profile is not platform-automation authorization, service relevance is not a need or opportunity, and contact relevance is not outreach authorization.

Lot `22` provides a fail-closed approval and control layer for conditional, premium, LinkedIn, Discord, BrixHub, licensed CTI, and licensed commercial-data providers. It preserves immutable dossier revisions with actor/reason, resolves onboarding, Source Governance, Source Portfolio, capability, quota, cost, pause, and kill-switch state from PostgreSQL, and records immutable eligibility decisions. Candidate visibility, an account reference, a licence, or a positive dossier is not by itself execution authorization. LinkedIn is limited to official or licensed API methods; Discord requires an administrator-installed connector or authorized export; BrixHub remains quarantined with no permitted execution method. Default Lot 22 catalogues contain no executable adapter or schedule, and the workspace never performs provider login or collection from a page view.

Lot `23` provides policy-aware analyst research orchestration over existing governed capabilities. A research question is never treated as authorization. Plans bind exact purposes, categories, source/tool IDs, approved step keys, host/path scope, budgets and risk ceilings; automated steps resolve persisted governance/onboarding/portfolio/capability/quota/cost/conditional controls before execution; manual links stay explicit analyst actions; retries use persisted idempotent attempts; and captured results must reference existing evidence with valid provenance. The research workspace and protected APIs never create a general-purpose browser, arbitrary HTTP tool, automatic opportunity, or outreach path.

The next planned implementation lot is `24`: Signal fusion, need hypotheses, and commercial taxonomy.

## Implemented and modeled source portfolio

Executable or installed adapters currently include:

- **CISA KEV** for known-exploited vulnerability metadata and canonical KEV history;
- **TED Search API** for European procurement notices;
- **BOAMP/DILA Explore API** for French procurement notices;
- **DECP** for published French contract history;
- **Greenhouse Job Board API**, **Lever Postings API**, and **SmartRecruiters Posting API** for public hiring signals;
- **API Recherche d'entreprises**, **GLEIF**, and **BODACC** for organization identity;
- **public-web-sitemap** as a governed but non-activated public-footprint adapter;
- a synthetic reference adapter for runtime contract testing.

Selected vulnerability schemas and deterministic mappings are implemented for CVE.org/CVE v5, NVD API 2.0, FIRST EPSS, OSV, GitHub Global Security Advisories, and CIRCL-compatible CVE records. These entries remain non-executable candidates.

Selected incident schemas and deterministic mappings are implemented for official company disclosures, regulator and CERT notices, bounded public or licensed incident reporting, and licensed ransomware metadata. These entries remain non-executable candidates.

Selected defensive telemetry schemas and deterministic mappings are implemented for:

- licensed STIX/TAXII indicators;
- licensed phishing metadata;
- licensed passive DNS;
- licensed certificate telemetry;
- licensed malware family and hash metadata.

Selected passive observation schemas and deterministic mappings are implemented for:

- licensed passive-exposure metadata;
- licensed technographic observations;
- licensed cloud-asset observations.

Selected advisory schemas and deterministic mappings are implemented for:

- official vendor PSIRT advisories;
- official Linux distribution security advisories;
- official package-ecosystem security advisories.

Selected corporate-change schemas and deterministic mappings are implemented for:

- official corporate disclosures;
- official regulatory change notices;
- licensed corporate-news metadata with bounded excerpts and explicit syndication identity.

Selected relationship schemas and deterministic mappings are implemented for:

- official relationship disclosures;
- public partner directories;
- bounded public case-study metadata;
- public certificate relationship metadata.

Selected professional-context candidate contracts are implemented for:

- organization-published team and business-contact metadata;
- licensed or explicitly authorized professional-directory metadata;
- approved community exports or APIs with an explicit authorization reference.

Selected conditional-provider contracts are now modeled for:

- existing governed `linkedin-official-api` and quarantined `brixhub` source identities;
- an administrator-consented Discord integration candidate;
- deployment-specific licensed premium-CTI and commercial-data placeholders.

The new Lot 22 candidates are fail-closed: missing authorization, empty approved hosts/paths/purposes, no runtime adapter, no collection schedule, no raw-storage permission, and no automatic opportunity or outreach path. Premium-provider placeholders use `.example.invalid` and do not imply approval of a real vendor.

Every newly modeled passive, advisory, corporate-change, relationship, or professional-context candidate is `draft`, has missing authorization, has no approved hosts or paths, has no schedule or registered runtime adapter, and is marked `executable: false`. Active probing, authentication, access-control bypass, direct exposure validation, autonomous opportunities, and outreach are explicitly forbidden. Vulnerability applicability operates only on stored evidence from both organization-specific technology observations and advisory affected-range evidence.

OSINT Framework entries remain non-executable catalog candidates. LinkedIn, Discord, BrixHub, browser automation, premium providers, search APIs, archive providers, and every unapproved vulnerability, incident, telemetry, passive-observation, advisory, corporate-change, relationship, professional-context, or conditional provider remain disabled unless their exact method, fields, purpose, authorization, retention, licence, onboarding, runtime capability, quota, cost, and security controls are approved.

## Evidence flow

```text
source candidate
  -> source governance and onboarding
  -> scheduled backfill or incremental collection
  -> immutable source record and provenance
  -> canonical observation or claim
  -> organization, event, product, provider, asset, or role resolution
  -> contradiction and corroboration processing
  -> commercial signal
  -> need hypothesis
  -> explainable score
  -> alert, research task, company workspace, or opportunity
  -> analyst decision and outcome feedback
```

Global vulnerability knowledge remains a separate canonical layer:

```text
provider vulnerability record
  -> immutable source snapshot
  -> exact identifier and alias reconciliation
  -> source-specific CVSS / EPSS / affected-range / exploitation facts
  -> canonical vulnerability read model

canonical vulnerability
  != organization technology evidence
  != affected installation
  != exposure
  != current opportunity
```

Public incident knowledge also remains separate from commercial conclusions:

```text
public or licensed incident metadata
  -> immutable source claim revision
  -> allegation / report / official confirmation / denial / correction / retraction
  -> explicit incident-key reconciliation
  -> organization link or review-required candidate
  -> canonical incident timeline

attacker allegation
  != independent corroboration
  != official confirmation
  != proof of compromise
  != current opportunity
  != authorization to contact
```

Defensive threat telemetry remains separate from organization attribution:

```text
provider indicator metadata
  -> deterministic indicator normalization
  -> immutable source snapshot
  -> source independence, sensor scope, and classification history
  -> canonical indicator and campaign relations

canonical indicator
  != direct validation by this platform
  != organization asset evidence
  != proof of exposure
  != proof of compromise
  != current opportunity
```

Passive observations remain separate from exposure and applicability conclusions:

```text
provider passive metadata
  -> deterministic public-asset normalization
  -> immutable passive observation snapshot
  -> source-aware chronology and attribution-risk reconciliation
  -> canonical passive asset and technology evidence

passive asset or observed version
  != active validation
  != vulnerability applicability by itself
  != verified exposure
  != proof of compromise
  != current opportunity
```

Applicability remains a separate evidence-backed decision layer:

```text
organization-specific passive technology evidence
  + official advisory affected-product and version-range evidence
  -> deterministic or review-required applicability assessment
  -> immutable assessment snapshot and current projection

vulnerability applicability
  != active validation
  != verified exposure
  != proof of compromise
  != current opportunity
  != authorization to contact
```

Corporate-change intelligence remains a separate source-aware evidence layer:

```text
public or licensed change metadata
  -> immutable source/article claim revision
  -> filing / regulator / company / report / speculation / dispute / correction / retraction
  -> syndication-aware reconciliation and organization-link review
  -> canonical material-change event

material change event
  != independent corroboration merely because it was republished
  != official confirmation unless an official source confirms it
  != service mapping
  != need hypothesis or opportunity
  != authorization to contact
```

Entity resolution remains a reversible projection over source-aware evidence:

```text
persisted organization / identity / relationship / asset / incident / change / applicability evidence
  -> immutable graph node and edge snapshots
  -> deterministic exact resolution or review-only candidate
  -> temporal projection and analyst conflict queue
  -> versioned blast-radius preview
  -> append-only human merge / reject / split / override / restore decision

same name, alias, domain, or identifier
  != same legal entity
graph membership
  != evidence upgrade
historical or inferred edge
  != verified current fact
resolution decision
  != opportunity or authorization to contact
```

Professional context remains a bounded, source-aware evidence layer:

```text
approved professional source evidence
  -> source-qualified person reference
  -> temporal role / team / direct reporting-line claim
  -> public business contact or authorized community metadata
  -> analyst professional-context workspace

same display name
  != same person
role claim
  != verified employment
public profile
  != authorization to automate the platform
service relevance
  != need hypothesis or opportunity
contact relevance
  != outreach authorization
```

Conditional-provider eligibility remains a local control decision over persisted state:

```text
provider candidate
  + immutable provider-specific dossier
  + persisted onboarding state
  + Source Governance decision for exact target/purpose/category
  + executable Source Portfolio state
  + registered adapter capability
  + quota/cost state
  + local pause/kill-switch state
  -> immutable eligibility audit

provider candidate
  != approved provider
approved dossier
  != registered runtime capability
eligibility audit
  != provider request or collection
source-value contribution
  != service need or commercial opportunity
```

Provider payloads remain inside adapter packages. Adapters never write directly to company, score, alert, or opportunity projections.

## Product access model

The ordinary read experience requires no visitor registration, password, or email address. Visitors receive only a short-lived anonymous platform session for navigation continuity, rate limiting, abuse prevention, and temporary interface state.

Collection is centralized and uses approved public feeds, official APIs, open-data sources, licensed providers, and governed platform identities. Anonymous visitor sessions are never reused as identities on external services.

The product is database-first. Normal page views read stored and indexed evidence; they do not crawl sources on demand. Schedulers refresh sources according to freshness, value, cost, quota, authorization, and change frequency. Stale data remains visible with an explicit freshness state.

The `/research`, `/vulnerabilities`, `/incidents`, `/threat-intelligence`, `/passive-exposure`, `/vulnerability-applicability`, `/corporate-changes`, `/relationships`, `/graph`, and `/professional-context` workspaces and their APIs search persisted data only. They never launch external collection from an analyst page view.

The `/conditional-integrations` workspace is a deployment-protected control-plane workspace. It reads and writes local approval/control/audit state and can request a persisted-state eligibility preview, but that preview performs no provider login, HTTP collection, browser automation, outreach, or opportunity creation. Production requires the configured control-plane token at request time.

## Architecture

The backend is a Python 3.12 modular monolith using FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic, and durable scheduler/worker orchestration. The analyst interface is a Next.js application under `apps/web`.

The architecture separates:

- an accountless public read data plane;
- a deployment-protected control and commercial-operations plane.

Canonical layers are:

1. source catalog and authorization;
2. provider onboarding, provider-specific conditional approvals, and adapter capabilities;
3. collection runs and immutable source records;
4. evidence, observations, public claims, vulnerability snapshots, incident claims, telemetry snapshots, passive observation snapshots, advisory revisions, corporate-change claim revisions, relationship evidence snapshots, immutable corporate-graph snapshots, professional-context evidence snapshots, and conditional-provider control/eligibility audits;
5. resolved organizations, incidents, vulnerabilities, indicators, passive assets, technologies, products, providers, material changes, business relationships, roles, temporal relationships, professional people references, and reversible entity-resolution bindings;
6. vulnerability applicability, service mappings, professional service relevance, commercial signals, and need hypotheses;
7. scores, alerts, opportunities, tasks, and analyst decisions.

Dependencies point inward:

```text
API / CLI / composition
  -> application
  -> domain

infrastructure implements application ports
```

Domain modules cannot depend on FastAPI, SQLAlchemy models, adapters, API packages, or infrastructure implementations.

## Delivery roadmap

[`docs/PROJECT_DELIVERY_PLAN.md`](docs/PROJECT_DELIVERY_PLAN.md) is authoritative.

- lots `00–23`: implemented and validated foundations, procurement, hiring, identity, onboarding, source runtime, contracts, public footprint, vulnerability knowledge, public incident intelligence, defensive telemetry, passive technographic evidence, vendor advisories, vulnerability applicability, corporate/regulatory change intelligence, temporal relationship intelligence, entity resolution, the temporal corporate knowledge graph, governed professional context, conditional provider governance, and governed analyst research orchestration;
- lots `24–27`: signal fusion, need hypotheses, calibrated scoring, native commercial operations, and Company 360;
- lots `28–32`: data quality, release security, resilience, optional isolated browser runtime, and controlled production pilot.

## Quality gates

Every pull request must pass on one final SHA:

1. dependency consistency and security audits;
2. Ruff;
3. Mypy strict;
4. architecture, complexity, dependency, safety, release, and roadmap contracts;
5. reversible PostgreSQL migrations;
6. backend coverage instrumentation including branches, with the configured aggregate threshold at or above 90%;
7. frontend dependency audit, TypeScript checking, and production build.

Executable rules include:

- application Python files: maximum 400 lines;
- functions and methods: maximum 120 lines;
- classes: maximum 300 lines;
- function parameters: maximum 10;
- control-flow nesting: maximum 6;
- no duplicate definitions or wildcard imports;
- one authoritative package and API version;
- unit tests cannot open live network connections;
- UTC-aware persistence;
- roadmap lots remain continuous and status-consistent;
- threat telemetry cannot import network clients, organization modules, or opportunity modules;
- passive exposure cannot import network clients, collection adapters, opportunity modules, or vulnerability-applicability modules;
- vulnerability applicability cannot import network clients, collection adapters, opportunity modules, or contact/outreach modules;
- corporate change intelligence cannot import network clients, collection adapters, opportunity modules, contacts, or outreach modules;
- relationship intelligence cannot import network clients, collection adapters, or opportunity modules;
- corporate graph cannot import network clients, source adapters, browser automation, `neo4j`, or `networkx`, and its domain cannot depend on FastAPI, SQLAlchemy, infrastructure implementations, or opportunity modules;
- professional context cannot import network clients, browser or platform automation, collection orchestration, opportunity, or outreach modules, and its domain cannot depend on FastAPI, SQLAlchemy, or infrastructure implementations;
- conditional integrations cannot import provider network clients, browser/platform automation, collection adapters, opportunity, contact-enrichment, or outreach modules, and provider eligibility must be resolved from persisted governed state rather than client-supplied runtime booleans.

## Source and data safety

Never commit API keys, sessions, prospect lists, collected personal data, proprietary datasets, or production evidence. Tests use synthetic, provider-published, minimized, licensed, or redistributable fixtures.

The platform does not:

- interact with threat actors;
- enter victim negotiation portals or use `.onion` incident sources;
- download victim files, stolen datasets, malware samples, or other binary payloads;
- validate leaked credentials;
- store private communications or private-life data;
- bypass authentication, paywalls, CAPTCHA, MFA, invitations, or access controls;
- actively scan or exploit prospects;
- directly connect to suspicious or malicious infrastructure merely to validate an indicator;
- turn passive metadata alone into vulnerability applicability or verified exposure;
- create fake accounts or rotate accounts after a ban;
- perform autonomous outreach;
- infer organization exposure from a global CVE, CVSS, EPSS, PoC, or KEV record alone;
- infer compromise from an IOC, passive observation, applicability assessment, or attacker allegation alone;
- treat syndicated copies of one report as independent corroboration;
- turn a public/media material-change report directly into an official confirmation, service need, opportunity, contact target, or outreach action;
- treat a marketing claim as contract evidence or an active incumbent;
- treat a historical or inferred organization relationship as a verified current relationship;
- treat shared names, aliases, domains, or identifiers as automatic entity merges;
- treat graph membership or a resolution candidate as an upgrade in evidence strength;
- treat a public professional profile as authorization to automate that platform;
- turn professional role or contact relevance directly into a need, opportunity, or outreach authorization;
- treat a conditional-provider catalogue entry, account, licence, approval dossier, eligibility preview, or observed source-value contribution as authorization to collect, proof of a service need, a commercial opportunity, or authorization to contact;
- treat a research question, plan, ranked source, eligible step, manual link, attempt, or captured result as permission to bypass source controls, proof of a commercial need, an opportunity, or outreach authorization.

LinkedIn collection remains disabled unless official API scopes, a licensed product, or reviewed written authorization covers the exact method and purpose and all shared runtime gates are positive. Discord collection requires an administrator-installed connector, authorized export, or equivalent consented integration plus positive shared gates. BrixHub remains quarantined and has no permitted execution method in Lot 22. Premium provider placeholders are non-executable until a deployment selects a real provider and separately approves its exact contract, fields, scopes, hosts, retention, onboarding, runtime adapter, quota, cost, and security controls.

## Local development

Requirements:

- Python 3.12;
- Node.js 24;
- Docker with Compose.

```bash
cp .env.example .env
docker compose up -d postgres
python -m pip install -e '.[dev]'
alembic upgrade head
uvicorn cip.main:app --reload
```

In separate terminals:

```bash
cip-scheduler
cip-worker
```

Frontend:

```bash
cd apps/web
npm install
npm run dev
```

## Validation commands

```bash
python -m pip check
pip-audit --skip-editable
ruff check .
mypy
pytest tests/architecture
alembic upgrade head
alembic downgrade base
alembic upgrade head
pytest --cov=cip --cov-branch --cov-report=term-missing --cov-fail-under=90
```

```bash
cd apps/web
npm audit --audit-level=high
npm run typecheck
npm run build
```

## Project documents

- [`docs/PRODUCT.md`](docs/PRODUCT.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/ANONYMOUS_ACCESS_AND_REFRESH_MODEL.md`](docs/ANONYMOUS_ACCESS_AND_REFRESH_MODEL.md)
- [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md)
- [`docs/COMMERCIAL_INTELLIGENCE_INTEGRATION_ARCHITECTURE.md`](docs/COMMERCIAL_INTELLIGENCE_INTEGRATION_ARCHITECTURE.md)
- [`docs/CYBER_SERVICE_NEED_TAXONOMY.md`](docs/CYBER_SERVICE_NEED_TAXONOMY.md)
- [`docs/SOURCE_POLICY.md`](docs/SOURCE_POLICY.md)
- [`docs/OSINT_COLLECTION_CATALOG.md`](docs/OSINT_COLLECTION_CATALOG.md)
- [`docs/LIVE_CYBER_THREAT_SOURCE_CATALOG.md`](docs/LIVE_CYBER_THREAT_SOURCE_CATALOG.md)
- [`docs/DEVELOPMENT_STANDARDS.md`](docs/DEVELOPMENT_STANDARDS.md)
- [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md)
- [`docs/SOURCE_INTEGRATION_TEST_MATRIX.md`](docs/SOURCE_INTEGRATION_TEST_MATRIX.md)
- [`docs/PROJECT_DELIVERY_PLAN.md`](docs/PROJECT_DELIVERY_PLAN.md)
- [`docs/ROADMAP_AND_ARCHITECTURE_AUDIT.md`](docs/ROADMAP_AND_ARCHITECTURE_AUDIT.md)
- [`docs/MULTI_SERVICE_DETECTION_AUDIT.md`](docs/MULTI_SERVICE_DETECTION_AUDIT.md)
- [`docs/lots/LOT_12_CORPORATE_PUBLIC_FOOTPRINT.md`](docs/lots/LOT_12_CORPORATE_PUBLIC_FOOTPRINT.md)
- [`docs/lots/LOT_12_VALIDATION_REPORT.md`](docs/lots/LOT_12_VALIDATION_REPORT.md)
- [`docs/lots/LOT_13_VULNERABILITY_KNOWLEDGE.md`](docs/lots/LOT_13_VULNERABILITY_KNOWLEDGE.md)
- [`docs/lots/LOT_13_VALIDATION_REPORT.md`](docs/lots/LOT_13_VALIDATION_REPORT.md)
- [`docs/lots/LOT_14_INCIDENT_INTELLIGENCE.md`](docs/lots/LOT_14_INCIDENT_INTELLIGENCE.md)
- [`docs/lots/LOT_14_VALIDATION_REPORT.md`](docs/lots/LOT_14_VALIDATION_REPORT.md)
- [`docs/lots/LOT_15_THREAT_TELEMETRY.md`](docs/lots/LOT_15_THREAT_TELEMETRY.md)
- [`docs/lots/LOT_15_VALIDATION_REPORT.md`](docs/lots/LOT_15_VALIDATION_REPORT.md)
- [`docs/lots/LOT_16_PASSIVE_EXPOSURE.md`](docs/lots/LOT_16_PASSIVE_EXPOSURE.md)
- [`docs/lots/LOT_16_VALIDATION_REPORT.md`](docs/lots/LOT_16_VALIDATION_REPORT.md)
- [`docs/lots/LOT_17_VENDOR_ADVISORY_APPLICABILITY.md`](docs/lots/LOT_17_VENDOR_ADVISORY_APPLICABILITY.md)
- [`docs/lots/LOT_17_VALIDATION_REPORT.md`](docs/lots/LOT_17_VALIDATION_REPORT.md)
- [`docs/lots/LOT_18_CORPORATE_CHANGE_SIGNALS.md`](docs/lots/LOT_18_CORPORATE_CHANGE_SIGNALS.md)
- [`docs/lots/LOT_18_VALIDATION_REPORT.md`](docs/lots/LOT_18_VALIDATION_REPORT.md)
- [`docs/lots/LOT_19_RELATIONSHIP_INTELLIGENCE.md`](docs/lots/LOT_19_RELATIONSHIP_INTELLIGENCE.md)
- [`docs/lots/LOT_19_VALIDATION_REPORT.md`](docs/lots/LOT_19_VALIDATION_REPORT.md)
- [`docs/lots/LOT_20_ENTITY_RESOLUTION_CORPORATE_GRAPH.md`](docs/lots/LOT_20_ENTITY_RESOLUTION_CORPORATE_GRAPH.md)
- [`docs/lots/LOT_20_VALIDATION_REPORT.md`](docs/lots/LOT_20_VALIDATION_REPORT.md)
- [`docs/lots/LOT_21_PROFESSIONAL_CONTEXT.md`](docs/lots/LOT_21_PROFESSIONAL_CONTEXT.md)
- [`docs/lots/LOT_21_VALIDATION_REPORT.md`](docs/lots/LOT_21_VALIDATION_REPORT.md)
- [`docs/lots/LOT_22_CONDITIONAL_INTEGRATIONS.md`](docs/lots/LOT_22_CONDITIONAL_INTEGRATIONS.md)
- [`docs/lots/LOT_22_VALIDATION_REPORT.md`](docs/lots/LOT_22_VALIDATION_REPORT.md)
- [`docs/lots/LOT_23_GOVERNED_OSINT_RESEARCH.md`](docs/lots/LOT_23_GOVERNED_OSINT_RESEARCH.md)
- [`docs/lots/LOT_23_VALIDATION_REPORT.md`](docs/lots/LOT_23_VALIDATION_REPORT.md)
- [`SECURITY.md`](SECURITY.md)
