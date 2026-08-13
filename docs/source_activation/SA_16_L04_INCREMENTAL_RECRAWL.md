# SA-16 L04 — Conditional incremental public-web recrawl

## Status

`FINAL_EXACT_HEAD_REVALIDATION_PENDING`.

L04 extends the merged SA16-L01/L02/L03 public-web path with durable HTTP conditional recrawl. The pre-documentation implementation candidate `e235bcfca4022da7efd17d8b3cde374156ece315` passed complete repository CI and the dedicated real-network SA-16 L04 live workflow. Because this closeout document changes the PR content tree, those runs are candidate evidence only: the documentation head produced by this commit must independently repeat both gates before merge.

L04 does not add browser rendering, authenticated navigation, JavaScript execution, CAPTCHA/MFA automation or a second source-health subsystem.

## Capability

```text
previous durable checkpoint
-> exact URL representation metadata
   -> ETag
   -> Last-Modified
   -> content hash / version id
   -> discovery method / locator / depth
-> If-None-Match / If-Modified-Since on that exact URL
-> normal Source Governance / robots / crawl scope / budgets
-> HTTP response
   -> 200 changed: normal observation/version path
   -> 304 unchanged: NOT_MODIFIED, no new RawObservation/content version
   -> existing error/tombstone handling for other responses
-> refreshed durable checkpoint
```

The existing collection checkpoint remains the durable persistence boundary for validators and discovery-resume metadata. L04 deliberately does not introduce a database migration solely for ETag/Last-Modified state.

## Implemented behavior

- `ETag` and `Last-Modified` are persisted per exact canonical fetched URL together with existing representation/version metadata.
- Conditional headers are sent only when a prior representation exists for the same URL; validators are not transferred to another resource.
- A real HTTP `304 Not Modified` maps the resource to `ResourceRetrievalState.NOT_MODIFIED`.
- A 304 does not create a new `RawObservation`, content hash or replacement content version; the existing version identity is reused.
- Legacy checkpoint payloads without validators, frontier metadata or feed URLs remain readable.
- The worker's existing SourceHealth/Freshness behavior is reused rather than creating a competing health state.

## Recursive-frontier preservation

A conditional parent response creates a subtle recursive-crawl problem: a `304` has no HTML body, so its child links cannot be rediscovered from the parent during that run.

L04 therefore persists the minimum known page frontier required for deterministic bounded recrawl: URL, depth, discovery method and source locator. Known descendants can be revisited even when the parent is unchanged. Every resumed URL still re-enters the existing `PublicWebClient` path and is subject to source authorization, robots, same-origin/path scope and crawl budgets.

This is resume metadata, not permission expansion: checkpoint contents cannot authorize a URL that the current target/governance rules reject.

## Dynamic-feed preservation

The same issue applies to an RSS/Atom feed declared by HTML. If the declaring page returns `304`, its `<link rel="alternate">` declaration cannot be reparsed, while the feed itself may have new entries.

L04 persists dynamically discovered feed URLs separately and revisits them under the existing structured-discovery governance. A 304 declaring page therefore does not freeze its feed or prevent new feed entries from entering the normal governed candidate path.

## Safety invariants

- Source Governance remains authoritative before acquisition; conditional requests do not bypass authorization.
- robots, origin/path scope, redirect limits and page/byte/resource budgets remain authoritative.
- validators are bound to the exact previously fetched URL.
- checkpoint frontier/feed state does not become an authorization source.
- `304` means only that the HTTP representation is unchanged relative to the supplied validator; it is not evidence of new content, a commercial signal or independent corroboration.
- raw-content storage policy is unchanged.
- no browser, authenticated-session, CAPTCHA/MFA or anti-bot bypass path is introduced.

## Architecture corrections during validation

The first L04 composition made `mapper.py` exceed the repository module-size contract and left a representation helper with too many parameters. The implementation was refactored rather than weakening the architecture gate:

- representation/version construction was extracted into `page_representation.py`;
- the representation inputs are grouped through a typed context instead of an oversized parameter list;
- `PreviousPageState` remains an explicit compatible public re-export for existing consumers after the extraction.

The corrected candidate passes the repository architecture/release suite.

## Deterministic validation

The L04 tests exercise the production adapter with deterministic HTTP transports and prove, among other cases:

1. a first parent/child crawl stores distinct ETags and the child's discovery depth/method;
2. a second crawl can receive `304` for the parent and still recrawl the known child with its own validator;
3. no new observations are created when the known representations are unchanged;
4. a dynamically discovered feed is persisted and fetched again even when its declaring HTML later returns `304`;
5. a newly appearing feed item is still discovered on that second run;
6. runnable automated test sources satisfy the same documented-terms governance contract as production sources.

## Validation history

### Rejected intermediate head — `a7e599edc51ec0cf4e0d7d9e47a30159ec84a44a`

The dedicated real-network 304 workflow passed, and Ruff/Mypy/architecture/migrations/frontend also passed, but full CI correctly rejected the candidate:

- two incremental-recrawl tests failed before exercising the L04 behavior because their runnable `SourcePolicy` fixture lacked terms/licence evidence;
- 1503 tests passed and 2 failed;
- branch-aware total coverage was 89.91%, below the required 90.00%.

The governance rule was not weakened. The fixture was corrected to include documented terms.

### External live-surface failure — `b81515fd444d29af97d676ec26a3cd20225507b5`

After correcting the test fixture, the first new live attempt failed before the ETag resource was fetched because `https://httpbin.org/robots.txt` returned HTTP 503. No production L04 behavior had changed. That failed run is not counted as live proof.

The controlled live surface was moved to HTTPBingo, which provides both `/robots.txt` and an ETag conditional endpoint. The production acquisition path and assertions were left unchanged.

### Validated pre-documentation candidate — `e235bcfca4022da7efd17d8b3cde374156ece315`

Normal CI #2030 (`31680302970`) passed completely:

- dependency consistency: PASS;
- Python dependency audit: no known vulnerabilities;
- Ruff: PASS;
- strict Mypy: PASS on 702 source files;
- architecture/release contracts: 36 passed;
- reversible migrations: PASS;
- backend suite: 1505 passed;
- branch-aware coverage: 90.01%;
- frontend dependency audit/typecheck/build: PASS.

SA-16 L04 Live Validation #5 (`31680302980`) also passed on that exact head using the production `PublicWebClient` and collector against the real HTTPBingo conditional endpoint.

These runs prove the implementation candidate but do not substitute for validation of this documentation head.

## Controlled real-network validation contract

`scripts/live_validate_sa16_l04.py` provisions a governed automatic public-web target for `https://httpbingo.org/` and uses `https://httpbingo.org/etag/sa16-l04` as its sole page seed.

The first production-path collection must obtain a real ETag and persist exactly one observation/projection. The second collection supplies the durable checkpoint and must receive the conditional not-modified behavior. The workflow fails unless all of the following hold:

- the second collection is `not_modified`;
- it creates zero new observations;
- its projection remains present and maps to `ResourceRetrievalState.NOT_MODIFIED`;
- the checkpoint retains the same content-version id;
- the representation hash is unchanged;
- the workflow checked out the exact pull-request head.

A mock, skipped workflow, prior SHA, or successful deterministic unit test does not satisfy this live gate.

## Exit gate

L04 is complete only when the final documentation PR head has all of the following on that exact content:

1. frontend audit/typecheck/build green;
2. dependency consistency and Python audit green;
3. Ruff green;
4. strict Mypy green;
5. architecture/release contracts green;
6. reversible migrations green;
7. complete backend tests and branch-aware coverage >= 90% green;
8. the SA-16 L04 real-network conditional-recrawl workflow green;
9. zero unresolved review threads;
10. PR mergeability confirmed;
11. squash-merged Git tree proven identical to the validated final head tree.

Until those conditions hold, this document intentionally keeps L04 at `FINAL_EXACT_HEAD_REVALIDATION_PENDING` rather than claiming completion.
