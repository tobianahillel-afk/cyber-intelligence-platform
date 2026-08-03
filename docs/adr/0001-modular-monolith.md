# ADR 0001: Modular Monolith First

- Status: Accepted
- Date: 2026-08-03
- Decision owners: project maintainers

## Context

The platform must support many source adapters, continuous ingestion, browser research, entity resolution, evidence management, commercial-signal detection, opportunity scoring, professional-role intelligence, and a rich analyst UI.

Starting with many independently deployed services would create significant operational and contractual complexity before the product boundaries and workloads are validated. A single unstructured application, however, would quickly produce large files, circular dependencies, source-specific business logic, and difficult testing.

## Decision

Build the initial backend as a modular monolith with separate process entry points:

- API;
- worker;
- scheduler;
- migration and maintenance commands.

Business capabilities are isolated as bounded modules. Each module owns its domain model, application handlers, ports, infrastructure implementations, API composition, and tests.

Source adapters and browser implementations remain outside business modules. They communicate through canonical raw-observation and research-job contracts.

The Next.js frontend is a separate application organized by product feature.

## Dependency direction

```text
API -> application -> domain
infrastructure -> application ports
source and browser adapters -> canonical contracts
```

A module cannot import another module's infrastructure package or database models. Cross-module behavior uses application interfaces, read models, or versioned events.

## Consequences

### Positive

- one local development and deployment environment;
- straightforward transactions where needed;
- strong modular boundaries without distributed-system overhead;
- easier refactoring while product concepts evolve;
- simpler end-to-end testing;
- source adapters and opportunity logic remain independently testable;
- modules can later be extracted based on measured load or isolation requirements.

### Negative

- boundaries require automated architecture tests and disciplined reviews;
- one deployment may contain more code than each runtime needs;
- background workloads require careful queue and resource isolation;
- a badly designed shared package could become a hidden monolith.

## Extraction criteria

A module may become an independent service only when at least one condition is demonstrated:

- materially different scaling profile;
- independent release cadence with recurring deployment conflicts;
- strict security or data-isolation boundary;
- separate availability requirement;
- technology requirement incompatible with the main runtime;
- queue or database workload that harms the rest of the system;
- ownership by a stable independent team.

An extraction requires a separate ADR covering contracts, data ownership, failure modes, migration, observability, and rollback.

## Rejected alternatives

### Single-layer FastAPI application

Rejected because routes, collectors, persistence, and scoring would become tightly coupled and produce very large files.

### Microservices from the first release

Rejected because product boundaries, source volume, tenancy, and scaling requirements have not yet been validated.

### One service per source

Rejected because most connectors share orchestration infrastructure and do not justify independent deployment. Source isolation is achieved through adapter contracts, queues, quotas, and worker pools.
