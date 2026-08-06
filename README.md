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

The current validated release is version `0.16.0`, covering lots `00` through `15`.

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
- canonical defensive threat indicators with deterministic normalization, immutable source history, conflicting classifications, sensor scope, campaign/malware/CVE relations, protected APIs, and the Threat Intel workspace.

Lot `12` remains under an explicit activation boundary: merging the software does not authorize collection against a real organization. The checked-in public-web example is disabled, unauthorized, unscheduled, and non-executable. Search and archive providers remain disconnected until separately approved.

Lot `13` provides global vulnerability knowledge without asserting organization exposure. CISA KEV uses its existing governed runtime path. CVE.org, NVD, EPSS, OSV, GitHub Global Security Advisories, and CIRCL mappings remain non-executable candidates until their access, quota, authorization, retention, and scheduling contracts are approved.

Lot `14` provides public incident intelligence without contacting threat actors or handling victim data. An attacker allegation remains an allegation; only an active company confirmation, regulator notice, or CERT notice can provide official confirmation. Incident provider candidates remain non-executable, unauthorized, and unscheduled.

Lot `15` provides a global defensive telemetry layer without organization attribution. It normalizes public-safe indicators, preserves malicious, suspicious, benign, sinkholed, expired, shared-infrastructure, and retracted states, and exposes immutable source history. It performs no active connection, scan, binary download, compromise inference, opportunity creation, or outreach. All newly modeled telemetry providers remain non-executable candidates.

Lot `16` is the active `0.17.0` release candidate and remains `IN_PROGRESS` until one exact final commit passes every required CI gate. The candidate provides passive exposure and technographic observations without probing assets or verifying exposure. It normalizes public technical assets, preserves immutable provider revisions and supersession history, separates technology mentions from passive observations and observed versions, and represents organization attribution as exact, candidate, review-required, rejected, or unresolved with explicit risks. It performs no authentication, service connection, applicability assessment, opportunity creation, or outreach. All newly modeled passive providers remain unauthorized, unscheduled, and non-executable candidates.

Lot `17`, official advisories, customer technologies, and vulnerability applicability, remains planned and must not start before Lot `16` is validated and merged to `main`.

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

Every newly modeled passive candidate is `draft`, has missing authorization, has no approved hosts or paths, has no schedule or registered runtime adapter, and is marked `executable: false`. Active probing, authentication, access-control bypass, direct validation, applicability assessment, exposure verification, autonomous opportunities, and outreach are explicitly forbidden.

OSINT Framework entries remain non-executable catalog candidates. LinkedIn, Discord, BrixHub, browser automation, premium providers, search APIs, archive providers, and every unapproved vulnerability, incident, telemetry, or passive-observation provider remain disabled unless their exact method, fields, purpose, authorization, retention, licence, and security controls are approved.

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
  != vulnerability applicability
  != verified exposure
  != proof of compromise
  != current opportunity
```

Provider payloads remain inside adapter packages. Adapters never write directly to company, score, alert, or opportunity projections.

## Product access model

The ordinary read experience requires no visitor registration, password, or email address. Visitors receive only a short-lived anonymous platform session for navigation continuity, rate limiting, abuse prevention, and temporary interface state.

Collection is centralized and uses approved public feeds, official APIs, open-data sources, licensed providers, and governed platform identities. Anonymous visitor sessions are never reused as identities on external services.

The product is database-first. Normal page views read stored and indexed evidence; they do not crawl sources on demand. Schedulers refresh sources according to freshness, value, cost, quota, authorization, and change frequency. Stale data remains visible with an explicit freshness state.

The `/research`, `/vulnerabilities`, `/incidents`, `/threat-intelligence`, and `/passive-exposure` workspaces and their APIs search persisted data only. They never launch external collection from an analyst page view.

## Architecture

The backend is a Python 3.12 modular monolith using FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic, and durable scheduler/worker orchestration. The analyst interface is a Next.js application under `apps/web`.

The architecture separates:

- an accountless public read data plane;
- a deployment-protected control and commercial-operations plane.

Canonical layers are:

1. source catalog and authorization;
2. provider onboarding and adapter capabilities;
3. collection runs and immutable source records;
4. evidence, observations, public claims, vulnerability snapshots, incident claims, telemetry snapshots, and passive observation snapshots;
5. resolved organizations, incidents, vulnerabilities, indicators, passive assets, technologies, providers, roles, and temporal relationships;
6. service mappings, commercial signals, and need hypotheses;
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

- lots `00–15`: implemented and validated foundations, procurement, hiring, identity, onboarding, source runtime, contracts, public footprint, vulnerability knowledge, public incident intelligence, and defensive telemetry;
- lot `16`: active `0.17.0` release candidate for passive exposure and technographic observations, pending final CI and merge;
- lots `17–19`: advisories and applicability, corporate changes, and provider relationships;
- lots `20–23`: entity resolution, professional context, conditional sources, and governed research orchestration;
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
- passive exposure cannot import network clients, collection adapters, opportunity modules, or vulnerability-applicability modules.

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
- turn passive metadata into vulnerability applicability or verified exposure;
- create fake accounts or rotate accounts after a ban;
- perform autonomous outreach;
- infer organization exposure from a global CVE, CVSS, EPSS, PoC, or KEV record alone;
- infer compromise from an IOC, passive observation, or attacker allegation alone.

LinkedIn collection remains disabled unless official API scopes, a licensed product, or reviewed written authorization covers the exact method and purpose. Discord collection requires an administrator-installed connector, authorized export, or equivalent consented integration. BrixHub remains quarantined.

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
- [`SECURITY.md`](SECURITY.md)
