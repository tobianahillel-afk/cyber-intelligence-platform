# Cyber Intelligence Platform

Cyber Intelligence Platform is a standalone cyber revenue-intelligence and commercial-operations system. It collects approved public or licensed evidence, resolves it to organizations, converts it into explainable cybersecurity need hypotheses, and lets analysts discover, investigate, qualify, assign, and track potential clients.

The product is not a Salesforce, HubSpot, or external-CRM extension. It owns company intelligence, evidence, alerts, saved searches, professional organization maps, contacts, opportunities, tasks, notes, assignments, engagement history, and reporting.

The product is evidence-first. A material statement must expose its source, observed time, event time, confidence, freshness, claim type, contradictions, and review history. An attacker claim is not an official confirmation. A technology observation is not proof of a vulnerable deployment. A public professional discussion is not automatically an employer fact.

## Product objective

The platform should answer:

- Which organizations show a current or emerging cybersecurity need?
- What evidence supports that need?
- Is the signal explicit buying intent, urgency, transformation, renewal timing, product risk, provider displacement, or a weak lead?
- Which services or products fit the evidence?
- Which professional roles and business contact channels are relevant?
- What should the analyst do next?

The product is not limited to SIEM and SOC. It covers strategy and vCISO, audit, GRC, pentest, red and purple teaming, vulnerability management, SOC and MDR, incident response, cyber resilience, IAM and PAM, cloud security, AppSec and DevSecOps, network security, data protection, supply-chain security, OT security, awareness, product integration and cyber-insurance readiness.

Source breadth is useful only when it improves reliable client discovery. A source that adds records but no unique commercial value should be deprioritized or removed.

See [`docs/CYBER_SERVICE_NEED_TAXONOMY.md`](docs/CYBER_SERVICE_NEED_TAXONOMY.md).

## Accountless product access

The ordinary product experience requires no visitor registration, login, password, or email address. A visitor receives only a short-lived anonymous platform session for navigation continuity, rate limiting, abuse prevention, and temporary interface state.

That anonymous session is never reused as an identity on external providers. Collection is performed centrally by approved public feeds, official APIs, open-data sources, licensed providers, and governed platform service identities.

The product is database-first. Normal page views read stored and indexed evidence. They do not crawl every source again. Schedulers refresh sources according to freshness, value, cost, quota, and change frequency. A stale entity may enqueue a bounded priority refresh while the interface continues to show the latest stored evidence with a visible freshness state.

See [`docs/ANONYMOUS_ACCESS_AND_REFRESH_MODEL.md`](docs/ANONYMOUS_ACCESS_AND_REFRESH_MODEL.md).

## Current validated baseline

The merged validated baseline is version `0.9.0`, covering lots `00` through `08`.

Implemented source adapters include:

- **CISA KEV** for known-exploited vulnerability metadata;
- **TED Search API** for European procurement notices;
- **BOAMP/DILA Explore API** for French procurement notices;
- **Greenhouse Job Board API** for public cyber hiring signals;
- **Lever Postings API** for public published jobs;
- **SmartRecruiters Posting API** for public job lists and details;
- **API Recherche d'entreprises** for French legal-unit and establishment identity;
- **GLEIF** for LEI and parent relationship data;
- **BODACC** for selected legal-event identity claims.

Lot `08` separates legal units, establishments, groups, aliases, statuses, exact identifiers, registry claims, conflicts, and review candidates. Exact identifiers can link automatically; ambiguous matches remain reviewable.

The current branch targets version `0.10.0` and implements lot `09`: official provider onboarding and secret lifecycle.

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

## Planned source portfolio

The project catalogs and prioritizes:

- official company registries, procurement, awards, contracts, and renewals;
- corporate websites, documents, sitemaps, archives, public repositories, Google dorks and approved search APIs;
- vulnerability, advisory, KEV, EPSS, and exploitation-state sources;
- ransomware claims, official incident confirmations, regulator notices, and public disclosures;
- IOC, phishing, malicious infrastructure, C2, attack telemetry, and threat intelligence;
- passive exposure, certificates, DNS, ASN, service, and technographic providers;
- provider, partner, customer, supplier, integrator, MSSP, auditor, insurer, and supply-chain relationships;
- governed public professional roles, business contacts, forums, and community signals;
- licensed and conditional providers, including official LinkedIn paths, consented Discord connectors, commercial CTI, and BrixHub after explicit approval.

Google and equivalent search dorks are a governed discovery mechanism. Google queries are generated as analyst links unless an approved official API or written authorization covers automated retrieval. Search-result metadata is not a confirmed fact; the referenced public page or document must be retrieved through an approved path before it supports a signal or opportunity.

The broad catalogs are planning inputs, not automatic permission to crawl:

- [`docs/OSINT_COLLECTION_CATALOG.md`](docs/OSINT_COLLECTION_CATALOG.md)
- [`docs/LIVE_CYBER_THREAT_SOURCE_CATALOG.md`](docs/LIVE_CYBER_THREAT_SOURCE_CATALOG.md)

## Architecture

The backend is a Python 3.12 modular monolith using FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic, and durable scheduler/worker orchestration. The analyst UI is a Next.js application under `apps/web`.

The architecture separates:

- an accountless public data plane for approved stored intelligence;
- a deployment-protected control plane for source governance, provider onboarding, schedules, secrets, retention, correction, deletion, and operations.

The canonical data layers are:

1. source catalog and authorization;
2. provider onboarding and adapter capabilities;
3. collection runs and immutable source records;
4. evidence, observations, and claims;
5. resolved entities, events, technologies, providers, roles, and temporal relationships;
6. service-family mappings, commercial signals and need hypotheses;
7. scores, alerts, opportunities, tasks, and analyst decisions.

See:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md)
- [`docs/COMMERCIAL_INTELLIGENCE_INTEGRATION_ARCHITECTURE.md`](docs/COMMERCIAL_INTELLIGENCE_INTEGRATION_ARCHITECTURE.md)
- [`docs/CYBER_SERVICE_NEED_TAXONOMY.md`](docs/CYBER_SERVICE_NEED_TAXONOMY.md)

## Delivery roadmap

[`docs/PROJECT_DELIVERY_PLAN.md`](docs/PROJECT_DELIVERY_PLAN.md) is authoritative.

Completed and current sequence:

- lots `00–08`: validated foundations, durable collection, opportunities, procurement, hiring, and organization identity;
- lot `09`: provider onboarding and secret lifecycle, currently in progress;
- lot `10`: common source portfolio runtime, backfill, freshness, source health, and machine-readable catalog;
- lots `11–23`: procurement history, public corporate footprint, governed dorks, vulnerabilities, live incidents, telemetry, exposure, relationships, professional context, conditional sources, and research orchestration;
- lot `24`: executable service taxonomy, signal fusion and need hypotheses;
- lots `25–27`: calibrated scoring, native commercial operations, and Company 360;
- lots `28–32`: data quality, release security, resilience, optional isolated browser runtime, and controlled production pilot.

BrixHub is explicitly assigned to lot `22`. It remains non-executable until its exact access path, allowed fields, provenance, licence, retention, security, and authorization are approved. If approved, its adapter must support a controlled historical import, incremental refresh, corrections, deletion, provenance, and unique-value measurement.

## Testing and quality gates

Every pull request must pass on one final SHA:

1. dependency consistency and security audits;
2. Ruff;
3. Mypy strict;
4. architecture, complexity, dependency, release, and roadmap contracts;
5. reversible PostgreSQL migrations;
6. backend line and branch coverage at or above the configured threshold;
7. frontend dependency audit, TypeScript checking, and production build.

Every source integration must additionally prove:

- policy denial before network access;
- strict provider schemas and bounded transport;
- durable backfill and incremental convergence;
- deterministic mapping and provenance;
- entity resolution and false-merge prevention;
- cross-source deduplication and contradiction handling;
- correction, retraction, suppression, and deletion propagation;
- source-to-signal and signal-to-opportunity behavior;
- service-family classification with positive, negative and ambiguous fixtures;
- measurable incremental commercial value across more than one service family.

See:

- [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md)
- [`docs/SOURCE_INTEGRATION_TEST_MATRIX.md`](docs/SOURCE_INTEGRATION_TEST_MATRIX.md)
- [`docs/DEVELOPMENT_STANDARDS.md`](docs/DEVELOPMENT_STANDARDS.md)
- [`docs/MULTI_SERVICE_DETECTION_AUDIT.md`](docs/MULTI_SERVICE_DETECTION_AUDIT.md)

Executable rules include:

- application Python files: maximum 400 lines;
- functions and methods: maximum 120 lines;
- classes: maximum 300 lines;
- function parameters: maximum 10;
- control-flow nesting: maximum 6;
- no duplicate definitions or wildcard imports;
- one authoritative package and API version;
- unit tests cannot open live network connections;
- UTC-aware persistence across SQLite and PostgreSQL;
- roadmap lots remain continuous and status-consistent.

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

## Source and data safety

Never commit API keys, sessions, prospect lists, collected personal data, proprietary datasets, or production evidence. Tests use synthetic, provider-published, minimized, licensed, or redistributable fixtures.

The source registry is authoritative. Quarantined or unapproved sources have no executable collection path. Browser automation remains deferred until structured APIs and bounded static HTTP are insufficient and an isolated runtime passes its own gate.

The platform may ingest lawful public or licensed incident metadata and published anonymized research. It does not interact with threat actors, enter victim negotiation portals, download victim files, validate leaked credentials, or store stolen datasets or private communications.

LinkedIn collection remains disabled unless official API scopes, a licensed product, or reviewed written authorization covers the exact method and purpose. Discord collection requires an administrator-installed connector, authorized export, or equivalent consented integration.

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
- [`SECURITY.md`](SECURITY.md)
