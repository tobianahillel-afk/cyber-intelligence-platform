# Cyber Intelligence Platform

Cyber Intelligence Platform is a standalone cyber revenue-intelligence and commercial-operations system. It collects approved public or licensed evidence, resolves it to organizations, converts it into explainable cybersecurity need hypotheses, and lets analysts discover, investigate, qualify, assign, and track potential clients.

The product is not a Salesforce, HubSpot, or external-CRM extension. It owns company intelligence, evidence, alerts, saved searches, professional organization maps, contacts, opportunities, tasks, notes, assignments, engagement history, and reporting.

The product is evidence-first. A material statement must expose its source, observed time, event time, confidence, freshness, claim type, contradictions, and review history. An attacker claim is not an official confirmation. A technology mention is not proof of deployment or vulnerability. Search-result metadata is a discovery lead, not an independently corroborated fact.

## Product objective

The platform should answer:

- Which organizations show a current or emerging cybersecurity need?
- What evidence supports that need?
- Is the signal explicit buying intent, urgency, transformation, renewal timing, product risk, provider displacement, or a weak lead?
- Which services or products fit the evidence?
- Which professional roles and business contact channels are relevant?
- What should the analyst do next?

The product covers the complete cyber-service portfolio: strategy and vCISO, audit, GRC, pentest, red and purple teaming, vulnerability management, SOC and MDR, incident response, resilience, IAM and PAM, cloud security, AppSec and DevSecOps, network security, data protection, supply-chain security, OT security, awareness, product integration, and cyber-insurance readiness.

Source breadth is useful only when it improves reliable client discovery. Sources that add records without unique commercial value should be deprioritized or removed.

## Current validated baseline

The current release is version `0.13.0`, covering lots `00` through `12`.

Implemented capabilities include:

- source governance, authorization, retention, suppression, and provenance;
- PostgreSQL persistence and reversible Alembic migrations;
- durable scheduler, worker, checkpoints, retries, circuits, and recovery;
- evidence-backed opportunities with analyst review and explainable score components;
- TED and BOAMP procurement signals;
- Greenhouse, Lever, and SmartRecruiters public hiring signals;
- French and European organization identity using Recherche d'entreprises, GLEIF, and BODACC;
- official provider onboarding and secret-reference lifecycle;
- common source-portfolio runtime, backfill, freshness, health, cost, and controls;
- DECP/TED/BOAMP contract history, providers, and renewal timing;
- governed corporate public-footprint resources, immutable versions, tombstones, quarantined search leads, protected APIs, and the Research workspace.

Lot `12` is implemented and mergeable under an explicit governance boundary: **merging the software does not authorize collection against a real organization**. The checked-in public-web example is disabled, has no approved authorization, has no enabled schedule, and cannot execute. Search and archive providers also remain disconnected until separately reviewed and approved.

The next planned implementation lot is `13`, vulnerability knowledge and exploitation-state reconciliation.

## Implemented source portfolio

Executable or installed adapters currently include:

- **CISA KEV** for known-exploited vulnerability metadata;
- **TED Search API** for European procurement notices;
- **BOAMP/DILA Explore API** for French procurement notices;
- **DECP** for published French contract history;
- **Greenhouse Job Board API** for public cyber hiring signals;
- **Lever Postings API** for public published jobs;
- **SmartRecruiters Posting API** for public job lists and details;
- **API Recherche d'entreprises** for French legal-unit and establishment identity;
- **GLEIF** for LEI and parent relationships;
- **BODACC** for selected legal-event identity claims;
- **public-web-sitemap** as a governed but non-activated corporate public-footprint adapter;
- a synthetic reference adapter for runtime contract testing.

OSINT Framework entries remain non-executable catalog candidates. LinkedIn, Discord, BrixHub, browser automation, premium providers, search APIs, and archive providers remain disabled unless their exact access path, fields, purpose, authorization, retention, and security controls are approved.

## Source-to-opportunity flow

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

Provider payloads remain inside adapter packages. Adapters never write directly to company, score, alert, or opportunity projections.

## Product access model

The ordinary read experience requires no visitor registration, password, or email address. Visitors receive only a short-lived anonymous platform session for navigation continuity, rate limiting, abuse prevention, and temporary interface state.

Collection is centralized and uses approved public feeds, official APIs, open-data sources, licensed providers, and governed platform identities. Anonymous visitor sessions are never reused as identities on external services.

The product is database-first. Normal page views read stored and indexed evidence; they do not crawl sources on demand. Schedulers refresh sources according to freshness, value, cost, quota, and change frequency. Stale data remains visible with an explicit freshness state while a bounded refresh may be queued.

## Architecture

The backend is a Python 3.12 modular monolith using FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic, and durable scheduler/worker orchestration. The analyst interface is a Next.js application under `apps/web`.

The architecture separates:

- an accountless public read data plane;
- a deployment-protected control and commercial-operations plane.

Canonical layers are:

1. source catalog and authorization;
2. provider onboarding and adapter capabilities;
3. collection runs and immutable source records;
4. evidence, observations, and claims;
5. resolved entities, events, technologies, providers, roles, and temporal relationships;
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

- lots `00–12`: implemented and validated foundations, procurement, hiring, identity, onboarding, source runtime, contracts, and public footprint;
- lots `13–19`: vulnerability knowledge, incidents, telemetry, exposure, advisories, regulatory and corporate changes, and provider relationships;
- lots `20–23`: entity resolution, professional context, conditional sources, and governed research orchestration;
- lots `24–27`: signal fusion, need hypotheses, calibrated scoring, native commercial operations, and Company 360;
- lots `28–32`: data quality, release security, resilience, optional isolated browser runtime, and controlled production pilot.

## Quality gates

Every pull request must pass on one final SHA:

1. dependency consistency and security audits;
2. Ruff;
3. Mypy strict;
4. architecture, complexity, dependency, release, and roadmap contracts;
5. reversible PostgreSQL migrations;
6. backend branch coverage at or above the configured threshold;
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
- roadmap lots remain continuous and status-consistent.

## Source and data safety

Never commit API keys, sessions, prospect lists, collected personal data, proprietary datasets, or production evidence. Tests use synthetic, provider-published, minimized, licensed, or redistributable fixtures.

The platform does not:

- interact with threat actors;
- enter victim negotiation portals;
- download victim files or stolen datasets;
- validate leaked credentials;
- store private communications;
- bypass authentication, paywalls, CAPTCHA, MFA, invitations, or access controls;
- perform active scanning or exploitation of prospects;
- create fake accounts or rotate accounts after a ban;
- perform autonomous outreach.

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
- [`SECURITY.md`](SECURITY.md)
