# SA-16 L10 — Structured public web-surface inventory

## Status

`FINAL_EXACT_HEAD_REVALIDATION_PENDING`

SA16-L10 closes the structured page-surface inventory gap identified by the post-L09 SA-16 completion audit. It adds version-bound, typed, queryable surface records without converting resource references into commercial/technology claims and without introducing browser interaction.

Pre-documentation candidate:

`a18d61719a2e0154a1b6d2a45d8dd6587d766f52`

Candidate Git tree:

`cea109382f13dea82559d320304696076c629340`

Candidate evidence:

- CI #2148 / run `31798385824`: **PASS** backend and frontend;
- SA-16 L10 Live Validation #1 / run `31798385848`: **PASS, 20/20**;
- tests: **1,628 passed, 0 failed, 0 errors, 0 skipped**;
- global line coverage: **93.32%**;
- `response_headers.py`: **100% line / 100% branch**;
- `surface_extraction.py`: **99.21% line / 98.08% branch**;
- `domain/surfaces.py`: **100% line / 100% branch**;
- `surface_persistence.py`: **100% line / 100% branch**;
- Ruff, strict Mypy, architecture/release 36/36 and reversible migrations: **PASS**;
- standard runtime import without browser bindings: **PASS**;
- frontend audit, typecheck and production build: **PASS**.

The closeout and canonical remaining-lot roadmap are now part of the PR tree. Complete CI and the dedicated L10 live workflow must repeat on the resulting documentation head before merge. Historical candidate evidence above remains supporting evidence only; the final merge gate is the exact current PR head.

## Capability

Each fetched resource version can now carry a typed inventory of public surfaces:

- `response_header`;
- `canonical_link`;
- `alternate_link`;
- `stylesheet`;
- `script`;
- `resource_reference`;
- `form_endpoint`;
- `document_link`;
- `media_link`.

Surfaces are metadata observations, not evidence claims. A script/style/resource reference does not by itself prove a technology deployment, and a form endpoint does not authorize submission.

## Version and history semantics

`PublicSurfaceReference` is bound to an exact public-resource version. The identity key contains the organization, persisted resource-version identity, surface kind, locator and normalized metadata.

This preserves two required properties:

1. replay of the same representation is idempotent and does not duplicate a surface;
2. when page content changes, surfaces from the older version remain historically attached to that version instead of moving to the newest representation.

The public-web mapper also preserves the previous version UUID for an unchanged HTTP 200 representation, matching the existing 304 semantics.

## Persistence

Migration `20260814_0025` adds `public_surface_references` with:

- FK to organization;
- FK to `public_resource_versions` with cascade deletion;
- unique `surface_key`;
- organization/kind and version/kind indexes;
- bounded typed columns for URL, relation, HTTP method, MIME type, header name/value and source locator.

Persistence resolves the actual persisted version record before calculating the surface key. This safely handles a generic replay where an equivalent transient projection uses a different UUID but the same resource `version_key`.

Identity collisions with inconsistent metadata fail closed.

## Approved response headers

Headers use a positive evidence allowlist. Current approved names include public delivery/security metadata such as:

- `content-language`;
- `content-security-policy`;
- `content-type`;
- cross-origin policies;
- `permissions-policy`;
- `referrer-policy`;
- `server`;
- `strict-transport-security`;
- `via`;
- `x-content-type-options`;
- `x-frame-options`;
- `x-powered-by`.

Values are whitespace-normalized and bounded to 2,000 characters.

Sensitive/arbitrary headers such as `Set-Cookie` and `Authorization` are never placed into the surface model. The Playwright path queries only allowlisted names rather than retrieving the complete browser response-header map.

## HTML surface extraction

Extraction is bounded to 256 surfaces per page and normalizes relative URLs through the same `CanonicalUrl` contract used elsewhere by public-web collection.

Supported HTML sources include:

- `<link rel=canonical>`;
- non-feed `<link rel=alternate>`;
- stylesheets;
- icon/manifest/preload/prefetch/modulepreload resource references;
- external script `src`;
- form `action`, method and enctype metadata;
- document anchors identified by approved document MIME/extension families;
- image/video/audio/source media URLs and video posters;
- iframe/object/embed resource references.

RSS/Atom alternate links remain owned by the existing L03 feed-discovery path and are not duplicated as generic alternate surfaces.

Invalid or unsupported URL schemes such as `javascript:` and `data:` do not enter the surface inventory.

## No new network authority

L10 does not make a recognized surface automatically executable.

The extractor:

- performs no request itself;
- submits no form;
- clicks no element;
- downloads no artifact solely because it was recognized as a surface;
- does not expand browser/source authorization;
- does not change ordinary crawl admission.

A target URL can only be fetched later by an existing or future governed path that independently passes source authorization, same-origin/path scope and relevant budgets.

## Browser compatibility

Static HTTP and browser-rendered pages produce the same bounded response-header representation.

Existing browser safeguards remain unchanged:

- Chromium sandbox enabled;
- downloads disabled;
- CSP not bypassed;
- TLS errors not ignored;
- service workers blocked;
- host/path authorization before requests;
- images/fonts/media blocked in the rendered acquisition runtime;
- request and DOM budgets retained.

L10 adds no click/form/login behavior.

## Tests

Coverage includes:

- every surface kind;
- response-header allowlist and sensitive-header exclusion;
- 2,000-character header bound;
- canonical/alternate/feed distinction;
- form method/enctype normalization;
- document MIME and extension detection;
- relative URL normalization;
- invalid URL schemes;
- duplicate surfaces;
- 256-surface cap, including a cap reached within a multi-surface video element;
- domain required/optional field bounds;
- response-header vs URL-surface invariants;
- projection organization/version invariants;
- same-version persistence replay with a different transient UUID;
- historical surfaces across changed resource versions;
- persistence identity-collision fail-closed behavior;
- unchanged HTTP 200 version-ID reuse;
- changed-page version/supersession semantics.

## Live validation

The dedicated workflow checks out the exact pull-request head, installs the normal project package, runs dependency consistency checks, then exercises the real `PublicWebAdapter`, mapper and SQLAlchemy projection persistence against 20 public neutral/first-party pages with depth zero and a one-page target budget.

The live set includes Example, Python, Python Docs, PyPI, Django, FreeBSD, Go, Node.js, Kubernetes, PostgreSQL, SQLite, kernel.org, IETF, RFC Editor, curl, Debian, Selenium Web Form, Selenium Downloads and two W3C pages.

The candidate live run proved all nine surface kinds in aggregate. Examples recorded by the workflow include:

- Node.js and Kubernetes: `alternate_link`;
- Python Docs/PyPI/FreeBSD/Go/RFC Editor/W3C: `canonical_link`;
- kernel.org and W3C PDF technique: `document_link`;
- Selenium Web Form: `form_endpoint`;
- multiple targets: stylesheet/script/resource/media/header surfaces.

Final candidate summary:

```text
targets=20
persisted_surfaces=535
surface_kinds=9
form_submissions=0
```

The Selenium form is inventoried only. No POST, click or submit operation exists in the L10 live path.

## Explicit exclusions

L10 does not add:

- rendered XHR/fetch JSON capture (L11);
- arbitrary script/global state capture (L11);
- crawl wall-clock/concurrency telemetry (L12);
- browser action plans or form submission (L13);
- screenshots/downloads (L14);
- delegated identities/sessions (L15);
- login (L16);
- OAuth/SSO or human MFA/CAPTCHA resume (L17).

## Continuation reference

The canonical remaining implementation plan is:

- `docs/source_activation/SA_16_EXECUTION_ROADMAP_L10_L18.md`.

The status/gap matrix remains:

- `docs/source_activation/SA_16_COMPLETION_AUDIT_AND_REMAINING_LOTS.md`.

After L10 is exact-head validated and merged, the next mandatory implementation lot is **SA16-L11 — Rendered public JSON and script-state capture**. A future session should re-read the normative SA-16 documents, the completion audit, the execution roadmap, this L10 closeout and the current `main` before creating the L11 branch.

The execution roadmap owns the detailed L11-L18 sequencing, dependencies, invariants, tests, live-proof requirements and the normative traceability matrix. It may make implementation details more precise but may not weaken the normative SA-16 scope.

## Completion rule

L10 may be closed only when the documentation head itself repeats:

- complete CI;
- dedicated 20-target live validation;
- critical coverage targets;
- review/thread audit;
- locked merge against the validated head;
- post-squash Git-tree equality.
