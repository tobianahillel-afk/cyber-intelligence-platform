# Lot 12 — Validation Report

## Decision

- Technical implementation: `PASS`
- Security and governance controls: `PASS`
- Software release status: `IMPLEMENTED_VALIDATED`
- Production source activation: `SEPARATE_GOVERNANCE_OPERATION`
- Application version: `0.13.0`
- Migration head: `20260805_0012`

The project accepts the Lot 12 boundary: software readiness and permission to collect a real organization are separate decisions. Merging this lot does not authorize or schedule collection against a real target.

The checked-in public-web example remains deliberately non-executable. A future activation requires a reviewed organization target, source policy, authorization reference, executable source-portfolio state, and explicit schedule. Search and archive providers require their own approvals.

## Validation rule

The authoritative release evidence is the successful GitHub Actions CI run attached to the final pull-request head of PR `#35`.

A validation result is valid only when that exact final head passes:

- Python dependency consistency and vulnerability audit;
- Ruff;
- Mypy strict;
- architecture, complexity, dependency, release, and roadmap contracts;
- PostgreSQL migration `upgrade -> downgrade -> upgrade`;
- complete backend tests with branch coverage at or above `90%`;
- frontend dependency audit;
- TypeScript typecheck;
- Next.js production build.

Any later commit invalidates the result and requires another complete run.

## Prior implementation evidence

Before final release reconciliation, the implementation passed CI runs `#606` and `#607`.

The validated implementation included:

- `604` passing backend tests;
- `0` failed backend tests;
- `91.33%` branch coverage;
- `13` passing architecture and release contracts;
- successful PostgreSQL migration reversal;
- successful frontend audit, typecheck, and production build;
- no known Python dependency vulnerability reported by the configured audit.

These prior runs demonstrate implementation stability. The final release decision still depends on a successful run for the final version and documentation head.

## Capabilities validated

### Canonical public evidence

- deterministic canonical URL handling;
- IDNA-safe rendering;
- rejection of embedded credentials and invalid schemes;
- rejection of local names, internal suffixes, and IP-literal targets;
- stable resource, corroboration-group, and immutable-version identities.

### Governed bounded collection

- explicit organization-bound targets;
- source-policy and authorization checks before requests;
- `robots.txt` before sitemap and page requests;
- explicit host and path scope;
- bounded pages, total bytes, resource size, and redirects;
- redirect scope re-evaluation;
- bounded HTML, PDF, and text handling;
- sitemap duplicate filtering and XML DTD/entity rejection;
- `noindex` and `noarchive` suppression;
- credential-marker quarantine;
- no raw-content persistence;
- runtime-derived collector user-agent version.

### Persistence and replay

- transactional worker persistence;
- durable chain from collection job to observation, resource, version, claim, and checkpoint;
- idempotent replay without duplicate observations or versions;
- compatible loading of earlier checkpoint shapes;
- no current opportunity generated from historical public-footprint evidence alone.

### Change history and tombstones

- changed content produces a new immutable version;
- unchanged content does not duplicate versions;
- HTTP `404` and `410` produce explicit tombstones;
- tombstones preserve resource identity, kind, title, and chronology;
- tombstones contain no response body and create no claim;
- tombstones supersede earlier versions and replay idempotently.

### Search-result quarantine

- versioned query templates are machine-readable;
- all checked-in templates are disabled by default;
- no external search provider is connected;
- search metadata remains a quarantined lead;
- search-derived claims remain candidates with confidence capped at `0.5`;
- search metadata cannot confirm a claim;
- a search lead and its target page cannot count as independent corroboration.

### Protected read access and analyst workspace

- authenticated resource list and detail endpoints;
- pagination and organization/source/kind/state filters;
- local search over persisted data only;
- no analyst-query-triggered network collection;
- immutable version chronology and claim provenance;
- `/research` resource list and detail views;
- states, hashes, predecessor links, evidence basis, resolution status, confidence, and corroboration provenance.

## Non-executable safeguards

The example is blocked independently at multiple levels:

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

Cross-registry tests verify that identifiers remain aligned while the example cannot execute accidentally.

## Review findings incorporated during finalization

- The release version was advanced from `0.12.0` to `0.13.0`.
- The collector user agent now derives its version from the authoritative runtime package instead of a hard-coded value.
- The README and authoritative delivery plan were reconciled with the implemented state of lots `09–12`.
- Lot 12 was marked complete while retaining the production-authorization boundary.
- The next planned implementation lot is Lot `13`.

## Accepted limitations and residual risks

1. No real organization website is authorized in the repository.
2. No approved search provider is connected.
3. No approved archive provider such as CDX is connected.
4. PDF support stores bounded evidence metadata; advanced extraction remains format-dependent.
5. DNS-resolution pinning remains a future hardening topic; current collection is restricted to explicitly reviewed public DNS targets and bounded static HTTP.
6. Isolated browser and download-quarantine execution remains deferred.
7. A dependency-maintenance lot should address the existing Starlette TestClient deprecation warning.

## Release recommendation

Merge using a squash commit only after the exact final PR head completes the full CI workflow successfully and the PR has no unresolved review threads.

After merge:

- close Lot 12 issue `#34` as completed;
- retain issues `#3`, `#5`, and `#6` because they represent deferred or future work rather than unfinished Lot 12 tasks;
- begin Lot 13 only from the merged `main` commit;
- do not activate any public-web, search, or archive source without a separate governance review.
