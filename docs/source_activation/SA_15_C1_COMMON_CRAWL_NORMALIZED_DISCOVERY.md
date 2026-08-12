# SA-15 C1 — Common Crawl normalized discovery bridge

## Status

`IN_PROGRESS` until the exact final candidate SHA passes both normal repository CI and the real Common Crawl production live workflow.

Common Crawl already has a real production adapter and historical `live_tested` proof from SA-14. C1 closes the remaining SA-15 consolidation gap: Common Crawl archive-index discoveries must enter the same normalized discovery and governed acquisition path introduced by SA15-L01/L09.

## Objective

The required runtime chain is:

```text
PublicWebTarget
-> CommonCrawlIndexAdapter
-> immutable RawObservation + quarantined ARCHIVE_SNAPSHOT projection
-> Common Crawl normalized bridge
-> SearchProviderExecution
-> normalize_search_executions()
-> SearchDiscoveryCandidate
-> governed SA15-L09 acquisition routing
```

The bridge does not relabel Common Crawl as a general web-search engine. It uses an explicit archive-discovery template and preserves `common-crawl-index` as the provider/source identity.

## Implementation contract

`common_crawl_search_bridge.py` provides:

- `build_common_crawl_search_plan()` with the explicit `common-crawl-archive-discovery` template;
- `common_crawl_batch_to_search_execution()` to translate bounded Common Crawl projections into the canonical L01 `SearchProviderExecution` contract;
- `normalize_common_crawl_batch()` to execute the existing `normalize_search_executions()` path without a parallel normalization implementation.

The bridge fails closed when:

- the template, version, purpose or provider identity is not the Common Crawl archive-discovery contract;
- a projection belongs to another organization;
- a projection originates from another source;
- archive metadata contains claims;
- archive metadata escaped quarantine;
- more than the Common Crawl adapter's 50-result bound reaches normalization.

## Evidence boundary

C1 preserves all existing archive restrictions:

- Common Crawl index metadata is discovery lineage, not proof of current website state;
- WARC bodies are not retrieved by this path;
- no automatic claim is created;
- normalized candidates begin as `UNROUTED`;
- only SA15-L09 may choose an approved acquisition route;
- a candidate outside an executable same-organization public-web target remains source-review work.

## Deterministic validation

Network-free tests cover:

- explicit archive-plan identity;
- real adapter-batch to `SearchProviderExecution` conversion;
- canonical URL normalization;
- provider provenance;
- deterministic ordering;
- `UNROUTED` initial acquisition state;
- non-archive plan rejection;
- cross-organization rejection.

## Controlled production live validation

The C1 live runner uses the real production `CommonCrawlIndexAdapter` against Common Crawl's public index and the neutral Common Crawl Foundation website target.

The exact live chain must produce:

1. between 1 and 50 real Common Crawl observations;
2. one quarantined archive projection per observation;
3. zero claims;
4. at least one normalized `SearchDiscoveryCandidate`;
5. preserved provider identity `common-crawl-index` in every normalized hit;
6. candidate count no greater than the underlying observation count after canonical deduplication;
7. one SA15-L09 route per candidate;
8. every controlled candidate routed through the executable governed `PublicWebTarget` rather than an unrestricted fetch.

The runner performs real network I/O through the production Common Crawl client. A mock, skipped workflow, earlier SA-14 run, or documentation-only assertion does not satisfy the C1 completion gate.

## Completion rule

C1 becomes `IMPLEMENTED_VALIDATED` only after:

1. deterministic tests pass;
2. Ruff passes;
3. strict Mypy passes;
4. architecture/release contracts pass;
5. reversible migration gates remain green;
6. complete backend tests and coverage remain above repository thresholds;
7. frontend gates remain green;
8. the C1 real Common Crawl workflow succeeds;
9. the exact live proof is recorded in this document;
10. that documentation commit itself passes both CI and the C1 live workflow on the same final SHA.

Only after those ten conditions are met may the SA-15 audit mark the Common Crawl normalized-pipeline row green.
