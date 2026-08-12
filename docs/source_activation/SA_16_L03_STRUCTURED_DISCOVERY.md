# SA-16 L03 — Governed sitemap and feed discovery

## Status

`IMPLEMENTATION_VALIDATION_IN_PROGRESS`.

L03 extends the merged L01/L02 public-web path with structured static discovery. It does not add browser rendering, authenticated sessions, JavaScript extraction, incremental recrawl, freshness scheduling or crawl-health metrics.

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

all discovered URLs
-> Source Governance
-> same-origin/path scope
-> robots
-> size/byte/page budgets
-> existing PublicWebClient
-> existing provenance/checkpoint mapping
```

Automatic targets enable structured discovery with conservative limits. Legacy targets keep `discover_sitemaps=false` and `discover_feeds=false` unless explicitly configured.

## Safety invariants

- no blind sitemap/feed URL guessing;
- robots sitemap declarations are accepted only on the governed target origin and approved path scope;
- sitemap-index children are same-origin/path filtered and bounded by `max_sitemap_depth` and `max_sitemaps`;
- HTML feed discovery accepts only declared alternate RSS/Atom MIME types;
- discovered feeds are same-origin/path filtered and bounded by `max_feeds`;
- every dynamic sitemap/feed is source-authorized before network I/O;
- structured discovery bytes count against the target total-byte budget;
- page candidates still count against `max_pages`;
- structured discovery metadata remains provenance, not an automatic commercial claim.

## Deterministic validation

Tests cover declared feed extraction, sitemap-index filtering/deduplication/bounds, robots-declared sitemap traversal, nested sitemap traversal, dynamic feed fetch, source locators and off-origin rejection.

## Real live validation

The dedicated exact-head workflow uses two public first-party/neutral Python ecosystem surfaces:

1. `https://docs.python.org/` — the production client reads `robots.txt`, discovers its declared sitemap and requires at least one real page candidate with `DiscoveryMethod.SITEMAP` and sitemap source locator.
2. `https://blog.python.org/` — the production client reads the homepage, discovers an HTML-declared RSS/Atom feed and requires at least one real page candidate with `DiscoveryMethod.FEED` and feed source locator.

Both cases remain same-origin and bounded. A skipped workflow, mock, configured static feed/sitemap, or another lot's live proof does not satisfy L03.

## Exit gate

L03 is complete only when one final PR head has normal repository CI green, the SA-16 L03 real-network workflow green, zero unresolved review threads, and the squash-merged Git tree is identical to that validated head tree.
