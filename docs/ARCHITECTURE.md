# Architecture

## Architectural goals

- ingest high-volume heterogeneous sources without coupling the core domain to a specific provider;
- preserve provenance and uncertainty;
- separate collection, normalization, entity resolution, scoring, and presentation;
- enforce source and privacy policy before data enters durable storage;
- support both scheduled feeds and analyst-triggered investigations;
- remain deployable locally for development and scalable to distributed workers later.

## Proposed stack

### Application layer

- Python 3.12
- FastAPI for HTTP APIs
- Pydantic v2 for validation
- SQLAlchemy 2 and Alembic for persistence
- Dramatiq or Celery for background jobs

### Data layer

- PostgreSQL as the system of record
- OpenSearch for full-text and faceted search
- Redis for queues, locks, rate limiting, and cache
- S3-compatible object storage for permitted source snapshots and evidence artifacts

### Front end

- Next.js with TypeScript
- analyst workspaces for companies, events, evidence, searches, opportunities, and source governance

### Observability

- structured JSON logs
- OpenTelemetry traces and metrics
- per-source ingestion metrics
- audit log for collection, review, export, suppression, and deletion actions

## Components

### API

Provides authenticated endpoints for:

- companies and domains;
- cyber events and timelines;
- technologies and vulnerabilities;
- evidence and provenance;
- source registry;
- saved dork templates;
- opportunity scoring;
- review and suppression workflows.

### Scheduler

Creates ingestion jobs according to source-specific schedules, licences, and rate limits.

### Collectors

A collector retrieves permitted data from exactly one source or source family. It returns an immutable raw observation envelope and never writes directly to domain tables.

Collector interface:

```python
class Collector(Protocol):
    source_id: str

    async def collect(self, cursor: str | None) -> CollectionBatch:
        ...
```

### Policy gateway

Runs before collection and before storage. It verifies:

- source status;
- allowed data categories;
- rate limit;
- retention rules;
- raw-content permission;
- personal-data restrictions;
- human-review requirements.

### Normalization pipeline

Transforms source-specific records into canonical observations while preserving the original source identifier, timestamp, and source record key.

### Entity resolution

Links observations to organizations, domains, technologies, vulnerabilities, threat actors, professional roles, and events.

Resolution must be confidence-based and reversible. A source string match alone must not silently merge two companies.

### Evidence service

Stores factual observations, claims, confirmations, inferences, and contradictions as separate records. Every derived object references the evidence that supports it.

### Opportunity engine

Calculates an explainable score from normalized signals. It emits both the numeric value and the component contributions.

### Search research service

Stores approved query templates and result metadata. Search providers are adapters governed by the same source registry. Potentially sensitive results are redacted and placed into manual review rather than automatically downloaded.

## Data flow

```text
source registry
      |
      v
scheduler -> policy gateway -> collector -> raw observation envelope
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
                    analyst UI
```

## Trust boundaries

1. External source boundary: all incoming data is untrusted.
2. Collector boundary: source parsers cannot bypass policy checks.
3. Personal-data boundary: contact data is isolated and permissioned.
4. Evidence boundary: raw source content is separate from normalized claims.
5. Outreach boundary: no message leaves the system without explicit human action.

## Deployment phases

### Phase 1: local MVP

- API and worker in one Python project
- PostgreSQL
- Redis
- selected public APIs and feeds
- manual dork result review

### Phase 2: scalable ingestion

- independent workers per source class
- OpenSearch
- object storage
- source backpressure and dead-letter queues

### Phase 3: multi-tenant product

- tenant isolation
- organization-level policies
- role-based access control
- per-tenant encryption keys
- billing and usage quotas
- external CRM integrations

## Security controls

- secrets only through environment or secret manager;
- outbound network allowlists for collectors;
- no arbitrary URL fetch from end-user input;
- SSRF protection and DNS rebinding defenses;
- content-type and size limits;
- malware-safe object handling;
- audit logging;
- role-based export controls;
- deletion and suppression propagation;
- dependency and container scanning in CI.
