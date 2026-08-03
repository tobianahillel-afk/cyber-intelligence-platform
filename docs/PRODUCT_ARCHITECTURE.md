# Product Architecture

## Product objective

Cyber Intelligence Platform is a human-operated cyber revenue intelligence workspace. It continuously collects authorized public or licensed signals, resolves them to organizations and professional roles, detects commercial cybersecurity needs, and presents explainable opportunities to an analyst.

The product must answer five questions for every opportunity:

1. Which organization should be reviewed?
2. What current or future cybersecurity need was detected?
3. Which evidence supports that conclusion?
4. Which professional roles or people are relevant?
5. Which service or product should be proposed, and why now?

## Product principles

- Human-in-the-loop: collection and scoring may be automated; outreach and sensitive conclusions require explicit analyst action.
- Evidence-first: every alert, relationship, score, and recommendation links to provenance.
- Freshness-aware: every observation has first-seen, last-seen, collected, verified, and expiry timestamps.
- Modular monolith first: one deployable backend with strict package boundaries; extract services only when operational scale requires it.
- Adapter-based collection: one source adapter cannot modify another source or domain module.
- Small units: modules, classes, functions, API routes, and UI components have explicit size limits.
- Reversible inference: entity merges, technology matches, and opportunity scores can be rejected or recomputed.
- Safe browser automation: browser workers run in isolated sandboxes with source allowlists, quotas, audit logs, download restrictions, and no access to application secrets unrelated to their job.

## Human workflow

```text
Signals arrive
    -> normalized observations
    -> organization resolution
    -> evidence graph
    -> need detection
    -> opportunity scoring
    -> alert inbox
    -> analyst review
    -> organization workspace
    -> contact and buying-committee review
    -> offer recommendation
    -> export or CRM action
    -> follow-up and outcome
```

## Main product areas

### 1. Command Center

The landing page shows what requires attention now:

- urgent incident opportunities;
- newly detected high-confidence exposures;
- tenders and contract-renewal windows;
- new buying signals;
- opportunities whose score changed materially;
- source failures and stale coverage;
- tasks awaiting human review.

### 2. Opportunity Inbox

A triage queue for commercial opportunities. Each card shows:

- organization;
- need type;
- recommended offer;
- priority and confidence;
- freshness;
- strongest evidence;
- relevant contact roles;
- unresolved warnings;
- next recommended action.

The analyst can accept, reject, snooze, assign, merge, or request enrichment.

### 3. Organization Workspace

A complete workspace with tabs:

- Overview
- Timeline
- Needs and opportunities
- External footprint
- Technologies
- Vulnerability relevance
- Incidents and claims
- Contracts and tenders
- Jobs and transformation signals
- Organization chart
- Professional contacts
- Evidence
- Notes and tasks
- Audit and compliance

### 4. Research Workspace

Used for analyst-triggered research:

- organization or domain search;
- saved searches;
- approved dork templates;
- browser research jobs;
- source-by-source enrichment;
- evidence capture;
- entity comparison and merge review.

### 5. Source Operations

Used to control ingestion:

- source registry;
- activation state;
- licence and authorization records;
- schedules and quotas;
- connector health;
- latest successful collection;
- lag and failure rates;
- data categories collected;
- retention and deletion rules;
- dead-letter records.

### 6. Contact and Buying Committee

Presents roles before people. It must distinguish:

- economic buyer;
- technical buyer;
- security owner;
- operational user;
- procurement;
- legal, privacy, or risk stakeholder;
- executive sponsor.

For named professional contacts, show source, recency, confidence, role relevance, contact channel, objection status, and retention deadline.

### 7. Offer Catalog

A configurable catalog of what the user can sell:

- incident response;
- forensic investigation;
- pentest;
- external exposure audit;
- Active Directory audit;
- cloud security audit;
- SIEM or CMDR;
- SOC or MDR;
- compliance and governance;
- IAM or PAM;
- vulnerability management;
- awareness and training.

Each offer defines qualifying signals, disqualifying conditions, target roles, evidence requirements, messaging constraints, and recommended timing.

## Opportunity lifecycle

```text
candidate
-> enriched
-> needs_review
-> qualified
-> ready_for_outreach
-> contacted
-> engaged
-> won | lost | disqualified | suppressed
```

Additional states:

- `snoozed`: wait until a future date or signal;
- `monitoring`: evidence is not yet sufficient;
- `expired`: underlying signals are stale;
- `blocked`: compliance, data-quality, or source-policy issue.

Every transition records actor, timestamp, reason, previous state, and evidence context.

## Opportunity families

### Crisis opportunity

Signals include official incident disclosures, credible service disruption, confirmed breach notifications, ransomware claims, and regulator notices.

### Exposure opportunity

Signals include passive technology observations, publicly indexed exposure metadata, certificate or mail-security weaknesses, relevant KEV entries, and high-confidence vulnerable-version matches.

### Buying-intent opportunity

Signals include tenders, job openings, SOC creation, cloud migration, security transformation, certification programs, and explicit requests for suppliers.

### Renewal opportunity

Signals include contract award date, contract duration, optional renewals, known incumbent, procurement cycle, budget cycle, and replacement indicators.

### Product-fit opportunity

Signals indicate that an organization may benefit from SIEM, CMDR, SOC, MDR, pentest, compliance, or another configured offer even without an immediate crisis.

## Backend bounded contexts

The backend is a modular monolith. Each context owns its domain logic, database access interface, application services, API routes, events, and tests.

### Identity and access

Users, teams, roles, permissions, sessions, API keys, and audit identity.

### Source governance

Source policies, authorizations, licences, schedules, quotas, allowed data categories, retention, and connector activation.

### Collection orchestration

Job creation, scheduling, cursors, retries, backoff, browser sessions, rate limits, dead letters, and collection telemetry.

### Raw observations

Immutable source envelopes and permitted snapshots. No business conclusions are made here.

### Normalization

Source-specific records become canonical observations with schema validation and provenance.

### Organizations

Legal entities, brands, groups, subsidiaries, sites, identifiers, domains, and ownership relationships.

### Professional intelligence

Professional roles, named business contacts, organization-chart relationships, buying committees, contact provenance, suppression, and retention.

### Cyber intelligence

Cyber events, claims, threat actors, incidents, advisories, indicators, and public confirmations.

### Technology intelligence

Technologies, products, versions, observations, vendors, infrastructure relationships, and observation expiry.

### Vulnerability intelligence

CVE, advisories, CPE and package identifiers, KEV, EPSS, affected ranges, and remediation metadata.

### Commercial intelligence

Tenders, contract awards, renewal estimates, job signals, funding, acquisitions, transformation initiatives, and budget-cycle signals.

### Evidence and provenance

Evidence records, claims, contradictions, snapshots, source references, content hashes, review state, and confidence.

### Entity resolution

Candidate matching, merge proposals, analyst decisions, alias history, reversible links, and confidence scoring.

### Need detection

Rules and models that convert evidence-backed signals into candidate cybersecurity needs.

### Opportunity engine

Opportunity aggregation, scoring, prioritization, freshness decay, explanation, offer matching, lifecycle, and assignment.

### Research

Saved searches, dork templates, browser research jobs, result review, evidence capture, and analyst notes.

### Notifications

In-product alerts, email summaries, webhooks, subscriptions, deduplication, and acknowledgement.

### Integrations

CRM, ticketing, calendar, messaging, and export adapters. Integrations consume application APIs; they do not query internal tables directly.

## Recommended repository layout

```text
apps/
  api/                         FastAPI composition root
  worker/                      background worker composition root
  scheduler/                   schedule and recurring-job entry point
  web/                         Next.js analyst interface

src/cip/
  shared/
    kernel/                    IDs, time, results, domain events
    config/                    settings and feature flags
    observability/             logs, traces, metrics
    security/                  auth helpers, redaction, encryption
    testing/                   factories and shared test helpers

  modules/
    identity/
    source_governance/
    collection/
    raw_observations/
    normalization/
    organizations/
    professional_intelligence/
    cyber_intelligence/
    technology_intelligence/
    vulnerability_intelligence/
    commercial_intelligence/
    evidence/
    entity_resolution/
    need_detection/
    opportunities/
    research/
    notifications/
    integrations/

  adapters/
    sources/                   one directory per external source
    browsers/                  browser runtime implementations
    search_providers/          search API adapters
    storage/                   PostgreSQL, OpenSearch, Redis, S3
    messaging/                 queue implementation

packages/
  contracts/                   generated API and event schemas
  ui/                          reusable design-system components
  source_sdk/                  source-adapter SDK and test kit

infra/
  docker/
  compose/
  migrations/
  monitoring/

docs/
  adr/                         architecture decision records
  modules/                     module contracts and ownership
  sources/                     source-specific reviews
  runbooks/                    operational procedures

tests/
  architecture/
  integration/
  end_to_end/
```

## Standard backend module layout

Each module uses the same internal structure:

```text
module_name/
  domain/
    entities.py
    value_objects.py
    events.py
    policies.py
  application/
    commands/
    queries/
    services/
    ports.py
  infrastructure/
    repositories/
    consumers/
    providers/
  api/
    routes.py
    schemas.py
    dependencies.py
  tests/
```

Rules:

- `domain` imports only the shared kernel and Python standard library.
- `application` depends on domain and declared ports.
- `infrastructure` implements ports.
- `api` calls application services; routes contain no business logic.
- cross-module calls use application interfaces or domain events, never another module's repository.

## Source adapter layout

```text
adapters/sources/<source_id>/
  manifest.yml
  client.py
  collector.py
  parser.py
  mapper.py
  schemas.py
  fixtures/
  tests/
  README.md
```

Responsibilities:

- `manifest.yml`: source status, authorization, data categories, schedule, rate limits, retention, and owner;
- `client.py`: transport only;
- `collector.py`: pagination, cursors, batching, retries;
- `parser.py`: source payload validation;
- `mapper.py`: mapping to raw observation envelopes;
- `tests`: contract, fixture, pagination, rate-limit, and failure tests.

A source adapter never writes directly to organization, person, opportunity, or evidence tables.

## Browser research architecture

Browser automation is separated from API collectors.

```text
research request
-> policy decision
-> browser-job queue
-> isolated browser worker
-> approved host navigation
-> metadata and permitted content extraction
-> artifact screening and redaction
-> evidence review queue
```

Browser workers must use:

- ephemeral browser profiles;
- no shared analyst cookies by default;
- domain and path allowlists;
- per-source rate and concurrency limits;
- download blocking unless explicitly permitted;
- maximum page and artifact sizes;
- navigation timeouts;
- screenshot and trace policies;
- malware-safe storage;
- full audit logs;
- kill switch per source.

## Frontend architecture

Use Next.js, React, and TypeScript with feature-oriented folders.

```text
apps/web/src/
  app/                         routes and layouts
  features/
    command_center/
    opportunities/
    organizations/
    research/
    sources/
    contacts/
    offers/
    alerts/
    settings/
  entities/                    typed client-side domain models
  shared/
    api/
    auth/
    components/
    hooks/
    tables/
    charts/
    forms/
    state/
    utils/
```

Frontend rules:

- route files compose features and do not contain business logic;
- server state is managed through a query library, not copied into global state;
- URL parameters preserve filters, sorting, tabs, and selected date ranges;
- tables support saved views and column configuration;
- every score and warning has an explanation drawer;
- sensitive fields are permission-gated and redacted by default;
- long-running research jobs show progress and partial results;
- keyboard navigation and accessible labels are mandatory.

## UI navigation

Primary navigation:

1. Command Center
2. Opportunities
3. Organizations
4. Research
5. Alerts
6. Contacts
7. Offers
8. Sources
9. Tasks
10. Settings

Global UI elements:

- universal search;
- freshness indicator;
- source-health indicator;
- active research jobs;
- notification center;
- analyst task queue;
- quick organization lookup;
- global date and geography filters where relevant.

## API design

Use resource APIs for read models and command endpoints for meaningful transitions.

Examples:

```text
GET  /v1/opportunities
GET  /v1/opportunities/{id}
POST /v1/opportunities/{id}/qualify
POST /v1/opportunities/{id}/reject
POST /v1/opportunities/{id}/snooze
POST /v1/opportunities/{id}/request-enrichment

GET  /v1/organizations/{id}
GET  /v1/organizations/{id}/timeline
GET  /v1/organizations/{id}/technologies
GET  /v1/organizations/{id}/contacts
GET  /v1/organizations/{id}/evidence

POST /v1/research/jobs
GET  /v1/research/jobs/{id}
POST /v1/research/jobs/{id}/cancel

GET  /v1/sources
POST /v1/sources/{id}/pause
POST /v1/sources/{id}/resume
GET  /v1/sources/{id}/health
```

Requirements:

- cursor pagination for large lists;
- explicit filtering and sorting contracts;
- idempotency keys for commands;
- optimistic concurrency for analyst edits;
- generated OpenAPI client for the frontend;
- no API response exposes raw secrets or unrestricted source payloads.

## Events and asynchronous processing

Use durable jobs and domain events.

Representative events:

```text
observation.collected
observation.normalized
organization.resolution_requested
organization.link_changed
evidence.created
cyber_event.updated
technology.observed
vulnerability.relevance_changed
commercial_signal.created
need.detected
opportunity.created
opportunity.score_changed
opportunity.state_changed
contact.suppressed
source.health_changed
```

Consumers must be idempotent. Event payloads contain identifiers and minimal context, not complete personal or raw source records.

## File and function size budgets

These are review thresholds, not arbitrary style rules:

- function: target <= 40 logical lines; hard review at 70;
- class: target <= 250 lines; hard review at 400;
- Python or TypeScript source file: target <= 300 lines; hard review at 500;
- React component: target <= 200 lines; split presentation, data loading, and state logic;
- API route module: target <= 250 lines;
- source adapter file: target <= 300 lines;
- test file: target <= 500 lines;
- no generated file is included in these limits.

A size exception requires a comment or ADR explaining why separation would reduce clarity.

## Dependency rules

- No circular module dependencies.
- No module imports another module's infrastructure package.
- Domain code never imports FastAPI, SQLAlchemy, Redis, browser libraries, or HTTP clients.
- External provider schemas never escape their adapter.
- Opportunity rules consume canonical signals, not source-specific payloads.
- UI features use generated contracts and cannot depend on backend implementation details.

Architecture tests should enforce these rules.

## Quality gates

Every module or adapter requires:

- unit tests for domain logic;
- schema and contract tests;
- integration tests for persistence or provider boundaries;
- failure and retry tests for collectors;
- authorization and redaction tests;
- architecture dependency tests;
- type checking;
- linting;
- migration review when persistence changes;
- observability for background work.

## Initial implementation slices

### Slice 1: analyst shell

- application navigation;
- Command Center placeholder;
- Opportunity Inbox with fixture data;
- Organization Workspace shell;
- shared UI components and generated API client.

### Slice 2: opportunity backbone

- organizations;
- evidence;
- canonical signals;
- need detection;
- opportunity lifecycle and explainable score;
- list and detail APIs.

### Slice 3: collection platform

- source registry;
- schedules;
- durable jobs;
- source SDK;
- one official feed adapter;
- connector health UI.

### Slice 4: research workspace

- research-job model;
- approved search-provider adapter;
- isolated browser worker interface;
- result review and evidence capture.

### Slice 5: commercial intelligence

- tenders;
- contract awards;
- renewal estimation;
- jobs and transformation signals;
- offer matching.

### Slice 6: professional intelligence

- roles and buying committees;
- named professional contacts;
- provenance, freshness, suppression, and retention;
- CRM export interface.

## Non-goals for the architecture phase

- splitting every module into an independent service;
- building a generic web crawler before source contracts exist;
- allowing arbitrary browser navigation from user-provided URLs;
- coupling scoring directly to one vendor or feed;
- autonomous outreach;
- storing raw sensitive or compromised datasets as prospecting material.
