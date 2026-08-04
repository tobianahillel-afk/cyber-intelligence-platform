# Cyber Intelligence Platform

Cyber Intelligence Platform is a human-operated cyber revenue intelligence workspace. It collects authorized public or licensed cyber, company, technology, commercial, and professional-role signals to identify organizations that may currently or soon need cybersecurity services or products.

The product is designed to answer:

1. Which organization should be reviewed?
2. What cybersecurity need or buying signal was detected?
3. Which evidence supports the conclusion?
4. Which professional roles are relevant?
5. Which offer should be proposed, and why now?

## Current implementation status

The repository contains an executable foundation, a durable collection pipeline, and the first live opportunity workflow:

- FastAPI application factory, source-governance endpoints, and opportunity list/detail/action APIs;
- framework-independent domain modules for organizations, evidence, cyber events, raw observations, opportunity scoring, retention, suppression, source accounts, product metrics, collection orchestration, and analyst-reviewed opportunities;
- explicit source policies, authorization records, runtime state, and collection decisions;
- PostgreSQL persistence models and reversible Alembic migrations;
- local PostgreSQL through Docker Compose;
- HMAC-SHA256 suppression records without raw contact identifiers;
- executable retention rules;
- machine-readable source and collection-schedule registries;
- an official CISA KEV feed adapter with conditional HTTP requests, size/type checks, strict schemas, checkpoints, provenance, and network-free tests;
- durable collection jobs with deterministic idempotency keys, leases, retries, bounded exponential backoff, circuit breakers, dead letters, and recovery after interruption;
- atomic observation/checkpoint/job completion and observation deduplication;
- source freshness, queue lag, error, dead-letter, and volume metrics;
- separate `cip-scheduler` and `cip-worker` process entry points;
- normalized commercial signals, need hypotheses, evidence links, and persistent opportunity lifecycle;
- a versioned SIEM/SOC buying-intent rule using public-tender and security-operations hiring signals;
- explainable score components for tender intent, hiring, corroboration, freshness, confidence, and single-source uncertainty;
- analyst qualification, rejection, snooze, enrichment request, reopen, score-component override, and immutable review history;
- a Next.js Opportunity Inbox and detail workspace backed by FastAPI and PostgreSQL, with no demonstration fixtures;
- loading, empty, stale-context, backend-unavailable, and not-found UI states;
- pinned direct dependencies, dependency audits, Ruff, Mypy, migration validation, frontend build validation, and 90% branch-aware coverage gates;
- Dependabot, CODEOWNERS, contribution rules, a PR template, and manually runnable CodeQL.

Not yet implemented:

- production adapters that produce the MVP tender and job-posting commercial signals, such as BOAMP, TED, or authorized careers/ATS sources;
- Chromium/browser workers and download quarantine runtime;
- named professional-contact enrichment and organization-chart workflows;
- OpenSearch, Redis, object storage, CRM integration, or autonomous outreach;
- active LinkedIn collection;
- any executable BrixHub integration.

The live opportunity pipeline currently consumes normalized commercial signals. It does not claim that BOAMP, TED, job boards, LinkedIn, or other future sources are already connected.

Redis is not required for the current durable queue: PostgreSQL owns scheduling, locking, leases, checkpoints, and recovery. Redis should be introduced only when measured throughput or coordination requirements justify it.

## Local setup

Requirements:

- Python 3.12;
- Docker with Compose;
- Node.js 24 for the current frontend toolchain.

```bash
cp .env.example .env
docker compose up -d postgres
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
alembic upgrade head
cip-api
```

On PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up -d postgres
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
alembic upgrade head
cip-api
```

Start the scheduler and worker in separate terminals:

```bash
cip-scheduler
cip-worker
```

The scheduler reads `policies/collection_schedules.yml`, synchronizes the authorized source registry, and creates at most one active job per source/adapter. The worker claims jobs with a bounded lease, performs source access outside the database transaction, and commits observations, checkpoint advancement, and job completion atomically.

Start the UI separately:

```bash
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```

The API is available on `http://127.0.0.1:8000` by default. The Next.js server uses `CIP_API_BASE_URL` to load and update the Opportunity Inbox. With no commercial signals in PostgreSQL, the UI displays an explicit empty state rather than synthetic records.

## Validation

```bash
python -m pip check
pip-audit --skip-editable
ruff check .
mypy
alembic upgrade head
alembic downgrade base
alembic upgrade head
pytest --cov=cip --cov-branch --cov-fail-under=90

cd apps/web
npm install
npm audit --audit-level=high
npm run typecheck
npm run build
```

The live-opportunity phase was independently validated with 256 passing tests and 94.94% combined line-and-branch coverage. Mypy strict passed on 94 source files, migration `0004` passed the PostgreSQL upgrade/downgrade/upgrade cycle, and the Next.js audit, typecheck, and production build passed.

## Architecture

The system begins as a modular monolith with separate API, worker, scheduler, and frontend composition roots. Domain modules do not depend on FastAPI, SQLAlchemy, HTTP clients, Redis, or browser libraries.

```text
apps/
  web/                         Next.js analyst application

src/cip/
  shared/                      time, configuration, persistence
  modules/                     bounded business contexts
  adapters/                    isolated external-source integrations

infra/
  migrations/                  reversible Alembic revisions

policies/
  sources.example.yml          source and authorization registry
  collection_schedules.yml     cadence, lease, retry, and circuit settings
  retention.yml                executable retention and suppression policy
  product_metrics.yml          quality and commercial-value targets

tests/
  unit/                        domain, adapter, governance, persistence, and recovery tests
  integration/                 persisted signal-to-opportunity workflows
```

## Durable collection lifecycle

```text
source registry synchronization
-> deterministic schedule slot
-> idempotent job enqueue
-> transactional claim with SKIP LOCKED
-> bounded worker lease
-> policy-checked source collection
-> validation and raw-observation mapping
-> atomic observation insert + checkpoint advance + job completion
-> retry/circuit breaker/dead letter on failure
-> freshness and queue metrics
```

A replayed schedule slot cannot create a duplicate job. A replayed observation cannot create a duplicate raw record. If execution stops before the completion transaction commits, the previous checkpoint remains authoritative. A worker whose lease expired cannot commit a late result.

## Opportunity lifecycle

```text
normalized commercial signal
-> idempotent signal persistence
-> versioned SIEM/SOC need rule
-> explainable score and freshness
-> persistent need hypothesis
-> Opportunity Inbox and detail API
-> analyst qualification, rejection, snooze, enrichment, or reopen
-> immutable review history
-> automatic recalculation preserving analyst overrides
```

The first rule family detects possible SIEM/SOC buying intent from normalized public-tender and security-operations hiring signals. A single source remains visible as `partial`, receives a score penalty, and requires analyst validation. Corroborating evidence from independent source families raises confidence and data quality.

The browser cannot directly create an opportunity. Opportunities are produced by the backend from evidence-linked normalized signals. Analyst score overrides are retained during later automatic recalculations, while the latest generated baseline remains visible.

## Acquisition model

A source uses the least complex authorized method that can reliably retrieve the required evidence:

```text
official API
-> feed or bulk export
-> static HTTP
-> isolated Chromium browser
-> analyst-assisted browser session
-> manual import
```

The current executable source adapter uses the official CISA KEV JSON feed. Chromium is intentionally deferred until API and static-HTTP acquisition, normalization, provenance, and value metrics are stable.

CAPTCHA, bot challenges, MFA, changed terms, or account-security prompts must produce a safe pause and human task. They are not automatically bypassed. Temporary-account rotation, copied cookies, CAPTCHA-solving services, and access-control circumvention are out of scope.

## Source governance

A collection request is permitted only when all applicable checks pass:

- source is enabled;
- data category is allowed and not prohibited;
- authorization is approved and unexpired;
- automation and raw storage are explicitly permitted;
- human review is complete when required;
- quota remains available;
- purpose, target host, and target path are approved.

LinkedIn entries remain disabled until the relevant application scopes or written authorization are recorded. BrixHub is present only as a quarantined governance record: no account creation, payment, network access, crawling, download, or import is enabled.

## Normalization layers

```text
L0 source response or artifact
L1 immutable raw observation envelope
L2 typed provider record
L3 canonical observation
L4 resolved entity links
L5 evidence-backed signal
L6 need hypothesis
L7 commercial opportunity
L8 UI and search read models
```

The CISA adapter currently implements L0 through L1. The live SIEM/SOC workflow implements L5 through L8 for normalized commercial signals. Future tender and job adapters must implement L0 through L5 and cannot bypass source governance, evidence provenance, or entity resolution.

## Code and test standards

- functions target at most 40 logical lines;
- handwritten source files target at most 300 lines;
- React components target at most 200 lines;
- API routes contain transport concerns only;
- source adapters never resolve organizations or calculate opportunities;
- scores are calculated by the domain and include a reproducible hash;
- timestamps must be timezone-aware;
- every adapter requires policy-denial, schema, mapping, checkpoint, and failure tests;
- backend line and branch coverage must remain at least 90%;
- critical policy and scoring modules target 95%.

## Documentation

- [`docs/PRODUCT_ARCHITECTURE.md`](docs/PRODUCT_ARCHITECTURE.md)
- [`docs/UI_UX.md`](docs/UI_UX.md)
- [`docs/ACQUISITION_ARCHITECTURE.md`](docs/ACQUISITION_ARCHITECTURE.md)
- [`docs/SOURCE_ADAPTER_STANDARD.md`](docs/SOURCE_ADAPTER_STANDARD.md)
- [`docs/NORMALIZATION_PIPELINE.md`](docs/NORMALIZATION_PIPELINE.md)
- [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md)
- [`docs/DEVELOPMENT_STANDARDS.md`](docs/DEVELOPMENT_STANDARDS.md)
- [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md)
- [`docs/SOURCE_POLICY.md`](docs/SOURCE_POLICY.md)
- [`SECURITY.md`](SECURITY.md)
- [`CONTRIBUTING.md`](CONTRIBUTING.md)

## Security

The repository is private, but secrets and collected data must still remain outside Git. Never commit API keys, passwords, cookies, tokens, private communications, victim files, leaked datasets, production contact exports, or proprietary provider content.
