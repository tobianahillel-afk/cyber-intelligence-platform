# SA-16 L02 — Bounded recursive static public-web crawler

## Status

`IMPLEMENTED_FINAL_VALIDATION_PENDING`.

L02 extends the automatic governed target delivered by SA16-L01 into bounded same-origin static link traversal. The implementation candidate immediately preceding this closeout document passed both complete repository CI and a real exact-head Python.org recursive crawl. Because this documentation change creates a new content head, **this final PR head must independently repeat both gates before merge**. No earlier successful run is substituted for the final gate.

L02 does not introduce browser rendering, authenticated navigation, JavaScript execution, sitemap-index recursion or incremental recrawl; those remain later SA16 increments.

## Production path

```text
Organization.website_url
-> SA16-L01 automatic governed PublicWebTarget
-> homepage / explicit discovery candidates
-> PublicWebClient
-> static HTML link extraction
-> deterministic BFS frontier
-> same-origin + approved-path + max-link-depth admission
-> PublicWebClient again for every child URL
-> RawObservation + PublicResourceVersion + checkpoint
```

No recursive child fetch bypasses `PublicWebClient`. Each child therefore re-enters the existing robots, crawl-scope, redirect, response-type and byte-budget controls.

## Implementation

- `PublicWebTarget.max_link_depth` explicitly controls only HTML-anchor recursion.
- Checked-in/legacy targets default to `max_link_depth=0`, preserving their previous non-recursive HTML behavior.
- The underlying `CrawlScope` retains at least structural depth `1`, preserving the pre-L02 contract used by existing RSS/Atom and sitemap discovery. Link recursion and structural feed/sitemap discovery are therefore no longer conflated.
- `AutomaticPublicWebPolicy` defaults to a conservative one-link-hop `max_link_depth=1` and provisions that value into automatic company targets.
- `PublicWebClient.fetch_page()` receives the actual candidate depth rather than hard-coding depth zero, so depth admission is enforced by the existing crawl-scope gate before network I/O.
- Static HTML anchors are canonicalized relative to the fetched parent URL, fragments are removed by canonical URL identity, query parameters are deterministically normalized and duplicates are discarded.
- `rel=nofollow` anchors are not enqueued.
- non-HTTP(S) links are rejected by canonical URL validation.
- off-origin and out-of-approved-path links are discarded before enqueue and are still re-evaluated by source governance/client policy before any network request.
- traversal is deterministic breadth-first order.
- the existing `max_pages`, `max_total_bytes`, `max_resource_bytes`, `max_redirects` and robots rules remain authoritative.
- linked resources use `DiscoveryMethod.LINK` and retain the parent fetched URL in `PublicResourceVersion.source_locator`.

## Compatibility correction found during validation

The first L02 candidate set `PublicWebTarget` depth to zero by default. Normal CI correctly exposed that RSS/Atom parsing historically evaluates discovered entries at structural depth `1`; five existing feed tests failed even though the first real recursive Python.org live run succeeded.

That candidate was rejected. L02 now separates `max_link_depth` from the structural crawl-scope depth instead of weakening or rewriting the existing feed tests. Legacy feeds/sitemaps keep their historical admission behavior while HTML-link recursion remains opt-in for legacy targets.

## Replay and checkpoint boundary

L02 deliberately keeps the durable checkpoint format focused on resource/version state rather than persisting an arbitrary URL frontier. A collection run deterministically rebuilds its bounded BFS frontier from the governed seeds and the fetched HTML. This means retry/replay cannot expand beyond the same target link-depth/page/path/origin budgets, while unchanged page hashes reuse the existing checkpointed version ids.

Incremental frontier persistence, freshness prioritization, tombstone sweeps and recrawl scheduling are later SA16 work and are not claimed by L02.

## Deterministic tests

Tests cover:

- canonicalization and deduplication of static anchor links;
- `rel=nofollow` exclusion;
- bounded link extraction order;
- same-origin confinement;
- link-depth enforcement;
- no duplicate child fetch;
- automatic-target recursive default versus legacy HTML non-recursive default;
- preservation of the historical structural depth needed by existing feed/sitemap discovery;
- checkpoint replay rebuilding the frontier while producing no new observations/versions for unchanged content.

## Controlled real-network validation

`scripts/live_validate_sa16_l02.py` uses the real Python Software Foundation public website through the production provisioner, `PublicWebClient` and collector. The live gate requires:

- the generated homepage seed to be checkpointed;
- at least one real same-origin child page discovered with `DiscoveryMethod.LINK` and fetched by the production collector;
- the child to retain its parent discovery source locator;
- all observations/projections to keep `automatic-public-company-web` provenance;
- no URL to escape the approved `https://www.python.org/` origin;
- total projected pages to remain within the configured page budget;
- exact pull-request head checkout;
- normal repository CI on the same final head.

### Rejected intermediate candidate

`30ecc5254b9628fe39cacdb56afaa48c0ad40bdc` produced a genuine real-network result of **2 observations / 2 projections / 1 linked child**, but normal CI exposed the legacy feed compatibility regression described above. It is not accepted as final proof.

### Corrected validated implementation candidate

`1b4a98008f672f225cf295fea46f9171cb79c307` passed both gates after the compatibility fix:

- **SA-16 L02 Live Validation #9** (`31636984136`): PASS on the exact PR head, with **2 observations, 2 projections, 1 linked child, 2 checkpointed pages, max_link_depth=1**;
- **CI #2002** (`31636984113`): PASS;
- dependency consistency: PASS;
- Python dependency audit: no known vulnerabilities;
- Ruff: PASS;
- strict Mypy: PASS on **697 source files**;
- architecture/release contracts: **36 passed**;
- reversible migrations: PASS;
- backend suite: **1500 passed**;
- branch-aware coverage: **90.10%**;
- frontend audit/typecheck/build: PASS.

This proves the corrected implementation itself, but the **documentation head produced by this closeout must now repeat CI + SA-16 L02 live validation on its own exact SHA** before PR #139 may merge.

A mocked response, skipped workflow, synthetic merge ref, intermediate successful live run or successful L01 run does not satisfy L02 final live proof.

## Exit gate

PR #139 may merge only when its final content head has:

1. frontend audit/typecheck/build green;
2. dependency consistency and Python audit green;
3. Ruff green;
4. strict Mypy green;
5. architecture/release contracts green;
6. reversible migrations green;
7. complete backend tests/coverage green;
8. the real SA-16 L02 production-path live workflow green on that exact head;
9. zero unresolved review threads;
10. squash-merge content proven identical to the validated final Git tree.

Once those conditions hold and the tree-identical squash is on `main`, L02 is complete without another content-changing documentation edit.
