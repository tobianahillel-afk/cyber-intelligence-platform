# Test Strategy

## Objective

The test suite must prevent regressions in collection, parsing, normalization, entity resolution, scoring, privacy controls, browser behavior, downloads, APIs, UI workflows, and commercial intelligence quality.

Coverage is a quality gate, not the only measure of quality. A source adapter with high code coverage but poor resolution, duplicate handling, correction behavior, or commercial usefulness is not complete.

[`SOURCE_INTEGRATION_TEST_MATRIX.md`](SOURCE_INTEGRATION_TEST_MATRIX.md) is mandatory for roadmap lots 10 through 28. It defines the complete source-to-opportunity release path from catalog governance through measurable client-finding value.

## Coverage targets

### Global repository target

- at least 90% line coverage;
- at least 90% branch coverage for handwritten backend code;
- no decrease in coverage on changed files;
- changed-file coverage target of at least 95%.

### Critical modules

The following target at least 95% line and branch coverage:

- source governance;
- provider onboarding, authorization, and redaction;
- source catalog and adapter capability decisions;
- checkpoint, backfill, and incremental convergence;
- opportunity scoring;
- signal fusion and need-hypothesis invalidation;
- entity-resolution decisions;
- suppression, correction, retraction, and deletion propagation;
- download quarantine policy;
- browser-job policy;
- contract-renewal estimation;
- opportunity state transitions.

### Adapter code

Adapters target at least 90% for deterministic parsing, mapping, pagination, checkpoint, backfill, incremental refresh, correction, tombstone, and failure-classification code.

External-library internals, generated schemas, and unavoidable browser-engine behavior are excluded only through documented configuration. Exclusions must not hide business branches.

## Test categories

## 1. Unit tests

Test one function, policy, value object, parser, mapper, or handler in isolation.

Examples:

- opportunity score component;
- freshness decay;
- contract-renewal window calculation;
- domain normalization;
- source-policy decision;
- retry classification;
- challenge-page classification;
- archive-size validation;
- contact suppression;
- state transition;
- signal identity;
- claim correction and hypothesis invalidation.

Unit tests must be fast, deterministic, and network-free.

## 2. Property-based tests

Use generated inputs for invariant-heavy logic.

Targets:

- date ranges;
- money and currency parsing;
- URL and domain normalization;
- entity-match scores;
- pagination cursors;
- backfill partitions;
- archive limits;
- score bounds;
- state machines;
- deduplication keys;
- relationship validity intervals.

Example invariants:

- opportunity score remains within configured bounds;
- normalizing an already normalized domain is idempotent;
- a suppressed contact never appears in export read models;
- a retry delay never exceeds the configured maximum;
- an archive exceeding the uncompressed limit is always rejected;
- replaying the same source record cannot create another active commercial signal;
- a retracted claim cannot remain the sole support for an active need hypothesis.

## 3. Parser fixture tests

Every adapter stores sanitized fixtures representing:

- minimum valid payload;
- representative payload;
- optional fields;
- empty result;
- pagination boundary;
- invalid record;
- changed schema;
- provider error encoded as HTTP 200;
- encoding edge case;
- unusually large field;
- removed or tombstoned record;
- corrected record;
- retracted record where the provider supports it.

Fixtures must not contain real secrets, private messages, credentials, victim files, or unrestricted personal exports.

## 4. Golden or snapshot tests

Use for stable parser, mapper, observation, signal, and explanation outputs where a human-readable expected result is valuable.

Golden files must be reviewed like code. Updates require an explanation and should not be accepted automatically because a test failed.

## 5. Adapter contract tests

The source SDK runs a common test suite against every adapter.

Required contracts:

- valid source and capability manifests;
- stable source ID and adapter version;
- no unauthorized host or path;
- no direct domain, signal, score, alert, or opportunity table writes;
- deterministic mapping for the same input and mapper version;
- idempotent checkpoint handling;
- bounded retries;
- redacted logs;
- correct incremental, backfill, lookup, webhook, and priority-refresh declarations;
- backfill and incremental convergence;
- correction, tombstone, and retraction behavior;
- correct failure classification;
- policy denial before network access;
- authorization expiry disables execution.

## 6. HTTP transport tests

Use mocked or recorded permitted responses to test:

- redirects;
- TLS errors;
- timeouts;
- truncated bodies;
- content-length mismatch;
- chunked responses;
- compression;
- ETag and Last-Modified;
- pagination;
- 401, 403, 404, 409, 429, and 5xx;
- Retry-After;
- unexpected content type;
- redirect to an unauthorized host;
- DNS policy rejection;
- source schema or ownership change.

No routine CI test depends on a live third-party site.

## 7. Browser component tests

Test browser-flow state machines without a real external source where possible.

Simulated pages cover:

- JavaScript-rendered content;
- login required;
- expired session;
- MFA prompt;
- consent or terms update;
- CAPTCHA or bot challenge;
- access denied;
- rate-limit warning;
- changed selector;
- endless loading;
- popup and new tab;
- unexpected cross-domain navigation;
- download initiated;
- download host changed;
- service worker behavior;
- page crash;
- browser-process crash.

Expected behavior for CAPTCHA, bot challenges, or account-security prompts is a safe pause and explicit state, never bypass.

## 8. Browser end-to-end tests

Run against owned local test applications that emulate source behavior.

Scenarios:

- authorized login and session restore;
- JavaScript data extraction;
- permitted file export;
- browser restart and checkpoint resume;
- interrupted download;
- process cleanup;
- context isolation;
- cookie separation between sources;
- blocked third-party host;
- kill switch;
- manual-action resume.

A small optional provider-smoke suite may run against approved sandboxes, never against arbitrary production accounts on every commit.

## 9. Download-security tests

Test:

- spoofed Content-Type;
- double extension;
- reserved filename;
- path traversal;
- oversized file;
- archive bomb;
- too many archive entries;
- nested archive depth;
- encrypted archive;
- executable content inside an allowed container;
- macro-enabled document;
- malformed PDF;
- parser timeout;
- parser memory limit;
- malware scanner unavailable;
- CDR failure;
- quarantined object deletion;
- raw-storage prohibition.

Use safe synthetic fixtures rather than live malware in the standard repository.

## 10. Normalization tests

Test:

- dates and original precision;
- source, publication, event, modification, and retrieval times;
- timezones;
- organization suffixes and aliases;
- IDNA domains;
- invalid domains;
- registration identifiers;
- emails and generic mailboxes;
- international phone ambiguity;
- monetary ranges;
- CVE and advisory aliases;
- technology version expressions;
- indicator formats;
- language and transliteration;
- missing versus empty values.

## 11. Entity-resolution tests

Use curated positive, negative, and ambiguous pairs.

Measure:

- precision;
- recall;
- false merge rate;
- missed link rate;
- analyst-review rate.

Tests must include organizations with similar names, group subsidiaries, renamed companies, shared addresses, shared domains, CDN and hosting ambiguity, conflicting registration identifiers, victim-brand aliases, product aliases, and provider aliases.

A false merge is treated as more severe than a missed automatic link.

## 12. Opportunity-engine tests

Test each component independently and complete scenarios.

Scenarios:

- confirmed incident plus relevant professional role;
- unconfirmed ransomware claim only;
- actor claim later denied or retracted;
- open SIEM tender;
- contract award and estimated renewal;
- old technology observation plus recent KEV;
- exact affected version versus family-only evidence;
- contradictory evidence;
- stale data;
- weak-source and copied-upstream penalties;
- contact suppression;
- source-policy block;
- score-version migration;
- several sources reporting one event;
- one event supporting several service fits without duplicate opportunity creation.

Every test verifies both numeric output and human-readable explanation.

## 13. API tests

Test:

- anonymous public read access where allowed;
- protected administrative and mutation operations;
- authentication and authorization at the deployment boundary;
- pagination;
- filters and sorting;
- idempotency keys;
- optimistic concurrency;
- error mapping;
- redaction;
- rate limits;
- audit events;
- OpenAPI compatibility;
- no raw secret or unrestricted provider payload exposure.

## 14. Persistence integration tests

Run with real disposable PostgreSQL, Redis, object storage, and OpenSearch-compatible services where applicable.

Test:

- transactions;
- unique constraints;
- outbox delivery;
- idempotent consumers;
- concurrent updates;
- checkpoint locks;
- source-record immutability;
- tombstones;
- correction and retraction propagation;
- deletion and suppression propagation;
- derived-data invalidation;
- index rebuild;
- object quarantine lifecycle.

## 15. Migration tests

Every database migration is tested by:

- applying from the previous supported version;
- loading representative records;
- verifying constraints and backfill;
- applying the downgrade when supported;
- verifying application startup;
- checking that no protected data becomes exposed;
- verifying that existing analyst decisions survive derived-data schema changes.

## 16. Frontend component tests

Test:

- loading, empty, partial, stale, error, and success states;
- score explanations;
- confidence, claim, confirmation, dispute, and retraction labels;
- redaction;
- saved filters;
- table columns;
- keyboard navigation;
- dialogs and confirmation steps;
- long-running backfill and refresh progress;
- source-health and schema-drift warnings;
- anonymous read versus protected control-plane states.

## 17. Frontend end-to-end tests

Critical workflows:

1. Review and qualify an opportunity.
2. Reject a weak signal and observe score recalculation.
3. Open an organization and inspect evidence lineage and conflicts.
4. Create and monitor a research job.
5. Review a provider onboarding or manual-action state.
6. Pause a source and verify UI state.
7. Suppress a contact and verify removal from export and engagement views.
8. Inspect a contract-renewal estimate.
9. Handle partial source failure without losing existing data.
10. Compare an actor claim, media report, company statement, and regulator confirmation.
11. Inspect a stale entity while a bounded refresh is queued.

## 18. Security tests

Automated checks include:

- dependency vulnerability scanning;
- secret scanning;
- static analysis;
- container scanning;
- infrastructure configuration checks;
- SSRF test suite;
- redirect and DNS-rebinding simulations;
- log-redaction tests;
- authorization matrix tests;
- object-storage access tests;
- browser sandbox configuration tests;
- malicious-file pipeline tests;
- anonymous-session minimization;
- provider scope and authorization-expiry tests.

## 19. Resilience and chaos tests

Inject failures:

- worker killed mid-batch;
- Redis unavailable;
- database connection lost;
- object storage slow;
- browser crash;
- provider returns intermittent 500;
- queue delivers the same event twice;
- parser version changes during backfill;
- source record changes between pages;
- clock skew;
- partial index failure;
- source authorization expires during a run;
- a projection fails after source records are committed.

Verify no duplicate opportunities, lost checkpoints, uncontrolled retries, corrupt derived data, or incorrect success statuses.

## 20. Performance tests

Benchmarks cover:

- records normalized per second;
- historical backfill throughput;
- incremental refresh latency;
- entity-resolution batch time;
- signal and opportunity recalculation latency;
- list and search query latency;
- browser-worker concurrency;
- download and parser resource limits;
- index rebuild time;
- large organization timeline rendering;
- source portfolio scheduling under quota and cost budgets.

Performance thresholds are stored in versioned configuration and tested in scheduled CI rather than every small commit.

## 21. Data-quality regression tests

Use representative sanitized datasets to compare releases.

Monitor:

- parsed record count;
- field population rates;
- prohibited-field rejection;
- duplicate rate by layer;
- entity-link decisions;
- false merge and review rates;
- number and distribution of signals and hypotheses;
- opportunity score distribution;
- contradiction, correction, and retraction behavior;
- contact suppression behavior;
- freshness calculations;
- source incremental value.

Unexpected drift blocks deployment until reviewed.

## 22. Architecture tests

Automatically enforce:

- no domain imports of frameworks;
- no cross-module infrastructure imports;
- no direct database access from routes;
- no opportunity or score imports in source adapters;
- no direct canonical projection writes from provider transport code;
- no browser imports outside browser adapters;
- no files above the hard threshold without exception metadata;
- no circular package dependencies;
- frontend feature boundaries;
- one authoritative roadmap with continuous, unique lot numbers and status consistency.

## 23. Commercial-value tests

Every source family requires a labelled benchmark that measures:

- resolved-organization rate;
- duplicate suppression;
- contradiction and false-urgency rates;
- signal precision and recall;
- analyst acceptance, rejection, and snooze rates;
- unique accepted opportunities beyond the existing source portfolio;
- analyst time saved;
- cost per accepted opportunity;
- conversion or downstream usefulness by source family and signal type.

Source ablation tests compare product output with and without the candidate source. A source that increases record volume without adding reliable, unique commercial value fails the product gate.

## CI pipeline

### Pull request

1. formatting and linting;
2. type checking;
3. architecture and roadmap tests;
4. unit and property tests;
5. parser and adapter contract tests;
6. API and frontend component tests;
7. coverage enforcement;
8. dependency and secret scans;
9. migration checks;
10. selected integration and browser tests.

### Main branch

Additionally run:

- full integration suite;
- source-record-to-opportunity end-to-end scenarios;
- backfill and incremental convergence suites;
- frontend end-to-end suite;
- browser end-to-end suite when applicable;
- container scan;
- build reproducibility checks.

### Scheduled

- complete security suite;
- performance tests;
- resilience tests;
- optional approved provider smoke tests;
- source schema-drift checks;
- data-quality regression suite;
- source portfolio incremental-value benchmarks;
- dependency updates.

## Test organization

```text
tests/
  unit/
    modules/
    shared/
  property/
  contracts/
    api/
    events/
    adapters/
  integration/
    database/
    queue/
    search/
    storage/
  browser/
    components/
    end_to_end/
  security/
  migrations/
  architecture/
  data_quality/
  commercial_value/
  performance/
  end_to_end/
```

Adapter-local tests remain next to each adapter for fast ownership. Cross-adapter and platform tests live under the root `tests/` tree.

## Flaky-test policy

- flaky tests are defects;
- automatic retries may gather diagnostics but do not convert a failure into success silently;
- quarantined tests require an owner, issue, reason, and expiry date;
- no permanent skip without justification;
- browser traces, screenshots, logs, and videos are retained only when safe and redacted.

## Test-data policy

Use:

- synthetic data;
- provider-published examples;
- sanitized and minimized fixtures;
- approved sandbox data;
- generated organizations and contacts;
- published anonymized research datasets whose licence permits testing.

Do not commit:

- live credentials;
- cookies or tokens;
- private exports;
- leaked datasets;
- victim files;
- unrestricted personal data;
- malicious binaries.
