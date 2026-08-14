# SA-16 L11 — Rendered public JSON and script-state capture

## Status

`FINAL_EXACT_HEAD_REVALIDATION_PENDING`

SA16-L11 closes the rendered structured-state gap identified by the post-L09 SA-16 completion audit. It adds bounded, version-bound capture of same-origin rendered JSON responses and a fixed reviewed set of public browser script-state globals without adding arbitrary JavaScript execution, browser actions, authentication, downloads or new network authority.

Pre-documentation candidate:

`5b2ffb3d0c4f8060314373ab409612b61d8b3289`

Candidate Git tree:

`bfaa7d219bc9f17f010e3a1064f9fde9dd2652db`

Candidate base `main`:

`5e96040eb8c97af4f31a9dff94ef6ab698d77d9a`

Candidate evidence:

- CI #2184 / run `31823127726`: **PASS** backend and frontend against the pull-request integration ref built from the unchanged L10 `main` base and candidate head;
- SA-16 L11 Live Validation #17 / run `31823127806`: **PASS** on the exact candidate pull-request head;
- tests: **1,682 passed, 0 failed, 0 errors**;
- global combined line/branch coverage: **90.36%**;
- `browser_structured_state.py`: **100.00%**;
- `structured_state_capture.py`: **96.26%**;
- `browser_runtime.py`: **97.11%**;
- `structured_fetch_result.py`: **100.00%**;
- `structured_state_mapping.py`: **100.00%**;
- `domain/structured_state.py`: **100.00%**;
- `structured_state_persistence.py`: **100.00%**;
- Ruff: **PASS**;
- strict Mypy: **PASS, 730 source files**;
- architecture/release contracts: **PASS, 36/36**;
- reversible migrations `upgrade head -> downgrade base -> upgrade head`: **PASS** including `20260814_0026`;
- normal runtime import before Playwright installation: **PASS**;
- dependency consistency and `pip-audit`: **PASS, no known vulnerabilities**;
- frontend audit, typecheck and production build: **PASS**.

The closeout itself changes the pull-request tree. The evidence above is therefore candidate evidence only. Complete CI and the dedicated L11 live workflow must repeat after this documentation commit before the PR may be marked Ready or merged.

## Capability

L11 introduces a structured state representation distinct from L10 surface metadata.

Each captured structured state is bound to an exact public-resource version and has one of two kinds:

- `network_json` — a rendered same-origin HTTP JSON response observed during the browser run;
- `script_state` — a reviewed public browser global extracted through the fixed L11 extractor.

Structured state remains acquisition evidence/provenance. It is not promoted directly into a commercial signal, technology claim, opportunity or outreach action.

## Domain and version semantics

`PublicStructuredState` is version-bound rather than page-global. Its identity preserves:

- organization;
- public resource version;
- structured-state kind;
- source locator;
- canonical sanitized JSON payload identity;
- network or extractor provenance.

The version binding preserves historical truth when the rendered resource changes. Older structured state remains attached to the older resource representation rather than being silently moved to a newer page version.

Network JSON and script-state records share the same version lifecycle but retain distinct provenance semantics.

## Persistence

Migration `20260814_0026` adds persistent version-bound public structured-state records.

Persistence preserves:

- organization provenance;
- exact persisted resource-version provenance;
- structured-state kind;
- bounded source locator;
- canonical sanitized JSON;
- payload hash/identity;
- network source URL, status and MIME type when applicable;
- reviewed extractor identity when applicable;
- collection timestamp.

The mapper and projection persistence keep structured state separate from L10 `PublicSurfaceReference` records and from extracted claims.

## Same-origin rendered JSON capture

The browser collector listens for Playwright `requestfinished` events rather than attempting to materialize response bodies when only headers are available.

For a response to be considered for capture it must pass all relevant gates:

1. the request must have completed;
2. a response must exist;
3. Playwright must provide response-size metadata;
4. status must be in the 2xx family;
5. MIME type must be `application/json`, `text/json` or an approved `+json` family;
6. the response URL must independently pass the existing same-origin/path/source-authorization contract;
7. measured response body size must fit the per-response byte budget;
8. measured response body size must fit the aggregate JSON byte budget;
9. response count must remain inside the JSON response budget;
10. `Content-Length`, when valid and present, is an additional fail-closed size gate;
11. after `response.body()` materialization, the actual byte length is checked again before promotion;
12. JSON must decode and pass canonical sanitization before persistence.

If Playwright cannot provide usable completed-request size metadata, L11 does not call `response.body()` and does not promote that response.

`requestfinished` means that Chromium has already downloaded the network response. The size gate therefore bounds Python/Playwright body materialization and promotion; L11 does not claim to provide streaming cancellation of a response body after only a partial network read. Whole-crawl/network wall-clock and concurrency controls remain L12 scope.

## Network authorization and off-origin behavior

L11 creates no new authority.

Every candidate JSON response re-enters the existing governed URL checks before body materialization:

- canonical URL validation;
- same-origin comparison against the configured target;
- crawl-scope/path validation;
- source-policy authorization.

Off-origin browser requests remain blocked by the existing browser route policy and cannot become structured state. A recognized network response cannot widen target scope or authorize later requests.

## Fixed public script-state extractor

L11 does not accept caller-supplied JavaScript.

The reviewed extractor is a source constant with extractor ID:

`public-known-globals-v1`

It recognizes only the current versioned allowlist:

- `__NEXT_DATA__`;
- `__NUXT__`;
- `__APOLLO_STATE__`;
- `__INITIAL_STATE__`;
- `__PRELOADED_STATE__`.

The in-page extractor:

- reads only those fixed globals;
- serializes each value with `JSON.stringify`;
- measures UTF-8 byte size with `TextEncoder`;
- enforces a per-state transfer budget;
- enforces an aggregate script-state transfer budget;
- enforces the maximum state count;
- skips values that cannot be serialized;
- returns serialized JSON strings rather than arbitrary live JavaScript objects.

Python then parses the serialized value again and applies the canonical L11 sanitizer before promotion. This is intentional defense in depth: browser-side logic bounds transfer size and reviewed extraction scope, while Python owns canonical filtering, deterministic serialization and persistence semantics.

## Bounds and sanitization

The production defaults remain explicitly bounded.

Network JSON defaults include:

- maximum JSON response count;
- maximum bytes per response;
- maximum aggregate JSON bytes.

Script-state defaults include:

- maximum reviewed state count;
- maximum bytes per serialized state;
- maximum aggregate serialized state bytes.

Canonical sanitization additionally limits:

- nesting depth;
- scalar count;
- key length;
- string length;
- final promoted canonical JSON size.

Unsupported Python/JSON value shapes are dropped rather than coerced into uncontrolled text.

## Sensitive-key suppression

Structured state is filtered before persistence/promotion.

Sensitive-key matching covers normalized key forms associated with secrets/session material, including token, secret, password/passwd, API-key, authorization, credential, session, cookie, CSRF/XSRF and nonce families.

A sensitive branch is removed recursively. A payload that becomes empty after sanitization is not promoted.

The controlled live fixture intentionally includes secret-like keys in both rendered network JSON and script state and proves they are absent from mapped and persisted structured state.

L11 does not claim that untrusted bytes never enter the bounded Playwright/Python acquisition boundary. Its guarantee is that reviewed transfer limits, reauthorization and sanitization apply before the data becomes canonical structured state or persistent evidence.

## Browser-runtime responsibility split

During implementation, adding L11 capture directly to `browser_runtime.py` would have pushed that file above the repository's hard 400-line architecture limit.

The architecture gate was not weakened.

The structured-state collection responsibility was extracted into:

`src/cip/adapters/sources/public_web/browser_structured_state.py`

Responsibilities are now separated as follows:

- `browser_runtime.py` — navigation, request routing, sandbox/policy enforcement and rendered page lifecycle;
- `browser_structured_state.py` — Playwright request-finished admission, network structured-state capture and fixed reviewed script-state extraction;
- `structured_state_capture.py` — deterministic budgets, canonical parsing/sanitization and capture accounting;
- domain/mapping/persistence modules — version-bound canonical state and storage.

The resulting candidate keeps `browser_runtime.py` under the source-file architecture ceiling and all architecture contracts pass unchanged.

## Existing browser safeguards preserved

L11 retains the L07-L10 browser security posture:

- Chromium sandbox enabled;
- downloads disabled;
- CSP preserved;
- TLS errors not ignored;
- service workers blocked;
- same-origin/path authorization before requests;
- request budget retained;
- blocked image/font/media classes retained;
- no arbitrary caller JavaScript;
- no authentication state introduced.

No guardrail was relaxed to make the live validation pass.

## Tests

Deterministic coverage includes:

- same-origin 2xx JSON capture;
- `application/json`, `text/json` and `+json` MIME families;
- wrong status rejection;
- non-JSON rejection;
- off-origin rejection before body materialization;
- completed-request measured-size admission;
- missing/broken request-size metadata fail-closed behavior;
- per-response body-size rejection before `response.body()`;
- aggregate JSON byte budget;
- JSON response count budget;
- oversized valid `Content-Length` rejection before body materialization;
- invalid/negative `Content-Length` fallback to measured completed-response size;
- body-read error fail-closed behavior;
- malformed JSON and invalid UTF-8 rejection;
- sensitive-only payload rejection;
- key/string/depth/scalar bounds;
- canonical promoted-payload size ceiling;
- listener installation and missing browser API fail-closed behavior;
- fixed reviewed script extractor only;
- Playwright script-extraction error fail-closed behavior;
- per-state script transfer budget;
- aggregate script transfer budget;
- script-state count budget;
- unsupported globals/values;
- nested lists and supported JSON scalar preservation;
- sensitive-key suppression;
- network vs script provenance;
- version-bound mapping and persistence;
- persistence organization/version provenance;
- migration upgrade/downgrade/re-upgrade.

The final pre-documentation candidate raises the L11 critical modules to the required quality range instead of relying on the repository-wide 90% floor:

```text
browser_structured_state.py     100.00%
structured_state_capture.py      96.26%
browser_runtime.py               97.11%
domain/structured_state.py      100.00%
structured_state_persistence.py 100.00%
```

## Live validation

The dedicated L11 workflow checks out the exact pull-request head and installs the normal project package plus the isolated Playwright binding and sandboxed Chromium runtime.

The live proof uses a controlled first-party fixture rather than relying on a third-party arbitrary-HTML echo service.

The fixture server binds only to loopback inside the GitHub Actions runner. Production public-web hostname validation remains unchanged and continues to reject `localhost` and IP literals. The workflow alone maps the reserved test hostname:

`sa16-l11-fixture.example`

to loopback through the runner's `/etc/hosts`.

This mapping is test infrastructure only; no production hostname/SSRF rule is weakened.

The rendered page:

- defines reviewed `window.__INITIAL_STATE__` data;
- intentionally includes secret-like keys;
- performs a same-origin `fetch()` JSON request;
- performs a same-origin XHR JSON request using a `+json` MIME type;
- attempts an off-origin fetch which the existing browser policy must block.

The exact-head candidate live result is:

```text
network_json=2
script_state=1
persisted=3
off_origin_captured=0
secrets_promoted=0
```

The live path also verifies that mapper and SQLAlchemy persistence preserve browser acquisition, organization, resource-version and extractor/network provenance.

## Explicit exclusions

L11 does not add:

- arbitrary caller-supplied JavaScript;
- arbitrary page-global discovery outside the reviewed allowlist;
- generic script execution as research logic;
- whole-crawl deadline/concurrency/telemetry controls (L12);
- browser action plans, clicks or form submission (L13);
- screenshots or controlled downloads (L14);
- delegated identities or session governance (L15);
- authorized login/session reuse (L16);
- OAuth/SSO or human MFA/CAPTCHA checkpoint/resume (L17);
- direct claim/opportunity/outreach creation from captured JSON or script state.

## Continuation reference

The canonical remaining implementation plan is:

- `docs/source_activation/SA_16_EXECUTION_ROADMAP_L10_L18.md`.

The status/gap matrix remains:

- `docs/source_activation/SA_16_COMPLETION_AUDIT_AND_REMAINING_LOTS.md`.

After L11 is exact-head validated and merged, the next mandatory implementation lot is **SA16-L12 — Crawl deadline, bounded concurrency, and telemetry**.

A future implementation session must re-read the normative SA-16 documents, the completion audit, the execution roadmap, this L11 closeout and the current merged `main` before starting L12.

L12 must not be used to weaken the L11 response-count/byte/sanitization/source-authorization controls. It adds whole-crawl lifecycle controls and observability on top of the already governed public/browser acquisition paths.

## Completion rule

L11 may be closed only when the documentation head itself repeats:

- complete CI;
- dedicated exact-head L11 live validation;
- critical coverage targets;
- dependency/security checks;
- reversible migration validation;
- review/thread audit;
- Ready transition only after those gates pass;
- locked squash merge against the validated head SHA;
- post-squash Git-tree equality;
- final `main` pointer verification.

Until those gates repeat on the documentation head, this document deliberately remains `FINAL_EXACT_HEAD_REVALIDATION_PENDING`.