# Source and Tool Adapter Standard

## Objective

Every external tool, API, website, feed, search engine, browser workflow, and import format is integrated through an isolated adapter. The adapter owns provider-specific behavior but cannot contain company resolution, contact selection, need detection, or opportunity scoring.

## Adapter categories

```text
api
feed
static_http
browser
search_provider
bulk_file
manual_import
webhook
licensed_dataset
```

One source may expose several adapters, for example an API adapter and an analyst-assisted browser export adapter. They remain separate implementations with separate manifests and tests.

## Repository structure per source

```text
src/cip/adapters/sources/<source_id>/
  __init__.py
  manifest.yml
  README.md

  auth/
    models.py
    provider.py
    redaction.py

  transport/
    client.py
    requests.py
    responses.py
    retry_policy.py
    rate_limit.py

  discovery/
    endpoints.py
    pagination.py
    cursors.py
    change_detection.py

  extraction/
    collector.py
    browser_flow.py
    selectors.py
    downloads.py

  parsing/
    source_schemas.py
    parser.py
    validators.py

  mapping/
    mapper.py
    identifiers.py
    provenance.py

  runtime/
    checkpoints.py
    health.py
    telemetry.py

  fixtures/
    minimal/
    representative/
    edge_cases/
    schema_drift/

  tests/
    test_manifest.py
    test_auth.py
    test_transport.py
    test_pagination.py
    test_parser.py
    test_mapper.py
    test_incremental.py
    test_failures.py
    test_browser_flow.py
    test_downloads.py
```

Only create files and subfolders that the adapter needs. The standard prevents one large `scraper.py` while avoiding empty boilerplate.

## Manifest

The manifest is the control plane for the adapter.

```yaml
id: example-source
name: Example Source
owner: Example Company
category: commercial_intelligence
status: conditional

acquisition:
  modes:
    - api
    - browser
  preferred: api
  browser_allowed: true
  downloads_allowed: true
  analyst_assistance_allowed: true

scope:
  allowed_hosts:
    - api.example.com
    - app.example.com
  allowed_paths:
    - /v1/
    - /exports/
  allowed_data_categories:
    - organization_metadata
    - public_tenders
  prohibited_data_categories:
    - credentials
    - private_messages

schedule:
  cadence: PT15M
  full_reconciliation: P7D
  freshness_target: PT30M

limits:
  requests_per_minute: 30
  concurrent_jobs: 2
  max_pages_per_job: 100
  max_download_bytes: 25000000
  timeout_seconds: 30

retention:
  raw_days: 7
  normalized_days: 365
  personal_data_days: 180

authorization:
  terms_url: https://example.com/terms
  document_reference: null
  reviewed_at: 2026-08-03
  expires_at: null

schema:
  adapter_version: 1
  source_schema_version: unknown
```

The worker refuses to start an adapter with an invalid or inactive manifest.

## File responsibilities

### `auth/`

Contains only authentication behavior:

- OAuth token acquisition and refresh;
- API-key header construction;
- permitted session restore;
- authentication-state validation;
- secret redaction.

No scraping or mapping logic belongs here.

### `transport/`

Contains network communication:

- URL construction from approved endpoints;
- request serialization;
- response decoding;
- retry classification;
- rate-limit handling;
- transport errors.

The transport layer returns provider responses and never canonical entities.

### `discovery/`

Contains how records are enumerated:

- endpoint lists;
- page numbers;
- cursors;
- updated-since queries;
- index pages;
- change detection;
- backfill windows.

### `extraction/`

Contains acquisition workflow:

- API or HTTP collection orchestration;
- browser navigation flow;
- selectors and rendered-data extraction;
- download initiation;
- conversion to source records.

Selectors must be centralized and named by meaning, not copied across functions.

### `parsing/`

Contains strict provider schemas and validation.

It must detect:

- missing required fields;
- unexpected field types;
- encoding problems;
- schema version change;
- partial records;
- invalid dates;
- oversized values;
- provider error payloads returned with success status.

### `mapping/`

Maps validated provider records into the canonical raw-observation envelope.

It assigns:

- source record key;
- record type;
- observed and published timestamps;
- canonical external identifiers;
- source URL;
- content hash;
- provenance;
- data classification.

It must not decide that two organizations are identical or that a company has a commercial need.

### `runtime/`

Contains operational state:

- checkpoints;
- health calculation;
- collection metrics;
- schema fingerprint;
- latest success;
- failure streak;
- circuit-breaker state.

## Size budgets per adapter

Recommended limits:

| File | Target | Review threshold |
|---|---:|---:|
| `client.py` | 150 lines | 300 |
| `collector.py` | 200 lines | 350 |
| `browser_flow.py` | 200 lines | 350 |
| `parser.py` | 180 lines | 300 |
| `source_schemas.py` | 250 lines | 450 |
| `mapper.py` | 180 lines | 300 |
| `pagination.py` | 120 lines | 220 |
| `downloads.py` | 160 lines | 280 |
| individual test file | 300 lines | 500 |

When a source has several record families, create subpackages by record family instead of extending one parser or mapper indefinitely:

```text
parsing/
  organizations/
  contracts/
  contacts/
  incidents/
```

## Function subdivision

A source collector should read like an orchestration sequence:

```python
async def collect_incremental(context: CollectionContext) -> CollectionBatch:
    checkpoint = await load_checkpoint(context)
    pages = discover_pages(checkpoint)
    records = await fetch_pages(context, pages)
    validated = parse_records(records)
    observations = map_observations(validated)
    return build_batch(observations, checkpoint)
```

Each called function is tested independently. The orchestration function must not contain selector details, schema conversion, retry loops, persistence, and scoring at the same time.

## Adapter SDK

`packages/source_sdk/` provides reusable contracts and utilities:

```text
source_sdk/
  manifest/
  collection/
  transport/
  browser/
  downloads/
  observations/
  checkpoints/
  testing/
```

Reusable features include:

- manifest validation;
- safe URL policy;
- retry and backoff primitives;
- rate-limit tokens;
- pagination helpers;
- ETag and Last-Modified support;
- content hashing;
- browser-job contracts;
- download quarantine client;
- fixture loading;
- standard adapter contract tests.

The SDK must not include provider-specific selectors, endpoints, field names, or business rules.

## Incremental and historical modes

Every adapter explicitly supports zero or more modes:

- `incremental`: only new or changed records;
- `reconcile`: compare current source state with known state;
- `backfill`: retrieve a bounded historical interval;
- `single_target`: enrich one organization or identifier;
- `webhook`: process provider callbacks;
- `manual_export`: ingest an analyst-provided file.

Mode support is declared in the manifest and verified through contract tests.

## Failure strategy

Failures are classified as:

```text
retryable_transport
retryable_rate_limit
retryable_provider_error
authentication_required
manual_action_required
policy_denied
schema_changed
selector_changed
record_invalid
download_quarantined
permanent_not_found
```

Retry loops must be centralized. Parsers and mappers do not sleep or retry.

## Circuit breaker

Pause an adapter automatically when:

- authentication repeatedly fails;
- schema failures exceed the configured threshold;
- CAPTCHA or challenge pages repeatedly appear;
- the provider returns a prohibition or account warning;
- error rate remains above threshold;
- unexpected hosts or redirects are observed;
- downloaded artifacts exceed policy limits.

Resuming requires a successful health probe or analyst review, depending on the failure category.

## Browser-flow design

A browser flow is a state machine, not a long script.

```text
start
-> navigate_login_if_needed
-> verify_session
-> navigate_target
-> wait_for_required_state
-> extract_summary
-> optionally_request_export
-> capture_permitted_evidence
-> finish
```

Each transition has:

- precondition;
- action;
- expected observable state;
- timeout;
- recoverable errors;
- terminal errors;
- permitted screenshots or traces.

Selectors use semantic roles, labels, stable attributes, or documented data hooks before brittle CSS paths.

## Challenge detection tests

Fixtures and browser tests must cover:

- login page instead of expected content;
- expired session;
- MFA prompt;
- consent dialog;
- CAPTCHA or bot challenge;
- account locked or suspended;
- rate-limit warning;
- changed terms;
- access denied;
- changed export workflow.

Expected behavior is safe pause or failure classification, never automated circumvention.

## Account lifecycle

For authorized accounts, store metadata separately from secrets:

```text
account_id
source_id
account_type
owner
purpose
created_at
verified_at
expires_at
last_successful_login
status
secret_reference
authorization_reference
```

Statuses:

```text
pending_verification
active
mfa_required
expired
locked
revoked
needs_review
```

No adapter may automatically create replacement accounts after suspension or quota enforcement.

## Documentation requirements

Each adapter README documents:

- business value;
- source ownership;
- access and authorization;
- acquisition modes;
- records and fields collected;
- schedules and freshness target;
- authentication process;
- known source limitations;
- data-quality risks;
- parser and mapping assumptions;
- test fixtures;
- operational runbook;
- deletion and retention behavior.
