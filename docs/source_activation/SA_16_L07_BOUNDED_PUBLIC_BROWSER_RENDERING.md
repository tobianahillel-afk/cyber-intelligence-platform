# SA-16 L07 — Bounded public browser rendering

## Status

`FINAL_EXACT_HEAD_REVALIDATION_PENDING`.

L07 extends the merged SA16-L01/L02/L03/L04/L05/L06 governed public-web path with bounded JavaScript-capable rendering for explicitly approved public browser targets. The browser path reuses the existing public-web collection, canonical projection, provenance and checkpoint model instead of creating a parallel evidence pipeline.

The pre-documentation implementation candidate `780eb03bbb0fdd5743f31b56e99a6b7e7ef192cd` passed complete repository CI and the dedicated real-network SA-16 L07 workflow against the public Selenium JavaScript test surface. The dedicated live workflow checked out that exact pull-request head and exercised the production `PublicWebBrowserAdapter` path with sandboxed Chromium.

Because this closeout document changes the pull-request content tree, those runs are candidate evidence only. The documentation head produced by this commit must independently repeat complete CI and the dedicated live workflow before merge.

L07 does not add authenticated browsing, user-delegated accounts, OAuth/SSO flows, MFA/CAPTCHA automation or bypass, anti-bot bypass, cross-origin arbitrary browsing, downloads, arbitrary browser scripting as a service, or automatic static-to-browser fallback.

## Capability

```text
explicit enabled public-web target with SourceType.BROWSER
-> existing source-governance entry / authorization
-> existing public-web robots and crawl scope
-> PublicWebBrowserAdapter
   -> existing collect_public_web_target orchestration
   -> BrowserPublicWebClient
      -> canonicalize requested URL
      -> robots check
      -> existing source-policy authorization callback
      -> bounded Playwright Chromium render
         -> sandboxed headless Chromium
         -> disposable browser context
         -> JavaScript enabled for rendered public HTML
         -> downloads disabled
         -> CSP preserved
         -> TLS errors not ignored
         -> service workers blocked
         -> request interception and request budget
         -> same-origin + crawl-scope + source-policy check for requests
         -> blocked font/image/media requests
         -> bounded navigation/settle time
         -> redirect limit
         -> HTML-only final response
         -> rendered DOM response-size validation
-> existing public-web HTML parsing / semantic extraction
-> existing PublicResource / PublicResourceVersion / PublicClaim projection
-> existing observation provenance with adapter_id=public-web-browser
-> existing durable public-web checkpoint
```

Browser rendering therefore changes the acquisition representation, not the canonical evidence model.

## Runtime and dependency boundary

Playwright is intentionally not added to the normal application dependency manifest. Existing SA09 manifest contracts continue to forbid browser automation dependencies in the application/backend and frontend manifests.

L07 keeps the standard backend import path independent from Playwright by loading `PublicWebBrowserAdapter` only when an enabled public-web target is explicitly typed as `SourceType.BROWSER`. Normal static HTTP composition therefore remains importable after `pip install .` / `pip install -e '.[dev]'` without browser bindings installed.

The CI candidate explicitly proves this ordering:

1. install the normal project and dev dependencies;
2. import `cip.modules.collection_orchestration.application.adapter_composition` before Playwright is installed;
3. install the isolated browser bindings used for browser static analysis/unit tests;
4. run the normal dependency, type, architecture, migration and test gates.

The dedicated browser live workflow separately installs pinned `playwright==1.61.0` and the Chromium runtime. This keeps browser execution an explicit runtime requirement of the browser worker path instead of silently turning Playwright into a normal application dependency.

## Browser safety invariants

`browser_runtime.py` applies explicit fail-closed controls around every render:

- Chromium launches headless with `chromium_sandbox=True`;
- each render uses a disposable browser context closed in `finally` paths;
- downloads are disabled (`accept_downloads=False`);
- Content Security Policy is not bypassed;
- HTTPS certificate errors are not ignored;
- service workers are blocked;
- only canonical HTTP(S) URLs accepted by the existing URL identity model can proceed;
- browser requests must remain on the configured target origin;
- every allowed request passes the existing crawl-scope evaluation and source-policy authorization callback;
- font, image and media requests are aborted before broadening network acquisition;
- request count is bounded;
- navigation time is bounded;
- post-load settling time is bounded;
- main-frame redirects are bounded by the target contract;
- a missing navigation response is a render failure;
- HTTP error responses are render failures;
- the final representation must be `text/html`;
- rendered DOM bytes are evaluated through the existing resource/total-byte crawl budget;
- a source-policy, scope, request-budget or redirect violation fails closed rather than being converted into a successful representation.

The default browser-specific limits are:

- maximum intercepted requests: 64;
- navigation timeout: 15,000 ms;
- post-load settle timeout: 250 ms.

The limit dataclass rejects unreasonable configured values rather than silently accepting unbounded execution.

These browser limits are additional to the existing public-web target limits for pages, resource bytes, total bytes, redirects and crawl depth.

## Network and scope behavior

L07 is not an arbitrary browser or spider.

Before initial navigation, the requested URL is canonicalized, checked against the target origin/crawl scope and passed through the existing source-governance authorization callback. Intercepted browser requests repeat the governed URL checks before they are allowed to continue.

Cross-origin requests are denied. A denied main-frame navigation records the denial and causes the render to fail. Non-essential font/image/media resources are blocked by default. L07 therefore does not use JavaScript rendering as a way to expand an approved target into unrelated hosts.

The existing public-web robots decision remains authoritative before browser rendering is invoked by `BrowserPublicWebClient`.

## Canonical mapping and provenance

L07 does not add a browser-specific data store or shortcut the normative acquisition pipeline.

The browser client returns the same `PublicWebFetchResult` contract consumed by the existing public-web collector. The rendered representation then follows the existing parsing, canonical resource/version/claim projection and durable checkpoint path.

- the requested and final URLs remain canonical public-web URLs;
- the final MIME is `text/html`;
- rendered body size is recorded through the existing representation model;
- normal extracted text/hash/excerpt behavior is reused;
- observation provenance identifies `adapter_id="public-web-browser"`;
- the existing retention/provenance/checkpoint model remains authoritative;
- no browser rendering result directly creates a signal, need hypothesis or opportunity.

`SourceType.STATIC_HTTP` targets continue to use `PublicWebAdapter`. `SourceType.BROWSER` targets use `PublicWebBrowserAdapter`. L07 does not silently convert every existing static target into browser acquisition.

## Deterministic validation

The L07 deterministic tests prove, among other cases:

1. browser limit validation rejects invalid request/navigation/settle bounds;
2. sandboxed Chromium launch and disposable context options are wired as expected;
3. normal JavaScript-rendered HTML produces a bounded `PublicWebFetchResult`;
4. source policy is consulted through the existing authorization callback;
5. robots denial prevents browser page collection;
6. browser policy failures map to normal public-web policy errors;
7. browser render failures map to normal public-web response errors;
8. missing navigation responses fail closed;
9. HTTP error status and non-HTML response types fail closed;
10. rendered DOM over the crawl resource budget fails closed;
11. request-count overflow fails closed;
12. font/image/media resources are blocked;
13. invalid URLs and cross-origin requests are blocked;
14. disallowed target paths fail closed;
15. denied main-frame navigation records a browser policy denial;
16. redirect limits remain enforced;
17. the browser adapter reuses canonical collector output/checkpoint behavior;
18. browser adapter retry/error families remain consistent with collection orchestration;
19. central runtime registration selects static and browser adapters according to `SourceType`;
20. normal runtime composition remains importable without browser bindings installed.

The repository quality gates additionally enforce architecture, file/function size, type, dependency, migration, frontend and branch-aware coverage requirements.

## Validation history

### Implementation hardening

L07 was deliberately developed as a bounded public rendering primitive rather than a generic remote browser service.

The implementation hardened several cases instead of weakening existing controls:

- an early live candidate on the hosted Ubuntu 24.04 runner could not launch Chromium with its sandbox because the runner environment reported restricted user-namespace support;
- L07 explicitly rejected solving that failure with `--no-sandbox` or `chromium_sandbox=False`;
- the controlled live workflow was instead moved to the supported Ubuntu 22.04 hosted image while retaining Chromium sandboxing;
- Playwright was not added to the normal application dependency manifest;
- an initial central registration imported the browser adapter eagerly and would have made ordinary composition depend on Playwright; it was corrected to lazy-load the browser adapter only for `SourceType.BROWSER`;
- CI was strengthened to prove standard runtime composition imports before browser bindings are installed;
- browser-client tests were corrected to use the real `RobotFileParser`-backed `RobotsRules` contract rather than invented helper constructors;
- browser-runtime and browser-client safety branches were strengthened until critical coverage exceeded the project >=95% target without lowering any threshold.

### Validated pre-documentation candidate — `780eb03bbb0fdd5743f31b56e99a6b7e7ef192cd`

Normal CI #2082 (`31723441411`) passed for the pull request containing this candidate against unchanged base `087b2787ccf4bafcaa50374b9644832a0c0a9488`.

The normal pull-request CI executes GitHub's synthetic merge ref for the candidate and base, so it is integration evidence for that candidate/base pair rather than an exact-head checkout claim. The dedicated L07 live workflow below provides exact-head execution evidence.

Backend evidence from CI #2082 includes:

- normal project installation without Playwright: PASS;
- standard runtime composition import before browser bindings are installed: PASS;
- isolated browser bindings installation: PASS;
- dependency consistency: PASS;
- Python dependency audit: no known vulnerabilities;
- Ruff: PASS;
- strict Mypy: PASS on 708 source files;
- architecture/release contracts: 36 passed;
- reversible PostgreSQL migration cycle: PASS through migration `20260810_0024`;
- backend suite: 1,568 passed, 2 warnings;
- branch-aware repository coverage: 90.11%;
- `browser_client.py`: 100.00% coverage;
- `browser_runtime.py`: 96.91% coverage;
- `public_web_browser_adapter.py`: 100.00% coverage;
- `public_web_registration.py`: 100.00% coverage;
- frontend dependency audit: PASS;
- frontend TypeScript typecheck: PASS;
- frontend Next.js production build: PASS.

SA-16 L07 Live Validation #16 (`31723441406`) passed on the exact candidate pull-request head. The workflow explicitly checked out `780eb03bbb0fdd5743f31b56e99a6b7e7ef192cd`, installed pinned Playwright/Chromium and executed `scripts/sa16_l07_browser_check.py`.

The controlled live surface was:

- URL: `https://www.selenium.dev/selenium/web/javascriptPage.html`;
- provider/context: public Selenium JavaScript browser test surface;
- runner: Ubuntu 22.04;
- Playwright: 1.61.0;
- Chromium sandbox: enabled by production runtime configuration;
- final MIME: `text/html`;
- rendered bytes: 11,215;
- observation adapter provenance: `public-web-browser`;
- canonical public-web projection: proven;
- non-empty extracted text/hash/excerpt: proven;
- durable public-web checkpoint for the rendered URL: proven.

The observed excerpt began with:

`Testing Javascript Type Stuff Menu 1 Item 1 Item 2 Key Up: Key Down: Key Press: Change: Foo Bar Foo Bar Change the page `

These CI and live runs are pre-documentation candidate evidence. They do not substitute for exact validation of the documentation head created by this closeout commit.

## Controlled real-network validation contract

`scripts/sa16_l07_browser_check.py` exercises a real public JavaScript page through the production `PublicWebBrowserAdapter` path.

The dedicated workflow succeeds only if the controlled run proves:

- exactly one browser-backed observation and one canonical public-footprint projection for the target;
- observation provenance remains `public-web-browser`;
- canonical resource classification remains `WEB_PAGE`;
- final representation MIME is `text/html`;
- rendered bytes are non-zero and remain within the configured 1 MB live target budget;
- extracted text hash and bounded excerpt are non-empty;
- the rendered target URL is present in the durable checkpoint payload.

The workflow explicitly checks out `${{ github.event.pull_request.head.sha }}`, not the synthetic pull-request merge ref. Unit fixtures, mocks, a previous SHA or a green normal CI run alone do not satisfy the L07 live gate.

## Out of scope for L07

L07 intentionally does not implement:

- automatic fallback from static HTTP to browser rendering;
- automatic browser activation for all company websites;
- authenticated websites or session persistence;
- user-delegated account storage or account selection;
- login-form automation;
- OAuth or SSO flows;
- MFA automation;
- CAPTCHA solving or bypass;
- anti-bot/challenge bypass;
- proxy/Tor rotation or evasion;
- cross-origin arbitrary acquisition;
- browser-driven file downloads;
- browser form submission or other state-changing interactions;
- arbitrary analyst-supplied JavaScript execution;
- a general-purpose remote browser service;
- screenshots, OCR or visual/reverse-image research.

Those capabilities, where legitimate and still required by the roadmap, remain separate future microlots with their own governance, isolation and validation gates.

## Exit gate

L07 is complete only when the final documentation pull-request head has all of the following for the final content/base pair:

1. frontend audit/typecheck/build green;
2. normal application composition imports successfully before browser bindings are installed;
3. dependency consistency and Python audit green after the isolated browser bindings are installed for browser checks;
4. Ruff green;
5. strict Mypy green;
6. architecture/release contracts green;
7. reversible migrations green;
8. complete backend tests and branch-aware repository coverage >= 90% green;
9. critical browser client/runtime coverage >= 95% green;
10. the SA-16 L07 controlled real-network browser workflow green on the exact pull-request head;
11. zero unresolved actionable review threads;
12. PR mergeability confirmed;
13. squash-merged Git tree proven identical to the validated final head tree.

Until those conditions hold, this document intentionally keeps L07 at `FINAL_EXACT_HEAD_REVALIDATION_PENDING` rather than claiming completion.
