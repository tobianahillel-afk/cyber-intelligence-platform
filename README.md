# Cyber Intelligence Platform

Cyber Intelligence Platform is a human-operated cyber revenue intelligence workspace. It collects authorized public or licensed cyber, company, technology, commercial, and professional-role signals to identify organizations that may currently or soon need cybersecurity services or products.

The product is designed to answer:

1. Which organization should be reviewed?
2. What cybersecurity need or buying signal was detected?
3. Which evidence supports the conclusion?
4. Which professional roles or people are relevant?
5. Which offer should be proposed, and why now?

## Product experience

The analyst interface includes:

- a Command Center for urgent changes and source health;
- an Opportunity Inbox for triage and qualification;
- complete Organization Workspaces;
- timelines, technologies, vulnerability relevance, incidents, tenders, contracts, jobs, and transformation signals;
- organization charts and buying committees;
- professional-contact provenance and freshness;
- a Research Workspace for approved searches and browser research jobs;
- a Source Operations area for connector health, permissions, schedules, and quotas;
- an Offer Catalog used by the opportunity engine.

## Core capabilities

- organization, group, subsidiary, domain, and infrastructure intelligence;
- public incident, ransomware-claim, breach, and disruption monitoring;
- technology and vulnerability correlation;
- tenders, contract awards, renewal-window estimates, hiring, and transformation signals;
- professional organization mapping and decision-role identification;
- evidence-backed need detection and explainable opportunity scoring;
- saved searches and approved dork templates;
- freshness, confidence, provenance, retention, suppression, and deletion controls;
- human-reviewed export and CRM workflows.

## Architecture

The initial system is a **modular monolith**, not a collection of premature microservices. The API, workers, scheduler, and web application are separate entry points over strongly isolated business modules.

```text
apps/
  api/                         FastAPI composition root
  worker/                      background processing
  scheduler/                   recurring-job entry point
  web/                         Next.js analyst interface

src/cip/
  shared/                      kernel, configuration, security, observability
  modules/                     bounded business contexts
  adapters/                    sources, browsers, search, storage, messaging

packages/
  contracts/                   generated API and event contracts
  ui/                          reusable design-system components
  source_sdk/                  adapter SDK and contract-test kit

infra/                         containers, migrations, monitoring
policies/                      machine-readable source and retention policies
tests/                         architecture, integration, and end-to-end tests
```

Important module boundaries include source governance, collection, organizations, professional intelligence, cyber intelligence, technologies, vulnerabilities, commercial intelligence, evidence, entity resolution, need detection, opportunities, research, notifications, and integrations.

## Modularity rules

- Functions target 40 logical lines or fewer; review is mandatory above 70.
- Handwritten Python and TypeScript files target 300 lines or fewer; review is mandatory above 500.
- React components target 200 lines or fewer.
- API routes contain transport logic only.
- Domain code does not import FastAPI, SQLAlchemy, Redis, browser libraries, or HTTP clients.
- Source adapters do not resolve organizations or calculate opportunities.
- Opportunity rules consume canonical evidence-backed signals, not provider payloads.
- Cross-module operations use application interfaces or events, never another module's repositories.

## Operating principles

1. **Human in the loop.** Automation collects and prioritizes; a human reviews conclusions and controls outreach.
2. **Evidence before scoring.** Every alert, relationship, score, and recommendation links to provenance.
3. **Freshness-aware.** Observations record first seen, last seen, collected, verified, and expiry timestamps.
4. **Public, licensed, or explicitly authorized sources.** Each source has a machine-readable policy and activation state.
5. **Passive by default.** No intrusive scan, exploitation, authentication attempt, or unsolicited security test.
6. **No stolen-data repository.** Do not store credentials, victim files, private communications, or extorted datasets.
7. **Professional-data minimization.** Collect only information relevant to a professional role and documented B2B purpose.
8. **Reversible inference.** Entity merges, technology matches, and scores can be rejected and recomputed.
9. **Safe browser automation.** Browser workers are isolated, allowlisted, rate-limited, audited, and kill-switch controlled.
10. **No autonomous outreach.** No message leaves the system without explicit human action.

## Documentation

- [`docs/PRODUCT.md`](docs/PRODUCT.md): initial product definition and workflows
- [`docs/PRODUCT_ARCHITECTURE.md`](docs/PRODUCT_ARCHITECTURE.md): complete product, backend, pipeline, module, and repository architecture
- [`docs/UI_UX.md`](docs/UI_UX.md): analyst navigation, screens, tables, timelines, alerts, and interaction rules
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): technical components and trust boundaries
- [`docs/DEVELOPMENT_STANDARDS.md`](docs/DEVELOPMENT_STANDARDS.md): file-size budgets, dependency rules, testing, and code-review standards
- [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md): canonical entities and relationships
- [`docs/SOURCE_POLICY.md`](docs/SOURCE_POLICY.md): source authorization and collection policy
- [`SECURITY.md`](SECURITY.md): repository and platform security requirements

## Initial implementation sequence

1. Analyst application shell and navigation.
2. Organization, evidence, signal, need, and opportunity backbone.
3. Source registry, durable jobs, source SDK, and one official feed.
4. Opportunity Inbox and Organization Workspace with live backend data.
5. Research Workspace and isolated browser-worker interface.
6. Tenders, contracts, renewals, jobs, and transformation signals.
7. Professional roles, buying committees, contact provenance, and CRM export.

## Current status

Architecture and bootstrap phase. The repository contains the first FastAPI endpoint, canonical models, source-policy validation, tests, and CI configuration. The next implementation slice is the analyst shell and opportunity backbone.

## Security

Do not commit API keys, authentication material, personal-data exports, leaked datasets, or proprietary source content. The repository is currently public, so all runtime secrets and collected business data must remain outside Git.
