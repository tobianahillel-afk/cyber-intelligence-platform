# Architecture

## Architectural goals

- ingest high-volume heterogeneous sources without coupling the core domain to a specific provider;
- preserve provenance, conflicts, confidence, freshness, corrections, and retractions;
- separate catalog, onboarding, collection, source records, normalization, entity resolution, signal fusion, scoring, storage, and presentation;
- enforce source and privacy policy before any network request and before durable storage;
- provide an accountless read experience backed by stored data rather than crawling on every page view;
- support historical backfill, incremental refresh, webhooks, entity lookups, and bounded priority refreshes;
- isolate administrative and source-management operations from anonymous visitors;
- measure source value by reliable client discovery rather than ingestion volume;
- remain deployable locally for development and scalable to distributed workers later.

The complete source-to-opportunity design is defined in [`COMMERCIAL_INTELLIGENCE_INTEGRATION_ARCHITECTURE.md`](COMMERCIAL_INTELLIGENCE_INTEGRATION_ARCHITECTURE.md). Canonical records are defined in [`DATA_MODEL.md`](DATA_MODEL.md).

## Product access model

The ordinary product experience requires no user registration, login, password, or email address.

A visitor receives only a short-lived anonymous session identifier for navigation continuity, request correlation, rate limiting, abuse prevention, and optional temporary filters. It is not a personal account and is not reused as an identity on external providers.

The architecture has two separate planes.

### Public data plane

- accountless read access to approved companies, evidence, signals, opportunities, searches, and reports;
- database and index reads under normal operation;
- privacy-preserving anonymous sessions;
- bounded refresh requests that enqueue work rather than opening provider sessions in the browser;
- no access to provider credentials, secret references, onboarding consoles, source-policy mutation, or destructive operations.

### Administrative and commercial control plane

- deployment bootstrap and configuration;
- source authorization and governance;
- provider onboarding and secret lifecycle;
- collection schedules, quotas, cost budgets, and circuits;
- backfill, replay, correction, suppression, and deletion operations;
- billing or licence configuration where required;
- analyst alerts, tasks, opportunity changes, notes, and engagement state;
- operational health, audit, and emergency revocation.

The control plane must be protected by deployment-level controls such as a private network, reverse-proxy authentication, infrastructure identity, operator certificate, or equivalent administrative boundary. It does not require creating accounts for ordinary visitors.

See [`ANONYMOUS_ACCESS_AND_REFRESH_MODEL.md`](ANONYMOUS_ACCESS_AND_REFRESH_MODEL.md).

## Proposed stack

### Application layer

- Python 3.12;
- FastAPI for public and protected HTTP APIs;
- Pydantic v2 for validation;
- SQLAlchemy 2 and Alembic for persistence;
- durable scheduler and worker processes.

### Data layer

- PostgreSQL as the system of record;
- OpenSearch for full-text and faceted search when introduced;
- Redis for queues, locks, rate limiting, and cache when introduced;
- S3-compatible object storage only for source records and evidence artifacts whose storage is explicitly permitted.

### Front end

- Next.js with TypeScript;
- accountless workspaces for companies, events, evidence, searches, and reports;
- protected analyst workspaces for commercial operations;
- isolated administrative screens for source governance and provider operations.

### Observability

- structured JSON logs;
- OpenTelemetry traces and metrics;
- per-source ingestion, freshness, quota, cost, drift, and error metrics;
- per-source commercial-value metrics;
- audit log for collection, source authorization, secret lifecycle, review, export, correction, suppression, deletion, and opportunity actions.

## Canonical components

### Source catalog

Stores candidate and executable sources from official registries, provider documentation, OSINT Framework, live cyber catalogs, commercial providers, and named candidates such as BrixHub.

Catalog visibility does not grant execution. Each entry records the source owner, purpose, access method, licence, allowed and prohibited data, quota, retention, cost, risk, value hypothesis, and planned lot.

### Provider onboarding

Tracks anonymous, official provisioning, licensed, human-checkpoint, authorized browser, quarantined, and blocked states. Credentials remain secret references and are inaccessible to public visitors.

### Adapter capability registry

Each adapter declares:

- source and adapter version;
- provider schema version;
- canonical output types;
- backfill, incremental, conditional refresh, webhook, entity lookup, and priority-refresh capabilities;
- cursor, correction, tombstone, and retraction semantics;
- page, byte, record, date-window, time, concurrency, quota, and cost bounds;
- commercial use cases enabled.

### Public API

Provides read-oriented endpoints for:

- companies, establishments, groups, and domains;
- cyber events and timelines;
- technologies and vulnerabilities;
- evidence, provenance, confidence, contradiction, and freshness;
- public source-health summaries;
- approved research outputs;
- opportunity scores and explanations where exposed;
- bounded refresh requests.

Anonymous requests are rate limited and cannot mutate source governance, credentials, schedules, evidence history, analyst decisions, or administrative state.

### Protected API

Provides deployment-protected endpoints for:

- source registry and authorization;
- provider onboarding and secret references;
- collection schedules, backfills, quotas, and circuit state;
- review, merge, split, correction, suppression, and deletion workflows;
- alerts, tasks, opportunity state, notes, and engagement;
- audit and emergency revocation.

### Scheduler

Creates ingestion jobs according to:

- source schedules and freshness classes;
- licences and authorization expiry;
- provider quotas and cost budgets;
- historical backfill partitions;
- incremental checkpoints;
- webhooks and priority-refresh queues;
- source health and circuit state.

### Collectors

A collector retrieves permitted provider records from exactly one source or source family. It returns immutable source-record envelopes and never writes directly to canonical organization, event, signal, score, alert, or opportunity tables.

```python
class Collector(Protocol):
    source_id: str

    async def collect(self, request: CollectionRequest) -> CollectionBatch:
        ...
```

Collectors use approved shared platform service identities, official APIs, open-data feeds, licensed access, or authorized machine integrations. A new external account is not created for each anonymous visitor.

### Policy gateway

Runs before collection and before storage. It verifies:

- source status and authorization expiry;
- approved hosts, paths, methods, purposes, and data categories;
- authentication and granted scopes;
- rate, concurrency, cost, pagination, date-window, and byte limits;
- retention and raw-content rules;
- personal-data restrictions;
- human-review requirements.

### Source-record store

Stores immutable provider-specific envelopes with source record identity, schema version, content hash, source time, retrieval time, collection run, authorization decision, classification, and retention.

Provider payloads remain inside adapter boundaries. Raw storage is optional and separately governed.

### Normalization pipeline

Transforms source-specific records into typed canonical observations and claims while preserving source identifiers, source timestamps, event timestamps, retrieval timestamps, canonical URLs, provider record keys, evidence hashes, mapper versions, and provenance.

### Entity and event resolution

Links observations to organizations, establishments, domains, assets, technologies, vulnerabilities, providers, professional roles, contracts, and cyber events.

Resolution is identifier-first, confidence-based, temporal, and reversible. A source string match alone must not silently merge two entities. Accepted, rejected, and review-candidate links remain auditable.

### Evidence and contradiction service

Stores observations, allegations, public reports, confirmations, authority notices, telemetry, inferences, denials, disputes, corrections, and retractions as separate records.

Duplicate reporting increases corroboration only when source independence is established. Conflicts are retained rather than overwritten.

### Signal-fusion service

Produces deterministic, non-duplicated commercial signals from evidence and resolved entities. It manages active intervals, freshness, source independence, contradictions, service fit, urgency, corrections, and invalidation.

### Need-hypothesis service

Groups compatible commercial signals into explainable, versioned need hypotheses such as procurement intent, renewal, incident-response urgency, SOC/SIEM buildout, IAM/GRC transformation, product-risk remediation, passive-exposure review, provider replacement, or post-acquisition integration.

### Opportunity engine

Calculates explainable scores from need hypotheses and evidence. It emits numeric components and human-readable reasons while preserving analyst state and allowing rollback between scoring versions.

### Search research service

Stores approved query templates, research cases, catalog decisions, and permitted result metadata. Potentially sensitive results are minimized and quarantined rather than automatically downloaded.

### Freshness and refresh service

Maintains per-source, per-entity, and per-projection freshness. It:

- computes scheduled refreshes;
- partitions and resumes backfills;
- enqueues bounded priority refreshes;
- prevents duplicate concurrent work;
- respects quotas, costs, backoff, circuits, and authorization;
- exposes `fresh`, `aging`, `stale_refresh_queued`, `source_unavailable`, `authorization_expired`, and `historical_only` states;
- serves the last stored evidence while refresh is pending.

### Data-quality and publication gateway

Checks schema drift, volume drift, duplicate rates, false merges, lineage, corrections, stale data, signal distributions, score drift, and source incremental value before new projections are published.

## Data flow

```text
source catalog
      |
      v
onboarding and authorization
      |
      v
scheduler -> policy gateway -> collector -> immutable source record
                                                |
                                                v
                                  normalization into observations and claims
                                                |
                                                v
                               entity, event, and relationship resolution
                                                |
                         +----------------------+----------------------+
                         v                                             v
                  evidence and conflicts                          search index
                         |
                         v
                    signal fusion
                         |
                         v
                   need hypotheses
                         |
                         v
                  scoring and alerts
                         |
                         v
             company workspace and opportunities
                         |
                         v
                 analyst outcome feedback
```

Normal page views read PostgreSQL and indexes. They do not crawl every provider. A stale page may enqueue a bounded refresh and continue serving the latest stored evidence with a visible freshness label.

## Deduplication layers

1. Source replay: source, provider record ID, version, and content hash.
2. Mutable provider object: source and provider identity.
3. Observation: normalized subject, predicate, value, validity, and source record.
4. Entity and relationship: authoritative identifiers or reviewed candidates.
5. Event cluster: organization, event class, time window, and stable identifiers.
6. Commercial signal: organization, signal type, normalized subject, and active interval.
7. Opportunity: organization, commercial motion, service family, and lifecycle policy.

A copied upstream report must not be counted as several independent confirmations.

## Trust boundaries

1. External source boundary: all incoming data is untrusted.
2. Catalog boundary: discovery does not grant execution.
3. Collector boundary: source parsers cannot bypass policy checks.
4. Credential boundary: provider identities and secrets are inaccessible to public visitors.
5. Public-session boundary: an anonymous session is not an external provider identity.
6. Personal-data boundary: contact data is minimized, isolated, purpose-limited, correctable, and suppressible.
7. Evidence boundary: source artifacts are separate from canonical claims and facts.
8. Derivation boundary: signals, hypotheses, scores, and opportunities remain reproducible and invalidatable.
9. Administrative boundary: governance and mutation operations require deployment-level protection.
10. Outreach boundary: no message leaves the system without an explicitly approved workflow.

## Deployment phases

### Phase 1 — Local product

- public API, protected API, scheduler, and worker in one Python project;
- PostgreSQL;
- selected public APIs and feeds;
- accountless read interface;
- deployment-local control boundary;
- manual research review where automation is not approved.

### Phase 2 — Source portfolio and scalable ingestion

- common source SDK and capability registry;
- historical backfill and incremental workers;
- independent worker pools by source class;
- Redis-backed queues and locks where measured;
- OpenSearch;
- permitted object storage;
- source backpressure, dead letters, refresh prioritization, and publication gates.

### Phase 3 — Managed deployments

- separate deployment instances or explicit organization isolation where required;
- deployment-level encryption keys and administrative identities;
- per-deployment policies, licences, quotas, billing, retention, and secret backends;
- no requirement for ordinary visitor accounts unless deliberately added in a future product decision.

## Security controls

- secrets only through a secret manager or deployment references;
- outbound network allowlists for collectors;
- no arbitrary URL fetch from visitor input;
- SSRF protection and DNS-rebinding defenses;
- content-type, redirect, archive, and size limits;
- malware-safe quarantine for permitted artifacts;
- anonymous-session minimization and short retention;
- rate limiting and abuse prevention;
- control-plane isolation;
- audit logging;
- correction, deletion, retraction, and suppression propagation;
- source authorization expiry and emergency kill switches;
- dependency and container scanning in CI.
