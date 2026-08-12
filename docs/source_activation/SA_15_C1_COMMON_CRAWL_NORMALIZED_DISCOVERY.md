# SA-15 C1 — Common Crawl normalized discovery bridge

## Status

`IMPLEMENTED_VALIDATED_MERGED` on the corrected production-wired path.

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

## Corrected production-integration proof

The first corrected exact-head candidate was:

`e508822ddeaf56594b6a48db9599a9bfae862087`

SA-15 Live Validation run #76 (`31622886737`) checked out that exact PR head SHA rather than GitHub's synthetic merge ref and executed the real production `CommonCrawlIndexAdapter` against the public Common Crawl index. It passed with:

- **43** real observations;
- **43** quarantined archive projections;
- **0** automatic claims;
- **23** canonical normalized discovery candidates;
- **23 / 23** governed automatic `PUBLIC_WEB` routes;
- **0** source-review routes on the controlled first-party target;
- normalization/routing produced inside the production adapter and persisted in the `normalized_discovery` checkpoint;
- no WARC body retrieval.

Normal repository CI run #1974 (`31622886771`) also passed for that candidate:

- dependency consistency: pass;
- Python dependency audit: pass, no known vulnerabilities;
- Ruff: pass;
- strict Mypy: pass on **695** source files;
- architecture/release contracts: **36 passed**;
- reversible Alembic migrations: pass;
- complete backend suite: **1485 passed**;
- branch-aware coverage: **90.07%**;
- frontend audit/typecheck/build: pass.

## Final exact-head proof and merge

The final PR #133 documentation head was:

`99cd19d03ae7c1a245822067f786805c787fee5a`

That exact head independently repeated the required gates:

- SA-15 Live Validation run #77 (`31623449815`) explicitly checked out `99cd19d03ae7c1a245822067f786805c787fee5a` and again passed the real production path with **43** observations, **23** normalized candidates and **23 / 23** automatic governed routes;
- normal repository CI run #1975 (`31623449867`) completed successfully for frontend and backend, including Ruff, strict Mypy, architecture/release contracts, reversible migrations, tests and coverage;
- PR #133 had zero unresolved review threads before merge.

PR #133 was then squash-merged to `main` as:

`c6e46b47e0714d7859ad36daec9ab4c21865bd03`

The validated final PR head and the squash commit both point to the exact same Git tree:

`bad38f578f20bc0d8343aa877c13a9dc0b6ede68`

Therefore the content merged to `main` is exactly the content that passed the final exact-head CI and real Common Crawl live validation. The differing commit SHA is only the expected squash-history rewrite, not a content change.

## Completion result

C1 is complete. A skipped workflow, mock, earlier validation-only composition or synthetic merge-ref checkout does not count as its proof; the proof above is the real production adapter on the exact validated content tree.
