# SA-14 — Search, dorks, and archive discovery expansion

## Objective

SA-14 expands governed discovery without creating a second research subsystem. Search/archive metadata remains a lead that must be followed through an approved retrieval path before it can support a factual claim or commercial conclusion.

Existing Brave Search and Internet Archive/CDX adapters remain authoritative. SA-14 adds provider-specific capabilities only where they provide distinct coverage.

## Common Crawl URL Index

Source id: `common-crawl-index`.

The first SA-14 tranche uses Common Crawl's public CDXJ URL Index through `index.commoncrawl.org`. It does not download WARC bodies.

The adapter first retrieves `collinfo.json`, validates collection metadata and chooses the newest collection by the provider's `to` timestamp. It then queries only the exact approved target/path prefix selected from the existing governed `PublicWebTarget` registry.

### Published collection identity forms

Controlled live validation exposed historical collection identities that are still present in the provider's current `collinfo.json`. The implementation therefore validates the complete published family rather than assuming every historical record follows the modern naming convention:

- modern crawl: `CC-MAIN-YYYY-WW`, for example `CC-MAIN-2026-30`;
- annual legacy crawl: `CC-MAIN-2012`;
- legacy range crawl: `CC-MAIN-2009-2010` and `CC-MAIN-2008-2009`.

These forms are locked through deterministic regression tests. The newest crawl is selected from provider chronology, not by lexically comparing these heterogeneous identifiers.

Provider requests are bounded to 50 capture records and a 2 MB response. A descriptive User-Agent is supplied. Results outside the target's existing crawl scope are discarded even if returned by the provider.

Selected fields are limited to:

- timestamp;
- original URL;
- MIME type;
- HTTP status;
- digest;
- WARC record length;
- WARC offset;
- WARC filename.

The WARC filename/offset/length are retained only as archive-index provenance. This tranche never follows them to `data.commoncrawl.org` and never stores the crawled page body.

Each accepted capture emits an immutable `RawObservation` and a quarantined Lot 12 `ARCHIVE_SNAPSHOT` public-footprint projection. The projection contains no claims. Common Crawl historical presence is not current deployment, exposure, vulnerability, compromise, need, opportunity, or outreach authorization.

## Common Crawl target and checkpoint semantics

Common Crawl reuses the existing `PublicWebTarget` scope rather than introducing a parallel organization-target model.

The adapter expands each enabled target into exact allowed path prefixes. A target/prefix pair is queried using an index wildcard scoped to that origin and prefix. Returned URLs are independently checked through the target's `CrawlScope` before persistence.

The checkpoint contains:

- the next target/prefix index;
- the last processed Common Crawl collection ID per target/prefix pair.

The provider collection list may still be checked on a later schedule run, but an unchanged crawl ID prevents a duplicate capture query for the same target/prefix.

## Common Crawl provider governance

Only these Common Crawl provider paths are authorized:

- `/collinfo.json` for published collection metadata;
- `/CC-MAIN-...-index` for bounded CDXJ index queries.

Raw crawled content is not authorized by this source path. Common Crawl's terms also make clear that third-party crawled content may have separate rights and must not be treated as provider-verified truth.

## Common Crawl controlled live validation

The dedicated `.github/workflows/sa14-live-validation.yml` workflow runs `scripts/live_validate_sa14.py` against the production adapter itself. The controlled target is Common Crawl's own public domain, so provider behavior is tested without using a prospect organization as a test target.

The successful provider proof on source head `142208db3d42bc956d672297c2e7ef0408c086b9` used current crawl `CC-MAIN-2026-30` and produced:

- Common Crawl index observations: `43`;
- quarantined public-footprint projections: `43`;
- claims: `0`;
- WARC bodies retrieved: `0`.

The exact one-for-one observation/projection count proves that live provider index records survive the real adapter boundary while preserving the metadata-only quarantine boundary. It does not make those historical URLs factual evidence of current organization state.

This controlled proof justified adding `live_tested` to Common Crawl Source Activation. The Common Crawl tranche was later exact-SHA validated and squash-merged on `main`.

## GitHub REST code-search metadata

Source id: `github-code-search-metadata`.

The second SA-14 tranche adds a dedicated authenticated GitHub REST Code Search capability. It is intentionally separate from Priority B-2 `github-public-org-repositories`:

- B-2 enumerates public repository metadata for exact configured organizations and never performs global code search;
- SA-14 code search uses GitHub's `/search/code` endpoint only for explicitly configured `github_org` targets and explicitly approved query templates;
- the two adapters have independent source identities, authorization semantics, quotas and runtime credentials.

GitHub Code Search is not used as a source-code ingestion path. CIP never follows the returned content/blob API URLs and never retrieves or stores the matched file contents.

### Query governance

Checked-in templates are stored in `policies/github_code_search_templates.yml` and are disabled by default.

A template is rejected before runtime unless it:

- contains exactly one `{organization}` placeholder;
- contains the exact `org:{organization}` qualifier;
- avoids secret-hunting terms including `password`, `secret`, `token`, `credential` and `private_key`.

The checked-in `developer_ecosystem_targets.yml` registry also remains empty by default. Consequently, source registration alone cannot initiate a GitHub search.

A production request requires all of the following:

1. an enabled canonical-organization-bound `github_org` target;
2. an enabled approved code-search template;
3. Source Governance authorization for `/search/code` and purpose `code-search-discovery`;
4. a connected Provider Onboarding `api_token` secret;
5. an explicit runtime invocation or deployment-enabled schedule.

The checked-in schedule remains `enabled: false`.

### Provider and response bounds

The production client uses:

- `GET https://api.github.com/search/code`;
- `X-GitHub-Api-Version: 2026-03-10`;
- `Accept: application/vnd.github+json`;
- bearer authentication supplied through the existing `connected_secret_supplier` path;
- `per_page=20` and `page=1`;
- a maximum response body of 2 MiB;
- redirects disabled;
- explicit rejection of provider responses marked `incomplete_results=true`.

HTTP quota/rate failures are typed and retryable where appropriate. Schema drift, unsafe response size and invalid checkpoints fail closed.

### Persisted fields and evidence boundary

The provider may use indexed source code internally to answer the search, but CIP persists only bounded result metadata:

- public repository full name;
- repository/path identity;
- file SHA;
- GitHub HTML result URL;
- query-template identity/version;
- result rank.

Private repositories, results outside the exact configured organization and non-`github.com` HTML URLs are discarded.

Each accepted hit emits one immutable `RawObservation` and one quarantined Lot 12 `SEARCH_RESULT` projection. The generated excerpt explicitly states `file content not retrieved`. No candidate `PublicClaim`, `CommercialSignal`, need hypothesis, opportunity or outreach action is created.

A code-search hit therefore means only that GitHub's public search index returned metadata matching an approved organization-scoped query. It does not prove production deployment, technology use, exposure, vulnerability applicability, compromise, security maturity, commercial need or contact authorization.

### Provider Onboarding

Runtime credentials are not read directly from environment variables by the adapter. Production composition uses the existing Provider Onboarding mechanism:

`github-code-search-metadata / api_token -> connected_secret_supplier -> GitHubCodeSearchAdapter`.

The GitHub Actions live workflow is a controlled validation exception: it passes the ephemeral workflow `GITHUB_TOKEN` to the production adapter through the same adapter token-provider boundary. The token itself is never persisted by CIP.

### Controlled live validation

The dedicated SA-14 workflow exercised the real production adapter on source head `1d3079ab9f5a5a464e537b08e7ac4af778bc5b77` using the public GitHub organization `github` as a non-prospect controlled target and the query:

`security org:github filename:SECURITY.md`

The real provider returned the configured maximum page:

- observations: `20`;
- quarantined projections: `20`;
- claims: `0`;
- file-content fetches: `0`.

The same live proof passed again after the Ruff-only formatting correction on head `ad1a2e572ce7cd559104851e45b9fbd3bafda21d`.

This proves the authenticated provider path, organization filtering, metadata mapping and quarantine boundary. It does not turn the returned search hits into factual claims about the target organization.

The GitHub Code Search tranche was later exact-SHA validated and squash-merged on `main` at `2050cb19b4edf7ae7b9aaeaf8e58753d1cd7e5cf`.

## Crossref publication metadata

Source id: `crossref-publication-metadata`.

The third SA-14 tranche adds public scholarly-publication discovery through Crossref REST `/works`. It is target-bound by a canonical CIP organization UUID plus an explicit ROR identifier from `policies/crossref_publication_targets.yml`.

The checked-in target registry is empty and the checked-in schedule is `enabled: false`; merely registering the adapter cannot start organization-wide publication collection.

### ROR targeting semantics

The adapter calls Crossref with `filter=ror-id:<configured-ror>` rather than performing a fuzzy organization-name search. This gives a stable external identifier boundary, but the provider's ROR filter may represent contributor affiliation or funding metadata. Consequently, a returned work is only **ROR-associated publication metadata**. It is not automatically asserted to be authored, owned, endorsed or operationally used by the target organization.

The controlled live target uses Goethe University Frankfurt ROR `04cvxnb49` only to exercise the provider path. It is a research-organization validation target, not a prospect or commercial conclusion.

### Provider and response bounds

The production client uses:

- `GET https://api.crossref.org/works`;
- `filter=ror-id:<configured-ror>`;
- `rows=20`;
- `select=DOI,title,type,URL`;
- `Accept: application/json`;
- an identifiable CIP User-Agent;
- a maximum response body of 2 MiB;
- redirects disabled.

Crossref public REST access requires no provider credential in this capability. HTTP 429 and server failures are typed for retry; transport failures are retryable, while content-type, response-size and schema violations fail closed.

### Data-minimization boundary

The provider response may contain authors, ORCID identifiers, abstracts, references, funding structures or full-text links. Those structures are not part of the Pydantic materialized schema and therefore do not enter the normalized observation material.

CIP persists only:

- configured ROR identifier;
- DOI;
- first non-empty title;
- Crossref work type;
- canonical HTTPS `doi.org` URL.

A result with an empty first title, whitespace in the DOI or a result URL outside HTTPS `doi.org` is discarded.

Each retained item creates one immutable `RawObservation` and one quarantined Lot 12 `SEARCH_RESULT` projection. The excerpt states `Authors, abstract and full text not retrieved.` No candidate `PublicClaim`, commercial signal, need hypothesis, opportunity or outreach action is created.

### Controlled live validation

The dedicated SA-14 workflow runs `scripts/live_validate_sa14_crossref.py` against the production adapter itself. On source head `f0c4158ad033aae3aa8d25ab56b86fd91f7b4265`, the real Crossref API accepted the bounded ROR query and returned the configured full page:

- observations: `20`;
- quarantined projections: `20`;
- claims: `0`;
- full-text fetches: `0`.

The one-for-one observation/projection result proves that the current provider contract, ROR filter and minimal selected schema work through the production adapter. It does not establish authorship, ownership, endorsement, technology deployment or commercial need for the target organization.

That real provider proof justified adding `live_tested` to Crossref Source Activation. Because the documentation and activation promotion change the branch head, the complete normal repository CI and Crossref live workflow must pass again on the exact final candidate before merge.

## GDELT migration boundary

GDELT remains a high-value SA-14 event/news-discovery candidate. In 2026 the provider announced migration of the API ecosystem toward GDELT 5 / Spanner. SA-14 will not create a new production adapter against a legacy contract merely to mark the candidate complete. GDELT will be revisited against the current documented public interface once the migration provides a stable provider-specific execution contract.

## Remaining SA-14 work after Crossref

Crossref completes the first publication-metadata provider, but issue #108 remains open. Remaining work includes:

- a patent-discovery provider with a current provider-specific contract and real live proof;
- a standards/public-specification discovery provider with bounded metadata semantics;
- a second general web-search provider. Mojeek is the current candidate, but it requires a real API entitlement/key before CIP can legitimately mark it `live_tested`;
- GDELT once its current GDELT 5 execution contract is stable enough for a new production adapter.

No provider is considered complete merely because it is catalogued or because a synthetic test passes.

## Completion gate for the Crossref tranche

Crossref may be squash-merged only when:

1. Source Governance, portfolio, runtime registration, target registry and disabled-by-default schedule agree on `crossref-publication-metadata` / `crossref-ror-works`;
2. the checked-in ROR target registry remains empty by default;
3. provider selection is limited to `DOI,title,type,URL`, and authors/abstracts/references/full-text links cannot enter normalized observation material;
4. deterministic tests cover ROR normalization, no-target/no-network behavior, safe DOI mapping, invalid checkpoint, schema drift and rate limiting;
5. the production adapter obtains non-empty metadata from the real Crossref endpoint using a controlled ROR target;
6. every retained live result maps one-for-one to an observation and quarantined projection with zero claims and zero full-text retrieval;
7. `live_tested` is recorded only after the controlled provider proof;
8. complete backend/frontend CI and the dedicated live workflow pass on the exact final PR head;
9. reviews and review threads are clear before squash merge.
