# SA-16 L09 — Governed static-to-browser fallback

## Status

`FINAL_EXACT_HEAD_REVALIDATION_PENDING`.

SA16-L09 adds deterministic static-first browser fallback to the automatic public-company web runtime. It reuses the existing public-web collector, scope, robots, canonical projection and checkpoint path. Browser rendering remains a separately governed capability: approval for `STATIC_HTTP` never implies approval for `BROWSER`.

Pre-documentation candidate:

`0c6226cb737829cf9f2a018707c134ea7fa83bb0`

Candidate Git tree:

`884cf81b6cc7b0b08aca7cbcb25638bc87472028`

Candidate evidence:

- CI #2126 / run `31745939036`: **PASS** backend and frontend;
- SA-16 L09 Live Validation #2 / run `31745939155`: **PASS, 20/20**;
- tests: **1,608 passed, 0 failed, 0 errors, 0 skipped**;
- global line coverage: **93.27%**;
- diagnostic global branch coverage: **75.90%**;
- every new critical L09 module: **100% line / 100% branch**;
- Ruff, strict Mypy, architecture/release 36/36 and reversible migrations: **PASS**;
- standard runtime import before isolated Playwright installation: **PASS**;
- frontend audit, typecheck and production build: **PASS**.

This documentation commit changes the pull-request tree. These candidate runs are therefore not final merge evidence. Complete CI and the dedicated L09 live workflow must repeat on the documentation head itself.

## Capability

The runtime path is:

```text
approved organization website
-> automatic STATIC_HTTP target / authorization
-> PublicWebFallbackAdapter
-> FallbackPublicWebClient
   -> ordinary bounded HTTP fetch first
   -> deterministic fallback decision
   -> separate BROWSER authorization
   -> lazy BrowserPublicWebClient import
   -> sandboxed bounded Chromium render
-> existing public-web collector
-> existing canonical observation / projection
-> existing durable checkpoint
```

When browser fallback is disabled, the automatic runtime continues to construct the ordinary static `PublicWebAdapter` used by SA16-L08.

## Deterministic fallback decision

A page is browser-rendered only when all of the following are true:

- the static response is HTTP 200;
- the response MIME type is `text/html`;
- bounded static HTML extraction yields less than the configured useful-text threshold;
- the HTML contains a script marker;
- the target has not exhausted its configured browser-page allowance.

Defaults are conservative:

- useful static text threshold: `200` characters;
- maximum browser pages per collection client: `3`;
- hard browser-page setting range: `1..25`.

Responses that are sufficiently useful statically, non-HTML, not HTTP 200, or have no script marker stay on the static path.

## Separate browser governance

Automatic browser fallback has a distinct source identity:

`automatic-public-company-web-browser`

Activation requires its own:

- explicit browser enablement;
- authorization reference;
- timezone-aware review timestamp;
- optional expiry after the review timestamp;
- bounded fallback threshold and page cap.

The generated browser registry entry is `SourceType.BROWSER`, limits collection to the approved target host/path prefixes and `corporate-public-footprint` purpose, inherits the permitted public data categories and retention semantics from the static source, and keeps raw storage disabled.

Environment configuration uses the separate prefix:

`CIP_AUTOMATIC_PUBLIC_WEB_BROWSER_*`

Browser fallback is disabled by default.

## Budget and isolation semantics

The fallback client performs the normal HTTP request first. If Chromium is required, the static response bytes are added to the effective `CrawlUsage` passed into the browser path. The browser runtime then applies the target response budget to the rendered DOM using that effective usage.

Static-response overhead from previous fallback decisions is also carried into subsequent page requests in the same client. The fallback path therefore does not obtain a second unmetered resource budget merely because rendering switched to Chromium.

Existing browser safeguards remain unchanged:

- Chromium sandbox remains enabled;
- fresh browser process/context semantics remain bounded and disposable;
- request interception remains active;
- fonts/images/media remain blocked;
- same-origin, crawl scope and source authorization remain checked;
- service workers remain blocked;
- CSP is not bypassed;
- TLS errors are not ignored;
- downloads are not enabled;
- navigation, request, redirect and rendered-DOM budgets remain bounded.

Playwright remains outside the normal application dependency manifest and is lazy-loaded only when the governed fallback is actually selected.

## Error semantics

The fallback adapter preserves the standard collection error contract:

- malformed checkpoint -> `invalid_checkpoint`, non-retryable;
- source/robots/policy denial -> `source_policy_denied`, non-retryable;
- parser/schema failure -> `source_schema_drift`, non-retryable;
- unsafe source response -> `unsafe_source_response`, retryable;
- HTTP errors -> `http_<status>`, retryable only for 429 and 5xx;
- timeout/transport failure -> `source_transport_error`, retryable.

The adapter validates that the static entry matches `target.source_id`, that the separate fallback entry is explicitly `SourceType.BROWSER`, and that its timeout is positive.

## Architecture and non-regression

The L09 implementation was split into bounded responsibilities rather than exceeding repository limits:

- base automatic-public-web config;
- browser-aware config and settings mapping;
- runtime builder;
- tiny backward-compatible runtime facade;
- fallback run context;
- collection helper;
- execution/error mapping helper;
- adapter wrapper.

The architecture gate remains **36/36 PASS**. In particular, helper signatures were reduced below the hard ten-parameter limit using an immutable execution context instead of weakening the architecture rule.

Tests cover:

- trigger and no-trigger cases;
- fallback page cap;
- static-byte accounting before browser rendering;
- separate browser authorization construction and validation;
- browser authorization expiry and aware-time requirements;
- static-only compatibility when browser fallback is disabled;
- runtime selection of the fallback-capable adapter when browser approval exists;
- adapter input guards;
- execution-context delegation;
- error translation branches;
- HTTP 404/429/503 retry semantics;
- automatic-runtime adapter collision non-regression after the runtime split.

All newly introduced critical L09 modules are 100% line and branch covered in candidate CI #2126.

## Live validation

The dedicated workflow checks out the exact pull-request head on Ubuntu 22.04, installs the normal project package first, installs Playwright 1.61.0 separately, verifies dependency consistency, installs Chromium with its required OS dependencies, and runs the controlled L09 script.

The live proof contains 20 targets:

1. `https://example.com/`
2. `https://example.org/`
3. `https://example.net/`
4. `https://www.python.org/`
5. `https://docs.python.org/`
6. `https://pypi.org/`
7. `https://www.djangoproject.com/`
8. `https://www.freebsd.org/`
9. `https://go.dev/`
10. `https://nodejs.org/`
11. `https://kubernetes.io/`
12. `https://www.postgresql.org/`
13. `https://sqlite.org/`
14. `https://www.kernel.org/`
15. `https://www.w3.org/`
16. `https://www.ietf.org/`
17. `https://www.rfc-editor.org/`
18. `https://curl.se/`
19. `https://www.debian.org/`
20. `https://www.selenium.dev/selenium/web/javascriptPage.html`

The first 19 exercise the real automatic runtime with the fallback-capable adapter while preserving ordinary static-first acquisition. The Selenium JavaScript fixture deliberately uses a high static-text threshold to require Chromium. The live script directly asserts that `FallbackPublicWebClient.fallback_urls` contains exactly the Selenium fixture before independently executing the real `PublicWebFallbackAdapter` for canonical collection/checkpoint validation.

Candidate live #2 recorded:

- `rendered_bytes=11215` for the Selenium JavaScript fixture;
- one canonical observation from the full fallback adapter fixture run;
- `targets=20`;
- `forced_browser=1`;
- `runtime_targets=19`.

The fallback-capable adapter uses `public-web-browser-fallback` as the observation adapter provenance for the collection job. Actual Chromium execution in this microlot is proven separately and explicitly by the recorded fallback URL; L09 does not claim a per-page `public-web-browser` observation adapter override.

## Explicit exclusions

L09 does not add:

- authenticated browsing;
- delegated user sessions;
- OAuth/SSO login flows;
- form submission;
- CAPTCHA or MFA automation/bypass;
- anti-bot bypass;
- arbitrary cross-origin browser traversal;
- screenshots as evidence;
- controlled downloads;
- arbitrary browser scripting as a service.

Those capabilities require separate future governance and implementation work.

## Final completion rule

L09 may be squash-merged only when the final documentation head itself has:

1. complete backend and frontend CI green;
2. standard runtime import without browser bindings green;
3. dependency consistency/audits, Ruff, strict Mypy and architecture/release green;
4. reversible migrations green;
5. complete tests/coverage green with critical L09 coverage at target;
6. dedicated live validation **20/20** on that exact head, including the forced Selenium Chromium proof;
7. zero actionable reviews and unresolved review threads;
8. mergeability against current `main`;
9. squash merge locked with `expected_head_sha` to that validated head;
10. merged Git tree exactly identical to the validated final-head tree.

Previous-SHA results, skipped live jobs, mocked network paths, partial target passes or post-validation changes do not satisfy this closeout.
