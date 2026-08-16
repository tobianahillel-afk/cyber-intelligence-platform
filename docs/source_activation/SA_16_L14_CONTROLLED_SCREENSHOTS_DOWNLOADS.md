# SA-16 L14 — Controlled screenshots and downloads

## Status

`FINAL_EXACT_HEAD_REVALIDATION_PENDING`

SA16-L14 closes the governed browser-artifact gap identified by the SA-16 execution roadmap. It adds typed screenshot and download actions, policy-bound raw retention, bounded quarantine and parsing, durable artifact provenance, and real-browser proof without widening the public authority or authentication surface established by L01-L13.

Pre-documentation candidate:

`d3bc89d0479ea3aa47d8543ac5bc23ba0bee29cc`

Candidate Git tree:

`9d9ac9a3abba9a7cdc365b3a45ce546eb4d4c877`

Candidate base `main`:

`064146b9715bbac33443738b332ef14b5fc1e16b`

Candidate evidence:

- CI #2328 / run `31968583371`: **PASS** against the pull-request integration ref built from the unchanged L13 `main` base and candidate head;
- SA-16 L14 Live Validation #16 / run `31968583342`: **PASS** on the exact candidate pull-request head;
- tests: **1,811 passed, 0 failed, 0 errors**;
- repository combined line/branch coverage: **90.41%**, above the enforced 90% gate;
- `public_web/artifact_context.py`: **100.00%**;
- `public_web/artifact_download.py`: **100.00%**;
- `public_web/artifact_policy.py`: **98.63%**;
- `public_web/artifact_quarantine.py`: **100.00%**;
- `public_web/artifact_retention.py`: **100.00%**;
- `public_web/artifact_runtime.py`: **100.00%**;
- `public_web/artifact_screenshot.py`: **98.98%**;
- `public_web/browser_action_authorization.py`: **100.00%**;
- `public_web/browser_action_executor.py`: **95.19%**;
- `public_web/browser_action_steps.py`: **98.97%**;
- `public_footprint/domain/artifacts.py`: **99.47%**;
- `public_footprint/domain/browser_actions.py`: **98.61%**;
- `public_footprint/infrastructure/artifact_models.py`: **100.00%**;
- `public_footprint/infrastructure/artifact_persistence.py`: **100.00%**;
- `public_footprint/infrastructure/browser_action_persistence.py`: **97.70%**;
- Ruff: **PASS**;
- strict Mypy: **PASS, 755 source files**;
- architecture/release contracts: **PASS, 36/36**;
- reversible migrations `upgrade head -> downgrade base -> upgrade head`: **PASS** including `20260816_0030`;
- normal runtime import before Playwright installation: **PASS**;
- dependency consistency and `pip-audit`: **PASS, no known vulnerabilities**;
- frontend dependency audit, typecheck and production build: **PASS**;
- PR review audit before documentation: **0 reviews, 0 review threads, 0 conversation comments**.

The closeout itself changes the pull-request tree. The evidence above is therefore candidate evidence only. Complete CI and the dedicated L14 live workflow must repeat after this documentation commit before the PR may be marked Ready or merged.

## Capability

L14 extends the closed L13 browser-action vocabulary with two reviewed artifact actions only:

- `screenshot` for an explicitly reviewed viewport or element scope;
- `download` for an explicitly selected public link and expected canonical download URL.

There is no generic download endpoint, arbitrary filesystem access, caller-supplied JavaScript, secret injection, login flow or native browser-download capability.

The normal L13 browser context remains configured with `accept_downloads=False`. A DOM click therefore cannot cause Chromium to write an uncontrolled file. L14 downloads use a separate governed HTTP path with explicit authorization and byte limits.

## Artifact provenance and durable metadata

L14 introduces a typed `BrowserEvidenceArtifact` model carrying bounded provenance and integrity metadata, including:

- source, provider and target identity;
- execution job identity;
- browser plan ID/version and step ID;
- artifact kind and processing state;
- page URL and source URL;
- capture timestamp;
- SHA-256 content digest;
- media type and byte size;
- source locator;
- raw-retention decision and optional storage reference;
- screenshot mode, dimensions and optional element selector;
- download filename, extracted-text digest and bounded excerpt where applicable.

Migration `20260816_0030` adds `browser_evidence_artifacts`. The table stores artifact metadata and provenance only; raw artifact bytes are not written into PostgreSQL.

Artifact persistence is idempotent by deterministic artifact identity and rejects identity collisions rather than silently replacing provenance.

## Raw retention is opt-in and policy-bound

Raw artifact persistence is not a default side effect.

A raw screenshot or download can be retained only when all of the following are true:

1. the typed action explicitly requests raw retention;
2. the existing source policy permits raw-content storage;
3. source authorization permits raw storage;
4. the source purpose/URL remains authorized at capture time;
5. a deployment-owned artifact store is explicitly injected;
6. the returned storage reference is valid and the retention deadline is in the future.

The implementation reuses the existing `SourcePolicy.evaluate()` path with `store_raw_content=True`. It does not create a browser-specific retention permission system.

A storage **port** is defined at the application boundary, but L14 deliberately does not add implicit permanent local-file retention. When no approved deployment store exists, raw retention requests fail closed.

## Screenshot governance

Before a screenshot is produced, the runtime reauthorizes the current canonical page URL through the L13 host/path/method and source-governance rules.

Screenshot scope is typed as either:

- viewport; or
- one explicitly selected element.

Capture fails closed when the selected scope itself or any descendant contains a sensitive/challenge surface, including:

- password inputs;
- file inputs;
- one-time-code inputs;
- OTP-named inputs;
- CAPTCHA iframes/markers;
- explicitly `data-sensitive` elements.

The root element is inspected as well as descendants, preventing a direct selector on a sensitive input from bypassing the descendant guard.

Captured bytes must be a valid PNG signature with a valid IHDR and bounded positive dimensions before an artifact record is emitted. Screenshot count and byte budgets are enforced separately from normal browser request budgets.

## Controlled download admission

A download step must resolve to exactly one anchor element. Its actual `href`, resolved against the current page, must exactly match the plan's reviewed `expected_download_url` after canonicalization.

The destination is then authorized through the same L13 transition and source-governance checks used by browser navigation.

HTTP retrieval is bounded by:

- request timeout;
- per-artifact byte ceiling;
- aggregate download-byte ceiling;
- download count;
- redirect count;
- target redirect ceiling.

Redirects are not followed implicitly. Every redirect target is canonicalized and reauthorized before the next request. Redirects without `Location`, redirects beyond budget, off-scope destinations, unsupported methods and response-size violations fail closed.

## MIME, extension and magic validation

Downloaded content is not admitted solely because a server declares a MIME type.

L14 cross-checks:

- declared MIME type;
- URL/file extension where present;
- file magic/package shape;
- executable signatures;
- safe parser availability.

The intentionally limited admitted document families are the existing public-document families already handled by CIP:

- PDF;
- UTF-8 plain text;
- OOXML DOCX;
- OOXML XLSX;
- OOXML PPTX.

Opaque `application/octet-stream` content is accepted only when a safe permitted type can be determined. Executable magic, unknown binary content, inconsistent extension/MIME combinations, embedded NUL text and malformed package shape are rejected.

## Ephemeral quarantine and parser reuse

Approved download bytes enter a private temporary quarantine before parsing. The quarantine file is created with private permissions and is removed on both successful parsing and parser failure.

L14 does not introduce a second document parser. It routes admitted bytes into the existing bounded parsers:

- PDF parsing with existing encryption, byte, page and extracted-text limits;
- plain-text parsing with UTF-8/NUL/size limits;
- OOXML parsing with existing ZIP entry, path traversal, encryption, macro, expansion and compression-ratio protections.

The live proof explicitly verifies that no quarantine file remains after execution.

## Projection into the existing public-footprint model

A successfully parsed download is projected through the existing public-footprint model as:

`PublicResource(kind=DOCUMENT) -> PublicResourceVersion -> PublicFootprintProjection`

The document version carries its source URL, content hash, fetched timestamp, MIME type, byte size, optional title/language, extracted-text hash, excerpt and browser-action source locator.

L14 therefore produces evidence through the existing canonical public-footprint path instead of creating a parallel browser-document data model.

## Browser isolation posture

L14 keeps the existing L13 browser isolation posture intact:

- disposable browser context;
- `accept_downloads=False`;
- CSP bypass disabled;
- HTTPS errors not ignored;
- service workers blocked;
- bounded request interception;
- typed actions only;
- host/path/purpose/method authorization;
- no credential or delegated-session injection.

Browser bindings remain isolated from the normal runtime dependency path. CI again verifies that the standard runtime imports before Playwright is installed.

## Deterministic tests

L14 adds deterministic tests covering both positive and fail-closed behavior, including:

- screenshot/download action-shape validation;
- retention invariants and future-deadline checks;
- artifact identity/hash/size/MIME validation;
- screenshot versus download field-shape separation;
- rejected-artifact constraints;
- screenshot count and byte budgets;
- download count/per-artifact/aggregate-byte budgets;
- PNG signature and dimension guards;
- executable, MIME, extension and magic rejection;
- quarantine private permissions and cleanup after success/failure;
- retention policy denial, store absence and invalid storage references;
- artifact runtime dispatch and missing-context rejection;
- direct and descendant sensitive screenshot surfaces;
- exact link/HREF/expected-URL admission;
- redirect-without-Location and redirect-budget failures;
- parser-unavailable rejection;
- plan serialization compatibility;
- artifact persistence idempotence and collision rejection;
- metadata/foreign-key contracts.

No coverage, architecture, file-size, function-size, parameter-count or nesting guard was weakened. The executor integration was instead refactored into bounded execution context objects where necessary to remain inside the existing quality budgets.

## Live validation

The dedicated L14 workflow executes the production artifact path with real Chromium against a repository-controlled first-party fixture mapped to loopback.

The live scenario proves:

1. Chromium navigates to an authorized public fixture page through the L13 route guard;
2. an authorized element screenshot is captured through the production screenshot path;
3. PNG dimensions and artifact metadata are produced;
4. an authorized public text document is downloaded through the governed HTTP path rather than native Chromium download handling;
5. the download is quarantined and parsed through the existing public-document parser;
6. a canonical `DOCUMENT` public-footprint projection is persisted;
7. both artifact metadata records are persisted with plan/step provenance;
8. source policy denying raw storage results in no retained raw artifact URI;
9. the quarantine directory has no leaked artifact after execution.

The candidate live workflow result is **PASS** on `d3bc89d0479ea3aa47d8543ac5bc23ba0bee29cc`.

## Explicit exclusions

L14 does not add:

- arbitrary JavaScript or generic browser commands;
- credentials, passwords or secret-field handling;
- delegated browser identities or reusable sessions;
- provider login;
- OAuth/SSO;
- automated MFA/CAPTCHA/terms resolution or bypass;
- file upload;
- native/uncontrolled browser downloads;
- executable or arbitrary binary acquisition;
- implicit permanent local artifact storage;
- raw retention without explicit source policy, authorization and deployment storage;
- any weakening of L12 deadline/budget or L13 host/path/purpose/method controls.

Delegated browser identity/session governance belongs to L15. Provider login/session reuse belongs to L16. OAuth/SSO plus explicit human checkpoints belongs to L17.

## Continuation reference

The canonical remaining implementation plan is:

- `docs/source_activation/SA_16_EXECUTION_ROADMAP_L10_L18.md`.

The status/gap matrix remains:

- `docs/source_activation/SA_16_COMPLETION_AUDIT_AND_REMAINING_LOTS.md`.

After L14 is exact-head validated and merged, the next mandatory implementation lot is **SA16-L15 — Delegated browser identity and session governance**.

L15 must build on the existing source-governance account model and Provider Onboarding secret-reference lifecycle. It must establish tenant/provider/purpose-bound identity/session ownership, revocation, expiry, deletion and audit controls before any authenticated provider browsing is introduced. It must not perform provider login, MFA/CAPTCHA bypass or serialize secret/session values in ordinary domain/API/log paths.

## Completion rule

L14 may be closed only when the documentation head itself repeats:

- complete CI;
- dedicated exact-head L14 real-Chromium live validation;
- repository quality and coverage gates;
- critical L14 module coverage at or above the project's high-coverage target;
- bounded screenshot/download/quarantine/projection proof;
- dependency/security checks;
- reversible migration validation;
- review/thread/comment audit;
- Ready transition only after those gates pass;
- locked squash merge against the validated head SHA;
- post-squash Git-tree equality;
- final `main` pointer verification.

Until those gates repeat on the documentation head, this document deliberately remains `FINAL_EXACT_HEAD_REVALIDATION_PENDING`.
