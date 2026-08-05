# Lot 10 — Source Portfolio Runtime, Backfill, Freshness, and Source Health

## Status

`IN_PROGRESS`

Implementation is complete on the lot branch. Final repository-wide CI validation and merge remain required before this status becomes `IMPLEMENTED_VALIDATED`.

## Business outcome

Provide one common, governed execution lifecycle for future public, licensed, live cyber, corporate-web, community, and conditional sources without allowing each adapter to invent its own catalog, backfill, freshness, health, schema, cost, or control-plane model.

## Delivered architecture

### Machine-readable portfolio

`policies/source_portfolio.yml` is the reviewed source of truth for:

- source identity, canonical URL, category and commercial use cases;
- executable, paused, disabled and candidate states;
- freshness targets, review and authorization expiry;
- monthly cost limits and source metadata;
- adapter identity, version, provider schema and output types;
- historical, incremental, conditional, lookup, webhook and priority capabilities;
- correction, tombstone and retraction support;
- page and date-window limits.

OSINT Framework and BrixHub are represented only as non-executable candidates. Target-dependent identity sources remain paused until an approved target exists.

### Governed catalog import

External catalog entries become deterministic, idempotent candidates with `authorization_required=true`. Import never creates an adapter, source policy, authorization or executable status.

### Common adapter lifecycle

The existing durable collection scheduler, worker, checkpoints, leases, circuit breaker and dead-letter flow remain the execution core. Lot 10 adds a capability manifest and validates that every executable portfolio entry maps to a registered runtime adapter.

A deterministic no-network reference adapter proves the contract without relying on a third-party service.

### Durable backfill

Backfill partitions are persisted with stable source, adapter and bound identities. The state machine supports:

```text
pending -> running -> completed
                   -> failed -> running
pending/running -> paused -> pending
pending/running/paused/failed -> cancelled
```

Cursors, attempts, written-record counts, errors and timestamps survive interruption. Duplicate partition requests return the existing partition rather than creating parallel work.

### Freshness and health

The persisted source-health projection exposes:

- `fresh`, `aging`, `stale_refresh_queued`, `source_unavailable`, `authorization_expired` and `historical_only`;
- schema state and drift;
- volume and field-population anomaly state;
- last attempt, success and source-record timestamps;
- consecutive failures, quota and monthly cost;
- current backfill state;
- the existing collection circuit-breaker state.

Worker successes and failures update the projection transactionally. Page views read stored state and never trigger an unbounded crawl.

### Execution shutdown

The scheduler does not create work for paused, disabled or authorization-expired sources. A worker that claims an already queued job rechecks eligibility and cancels it before adapter execution when the source is no longer allowed.

### Priority refresh

Priority refresh is a bounded, idempotent queue request. Requests in the same source/adapter minute return the existing job identity. The endpoint refuses candidates, paused sources, unsupported adapters, expired authorization and sources whose governance record has not been synchronized.

### Protected API and interface

The protected `/v1/source-portfolio` control plane supports:

- portfolio list and detail;
- adapter capabilities and health;
- backfill request and cancellation;
- priority refresh;
- pause, resume and disable;
- explicit freshness recalculation.

The Next.js Sources page consumes the API server-side using `CIP_CONTROL_PLANE_TOKEN`; the token is never delivered to browser code. The page shows freshness, schema, anomalies, circuit, backfill, quota, cost and permitted operator actions beside provider onboarding.

### Persistence and release

- reversible migration `20260805_0008`;
- application version `0.11.0`;
- source portfolio and control-plane deployment settings documented in `.env.example`;
- portfolio models registered in shared metadata;
- no raw provider secret added to Git, database responses, UI or logs.

## Implemented tests

The lot includes tests for:

- domain and manifest validation;
- strict YAML loading and duplicate rejection;
- candidate import idempotence and non-execution;
- backfill creation, duplicate delivery, failure, retry, cursor preservation, pause, resume and cancellation;
- freshness degradation and recovery;
- schema drift and anomaly projection;
- priority-refresh idempotence and pause rejection;
- anonymous control-plane denial;
- API list, backfill, priority, pause, resume, cancel and disable;
- scheduler authorization-expiry shutdown;
- worker cancellation before provider execution;
- vertical `job -> worker -> raw observation -> checkpoint -> health` execution through the reference adapter;
- reversible migrations, architecture limits, backend coverage and frontend type/build gates through the repository CI.

## Remaining validation gate

Before merge, one final SHA must pass:

- dependency consistency and vulnerability audit;
- Ruff and strict Mypy;
- architecture, release and roadmap contracts;
- PostgreSQL `upgrade -> downgrade base -> upgrade`;
- complete backend tests with the repository coverage threshold;
- frontend dependency audit, TypeScript and production build.

## Exit gate

Lot 10 is complete when the final validated SHA proves:

```text
catalog
  -> governed activation
  -> schedule or priority queue
  -> durable worker
  -> source record/checkpoint
  -> freshness and health
  -> pause/expiry shutdown
```

Future sources must be able to reuse this lifecycle without adding provider-specific orchestration to the core.

## Non-goals

- implementing every OSINT or live cyber source;
- enabling BrixHub;
- unrestricted browser automation;
- final entity resolution, signal fusion, scoring or Company 360;
- treating catalog import as authorization;
- optimizing for record volume without commercial value.
