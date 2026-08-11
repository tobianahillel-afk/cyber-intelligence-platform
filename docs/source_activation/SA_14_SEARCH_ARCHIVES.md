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

## Target and checkpoint semantics

Common Crawl reuses the existing `PublicWebTarget` scope rather than introducing a parallel organization-target model.

The adapter expands each enabled target into exact allowed path prefixes. A target/prefix pair is queried using an index wildcard scoped to that origin and prefix. Returned URLs are independently checked through the target's `CrawlScope` before persistence.

The checkpoint contains:

- the next target/prefix index;
- the last processed Common Crawl collection ID per target/prefix pair.

The provider collection list may still be checked on a later schedule run, but an unchanged crawl ID prevents a duplicate capture query for the same target/prefix.

## Provider governance

Only these Common Crawl provider paths are authorized:

- `/collinfo.json` for published collection metadata;
- `/CC-MAIN-...-index` for bounded CDXJ index queries.

Raw crawled content is not authorized by this source path. Common Crawl's terms also make clear that third-party crawled content may have separate rights and must not be treated as provider-verified truth.

## Controlled live validation

The dedicated `.github/workflows/sa14-live-validation.yml` workflow runs `scripts/live_validate_sa14.py` against the production adapter itself. The controlled target is Common Crawl's own public domain, so provider behavior is tested without using a prospect organization as a test target.

The successful provider proof on source head `142208db3d42bc956d672297c2e7ef0408c086b9` used current crawl `CC-MAIN-2026-30` and produced:

- Common Crawl index observations: `43`;
- quarantined public-footprint projections: `43`;
- claims: `0`;
- WARC bodies retrieved: `0`.

The exact one-for-one observation/projection count proves that live provider index records survive the real adapter boundary while preserving the metadata-only quarantine boundary. It does not make those historical URLs factual evidence of current organization state.

This controlled proof justified adding `live_tested` to Common Crawl Source Activation. Because this documentation and activation change modify the branch head, the dedicated live workflow and complete repository CI must pass again on the exact final merge candidate.

## GDELT migration boundary

GDELT remains a high-value SA-14 event/news-discovery candidate. In 2026 the provider announced migration of the API ecosystem toward GDELT 5 / Spanner. SA-14 will not create a new production adapter against a legacy contract merely to mark the candidate complete. GDELT will be revisited against the current documented public interface once the migration provides a stable provider-specific execution contract.

## Completion gate for the Common Crawl tranche

Common Crawl may be squash-merged only when:

1. source governance, portfolio, schedule and runtime registration agree on the same provider identity;
2. deterministic tests cover collection selection, target scope, schema drift, historical collection identities, checkpoint replay and failure classification;
3. the production adapter obtains non-empty metadata from a controlled approved target through the real Common Crawl service;
4. each live capture maps one-for-one into a raw observation and a quarantined public-footprint projection with zero claims;
5. no WARC body is fetched;
6. the complete repository CI and dedicated SA-14 live workflow pass on the exact final PR head;
7. reviews and review threads are clear before squash merge.
