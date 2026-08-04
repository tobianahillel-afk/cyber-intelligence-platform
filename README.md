# Cyber Intelligence Platform

Cyber Intelligence Platform is a standalone, human-operated cyber revenue-intelligence and commercial-operations system. It collects authorized public or licensed evidence, converts it into normalized signals, and lets analysts discover, investigate, qualify, assign, and track organizations that may need cybersecurity services or products.

The platform is not a Salesforce, HubSpot, or external-CRM extension. Its target product owns company records, professional organization maps, business contacts, alert rules, saved searches, opportunities, tasks, notes, assignments, engagement history, and reporting.

The system is evidence-first: every material fact, alert, and opportunity exposes its source, timestamps, confidence, freshness, claim type, conflicts, and review history. It does not autonomously contact prospects, validate credentials, exploit systems, ingest leaked victim data, or retain private-life information.

## Current scope

Version `0.8.0` includes six durable official-source adapters:

- **CISA KEV** for known-exploited vulnerability metadata;
- **TED Search API** for active European cyber procurement notices;
- **BOAMP/DILA Explore API** for actionable French procurement notices;
- **Greenhouse Job Board API** for public cyber hiring signals;
- **Lever Postings API** for public published jobs;
- **SmartRecruiters Posting API** for public job lists and job details.

The three ATS paths are GET-only and run only for explicitly configured boards, sites, or companies. They store no candidate, application, resume, candidate email, screening answer, or raw HTML content. Job descriptions are normalized in memory, relevant terms are extracted, and changed postings update one deterministic signal instead of creating duplicates.

## Product direction

The complete native workspace will consolidate:

- companies, establishments, brands, subsidiaries, groups, domains, assets, and relationships;
- open tenders, historical awards, contracts, published incumbents, providers, end dates, and estimated renewals;
- technologies, products, versions, vulnerabilities, advisories, public exposures, and confidence;
- incidents, claims, confirmations, regulatory events, news, recruitment, and business changes;
- professional roles, organization charts, buying committees, public or licensed business emails, switchboards, direct business numbers, contact forms, and role mailboxes;
- alerts, watchlists, saved searches, opportunities, tasks, notes, assignments, engagement history, and dashboards.

Professional contact records require provenance, permitted purpose, freshness, retention, correction, objection, and suppression state. Home addresses, family details, private phones, private emails, credentials, private messages, and leaked personal datasets are excluded.

## Product flow

```text
approved source registry
  -> policy decision before network
  -> bounded transport and strict provider schema
  -> immutable observation metadata
  -> normalized organization, evidence, and signal
  -> versioned need hypothesis and score
  -> native alert, company workspace, task, and opportunity lifecycle
```

## Architecture

The backend is a Python 3.12 modular monolith using FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic, and durable scheduler/worker orchestration. The analyst UI is a Next.js application under `apps/web`.

Provider payloads stay inside adapter packages. Domain modules do not import frameworks or infrastructure implementations. External adapters produce approved observations and projections through application contracts rather than importing canonical persistence implementations.

The public-job subsystem now uses one canonical provider-independent contract. Greenhouse, Lever, and SmartRecruiters retain their own strict transport schemas but produce the same organization, evidence, observation, signal, checkpoint, and opportunity behavior.

## Development quality gates

Every pull request must pass on one final SHA:

1. dependency consistency and security audits;
2. Ruff;
3. Mypy strict;
4. architecture, complexity, dependency, release, and roadmap contracts;
5. reversible PostgreSQL migrations;
6. complete backend line and branch coverage with a 90% minimum;
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
- UTC-aware persistence is normalized across SQLite and PostgreSQL;
- roadmap lots must be continuous and status-consistent.

See [`docs/DEVELOPMENT_STANDARDS.md`](docs/DEVELOPMENT_STANDARDS.md) and [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md).

## Delivery roadmap

[`docs/PROJECT_DELIVERY_PLAN.md`](docs/PROJECT_DELIVERY_PLAN.md) defines lots `00` through `26` with dependencies, deliverables, tests, exit gates, and non-goals.

Lots `00` through `07` are implemented and validated. They cover governance, persistence, durable orchestration, opportunities, TED, BOAMP, executable architecture gates, and canonical public hiring signals from Greenhouse, Lever, and SmartRecruiters.

The next locked lot is `08`: French and European organization identity through official company registries, with legal-unit, establishment, alias, status, parent-group, and non-diffusion handling.

The roadmap explicitly treats Cyber Intelligence Platform as the authoritative commercial workspace. Lot 20 implements native alerts, tasks, queues, opportunity stages, assignments, notes, and engagement history rather than synchronizing Salesforce or HubSpot.

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

Never commit API keys, sessions, prospect lists, collected personal data, proprietary datasets, or production evidence. Tests use synthetic, provider-published, minimized, or redistributable fixtures.

The source registry is authoritative. Quarantined or unapproved sources have no executable collection path. Browser automation remains deferred until structured APIs are insufficient and an isolated browser plus download-quarantine runtime has passed its own gate.

OSINT Framework and other tool catalogs are discovery inputs only. Every imported entry must pass source-owner, terms, licence, privacy, security, provenance, rate, retention, and purpose review before an adapter can execute it.

LinkedIn collection remains disabled unless official API scopes or reviewed written authorization covers the exact method, hosts, paths, fields, and purpose. A warning checkbox is not an authorization mechanism.

## Project documents

- [`docs/PRODUCT.md`](docs/PRODUCT.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md)
- [`docs/SOURCE_POLICY.md`](docs/SOURCE_POLICY.md)
- [`docs/OSINT_COLLECTION_CATALOG.md`](docs/OSINT_COLLECTION_CATALOG.md)
- [`docs/DEVELOPMENT_STANDARDS.md`](docs/DEVELOPMENT_STANDARDS.md)
- [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md)
- [`docs/PROJECT_DELIVERY_PLAN.md`](docs/PROJECT_DELIVERY_PLAN.md)
- [`SECURITY.md`](SECURITY.md)
