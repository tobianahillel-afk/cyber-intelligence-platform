# SA-15 C1 — Common Crawl normalized discovery bridge

## Status

`IMPLEMENTED` / real provider live proof exists / production-integration revalidation pending on the current internal-completion candidate.

Common Crawl already had a real production adapter and provider `live_tested` proof from SA-14. C1 then proved the real provider path through normalized discovery and governed routing on PR #130. That proof was genuine, but a post-merge review found an integration gap: the live runner manually composed the normalization/router after `CommonCrawlIndexAdapter.collect()`, while scheduled production collection itself stopped after the quarantined archive projections.

The SA15 internal-completion pass closes that gap instead of relabeling the earlier proof. `CommonCrawlIndexAdapter.collect()` now invokes the C1 normalized-discovery/routing contract itself and records a bounded `normalized_discovery` checkpoint containing the provider id, canonical candidate count, governed route counts and route target identifiers. The C1 live runner no longer calls the bridge/router manually; it succeeds only if the real production adapter itself produced that checkpoint.

## Production chain

```text
PublicWebTarget
-> CommonCrawlIndexAdapter
-> real Common Crawl public index
-> immutable RawObservation + quarantined ARCHIVE_SNAPSHOT projection
-> common_crawl_search_bridge
-> SearchProviderExecution
-> normalize_search_executions()
-> SearchDiscoveryCandidate
-> SA15-L09 governed acquisition routing
-> durable normalized_discovery checkpoint
```

The bridge does not relabel Common Crawl as a general web-search engine. It preserves `common-crawl-index` provider/source identity and archive-discovery purpose.

## Fail-closed and evidence boundary

- Common Crawl index metadata is discovery lineage, not proof of current website state.
- WARC bodies are not retrieved by this path.
- no automatic claim is created.
- only same-organization URLs admitted by an executable `PublicWebTarget` can route automatically to `PUBLIC_WEB`.
- L09 cumulative target budgets are enforced across candidates.
- off-origin/out-of-scope/budget-exhausted candidates require source review.
- normalized provider execution timestamps are preserved for audit/replay.

## Existing real live proof

PR #130 final head `71bf84001592e6d294f6f1db2a868e04eef3133a` passed SA-15 Live Validation run #34 against the real Common Crawl public index. The earlier proof demonstrated non-empty provider observations, normalization and governed routing. It remains valid proof that the provider/bridge combination works, but it is not by itself proof of the new production-wired implementation.

## Current revalidation gate

The internal-completion candidate must independently pass, on its exact final SHA:

1. complete repository CI;
2. `live-common-crawl-normalized-discovery` using the real provider;
3. a non-empty production-adapter batch;
4. a non-empty `normalized_discovery` checkpoint produced by the adapter itself;
5. all normalized candidates routed consistently with the controlled governed target;
6. zero unsupported claims;
7. zero unresolved review threads.

No skipped workflow, mock, prior SHA, or manually recomposed bridge execution satisfies this new integration gate.
