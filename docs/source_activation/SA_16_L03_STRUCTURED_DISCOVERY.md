# SA-16 L03 — Governed sitemap and feed discovery

## Status

`FINAL_EXACT_HEAD_REVALIDATION_PENDING`.

L03 extends the merged L01/L02 public-web path with structured static discovery. It does not add browser rendering, authenticated sessions, JavaScript extraction, incremental recrawl, freshness scheduling or crawl-health metrics.

The implementation candidate `e7fb55741b18d43f64aa6fd809c6b9163b99ae99` passed normal repository CI run #2019 and the dedicated real-network SA-16 L03 live run #12. Because this documentation update creates a new PR head, those runs are recorded as candidate evidence only. L03 remains open until the new exact head independently passes both gates, has zero unresolved review threads, and its squash-merged Git tree is identical to the validated head tree.

## Capability

```text
robots.txt Sitemap declarations
-> bounded sitemap queue
-> sitemapindex recursion
-> urlset page candidates

HTML <link rel="alternate" type="application/rss+xml|application/atom+xml">
-> bounded feed queue
-> RSS/Atom entries
-> page candidates

all dynamically discovered URLs
-> Source Governance
-> same-origin/path scope
-> robots
-> size/byte/page budgets
-> existing PublicWebClient
-> existing provenance/checkpoint mapping
```

Automatic targets enable structured discovery with conservative limits. Legacy targets keep `discover_sitemaps=false` and `discover_feeds=false` unless explicitly configured.

Explicitly configured sitemap/feed URLs retain the pre-L03 contract: they are still checked against robots and network-response safety controls, while the new same-origin/path discovery scope is applied to dynamically discovered structured URLs. This preserves existing configured targets without weakening the dynamic-discovery fail-closed path.

## Safety invariants

- no blind sitemap/feed URL guessing;
- robots sitemap declarations are accepted only on the governed target origin and approved path scope;
- sitemap-index children are same-origin/path filtered and bounded by `max_sitemap_depth` and `max_sitemaps`;
- HTML feed discovery accepts only declared alternate RSS/Atom MIME types;
- discovered feeds are same-origin/path filtered and bounded by `max_feeds`;
- every dynamic sitemap/feed is source-authorized before network I/O;
- structured discovery bytes count against the target total-byte budget;
- page candidates still count against `max_pages`;
- structured discovery metadata remains provenance, not an automatic commercial claim;
- page versions discovered from a sitemap or feed retain the structured discovery URL in `source_locator` while keeping the fetched page URL as the version `source_url`.

## Deterministic validation

Tests cover declared feed extraction, sitemap-index filtering/deduplication/bounds, robots-declared sitemap traversal, nested sitemap traversal, dynamic feed fetch, explicit configured sitemap/feed compatibility, source locators and off-origin rejection.

The validated candidate passed the repository's Ruff, strict Mypy, architecture/release-contract, reversible-migration, frontend, full test and coverage gates in CI #2019. These results must be repeated on the final documentation head before merge.

## Real live validation

The dedicated exact-head workflow uses two public first-party/neutral Python ecosystem surfaces:

1. `https://docs.python.org/` — the production client reads `robots.txt`, discovers its declared sitemap and requires real page candidates with `DiscoveryMethod.SITEMAP` and sitemap source locators.
2. `https://blog.python.org/` — the production client reads the homepage, discovers an HTML-declared RSS/Atom feed and requires real page candidates with `DiscoveryMethod.FEED` and feed source locators.

On candidate `e7fb55741b18d43f64aa6fd809c6b9163b99ae99`, live run #12 checked out that exact SHA and completed with `robots_sitemap_pages=4` and `html_feed_pages=4`.

Both cases remain same-origin and bounded. A skipped workflow, mock, configured static feed/sitemap, or another lot's live proof does not satisfy L03.

## Exit gate

L03 is complete only when one final PR head has normal repository CI green, the SA-16 L03 real-network workflow green, zero unresolved review threads, and the squash-merged Git tree is identical to that validated head tree.
