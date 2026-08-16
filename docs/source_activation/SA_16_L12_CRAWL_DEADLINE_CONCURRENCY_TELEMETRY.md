# SA-16 L12 — Crawl deadline, bounded concurrency and telemetry

## Status

`FINAL_EXACT_HEAD_REVALIDATION_PENDING`

SA16-L12 closes the crawl operational-safety gap identified by the SA-16 completion audit and execution roadmap. It adds a whole-crawl wall-clock deadline, deterministic bounded concurrency, synchronized global page/byte accounting, partial-progress persistence, and bounded crawl telemetry through the existing source-health path without widening source authorization or weakening the L01-L11 acquisition safeguards.

Pre-documentation candidate:

`c2a960131058d148f70aeb91e3c73a12f565d782`

Candidate Git tree:

`4ca1b4091ae3218f62791c951a14b1bc61dc5579`

Candidate base `main`:

`8fa55bcce9168d371fa1ac1bc43b1d820c70c46d`

Candidate evidence:

- CI #2243 / run `31947348465`: **PASS** against the pull-request integration ref built from the unchanged L11 `main` base and candidate head;
- SA-16 L12 Live Validation #6 / run `31947348385`: **PASS** on the exact candidate pull-request head;
- tests: **1,692 passed, 0 failed, 0 errors**;
- repository combined line/branch coverage: **90.10%**, above the enforced 90% gate;
- `worker.py`: **96.04%**;
- `worker_persistence.py`: **95.35%**;
- `source_portfolio/application/health.py`: **96.51%**;
- `public_web/collector_state.py`: **92.47%**;
- `public_web/crawl_runtime.py`: **87.06%**;
- `public_web/browser_fallback.py`: **95.31%**;
- `public_web/browser_runtime.py`: **97.11%**;
- `public_web_browser_adapter.py`: **100.00%**;
- `public_web_fallback_adapter.py`: **100.00%**;
- `shared/config/public_web_crawl_settings.py`: **100.00%**;
- Ruff: **PASS**;
- strict Mypy: **PASS, 738 source files**;
- architecture/release contracts: **PASS, 36/36**;
- reversible migrations `upgrade head -> downgrade base -> upgrade head`: **PASS** including `20260816_0027`;
- normal runtime import before Playwright installation: **PASS**;
- dependency consistency and `pip-audit`: **PASS, no known vulnerabilities**;
- frontend audit, typecheck and production build: **PASS**;
- PR review audit before documentation: **0 reviews, 0 review threads**.

The repository-wide `public_web/collector.py` coverage figure includes substantial pre-L12 historical behavior and is therefore not used as a claim that every collector branch is a new L12 critical path. L12 closure instead relies on the enforced repository coverage gate, focused deterministic L12 tests, high coverage of the worker/persistence/health/runtime support modules above, and the dedicated production-path live proof. No coverage or architecture guard was weakened.

The closeout itself changes the pull-request tree. The evidence above is therefore candidate evidence only. Complete CI and the dedicated L12 live workflow must repeat after this documentation commit before the PR may be marked Ready or merged.

## Capability

L12 adds operational lifecycle controls around the already-governed public-web acquisition paths.

The new runtime contract provides:

- a monotonic whole-crawl wall-clock deadline;
- a configurable bounded crawl concurrency;
- deterministic candidate admission;
- synchronized shared page and byte reservations;
- streaming HTTP reads with bounded body materialization;
- cumulative redirect byte accounting;
- deadline-aware static and browser-fallback execution;
- partial-result checkpoint persistence on a classified deadline failure;
- bounded adapter-owned operational telemetry exposed through source health;
- retry/replay behavior that does not emit a success value event for partial failures.

L12 does not create new source authority, browser actions, authentication state, downloads, screenshots or arbitrary JavaScript execution.

## Configuration

The public-web target/runtime now has explicit bounded settings for:

- `crawl_deadline_seconds`;
- `max_crawl_concurrency`.

The configuration is propagated through both manual target loading and automatic public-web provisioning from `Organization.website_url`, so manually configured and automatically provisioned organization websites receive the same operational-safety contract.

Historical configurations remain compatible through conservative defaults:

- whole-crawl deadline: `300` seconds;
- maximum crawl concurrency: `1`.

Validation is fail-closed for out-of-range values. Existing depth, page, byte, freshness, source-policy, path/origin and robots controls remain authoritative.

## Whole-crawl deadline semantics

`CrawlDeadline` is created once for the crawl and is shared across the acquisition lifecycle rather than being recreated for each request.

The deadline begins before discovery work such as `robots.txt` retrieval and bounds later static/fallback work through the same monotonic clock.

Per-request timeout behavior is preserved: an HTTP call receives the smaller of the normal request timeout and the time remaining in the crawl. The crawl deadline therefore does not enlarge an existing request timeout.

The HTTP path also checks the deadline while streaming response chunks and after transfer so a slow response cannot evade the wall-clock contract merely by staying below an individual read timeout.

When the crawl deadline expires:

1. new candidate admission stops;
2. completed work may still be applied in deterministic admission order;
3. work that did not complete is not represented as completed in the checkpoint;
4. the batch carries deadline telemetry;
5. safely persistable partial observations/checkpoint state are committed;
6. the collection job is classified as a retryable `crawl_deadline_exceeded` failure rather than a false success.

## Deterministic concurrency and global budgets

Static crawling can execute bounded concurrent waves while preserving deterministic replay semantics.

The contract is:

- frontier/candidate admission is deterministic;
- page and byte allowances are reserved centrally before work is submitted;
- reservations are synchronized rather than copied independently into workers;
- the same final page or byte allowance cannot be consumed twice by concurrent workers;
- completion order may vary;
- results are applied in admission order;
- discovery/checkpoint updates therefore remain deterministic;
- only work that actually completed can advance the checkpoint.

The central budget coordinator has race tests for the final page allowance and final byte allowance.

HTTP byte accounting includes redirect responses rather than counting only the final body. `Content-Length`, where trustworthy, is an early fail-closed size gate; streamed bytes remain the authoritative runtime bound.

## Browser fallback concurrency

L12 deliberately does not parallelize the synchronous Playwright fallback client.

The fallback contains collection-scoped mutable accounting and uses the synchronous Playwright runtime. Until a later architecture explicitly provides safe browser-session coordination, the browser fallback reports an effective concurrency of `1` even if the target's configured static concurrency is higher.

This is a safety choice, not an implementation omission disguised in telemetry. Metrics distinguish configured concurrency, effective concurrency and the maximum concurrency actually used.

Fallback byte accounting includes both the static response cost and the rendered representation cost, preventing browser fallback from appearing artificially cheaper than the static path.

## Streaming and bounded cleanup

Static HTTP responses are consumed through bounded streaming rather than unconditional full-body buffering.

The client enforces:

- authorization before request execution;
- existing request timeout;
- whole-crawl remaining time;
- `Content-Length` admission when present and valid;
- per-response/body budgets;
- streamed chunk deadline checks;
- cumulative network bytes including redirects.

Concurrent wave shutdown stops new admissions promptly after deadline/budget state changes. Finished results can be safely applied; unfinished work is not promoted into a checkpoint as completed.

The controlled deadline live case proves that the worker returns with a partial checkpoint containing only the completed page while the slow request is classified through the deadline path.

## Typed telemetry contract

L12 introduces `AdapterOperationalMetrics`, a bounded generic adapter-owned metrics envelope rather than a public-web-only metrics subsystem.

The contract limits:

- namespace length;
- metric count;
- metric-key length;
- metric value types to numeric/boolean operational values;
- non-finite floats.

Public-web crawl telemetry uses a versioned namespace and records the operational signals required by the L12 roadmap, including applicable values for:

- attempted pages;
- fetched pages;
- HTTP-not-modified pages;
- tombstoned/gone pages;
- failed pages;
- bytes received/accepted;
- links discovered;
- links admitted;
- links denied by scope/policy;
- browser fallback count;
- robots/source-policy denials;
- redirects;
- elapsed time;
- deadline-exceeded/cancelled state;
- configured concurrency;
- effective concurrency;
- maximum concurrency actually observed.

Metrics are operational health information. They are not evidence claims, cyber-need hypotheses, commercial signals or opportunities.

## Source-health persistence

Migration `20260816_0027` adds bounded operational metrics to the existing source-health persistence model.

L12 reuses the existing collection-orchestration and source-portfolio lifecycle instead of creating a crawler-specific metrics database.

On normal success, the latest bounded metrics snapshot is persisted with source health.

On a partial deadline failure:

- completed observations can be persisted;
- a consistent checkpoint can be persisted;
- `last_success_at` is not advanced;
- source health records the classified failure and metrics snapshot;
- no successful `SourceValueEvent` is emitted for that partial attempt.

A later successful retry can advance the checkpoint/success state without double-counting the already-persisted observation. The integration test explicitly proves one partial observation before retry and still one raw observation after successful resume, while the successful value event appears only on the successful execution.

## Authorization and security posture

L12 changes operational scheduling/accounting, not authorization.

Every request continues to be governed by the existing controls for:

- canonical URL validation;
- same-origin and allowed-path scope;
- source-policy authorization;
- robots policy;
- redirect checks;
- request/page/byte budgets;
- browser sandboxing and request interception where browser fallback is enabled.

Concurrency does not grant each worker its own independent authority or budget. A concurrently admitted request remains subject to the same per-request scope and policy gates.

No safeguard from L01-L11 was removed or relaxed to enable parallelism or meet the live proof.

## Deterministic tests

L12 test coverage includes focused cases for:

- whole-crawl deadline configuration and validation;
- environment/runtime propagation;
- automatic public-web policy propagation;
- page-budget reservation race;
- byte-budget reservation race;
- deterministic admission/application ordering;
- configured versus effective concurrency;
- maximum concurrent work observed;
- deadline before/around response processing;
- deadline during streamed body transfer;
- streamed body-size rejection;
- redirect byte accounting;
- static concurrency bounds;
- serialized browser fallback behavior;
- fallback combined static/rendered byte accounting;
- partial checkpoint behavior;
- retryable deadline classification;
- persistence of partial observations and source-health metrics;
- absence of successful value-event double counting on a partial retry;
- migration upgrade/downgrade/re-upgrade.

The implementation was refactored to satisfy the existing source-file/function/parameter/nesting architecture limits rather than changing those limits.

## Live validation

The dedicated L12 workflow executes the production worker/runtime path against a controlled first-party multi-page fixture.

The healthy concurrency case provisions a public-web target with:

- four independent fast pages;
- `max_pages=4`;
- `max_crawl_concurrency=4`;
- a non-flaky ten-second crawl deadline.

It proves:

- all four pages are fetched;
- effective concurrency is persisted as four;
- maximum concurrency used is persisted as four;
- the fixture observes real overlapping requests (`>=2`);
- the healthy crawl does not report a deadline;
- metrics are persisted through the production worker/source-health path.

A separate deadline case uses one fast page followed by a deliberately slow page with:

- `max_pages=2`;
- effective concurrency `1`;
- a one-second whole-crawl deadline.

It proves:

- the fast page is retained as completed partial progress;
- the slow/incomplete page is absent from the checkpoint;
- `deadline_exceeded=true` is preserved in the partial metrics;
- exactly one page is counted as fetched;
- the worker error is `crawl_deadline_exceeded` and retryable.

The candidate live workflow result is **PASS** on `c2a960131058d148f70aeb91e3c73a12f565d782`.

## Explicit exclusions

L12 does not add:

- arbitrary JavaScript evaluation;
- generic browser commands;
- clicks, typed form filling or public form submission (L13);
- screenshots or controlled downloads (L14);
- delegated identities/session governance (L15);
- provider-specific login/session reuse (L16);
- OAuth/SSO/MFA/CAPTCHA checkpoint handling (L17);
- a separate crawler metrics datastore;
- direct claim/opportunity/outreach generation from crawl telemetry.

## Continuation reference

The canonical remaining implementation plan is:

- `docs/source_activation/SA_16_EXECUTION_ROADMAP_L10_L18.md`.

The status/gap matrix remains:

- `docs/source_activation/SA_16_COMPLETION_AUDIT_AND_REMAINING_LOTS.md`.

After L12 is exact-head validated and merged, the next mandatory implementation lot is **SA16-L13 — Governed browser action plans and public forms**.

A future implementation session must re-read the normative SA-16 documents, the execution roadmap, this L12 closeout and the current merged `main` before starting L13.

L13 must build on L12's deadline/budget/telemetry controls. It must not introduce arbitrary JavaScript, authentication, screenshots/downloads or bypass source authorization.

## Completion rule

L12 may be closed only when the documentation head itself repeats:

- complete CI;
- dedicated exact-head L12 live validation;
- the repository quality/coverage gates;
- health persistence and partial-retry proof;
- dependency/security checks;
- reversible migration validation;
- review/thread audit;
- Ready transition only after those gates pass;
- locked squash merge against the validated head SHA;
- post-squash Git-tree equality;
- final `main` pointer verification.

Until those gates repeat on the documentation head, this document deliberately remains `FINAL_EXACT_HEAD_REVALIDATION_PENDING`.
