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

The platform does not treat Chromium as a universal fallback. Browser jobs run in isolated workers with fresh contexts, source-specific network allowlists, time and page budgets, download restrictions, audit logs, and kill switches.

Downloads enter a quarantine pipeline before parsing:

```text
download
-> isolated temporary storage
-> hash, size, and type validation
-> archive and malware controls
-> sandboxed parser
-> redacted normalized output
-> evidence or rejection
```

CAPTCHA, bot challenges, MFA, changed terms, or account-security prompts produce a safe pause and human task. They are not automatically bypassed.

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

Important module boundaries include source governance, collection, raw observations, normalization, organizations, professional intelligence, cyber intelligence, technologies, vulnerabilities, commercial intelligence, evidence, entity resolution, need detection, opportunities, research, notifications, and integrations.

## Adapter architecture

Every source or external tool is isolated under its own adapter and split by responsibility:

```text
adapters/sources/<source_id>/
  manifest.yml
  auth/
  transport/
  discovery/
  extraction/
  parsing/
  mapping/
  runtime/
  fixtures/
  tests/
  README.md
```

A source adapter handles authentication, retrieval, parsing, mapping, checkpoints, and health for one provider. It never performs entity resolution or calculates commercial opportunities.

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

Every UI value remains traceable to the source record, collection job, adapter version, and evidence that produced it.

## Modularity rules

- Functions target 40 logical lines or fewer; review is mandatory above 70.
- Handwritten Python and TypeScript files target 300 lines or fewer; review is mandatory above 500.
- React components target 200 lines or fewer.
- API routes contain transport logic only.
- Domain code does not import FastAPI, SQLAlchemy, Redis, browser libraries, or HTTP clients.
- Source adapters do not resolve organizations or calculate opportunities.
- Opportunity rules consume canonical evidence-backed signals, not provider payloads.
- Cross-module operations use application interfaces or events, never another module's repositories.

## Test quality gates

- at least 90% line coverage;
- at least 90% branch coverage for handwritten backend code;
- at least 95% changed-file coverage;
- at least 95% line and branch coverage for critical policy and scoring modules;
- parser fixtures and adapter contract tests for every source;
- browser tests for login, session expiry, MFA, CAPTCHA detection, selector changes, downloads, crashes, and isolation;
- security tests for SSRF, redirects, DNS rebinding, redaction, hostile files, archives, and authorization;
- integration, migration, resilience, performance, data-quality, architecture, API, and UI end-to-end suites.

The Python CI currently fails below 90% branch-aware coverage.

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
- [`docs/ACQUISITION_ARCHITECTURE.md`](docs/ACQUISITION_ARCHITECTURE.md): API, HTTP, Chromium, authentication, challenge handling, downloads, isolation, and updates
- [`docs/SOURCE_ADAPTER_STANDARD.md`](docs/SOURCE_ADAPTER_STANDARD.md): standard source/tool folder structure, file responsibilities, checkpoints, account lifecycle, and adapter tests
- [`docs/NORMALIZATION_PIPELINE.md`](docs/NORMALIZATION_PIPELINE.md): raw-to-canonical layers, deduplication, entity resolution, freshness, change processing, and lineage
- [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md): coverage targets and the complete test-suite design
- [`docs/DEVELOPMENT_STANDARDS.md`](docs/DEVELOPMENT_STANDARDS.md): file-size budgets, dependency rules, testing, and code-review standards
- [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md): canonical entities and relationships
- [`docs/SOURCE_POLICY.md`](docs/SOURCE_POLICY.md): source authorization and collection policy
- [`docs/adr/0001-modular-monolith.md`](docs/adr/0001-modular-monolith.md): modular-monolith decision
- [`docs/adr/0002-multi-mode-acquisition.md`](docs/adr/0002-multi-mode-acquisition.md): HTTP, browser, assisted session, and quarantine decision
- [`SECURITY.md`](SECURITY.md): repository and platform security requirements

## Initial implementation sequence

1. Analyst application shell and navigation.
2. Organization, evidence, signal, need, and opportunity backbone.
3. Source registry, durable jobs, source SDK, and one official API or feed.
4. Static HTTP and incremental-update framework.
5. Isolated browser-worker and download-quarantine framework.
6. Opportunity Inbox and Organization Workspace with live backend data.
7. Research Workspace and analyst-assisted job handling.
8. Tenders, contracts, renewals, jobs, and transformation signals.
9. Professional roles, buying committees, contact provenance, and CRM export.

## Current status

Architecture and bootstrap phase. The repository contains the first FastAPI endpoint, canonical models, source-policy validation, tests, CI configuration, and detailed product, acquisition, normalization, adapter, UI, and testing architecture.

## Security

Do not commit API keys, authentication material, personal-data exports, leaked datasets, or proprietary source content. The repository is currently public, so all runtime secrets and collected business data must remain outside Git.
