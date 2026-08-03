# Test Strategy

## Objective

The test suite must prevent regressions in collection, parsing, normalization, entity resolution, scoring, privacy controls, browser behavior, downloads, APIs, and UI workflows.

Coverage is a quality gate, not the only measure of quality.

## Coverage targets

### Global repository target

- at least 90% line coverage;
- at least 90% branch coverage for handwritten backend code;
- no decrease in coverage on changed files;
- changed-file coverage target of at least 95%.

### Critical modules

The following target at least 95% line and branch coverage:

- source governance;
- authorization and redaction;
- opportunity scoring;
- entity-resolution decisions;
- suppression and deletion propagation;
- download quarantine policy;
- browser-job policy;
- contract-renewal estimation;
- opportunity state transitions.

### Adapter code

Adapters target at least 90% for deterministic parsing, mapping, pagination, checkpoint, and failure classification code.

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
- state transition.

Unit tests must be fast, deterministic, and network-free.

## 2. Property-based tests

Use generated inputs for invariant-heavy logic.

Targets:

- date ranges;
- money and currency parsing;
- URL and domain normalization;
- entity-match scores;
- pagination cursors;
- archive limits;
- score bounds;
- state machines;
- deduplication keys.

Example invariants:

- opportunity score remains within configured bounds;
- normalizing an already normalized domain is idempotent;
- a suppressed contact never appears in export read models;
- a retry delay never exceeds the configured maximum;
- an archive exceeding the uncompressed limit is always rejected.

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
- removed or tombstoned record.

Fixtures must not contain real secrets, private messages, credentials, or unrestricted personal exports.

## 4. Golden or snapshot tests

Use for stable parser and mapper outputs where a human-readable expected result is valuable.

Golden files must be reviewed like code. Updates require an explanation and should not be accepted automatically because a test failed.

## 5. Adapter contract tests

The source SDK runs a common test suite against every adapter.

Required contracts:

- valid manifest;
- stable source ID;
- no unauthorized host;
- no direct domain-table writes;
- deterministic mapping for the same input;
- idempotent checkpoint handling;
- bounded retries;
- redacted logs;
- correct incremental and backfill capabilities;
- correct failure classification;
- policy denial before network access.

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
- DNS policy rejection.

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

Expected behavior for CAPTCHA, bot challenges, or account-security prompts is a safe pause and human task, never bypass.

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

Tests must include organizations with similar names, group subsidiaries, renamed companies, shared addresses, shared domains, and conflicting registration identifiers.

A false merge is treated as more severe than a missed automatic link.

## 12. Opportunity-engine tests

Test each component independently and complete scenarios.

Scenarios:

- confirmed incident plus relevant contact;
- unconfirmed ransomware claim only;
- open SIEM tender;
- old technology observation plus recent KEV;
- estimated contract expiry;
- contradictory evidence;
- stale data;
- weak-source penalty;
- contact suppression;
- source-policy block;
- score-version migration.

Every test verifies both numeric output and human-readable explanation.

## 13. API tests

Test:

- authentication;
- authorization;
- pagination;
- filters and sorting;
- idempotency keys;
- optimistic concurrency;
- error mapping;
- redaction;
- rate limits;
- audit events;
- OpenAPI compatibility;
- no raw secret or unrestricted payload exposure.

## 14. Persistence integration tests

Run with real disposable PostgreSQL, Redis, object storage, and OpenSearch-compatible services where applicable.

Test:

- transactions;
- unique constraints;
- outbox delivery;
- idempotent consumers;
- concurrent updates;
- checkpoint locks;
- tombstones;
- deletion propagation;
- index rebuild;
- object quarantine lifecycle.

## 15. Migration tests

Every database migration is tested by:

- applying from the previous supported version;
- loading representative records;
- verifying constraints and backfill;
- applying the downgrade when supported;
- verifying application startup;
- checking that no protected data becomes exposed.

## 16. Frontend component tests

Test:

- loading, empty, partial, stale, error, and success states;
- score explanations;
- confidence and claim labels;
- redaction;
- saved filters;
- table columns;
- keyboard navigation;
- dialogs and confirmation steps;
- long-running job progress;
- source-health warnings.

## 17. Frontend end-to-end tests

Critical workflows:

1. Review and qualify an opportunity.
2. Reject a weak signal and observe score recalculation.
3. Open an organization and inspect evidence lineage.
4. Create and monitor a research job.
5. Review a manual-action-required browser job.
6. Pause a source and verify UI state.
7. Suppress a contact and verify removal from export.
8. Inspect a contract-renewal estimate.
9. Handle partial source failure without losing existing data.

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
- malicious-file pipeline tests.

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
- partial index failure.

Verify no duplicate opportunities, lost checkpoints, uncontrolled retries, or incorrect success statuses.

## 20. Performance tests

Benchmarks cover:

- records normalized per second;
- entity-resolution batch time;
- opportunity recalculation latency;
- list and search query latency;
- browser-worker concurrency;
- download and parser resource limits;
- index rebuild time;
- large organization timeline rendering.

Performance thresholds are stored in versioned configuration and tested in scheduled CI rather than every small commit.

## 21. Data-quality regression tests

Use representative sanitized datasets to compare releases.

Monitor:

- parsed record count;
- field population rates;
- duplicate rate;
- entity-link decisions;
- number and distribution of signals;
- opportunity score distribution;
- contact suppression behavior;
- freshness calculations.

Unexpected drift blocks deployment until reviewed.

## 22. Architecture tests

Automatically enforce:

- no domain imports of frameworks;
- no cross-module infrastructure imports;
- no direct database access from routes;
- no opportunity imports in source adapters;
- no browser imports outside browser adapters;
- no files above the hard threshold without exception metadata;
- no circular package dependencies;
- frontend feature boundaries.

## CI pipeline

### Pull request

1. formatting and linting;
2. type checking;
3. architecture tests;
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
- frontend end-to-end suite;
- browser end-to-end suite;
- container scan;
- build reproducibility checks.

### Scheduled

- complete security suite;
- performance tests;
- resilience tests;
- optional approved provider smoke tests;
- data-quality regression suite;
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
- generated organizations and contacts.

Do not commit:

- live credentials;
- cookies or tokens;
- private exports;
- leaked datasets;
- unrestricted personal data;
- malicious binaries.
