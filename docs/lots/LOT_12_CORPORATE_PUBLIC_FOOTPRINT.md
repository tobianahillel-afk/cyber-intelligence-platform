# Lot 12 — Corporate Public Footprint, Documents, Search, and Archives

## Status

`IN_PROGRESS`

The technical foundation, bounded public-web adapter, immutable history, protected read API, analyst workspace, tombstones, and quarantined search leads are implemented. The lot remains in progress because no real organization website or search provider has a reviewed authorization and executable policy in the repository.

## Primary business outcome

Build a reproducible public-evidence map for each organization so analysts can discover contracts, projects, technologies, providers, changes, security objectives, and professional contact paths that are absent from structured registries.

## Dependencies

- Lot 08 — organization identity foundation;
- Lot 10 — source portfolio runtime, backfill, freshness, cost, and health;
- Lot 11 — procurement history, contracts, published providers, and renewal timing.

## Canonical distinctions

```text
search result or analyst query
  != approved target retrieval
  != immutable resource version
  != extracted claim
  != resolved fact
  != current commercial opportunity
```

A search result is a discovery lead. It cannot independently confirm a claim. A search result and the target page it points to belong to the same corroboration group and never count as two independent sources.

## Implemented architecture

### Public resource identity

Every public resource has a deterministic identity based on:

- canonical organization;
- canonical URL;
- resource kind;
- source and discovery method.

The domain supports sitemaps, feeds, structured data, public pages, documents, public repositories, archive snapshots, search-result metadata, and direct analyst-approved targets.

### Immutable versions

Fetched content creates immutable versions containing only bounded metadata:

- SHA-256 content hash;
- canonical and fetched URL;
- MIME type and byte size;
- fetch, publication, and source-update timestamps;
- language and bounded title;
- optional hash of extracted text;
- optional minimized summary or excerpt;
- explicit predecessor relationship.

A changed page creates a new version. An unchanged response does not duplicate a version. Historical versions never automatically create a current buying signal.

### Governed public-web adapter

The `public-web-sitemap` adapter implements:

- explicit target registry and organization binding;
- source-policy and authorization evaluation before requests;
- `robots.txt` before sitemap and page retrieval;
- explicit sitemap URLs, host and path allowlists;
- HTTP(S)-only canonical URLs without embedded credentials;
- rejection of local names, internal suffixes and IP-literal targets;
- bounded pages, bytes, resource size and redirects;
- redirect re-evaluation before following;
- bounded HTML, PDF and text MIME handling;
- DTD/entity rejection for sitemap XML;
- `noindex` and `noarchive` suppression;
- credential-marker quarantine;
- transactional worker persistence and replay-safe checkpoints.

The checked-in example target is disabled. Its source remains `draft`, its authorization is `missing`, automated collection is false, and it has no schedule.

### Tombstones and archive chronology

HTTP 404 and 410 responses for previously known resources create explicit tombstone versions rather than deleting history or becoming generic transport failures. Tombstones:

- preserve the resource identity and previous resource kind;
- retain the last known resource title;
- contain no response body;
- record a deterministic status hash and bounded status excerpt;
- supersede the last known version;
- create no claim;
- replay without duplicate observations or versions.

### Search leads and query templates

Search support is intentionally split from provider execution:

- versioned query templates are loaded from `policies/search_query_templates.yml`;
- all checked-in templates are disabled by default;
- no external search provider is connected by this lot without a separate approved source;
- result metadata maps to `search_result` resources in `quarantined` state;
- optional claims remain `candidate` and are capped at 0.5 confidence;
- search metadata can never produce a confirmed claim;
- the search lead and its target page share one corroboration group but retain distinct resource identities.

### Protected analyst access

The protected read-only API exposes:

- `GET /v1/public-footprint/resources`;
- `GET /v1/public-footprint/resources/{resource_id}`.

The list supports pagination, organization/source/kind/access/retrieval/claim filters and local text search across already persisted URLs, titles and claims. An analyst search never launches network collection.

The `/research` workspace provides:

- resource list and filters;
- collection, access and quarantine state;
- version and claim counts;
- immutable version chronology;
- hashes and predecessor links;
- evidence basis, confidence and resolution state;
- canonical source and corroboration provenance.

## Source families planned

1. approved sitemap and feed discovery;
2. bounded public-domain crawl;
3. public PDF and document metadata with minimized extraction;
4. GitHub/GitLab public organization and repository metadata;
5. approved search APIs and versioned analyst query templates;
6. Common Crawl and Wayback/CDX when source policy permits;
7. official corporate reports, presentations, documentation, engineering blogs, and career pages.

Each family requires its own source-policy decision and adapter contract. Catalog entries remain non-executable until approved.

## Mandatory invariants

1. No target outside an approved host or path is fetched.
2. Robots, terms, authorization, quota, and source governance are evaluated before network access.
3. No paywall, authentication, CAPTCHA, MFA, or access-control bypass is attempted.
4. No private repository, personal workspace, secret, credential, or non-public document is collected.
5. Search metadata remains a lead until the target is retrieved through an approved path.
6. Search metadata and target content do not count as independent corroboration.
7. Full documents are not indiscriminately mirrored; extraction is bounded and purpose-limited.
8. Redirects, canonical URLs, copies, and archive snapshots converge without duplicate facts.
9. Corrections, disappearance, tombstones, and retractions remain historical events.
10. Backfill reconstructs historical footprint without flooding the current Opportunity Inbox.

## Validation coverage

The automated suite covers:

- URL canonicalization, IDNA and IPv6 rendering;
- invalid URL, local host and IP-literal rejection;
- host/path/page/byte/resource/redirect budgets;
- robots-first behavior and out-of-scope redirect refusal;
- MIME and resource-size rejection;
- sitemap duplicate filtering and XML entity rejection;
- deterministic resource identity and version keys;
- duplicate, changed and redirected resource behavior;
- credential quarantine and indexing suppression;
- 404/410 tombstone chronology and replay;
- search-result-only claims remaining candidates;
- shared corroboration group between search lead and target;
- query-template registry uniqueness and default disablement;
- source/target/portfolio non-executability consistency;
- transactional worker persistence and replay idempotence;
- reversible migrations;
- protected API authentication, filters, search and detail;
- frontend typecheck and production build;
- complete CI and coverage gate.

## Remaining exit work

- replace the schema-only example with at least one real organization and reviewed authorization, or explicitly accept that production activation is outside this lot;
- add an approved search provider before any query template can execute;
- add approved archive-provider adapters such as CDX only after source-policy review;
- produce the final validation report and release decision;
- update the PR from draft only when the accepted exit gate is satisfied.

## Exit gate

An organization workspace can display its public footprint, document versions, archive chronology, and extracted business/cyber claims with provenance, date, confidence, resolution status, and explanation, without indiscriminate mirroring or access bypass.

The software path for this workspace is implemented. Production collection remains intentionally unavailable until a real source and target receive reviewed authorization.

## Non-goals

- personal-profile crawling;
- LinkedIn, Discord, BrixHub, or other conditional sources without explicit authorization;
- global entity resolution;
- final commercial scoring;
- authenticated browser automation;
- mass storage of copyrighted documents;
- autonomous outreach or engagement.
