# SA-15 C1 — Common Crawl normalized discovery bridge

## Status

`IMPLEMENTED_VALIDATED` / normalized integration `live_tested` candidate.

Common Crawl already had a real production adapter and provider `live_tested` proof from SA-14. C1 closes the remaining SA-15 consolidation gap: Common Crawl archive-index discoveries now enter the same normalized discovery and governed acquisition path introduced by SA15-L01/L09.

The first complete candidate `d82297cbdd2fb22641a41f66bb2c001be46791cf` passed both the real Common Crawl live workflow and the complete repository CI. This documentation commit intentionally creates a new candidate SHA; C1 is mergeable only after that final documentation SHA independently repeats both gates successfully.

## Objective

The runtime chain is:

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

### First complete proof

Candidate SHA:

`d82297cbdd2fb22641a41f66bb2c001be46791cf`

SA-15 Live Validation run #33 passed the production path with:

- **43** real Common Crawl observations;
- **43** quarantined archive projections;
- **0** automatic claims;
- **23** canonical normalized `SearchDiscoveryCandidate` objects after URL deduplication;
- provider provenance `common-crawl-index` preserved for every normalized hit;
- **23 / 23** candidates routed automatically through SA15-L09 to the governed `PUBLIC_WEB` route;
- no WARC body retrieval and no unrestricted HTTP fallback.

Normal repository CI #1928 also passed on the same candidate:

- dependency consistency and dependency audit: pass;
- Ruff: pass;
- strict Mypy: pass;
- architecture/release contracts: pass;
- reversible migration validation: pass;
- complete backend tests and coverage gate: pass;
- frontend dependency audit, typecheck and production build: pass.

The earlier C1 live attempt failed because the SA16-L01 `PublicWebTarget` model now requires an explicit discovery path. C1 was corrected by declaring the controlled homepage seed instead of weakening the target invariant. The subsequent production run is the proof recorded above.

## Final completion rule

C1 is finally mergeable only when the exact documentation head containing this proof itself passes:

1. complete repository CI;
2. the real SA-15 Common Crawl normalized live workflow;
3. all live invariants again with a non-empty provider payload;
4. zero unresolved review threads.

A skipped job, mock, earlier SHA or successful run that does not execute the production adapter does not satisfy this gate.
