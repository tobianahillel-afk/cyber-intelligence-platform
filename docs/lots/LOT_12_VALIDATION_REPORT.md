# Lot 12 — Validation Report

## Decision

- Technical implementation: `PASS`
- Security and governance controls: `PASS`
- Production source activation: `BLOCKED_BY_DESIGN`
- Pull request recommendation: keep `DRAFT` until the project accepts that real-source authorization is a separate governance step, or until at least one real target receives reviewed authorization.

This decision distinguishes software readiness from permission to collect a real organization. The implementation is validated, but the checked-in public-web source remains deliberately non-executable.

## Validated implementation head

- Branch: `agent/corporate-public-footprint`
- Implementation commit: `6321a038da12638dc37a86a9000433a207250af2`
- CI run: `#606`
- Migration head: `20260805_0012`
- Application version: `0.12.0`

This report is added after the validated implementation commit. Its addition changes documentation only and does not alter runtime behavior.

## Automated validation evidence

### Dependencies and security audit

- editable project installation: `PASS`
- dependency consistency with `pip check`: `PASS`
- Python dependency audit: `PASS`, no known vulnerabilities reported
- frontend dependency audit: `PASS`

### Static quality

- Ruff: `PASS`
- Mypy strict: `PASS`
- typed Python files checked: `265`
- architecture and release contracts: `13 passed`

### Database lifecycle

The complete PostgreSQL migration cycle passed:

1. upgrade from base to `20260805_0012`;
2. downgrade from `20260805_0012` to base;
3. upgrade again from base to `20260805_0012`.

Result: `PASS`.

### Backend behavior and coverage

- tests passed: `604`
- tests failed: `0`
- warnings: `1`
- branch coverage: `91.33%`
- required coverage threshold: `90%`
- result: `PASS`

The single warning is a Starlette TestClient deprecation warning concerning the future `httpx2` transition. It is not a functional test failure and does not affect the Lot 12 release decision.

### Frontend

- TypeScript typecheck: `PASS`
- production build: `PASS`
- Research workspace routes: `PASS`

## Capabilities validated

### Canonical public evidence

- deterministic canonical URL handling;
- IDNA and IPv6-safe rendering;
- rejection of embedded credentials, invalid schemes, local names, internal suffixes and IP-literal targets;
- stable resource identity, corroboration group and immutable version keys.

### Bounded public-web collection

- explicit organization-bound targets;
- source-policy and authorization checks before requests;
- `robots.txt` before sitemap and page requests;
- explicit host and path scope;
- bounded pages, total bytes, resource size and redirects;
- redirect scope re-evaluation;
- bounded HTML, PDF and text handling;
- sitemap duplicate filtering and XML DTD/entity rejection;
- `noindex` and `noarchive` suppression;
- credential-marker quarantine;
- no raw-content persistence.

### Persistence and replay

- transactional worker persistence;
- durable chain from collection job to observation, resource, version, claim and checkpoint;
- idempotent replay without duplicate observations or versions;
- compatible loading of pre-resource-kind checkpoints;
- no current opportunity generated from historical public-footprint evidence alone.

### Change and tombstone history

- changed content produces a new immutable version;
- unchanged content does not duplicate versions;
- HTTP 404 and 410 produce explicit tombstones;
- tombstones preserve resource identity, resource kind and last known title;
- tombstones contain no response body and create no claim;
- tombstones supersede the previous version and replay idempotently.

### Search-result quarantine

- versioned query templates are machine-readable;
- all checked-in templates are disabled by default;
- no external search provider is connected;
- search-result metadata remains a quarantined lead;
- search-derived claims remain `candidate` and are capped at `0.5` confidence;
- search metadata cannot confirm a claim;
- search lead and target page share a corroboration group without counting as independent evidence.

### Protected read access

- authenticated resource list endpoint;
- authenticated resource detail endpoint;
- pagination and organization/source/kind/access/retrieval/claim filters;
- local search over persisted URLs, titles and claims;
- analyst search does not initiate network collection;
- complete immutable version chronology and claim provenance.

### Analyst workspace

- `/research` navigation entry;
- resource list and filters;
- collection, access, quarantine and tombstone states;
- version and claim counts;
- immutable version timeline;
- hashes and predecessor links;
- evidence basis, resolution status and confidence;
- canonical source and corroboration provenance.

## Non-executable safeguards validated

The checked-in schema example is blocked independently at multiple levels:

- source status: `draft`;
- authorization status: `missing`;
- automated collection allowed: `false`;
- approved hosts: empty;
- approved paths: empty;
- approved purposes: empty;
- target enabled: `false`;
- source portfolio status: `candidate`;
- collection schedule: absent;
- search templates enabled: `false`.

A cross-registry test verifies that the source, target and portfolio identifiers remain aligned while the example cannot execute accidentally.

## Residual risks and accepted limitations

1. No real organization website has reviewed authorization in the repository.
2. No approved search provider is connected.
3. No approved archive provider such as CDX is connected.
4. PDF support currently records bounded document evidence; advanced document text extraction remains source- and format-dependent.
5. The TestClient deprecation warning should be addressed during a future dependency-maintenance lot.
6. The pull request contains a large technical foundation and should receive normal human review before merge.

## Release recommendation

The Lot 12 technical foundation is suitable for merge only if the project treats production source activation as a separate, explicit governance operation. Merging this pull request does not authorize or schedule collection against a real organization.

If the Lot 12 acceptance criteria require a live authorized production target inside the same pull request, the pull request must remain in draft until that authorization exists. No code change should simulate or invent that approval.
