# Lot 10 — Source Portfolio Runtime, Backfill, Freshness, and Source Health

## Status

`PLANNED_LOCKED`

Implementation starts only after lot 09 is merged and validated on `main`.

## Business outcome

Provide one common execution lifecycle for all future public, licensed, live cyber, corporate-web, community, and conditional sources.

The lot prevents each adapter from inventing its own catalog format, backfill logic, checkpoint rules, freshness state, health model, schema-drift behavior, cost controls, and commercial-value metadata.

## Dependencies

- lots 00–08 validated;
- lot 09 provider onboarding merged and validated;
- revised architecture, data model, roadmap, and test matrix accepted.

## Deliverables

### Machine-readable source catalog

Create a versioned catalog format containing:

- source identity, owner, canonical URL, category, and subcategory;
- use cases and expected commercial value;
- collection mode and authorization state;
- onboarding level and authentication modes;
- approved hosts and paths;
- allowed and prohibited fields;
- quota, concurrency, response size, date window, cost, and retention limits;
- freshness class and maximum staleness;
- raw-storage, attribution, and human-review rules;
- planned adapter and roadmap lot;
- review and authorization expiry dates;
- source health and schema status.

Importing OSINT Framework or another catalog creates non-executable candidates only.

### Adapter capability contract

Add a provider-independent manifest declaring:

- adapter and provider schema versions;
- canonical output types;
- `historical_backfill`;
- `incremental_cursor`;
- `conditional_refresh`;
- `webhook`;
- `entity_lookup`;
- `priority_refresh`;
- cursor, checkpoint, correction, tombstone, and retraction semantics;
- operational and cost limits;
- commercial use cases enabled.

### Source record and collection run contracts

Introduce application contracts for:

- collection request;
- collection batch;
- collection run;
- immutable source record;
- rejected record and rejection reason;
- provider schema version;
- source and retrieval timestamps;
- content hashes;
- authorization and policy decision references.

Provider payloads must remain inside adapters.

### Historical backfill

Implement:

- bounded date or key partitions;
- durable partition checkpoints;
- resumable execution;
- progress and remaining-work metrics;
- pause, resume, cancel, and disable;
- replay without duplicate current signals;
- backfill-specific rate and cost budgets.

### Incremental refresh

Support:

- provider cursors;
- timestamps and overlap windows;
- ETag and Last-Modified;
- content hashes;
- provider deltas;
- webhooks where authorized;
- correction, deletion, tombstone, and retraction propagation.

### Freshness service

Implement source and projection states:

- `fresh`;
- `aging`;
- `stale_refresh_queued`;
- `source_unavailable`;
- `authorization_expired`;
- `historical_only`.

Normal page views read stored projections. Priority refreshes are bounded queue requests, not synchronous full crawls.

### Source health and schema drift

Track:

- last attempt and success;
- last source record time;
- lag and maximum staleness;
- HTTP and provider failures;
- quota and cost use;
- schema version and drift;
- volume and field-population anomalies;
- circuit state;
- authorization expiry;
- current backfill status.

### Source-value metadata

Record the planned measurement for:

- organization resolution;
- unique evidence;
- signal types;
- expected analyst workflow;
- duplicate overlap;
- cost per accepted opportunity;
- source ablation and incremental value.

Lot 10 provides the measurement hooks. Later source lots provide labelled benchmarks.

### API and interface

Protected control-plane views must show:

- catalog candidates;
- executable sources;
- authorization and onboarding state;
- adapter capabilities;
- schedules and freshness;
- backfill progress;
- source health and schema drift;
- pause, resume, disable, and revoke actions;
- redacted secret-reference state only.

Anonymous visitors may see only approved public freshness summaries where product requirements permit it.

## Required tests

### Architecture

- provider transports cannot import canonical persistence implementations;
- adapters cannot write directly to companies, signals, scores, alerts, or opportunities;
- catalog candidates cannot execute;
- one stable source and adapter identity contract.

### Governance and onboarding

- policy denial before network;
- blocked, quarantined, expired, and unauthorized states;
- scope mismatch;
- source ownership or terms change returns to review;
- secret redaction.

### Backfill

- partition generation;
- interruption and resume;
- duplicate partition delivery;
- cancellation;
- rate and cost budgets;
- historical replay does not create duplicate active alerts;
- checkpoint advances only after transactional success.

### Incremental convergence

- cursor overlap;
- ETag and Last-Modified;
- mutable source record;
- unchanged record;
- correction;
- tombstone;
- retraction;
- full backfill and incremental sequence converge to the same canonical source-record state.

### Source health

- provider outage;
- quota exhaustion;
- authorization expiry;
- schema drift;
- volume anomaly;
- stale and recovered states;
- circuit opening and closing;
- no false-success status.

### API and UI

- protected operations;
- anonymous denial;
- loading, empty, partial, stale, failure, and success states;
- progress updates;
- redaction;
- audit history;
- concurrent pause/resume behavior.

### Migration and CI

- reversible migrations;
- complete backend and frontend gates;
- coverage thresholds;
- common adapter contract suite included in CI.

## Exit gate

Lot 10 is complete when a synthetic reference adapter and at least one existing official adapter prove the complete lifecycle:

```text
catalog -> onboarding -> backfill -> incremental refresh -> source records -> freshness -> health -> disablement
```

The final SHA must pass all repository gates and demonstrate that future sources can reuse the lifecycle without adding provider-specific orchestration to the core.

## Non-goals

- implementing every OSINT or live cyber source;
- enabling BrixHub;
- introducing unrestricted browser automation;
- implementing final entity resolution, signal fusion, scoring, or Company 360;
- treating catalog import as source authorization;
- optimizing for record volume without commercial value.
