# Cyber Intelligence Platform

Cyber Intelligence Platform is a human-operated cyber revenue intelligence workspace. It collects authorized public or licensed evidence, converts it into normalized commercial signals, and helps analysts identify organizations that may need cybersecurity services or products.

The platform is deliberately evidence-first: every opportunity must expose its source, timestamps, confidence, freshness, claim type, and review history. It does not autonomously contact prospects, validate credentials, exploit systems, or ingest leaked victim data.

## Current validated scope

Version `0.7.0` includes four durable official-source adapters:

- **CISA KEV** for known-exploited vulnerability metadata;
- **TED Search API** for active European cyber procurement notices;
- **BOAMP/DILA Explore API** for actionable French procurement notices;
- **Greenhouse Job Board API** for public cyber hiring signals from explicitly configured boards.

The Greenhouse path is GET-only. It stores no candidate, application, resume, email, or raw HTML content. Job descriptions are normalized in memory, relevant terms are extracted, and changed listings update the same deterministic signal and opportunity instead of creating duplicates.

## Product flow

```text
approved source registry
  -> policy decision before network
  -> bounded transport and strict provider schema
  -> immutable raw observation metadata
  -> normalized organization, evidence, and commercial signal
  -> versioned need hypothesis and score
  -> human-operated Opportunity Inbox
```

The current Inbox combines procurement intent and hiring evidence for SIEM/SOC-related needs. Analyst decisions remain explicit and auditable.

## Architecture

The backend is a Python 3.12 modular monolith using FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic, and durable scheduler/worker orchestration. The analyst UI is a Next.js application in `apps/web`.

Core boundaries include:

- source and authorization governance;
- collection scheduling, leases, checkpoints, retries, circuits, and dead letters;
- raw observations and evidence provenance;
- organization and opportunity persistence;
- versioned scoring and analyst review;
- retention and suppression;
- product and source-health metrics.

Provider schemas stay inside adapter packages. Domain modules cannot import frameworks or infrastructure implementations. External connectors cannot import canonical persistence implementations directly.

## Development quality gates

Every pull request must pass on one final SHA:

1. dependency consistency and security audits;
2. Ruff;
3. Mypy strict;
4. architecture, complexity, dependency, release, and roadmap contracts;
5. reversible PostgreSQL migrations;
6. complete backend line and branch coverage with a 90% minimum;
7. frontend dependency audit, TypeScript checking, and production build.

Additional executable rules include:

- application Python files: maximum 400 lines;
- functions/methods: maximum 120 lines;
- classes: maximum 300 lines;
- function parameters: maximum 10;
- control-flow nesting: maximum 6;
- no duplicate definitions in a module or class;
- no wildcard imports;
- one authoritative application/package/API version;
- unit tests cannot open live network connections;
- UTC-aware persistence is normalized consistently across SQLite and PostgreSQL.

See [`docs/DEVELOPMENT_STANDARDS.md`](docs/DEVELOPMENT_STANDARDS.md) and [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md).

## Delivery roadmap

The authoritative roadmap is [`docs/PROJECT_DELIVERY_PLAN.md`](docs/PROJECT_DELIVERY_PLAN.md). It defines lots `00` through `26`, including dependencies, detailed deliverables, test suites, exit gates, and non-goals.

Validated lots:

- `00` product, legal, and source governance;
- `01` modular core, persistence, provenance, and retention;
- `02` durable scheduler, worker, checkpoints, and recovery;
- `03` evidence-backed opportunity engine and Inbox;
- `04` TED procurement;
- `05` BOAMP procurement and executable architecture gates;
- `06` Greenhouse public cyber hiring signals.

The next locked lot is `07`: multi-ATS hiring-source expansion through separately reviewed official public APIs.

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

The phase-6 pre-closing validation passed **344 backend tests**, **94.62% line/branch coverage**, Mypy strict on **123 source files**, reversible PostgreSQL migrations, dependency audits, architecture gates, TypeScript, and the Next.js production build.

## Source and data safety

The repository is public. Never commit API keys, session material, real prospect lists, CRM exports, collected personal data, proprietary datasets, or production evidence. Use only synthetic, minimized, provider-published, or explicitly redistributable fixtures.

The source registry is authoritative. Quarantined or unapproved sources have no executable collection path. Browser automation remains deferred until structured APIs are insufficient and an isolated browser plus download-quarantine runtime has been validated.

## Project documents

- [`docs/PRODUCT.md`](docs/PRODUCT.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md)
- [`docs/SOURCE_POLICY.md`](docs/SOURCE_POLICY.md)
- [`docs/DEVELOPMENT_STANDARDS.md`](docs/DEVELOPMENT_STANDARDS.md)
- [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md)
- [`docs/PROJECT_DELIVERY_PLAN.md`](docs/PROJECT_DELIVERY_PLAN.md)
- [`SECURITY.md`](SECURITY.md)
