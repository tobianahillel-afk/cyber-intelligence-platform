# SA-02 — Governed web search and archive acquisition

## Status

Implementation unit SA-02 in Wave A.

Clean base: merged SA-01 squash `7fa6d10ff7442098638d056c29946c9262d59c51` on `main`.

SA-02 is complete only when one exact final branch head passes every standard repository gate and is squash-merged without subsequent repository-content changes.

## Outcome

SA-02 activates two bounded external discovery paths around the existing Lot 12 corporate public-footprint model:

- Brave Search API for search-result discovery metadata;
- Internet Archive CDX for historical capture discovery metadata.

It does not create a new crawler. The Lot 12 public-web adapter remains the authoritative target-content collection path and continues to require explicit enabled `PublicWebTarget` configuration and exact target source policy.

## Architecture

```text
approved PublicWebTarget
  + enabled SearchQueryTemplate
  + Brave source governance
  + connected secret reference
  + executable adapter capability
  -> Brave Search metadata
  -> RawObservation
  -> SearchResultLead
  -> quarantined SEARCH_RESULT

approved PublicWebTarget
  + Internet Archive source governance
  + executable adapter capability
  -> bounded CDX capture metadata
  -> RawObservation
  -> ArchiveCaptureLead
  -> quarantined ARCHIVE_SNAPSHOT
```

Neither path produces a claim, evidence-backed signal, need hypothesis or opportunity.

The adapters register through the existing `collection_orchestration` composition and reuse the durable scheduler, worker, checkpoints, retry/circuit, source-health and provenance machinery. There is no separate search worker or archive worker.

## Brave Search adapter

The Brave adapter:

- considers only enabled public-web targets;
- considers only enabled search-query templates;
- renders the query from the target canonical organization name and the reviewed template;
- evaluates Source Governance before resolving a credential or making a request;
- obtains the API token transiently through a callable provider-secret supplier;
- fails closed with `provider_not_connected` if no connected secret is available;
- sends only a bounded result count;
- disables redirects;
- caps response size;
- validates JSON against provider-specific Pydantic schemas;
- hashes minimized provider result metadata into RawObservation provenance;
- maps results through the existing Lot 12 `SearchResultLead` path;
- keeps every resulting `SEARCH_RESULT` quarantined with zero claims.

Checkpoint state rotates deterministically through enabled `(target, template)` pairs. Invalid checkpoint state fails closed.

## Internet Archive CDX adapter

The archive adapter:

- considers only enabled public-web targets;
- evaluates Source Governance before network I/O;
- queries the exact CDX endpoint for the target base URL;
- requests only a bounded field set;
- filters successful historical captures;
- collapses duplicate digests;
- caps rows to 50 per request;
- validates header and row shape strictly;
- converts the CDX timestamp into an aware UTC `capture_at` value;
- maps metadata to `ARCHIVE_SNAPSHOT` in quarantined state;
- creates zero claims;
- records historical chronology explicitly;
- performs no request at all when there is no enabled target.

The adapter does not fetch archived page bodies. Any later content retrieval is a separate governed path.

## Provider onboarding and secret lifecycle

`provider_onboarding.yml` adds:

- Brave Search API: API-key authentication, secret name `api_token`, initial state `not_configured`, no automatic onboarding;
- Internet Archive CDX: no authentication, automatic onboarding, initial state `connected`.

`resolve_connected_secret()` resolves a secret value only from a persisted `CONNECTED` onboarding profile whose secret is not expired. It delegates to the existing Lot 09 secret-reference resolver and returns `None` for unavailable references rather than bypassing onboarding.

The adapter never persists the resolved token.

## Source Governance and Source Portfolio

SA-02 adds exact governed source definitions and portfolio capabilities for Brave and CDX.

Brave:

- exact HTTPS host/path/purpose;
- `public_result_metadata` only;
- raw storage false;
- executable adapter capability;
- deployment secret dependency;
- schedule disabled by default.

CDX:

- exact HTTPS host/path/purpose;
- `official_document_discovery` metadata only;
- raw archive-body storage false;
- executable adapter capability;
- weekly schedule;
- backfill capability limited to historical metadata discovery.

An executable portfolio entry is not permission by itself; runtime registration and Source Governance remain authoritative.

## Source activation truth

The machine-readable activation inventory is updated to distinguish:

- implementation and executable capability;
- schedule state;
- controlled live-test evidence.

SA-02 does not fabricate `live_tested=true` from deterministic unit tests. Live provider validation is recorded separately only when a controlled deployment has approved credentials/targets and a real provider request has been observed successfully.

## Tests

Deterministic tests cover:

- Brave successful result mapping;
- result remains quarantined and produces zero claims;
- exact provider header and decoded query semantics;
- missing Brave secret fails closed before network I/O;
- no enabled target means no secret lookup and no network I/O;
- CDX historical capture mapping;
- archive resource remains quarantined and produces zero claims;
- CDX capture chronology;
- no enabled archive target means no network I/O;
- provider-onboarding profile defaults;
- runtime secret resolution from connected/non-expired profiles;
- Source Activation/Source Portfolio reconciliation;
- runtime schedule composition including search/archive schedules;
- complete repository regression and branch-aware coverage gate.

Unit tests use mock transports and cannot access the live network.

## Explicit non-goals

SA-02 does not implement:

- arbitrary web search on analyst input;
- unrestricted dork execution;
- arbitrary HTTP tools;
- recursive crawler replacement;
- browser automation;
- login/session automation;
- CAPTCHA/MFA/paywall/access-control bypass;
- archived page-body scraping through CDX;
- evidence promotion from result metadata alone;
- current-fact inference from historical captures;
- opportunity creation or outreach.

## Exit gate

SA-02 is validated only when the exact final head passes:

1. dependency consistency;
2. installed-dependency security audit;
3. Ruff;
4. strict Mypy;
5. architecture/release contracts and hard complexity budgets;
6. reversible PostgreSQL Alembic cycle;
7. full pytest with branch-aware aggregate coverage >=90%;
8. frontend audit, typecheck and production build;
9. no unresolved review blocker;
10. no repository-content commit after the validated SHA before squash merge.
