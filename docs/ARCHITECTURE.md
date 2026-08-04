# Architecture

## Architectural goals

- ingest high-volume heterogeneous sources without coupling the core domain to a specific provider;
- preserve provenance, conflicts, confidence, and freshness;
- separate collection, normalization, entity resolution, scoring, storage, and presentation;
- enforce source and privacy policy before any network request and before durable storage;
- provide an accountless read experience backed by stored data rather than crawling on every page view;
- support scheduled collection and bounded priority refreshes;
- isolate administrative and source-management operations from anonymous visitors;
- remain deployable locally for development and scalable to distributed workers later.

## Product access model

The ordinary product experience requires no user registration, login, password, or email address.

A visitor receives only a short-lived anonymous session identifier for navigation continuity, request correlation, rate limiting, abuse prevention, and optional temporary filters. It is not a personal account and is not reused as an identity on external providers.

The architecture has two separate planes:

### Public data plane

- accountless read access to companies, evidence, signals, opportunities, searches, and reports;
- database and index reads only under normal operation;
- privacy-preserving anonymous sessions;
- bounded refresh requests that enqueue work rather than opening provider sessions in the browser;
- no access to provider credentials, secret references, onboarding consoles, source-policy mutation, or destructive operations.

### Administrative control plane

- deployment bootstrap and configuration;
- source authorization and governance;
- provider onboarding and secret lifecycle;
- collection schedules and quotas;
- retention, deletion, correction, and suppression;
- billing or licence configuration where required;
- operational health, audit, and emergency revocation.

The administrative plane must be protected by deployment-level controls such as a private network, reverse-proxy authentication, infrastructure identity, operator certificate, or equivalent administrative boundary. It does not require creating accounts for ordinary visitors.

See [`ANONYMOUS_ACCESS_AND_REFRESH_MODEL.md`](ANONYMOUS_ACCESS_AND_REFRESH_MODEL.md).

## Proposed stack

### Application layer

- Python 3.12
- FastAPI for public and administrative HTTP APIs
- Pydantic v2 for validation
- SQLAlchemy 2 and Alembic for persistence
- durable scheduler and worker processes

### Data layer

- PostgreSQL as the system of record
- OpenSearch for full-text and faceted search when introduced
- Redis for queues, locks, rate limiting, and cache when introduced
- S3-compatible object storage only for source snapshots and evidence artifacts whose storage is explicitly permitted

### Front end

- Next.js with TypeScript
- accountless workspaces for companies, events, evidence, searches, opportunities, and reports
- isolated administrative screens for source governance and provider operations

### Observability

- structured JSON logs
- OpenTelemetry traces and metrics
- per-source ingestion, freshness, quota, and error metrics
- audit log for collection, source authorization, secret lifecycle, review, export, suppression, and deletion actions

## Components

### Public API

Provides read-oriented endpoints for:

- companies, establishments, groups, and domains;
- cyber events and timelines;
- technologies and vulnerabilities;
- evidence, provenance, confidence, and freshness;
- public source-health summaries;
- approved saved dork templates and searches;
- opportunity scores and explanations;
- bounded refresh requests.

Anonymous requests are rate limited and cannot mutate source governance, credentials, schedules, evidence history, or administrative state.

### Administrative API

Provides protected deployment-level endpoints for:

- source registry and authorization;
- provider onboarding and secret references;
- collection schedules, quotas, and circuit state;
- review, correction, suppression, and deletion workflows;
- audit and emergency revocation.

### Scheduler

Creates ingestion jobs according to source-specific schedules, licences, freshness targets, rate limits, costs, and priority-refresh queues.

### Collectors

A collector retrieves permitted data from exactly one source or source family. It returns an immutable observation envelope and never writes directly to canonical domain tables.

Collector interface:

```python
class Collector(Protocol):
    source_id: str

    async def collect(self, cursor: str | None) -> CollectionBatch:
        ...
```

Collectors use approved shared platform service identities, official APIs, open-data feeds, or authorized machine integrations. A new external account is not created for each anonymous visitor.

### Policy gateway

Runs before collection and before storage. It verifies:

- source status and authorization expiry;
- allowed hosts, paths, purposes, and data categories;
- rate, concurrency, cost, and pagination limits;
- retention and raw-content rules;
- personal-data restrictions;
- human-review requirements;
- provider credential and scope state.

### Normalization pipeline

Transforms source-specific records into canonical observations while preserving the source identifier, source timestamp, retrieval timestamp, canonical URL, provider record key, and evidence hash.

### Entity resolution

Links observations to organizations, establishments, domains, technologies, vulnerabilities, providers, professional roles, and events.

Resolution must be confidence-based and reversible. A source string match alone must not silently merge two companies.

### Evidence service

Stores factual observations, claims, confirmations, inferences, contradictions, and historical states as separate records. Every derived object references the evidence that supports it.

### Opportunity engine

Calculates explainable scores from normalized signals. It emits both the numeric value and the component contributions.

### Search research service

Stores approved query templates and permitted result metadata. Search providers are adapters governed by the same source registry. Potentially sensitive results are redacted and placed into review rather than automatically downloaded.

### Freshness and refresh service

Maintains per-source and per-entity freshness state. It:

- computes the next scheduled refresh;
- enqueues bounded priority refreshes for stale entities;
- prevents duplicate concurrent refreshes;
- respects quotas, backoff, circuits, and authorization;
- exposes `fresh`, `aging`, `stale_refresh_queued`, `source_unavailable`, `authorization_expired`, and `historical_only` states;
- serves the last stored evidence while a refresh is pending.

## Data flow

```text
source registry and schedules
      |
      v
scheduler -> policy gateway -> collector -> observation envelope
                                           |
                                           v
                                   normalization
                                           |
                                           v
                                  entity resolution
                                           |
                        +------------------+------------------+
                        v                                     v
                  evidence store                        search index
                        |
                        v
                  signal generation
                        |
                        v
                 opportunity scoring
                        |
                        v
              accountless public interface
```

Normal page views read PostgreSQL and indexes. They do not crawl every provider. A stale page may enqueue a bounded refresh and continue serving the latest stored evidence with a visible freshness label.

## Trust boundaries

1. External source boundary: all incoming data is untrusted.
2. Collector boundary: source parsers cannot bypass policy checks.
3. Credential boundary: provider identities and secrets are inaccessible to public visitors.
4. Public-session boundary: an anonymous session is not an external provider identity.
5. Personal-data boundary: contact data is minimized, isolated, and purpose-limited.
6. Evidence boundary: source artifacts are separate from normalized claims.
7. Administrative boundary: governance and mutation operations require deployment-level protection.
8. Outreach boundary: no message leaves the system without an explicitly approved workflow.

## Deployment phases

### Phase 1: local product

- public API, administrative API, scheduler, and worker in one Python project;
- PostgreSQL;
- selected public APIs and feeds;
- accountless read interface;
- deployment-local administrative boundary;
- manual search-result review where automation is not approved.

### Phase 2: scalable ingestion

- independent workers per source class;
- Redis-backed queues and locks;
- OpenSearch;
- permitted object storage;
- source backpressure, dead-letter queues, and refresh prioritization.

### Phase 3: managed deployments

- separate deployment instances or explicit organization isolation where required;
- deployment-level encryption keys and administrative identities;
- per-deployment policies, licences, quotas, billing, retention, and secret backends;
- no requirement for ordinary visitor accounts unless the product scope is deliberately changed and documented later.

## Security controls

- secrets only through a secret manager or deployment references;
- outbound network allowlists for collectors;
- no arbitrary URL fetch from visitor input;
- SSRF protection and DNS-rebinding defenses;
- content-type, redirect, archive, and size limits;
- malware-safe quarantine for permitted artifacts;
- anonymous-session minimization and short retention;
- rate limiting and abuse prevention;
- administrative-plane isolation;
- audit logging;
- deletion and suppression propagation;
- dependency and container scanning in CI.
