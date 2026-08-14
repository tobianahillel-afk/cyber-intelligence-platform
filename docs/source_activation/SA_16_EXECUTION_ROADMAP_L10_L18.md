# SA-16 — Canonical execution roadmap from L10 to L18

## Status and purpose

`ACTIVE_EXECUTION_PLAN`

This document is the detailed execution plan for completing SA-16 after the post-L09 completion audit.

It is a **derived implementation plan**. It does not weaken, replace, reinterpret or remove any requirement from the normative documents:

- `docs/source_activation/SA_15_20_FULL_ACTIVATION_ROADMAP.md`;
- `docs/OSINT_FULL_IMPLEMENTATION_MANDATE.md`;
- `docs/OSINT_AUTOMATION_PIPELINES.md`;
- `docs/SOCIAL_COMMUNITY_ACQUISITION_REQUIREMENTS.md` where delegated accounts, sessions and legitimate challenge handling are relevant.

The companion audit is:

- `docs/source_activation/SA_16_COMPLETION_AUDIT_AND_REMAINING_LOTS.md`.

Historical lot closeouts remain truthful records of the tree that was validated at the time. This roadmap is the forward execution reference for the remaining SA-16 work.

## Source-of-truth hierarchy

When documents appear to overlap, use this order:

1. normative product/acquisition documents listed above;
2. the SA-16 completion audit for covered/partial/absent status;
3. this execution roadmap for lot sequencing and engineering acceptance criteria;
4. individual lot closeouts for exact implementation evidence and validated commit/tree IDs.

A lower-level document may make implementation details more precise, but it may not silently remove a higher-level requirement.

## Current baseline

Merged before this execution plan:

- SA16-L01 through SA16-L09;
- the post-L09 SA-16 completion audit and L10-L18 decomposition.

Current implemented public-web foundation:

```text
approved organization domain
-> automatic governed target
-> automatic schedule
-> robots
-> sitemap / sitemap indexes
-> RSS / Atom / security.txt
-> bounded recursive same-origin crawl
-> incremental recrawl / validators
-> versions / tombstones
-> semantic HTML / JSON-LD / OpenGraph / embedded JSON
-> PDF / text / DOCX / XLSX / PPTX extraction
-> isolated Chromium rendering
-> deterministic static-first browser fallback
-> canonical projections / provenance / checkpoints
```

SA16-L10 is implemented on PR #148 at the time this plan is written, including typed structured page-surface inventory and its dedicated live workflow. Because this document is committed on the L10 branch, L10 must repeat exact-head CI and live validation after this documentation change before merge.

## Remaining lot sequence

Recommended execution order:

```text
L10 -> L11 -> L12 -> L13 -> L14 -> L15 -> L16 -> L17 -> L18
```

Dependency view:

```text
L10 -> L11 -----------\
  \                    \
   -> L12 --------------> L18

L09 -> L13 -> L14 -----/
          \
Provider Onboarding -> L15 -> L16 -> L17 -> L18
```

The sequence may be restacked only when a smaller independently testable split is required by implementation evidence or architecture gates. A restack may not drop a normative capability.

## Global engineering rules for every remaining lot

Every lot must preserve the repository-wide development and evidence rules.

### Architecture

- API/CLI/composition may depend on application; application may depend on domain; domain must remain infrastructure-independent.
- New responsibilities should be split rather than growing files/classes/functions beyond repository architecture limits.
- Existing provider-onboarding, source-policy, checkpoint, artifact, worker, source-health and persistence primitives must be reused where semantically correct instead of creating parallel control planes.
- PostgreSQL remains source of record; derived search/cache stores remain derived.

### Source authority and network safety

- Every request/navigation/download must independently satisfy source authorization and host/path scope.
- Newly discovered metadata never grants new network authority by itself.
- Same-origin or explicit allowlist checks remain mandatory where the source contract requires them.
- No CAPTCHA/MFA/paywall/access-control bypass, credential guessing, account rotation, ban/quota evasion or arbitrary exploitation is part of SA-16.
- Browser work remains isolated and disposable.

### Evidence semantics

- Resource references, scripts, styles, headers and provider mentions are evidence candidates, not proof of technology deployment.
- Raw provider/browser state must preserve source/provenance and cannot be directly promoted to confirmed commercial facts.
- Sensitive/session/credential-like material must not be promoted into ordinary observations, logs or screenshots.

### Determinism, replay and checkpoints

- Unit/contract tests must not depend on the live network.
- Retry/replay behavior must be explicit for every state-changing browser action.
- Jobs that can pause or resume must retain enough persisted state to resume safely without re-executing an unsafe non-idempotent action.
- Idempotency keys and version identities must remain stable across equivalent replay.

### Lot completion protocol

A remaining lot is not closed merely because code exists. Unless the lot explicitly has no live component, closing it requires:

1. implementation complete on a dedicated branch;
2. deterministic unit/contract/integration tests;
3. reversible migration when persistence changes;
4. Ruff PASS;
5. strict Mypy PASS;
6. architecture/release contracts PASS;
7. migration up -> down -> up PASS when applicable;
8. normal backend/frontend CI PASS;
9. critical changed modules targeted at >=95% line and branch coverage, with branches tested rather than deleted solely to improve coverage;
10. controlled production-path live proof where the capability can legitimately be exercised;
11. closeout document committed;
12. CI and live proof repeated on the exact documentation head;
13. review/thread audit with no blocking unresolved feedback;
14. PR moved to Ready only after the exact head is validated;
15. merge locked to the validated head SHA;
16. post-squash Git-tree equality between validated head and merged commit;
17. `main` re-read after merge before the next lot begins.

## Tracking table

| Lot | Capability | State at plan creation | Closure condition |
|---|---|---|---|
| L10 | Structured web-surface inventory | Implemented on PR #148; final revalidation required after roadmap-doc commit | exact-head CI/live + merge/tree equality |
| L11 | Rendered public JSON and script-state capture | Not implemented | network/script structured state captured with bounds/provenance and live Chromium proof |
| L12 | Crawl deadline, concurrency and telemetry | Not implemented | bounded concurrent crawl with deadline and persisted crawl health/metrics |
| L13 | Governed browser action plans and public forms | Not implemented | typed bounded actions, safe form submit, resumable non-auth job |
| L14 | Screenshots and controlled downloads | Not implemented | governed screenshot/download artifact path with quarantine and live proof |
| L15 | Delegated browser identity and session governance | Not implemented | tenant/user/service-principal bound identity/session lifecycle and audit |
| L16 | Authorized login and governed session reuse | Not implemented | provider-specific legitimate login, secret-safe session persistence/reuse/revocation |
| L17 | OAuth/SSO and human MFA/CAPTCHA checkpoints | Not implemented | legitimate OAuth/SSO + same-job human challenge resume |
| L18 | Full SA-16 end-to-end proof and closeout | Not implemented | every SA-16 audit row Covered or explicitly product-owner removed; final public/auth live proofs |

---

# SA16-L10 — Structured public web-surface inventory

## Objective

Close the remaining page-surface extraction gaps without granting browser interaction or new network authority.

## Implemented/required capability

Persist typed, version-bound surface observations for:

- approved public response headers;
- canonical links;
- non-feed alternate links;
- stylesheet references;
- external script references;
- other bounded resource references useful for technology attribution;
- form action/method/enctype metadata;
- document links;
- media links;
- source locators and provenance.

## Data model

Surface observations are separate from commercial/technology claims.

Required semantics:

- surface identity is bound to an exact persisted resource version;
- replay of the same version is idempotent;
- changed content creates a new version whose surfaces remain historically separate;
- surface metadata cannot silently move from an old version to a new version;
- persistence collisions with inconsistent metadata fail closed.

## Network and interaction boundary

L10 may identify a form endpoint, script URL, media URL or document URL, but identification alone never authorizes:

- submitting the form;
- clicking an element;
- fetching an off-scope resource;
- downloading an artifact;
- executing a script.

A later acquisition path must independently pass ordinary authorization, origin/path and budget checks.

## Response-header policy

Only a positive reviewed allowlist may become structured evidence. Session/authentication-sensitive or arbitrary headers such as `Set-Cookie` and `Authorization` must not enter the surface model.

## Tests and live proof

Required coverage includes all surface kinds, bounds, invalid schemes, duplicate suppression, page caps, persistence/version history, response-header allowlisting and no-form-submit behavior.

The controlled live proof must exercise real production adapter -> mapper -> persistence behavior against neutral/first-party pages and prove all required surface kinds in aggregate with `form_submissions=0`.

## Exit gate

L10 closes only after its closeout head repeats exact-head CI and dedicated live validation and is merged with validated-tree equality.

## Explicit exclusions transferred to later lots

- rendered XHR/fetch JSON and non-L05 public script state -> L11;
- crawl deadline/concurrency/telemetry -> L12;
- clicks/fills/submissions -> L13;
- screenshots/downloads -> L14;
- delegated accounts/sessions -> L15;
- login -> L16;
- OAuth/SSO/human challenges -> L17.

---

# SA16-L11 — Rendered public JSON and script-state capture

## Objective

Capture useful public structured state that only becomes available during rendered application execution while preserving the browser/source authorization boundary.

This lot closes the normative requirements for:

- authorized structured JSON responses used by rendered applications;
- script-exposed public structured state not already handled by the L05 typed embedded-JSON path;
- explicit network/script provenance for those records.

## Production flow

Target flow:

```text
authorized rendered page
-> browser request interception remains active
-> response observed
-> source/origin/path authorization rechecked
-> status/MIME/size/request-count admission
-> bounded body capture only for approved JSON responses
-> JSON parse and depth/scalar/value bounds
-> sensitive-key suppression
-> structured observation/projection with page + response locator provenance
```

Script-state flow:

```text
rendered page
-> fixed reviewed extractor
-> public structured state only
-> bounded serialization
-> sensitive-key suppression
-> page/script locator provenance
```

## Planned ownership

Implementation should remain under the existing isolated public-web browser adapter/runtime and public-web mapping/domain paths. If the runtime begins mixing navigation, response capture and normalization responsibilities, create dedicated response/state collector modules rather than growing `browser_runtime.py` into a multi-purpose file.

Expected responsibility split:

- browser runtime: observe authorized network/page events;
- bounded JSON/state capture helper: admission + byte/count limits;
- structured-state sanitizer: depth/scalar/value/sensitive-key filtering;
- mapper/domain: normalize public structured state and provenance;
- persistence: use existing evidence/version model unless a genuinely new typed store is required.

## Required bounds

At minimum define and test explicit limits for:

- maximum captured JSON responses per rendered page/job;
- maximum bytes per response;
- maximum aggregate JSON bytes per page/job;
- accepted HTTP status classes;
- accepted JSON MIME/content types;
- JSON nesting depth;
- scalar count;
- string/key length;
- script-state serialized bytes;
- total number of script-state records.

## Sensitive-data boundary

Do not promote values whose names/locations indicate likely:

- access tokens;
- refresh tokens;
- authorization headers;
- cookies/session IDs;
- passwords/secrets/API keys;
- CSRF/session nonces where retention is unnecessary;
- private account state outside the approved source purpose.

Filtering must be deterministic, tested and consistent with the L05 public structured-data model.

## JavaScript boundary

Do not add arbitrary caller-supplied JavaScript evaluation.

If page evaluation is required for a supported state shape, use fixed reviewed extractors with:

- hard-coded extraction purpose;
- bounded output;
- no caller-controlled executable code;
- source/versioned implementation identity where useful.

## Off-origin behavior

Off-origin response bodies must not become captured state merely because the page requested them. Any explicit multi-origin support would require a separate reviewed source-policy contract; L11 does not implicitly broaden the target.

## Deterministic tests

Required fixtures:

- rendered page performs same-origin `fetch()` returning JSON;
- rendered page performs XHR JSON;
- off-origin JSON request;
- non-JSON response;
- oversized JSON response;
- too many JSON responses;
- deep/large structured payload;
- secret-like keys mixed with public keys;
- fixed script-state fixture not represented by `application/json` or JSON-LD;
- malformed JSON;
- redirects/status variants as applicable.

Tests must prove:

- admitted same-origin state is captured;
- off-origin state is not captured;
- secrets are suppressed;
- count/byte/depth bounds fail closed or truncate according to a documented deterministic contract;
- page URL and network/script locator provenance survives mapping.

## Live validation

Use a controlled neutral/first-party rendered fixture or public test site that makes real same-origin JSON requests. The production Chromium path must prove:

- sandbox remains enabled;
- response capture happens only after authorization;
- at least one non-empty JSON record is captured;
- off-origin/secret test paths remain excluded;
- canonical/provenance mapping is non-empty.

## Exit gate

Closeout requires exact-head CI, sandboxed Chromium live proof, critical-module line/branch targets, review audit, locked merge and post-squash tree equality.

## Explicit exclusions

- generalized form/action execution -> L13;
- login/authenticated session state -> L16/L17;
- arbitrary JavaScript evaluation remains out of scope.

---

# SA16-L12 — Crawl deadline, concurrency and crawl telemetry

## Objective

Complete the normative crawl operational-safety requirements for configurable **time**, **concurrency** and first-class crawl-health metrics.

## Target configuration additions

Add explicit bounded target/deployment settings for:

- whole-crawl wall-clock deadline;
- maximum crawl concurrency;
- any per-host concurrency/pace control required by the source policy;
- existing freshness/depth/page/byte budgets remain authoritative.

The wall-clock deadline is a whole-job/crawl deadline, not merely a request timeout.

## Concurrency model

Concurrency must remain deterministic enough for replay and testing.

Required properties:

- candidates have a deterministic admission ordering;
- shared page and byte budgets are synchronized;
- two workers cannot each consume the same final page/byte allowance;
- completion order may vary, but admitted work and final accounting must obey the documented deterministic contract;
- path/origin/robots/source policy is checked per request;
- cancellation stops new admissions promptly;
- active tasks are cancelled/cleaned within bounded time;
- checkpoints cannot claim work was completed when it was merely scheduled.

Do not implement concurrency by removing existing safety budgets or by giving each worker an independent copy of a global budget.

## Deadline behavior

When the crawl deadline expires:

```text
deadline reached
-> stop admitting new candidates
-> cancel/finish active work according to documented bounded cleanup
-> persist consistent checkpoint/result state
-> emit deadline metric/status
-> worker/job finishes with a classified retryable/non-retryable result according to the source contract
```

## Crawl result/telemetry contract

Promote crawl-specific metrics to a typed result/value-event/health path. At minimum capture:

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
- deadline exceeded/cancelled state;
- concurrency configuration actually used.

Where useful also record sitemap/feed/document counts, but do not duplicate unrelated generic worker metrics.

## Persistence/health integration

Reuse existing source portfolio, worker/source health and value-event primitives where semantically appropriate. Do not create an isolated metrics subsystem only for public web unless existing contracts cannot represent the needed data.

## Deterministic tests

Required tests include:

- page budget of one with multiple concurrent candidates;
- byte budget race with simultaneous responses;
- deterministic admission order;
- max concurrency respected;
- deadline before first response;
- deadline during active requests;
- cleanup/cancellation;
- checkpoint after partial crawl;
- metrics for 200, 304, tombstone, redirect, denial, fallback and failure;
- no metric double-count on retry/replay.

## Live validation

Controlled multi-page crawl with concurrency >1 and intentionally tight but non-flaky budgets. Prove:

- more than one page fetched;
- concurrency limit respected;
- budgets not oversubscribed;
- metrics persisted through the production worker/runtime path;
- a separate controlled deadline case cleans up without orphaned browser/network work.

## Exit gate

Exact-head CI/live, critical coverage, health persistence proof and normal merge/tree protocol.

---

# SA16-L13 — Governed browser action plans and public forms

## Objective

Extend the isolated browser from render/navigation into bounded, typed, auditable first-party interaction **without authentication yet**.

## Typed action model

Support only reviewed actions such as:

- `navigate`;
- `click`;
- `fill` for explicitly non-secret fields;
- `select`;
- `check` / `uncheck` where needed;
- `submit_form` for explicitly authorized public forms;
- bounded `wait_for_navigation` / `wait_for_dom_condition`.

Do not expose a generic arbitrary-browser-command or arbitrary-JavaScript API.

## Action-plan data model

Each action plan should carry:

- plan identity/version;
- source/provider/target identity;
- purpose;
- ordered action steps;
- selector/value/method metadata required by each step;
- action count and value-length budgets;
- allowed host/path transitions;
- retry/idempotency semantics;
- current persisted step/checkpoint state.

## Pre-action authorization

Before an action can result in a network request/navigation:

1. resolve the actual target/form/link destination where possible;
2. check source host/path/method authorization;
3. check same-origin/explicit allowlist policy;
4. enforce action/request budgets;
5. only then execute the action.

A DOM element being present is not authorization.

## Public form controls

Before `submit_form`:

- inspect form action;
- inspect HTTP method;
- inspect field names/types;
- deny credential/password fields in L13;
- deny file inputs/upload in L13;
- deny hidden values that are classified as secret material when the plan would persist/expose them;
- prevent off-scope action targets;
- prevent caller-controlled method/target substitution that bypasses inspected form metadata.

## Resumable non-authenticated jobs

Persist enough action state to recover from a worker/process interruption.

For each step classify replay safety. A non-idempotent submission must not be blindly repeated after an ambiguous crash. Use states such as:

```text
pending
-> executing
-> completed
```

with a recovery strategy that can distinguish a safely retryable step from one requiring verification before replay.

## Deterministic tests

Use local/controlled fixtures covering:

- navigation;
- click-driven DOM change;
- fill/select/check;
- GET form submission;
- explicitly controlled POST form submission;
- off-origin form denial;
- password/file-input denial;
- action count/value/selector bounds;
- timeout;
- crash before step;
- crash after network side effect but before completion persistence;
- safe resume without duplicate unsafe submission.

## Live validation

Use a neutral/first-party browser form fixture approved for interaction. Prove the production adapter executes the intended bounded plan and captures the resulting evidence without authentication.

## Exit gate

Exact-head CI/browser live proof, resumability proof, no arbitrary JS surface, review audit and locked merge/tree equality.

## Explicit exclusions

- credentials/login -> L16;
- OAuth/SSO/MFA/CAPTCHA -> L17;
- screenshots/downloads -> L14.

---

# SA16-L14 — Controlled screenshots and downloads

## Objective

Add evidence-safe screenshots and controlled artifact downloads without weakening browser isolation or source/data-governance controls.

## Screenshot contract

A screenshot is an evidence artifact/derived artifact, not an untracked local file.

Capture metadata should include:

- source/provider/target identity;
- page URL;
- job identity;
- collected/captured timestamp;
- screenshot mode/viewport or element locator when applicable;
- content hash;
- size/dimensions;
- artifact/storage reference when retained;
- retention/data-class policy;
- provenance back to the action/navigation that created it.

Screenshots must avoid credential/challenge pages where policy forbids capture and must never knowingly persist secrets.

## Download admission

A download may occur only when initiated by:

- an explicitly authorized typed browser action; or
- a governed resource/document link whose download path independently satisfies source policy.

Required controls before/while accepting an artifact:

- host/path/method authorization;
- MIME allowlist/validation;
- extension consistency checks where useful;
- maximum bytes per artifact;
- maximum downloads per job;
- aggregate download-byte budget;
- redirect bounds;
- off-origin denial unless separately authorized;
- timeout;
- content hash;
- quarantine before parsing.

## Quarantine and processing

Downloaded content must not be executed.

Target flow:

```text
authorized download
-> bounded temporary/quarantine location
-> MIME/type verification
-> hash
-> malware/file-reputation screening where available in current architecture
-> approved parser pipeline
-> derived evidence/provenance
-> retain raw artifact only if source/data policy permits
```

Reuse existing PDF/text/OOXML processing rather than reimplementing parsers.

## Retention rule

If policy permits raw artifact retention, use the approved artifact storage path (S3 where the repository architecture specifies it).

If raw retention is not allowed:

- process ephemerally;
- persist only permitted hashes/metadata/derived evidence;
- remove temporary bytes after bounded processing.

## Tests

Required:

- screenshot success and metadata/hash;
- screenshot policy denial/redaction/no-secret case;
- safe document download;
- oversized artifact denial;
- too many downloads;
- off-origin download denial;
- MIME/extension mismatch handling;
- executable/unapproved type denial;
- quarantine cleanup on parse failure;
- raw-retention allowed vs forbidden behavior;
- parser integration with existing document paths.

## Live validation

Controlled neutral/first-party screenshot plus bounded document download through the production browser/action path. Prove quarantine, parse/projection and retention behavior.

## Exit gate

Exact-head CI/live, critical coverage and normal locked merge/tree protocol.

---

# SA16-L15 — Delegated browser identity and session governance

## Objective

Create the account/session control plane required before authenticated browsing.

This lot implements the SA-16 portion of the normative delegated-account model and must reuse Provider Onboarding/secret-reference primitives rather than creating a second secret-management system.

## Delegated identity model

A delegated provider/browser identity must be bound to exactly one approved ownership context such as:

- CIP tenant + user;
- CIP tenant + deployment service principal;
- deployment-level service identity where product policy allows it.

Required fields/semantics include:

- stable delegated identity ID;
- provider/source identity;
- provider account identifier when known;
- owner tenant/user/service principal;
- purpose;
- authorization/source scope;
- permissions/scopes;
- isolated secret reference;
- isolated browser-session reference;
- created/authorized/reviewed timestamps;
- last-used timestamp;
- expiry/renewal state;
- revocation state/timestamp;
- deletion state/timestamp;
- audit history.

## Secret/session storage boundary

Normal relational records/logs/checkpoints must store references, not raw credential/session values.

Use existing validated Provider Onboarding secret-reference mechanisms where applicable. Browser storage state/cookie jars must be treated as secret session material and protected by the same isolation principles.

## Authorization isolation

Execution must fail closed when any ownership dimension mismatches, including:

- tenant;
- user/service principal;
- provider/source;
- purpose;
- approved scope;
- expired/revoked/deleted state.

An identity/session for one provider or tenant cannot be silently reused for another.

## Lifecycle operations

Implement at least:

- create/register metadata;
- authorize/review;
- attach/update secret reference;
- attach/update session reference;
- renew/rotate reference metadata where required;
- revoke;
- delete;
- audit/list/read for authorized operators;
- execution eligibility check.

Where a provider explicitly permits automated registration/service accounts or tenant-controlled aliases, model the lifecycle without implementing provider-specific signup unless that provider path belongs in a later provider lot. Never use disposable aliases/accounts to evade provider controls.

## Persistence

A reversible migration is expected unless an existing provider-onboarding table can safely and semantically hold every required delegated identity/session field. Prefer explicit dedicated records over overloading unrelated source-policy fields.

## Tests

Required:

- tenant isolation;
- user/service-principal ownership;
- provider/source mismatch;
- purpose/scope mismatch;
- missing/invalid secret reference;
- missing/invalid session reference where required;
- expiry;
- revocation;
- deletion;
- renewal/rotation metadata;
- audit events;
- secret/session values never serialized in normal API/log/domain repr paths;
- reversible migration.

## Live validation

L15 itself may use a controlled secret/session reference backend without logging in to an external provider. If no external interaction occurs, normal exact-head CI plus an integration proof of the real secret/session reference path is sufficient. Real login/session use is required by L16/L17.

## Exit gate

Governed delegated identity lifecycle exists, is tenant/provider/purpose isolated, revocation/deletion prevents future executable access, and exact-head CI/migration gates pass.

---

# SA16-L16 — Authorized login and governed session reuse

## Objective

Execute legitimate provider/customer-authorized username/secret login for an explicitly delegated L15 identity and safely reuse the resulting governed session.

OAuth/SSO and human CAPTCHA/MFA challenges remain L17.

## Provider-specific login profile

Login must use a reviewed provider/source profile rather than arbitrary caller-supplied login selectors/hosts.

A login profile should define only what the approved provider flow requires, such as:

- login host/origin;
- login path(s);
- username/account field selector;
- secret/password field selector;
- submit action;
- allowed intermediate redirects;
- success/session-established condition;
- logout/session-revocation path where available;
- expected challenge/SSO detection signals;
- provider-specific budgets.

## Secret resolution

Secret values are resolved only inside the isolated execution worker at the moment a reviewed login step requires them.

Secrets must never appear in:

- RawObservation/public-footprint observations;
- normal logs;
- exceptions returned to operators;
- checkpoints;
- screenshots;
- telemetry;
- PR/live artifacts;
- ordinary database fields.

## Session persistence

After successful authentication:

- validate that the resulting session belongs to the intended provider/origin;
- store session material only through the L15 session-reference mechanism;
- persist metadata such as created/last-used/expires, never the raw session in normal records;
- later jobs may reuse only an eligible, unexpired, unre-voked session for the exact tenant/provider/purpose scope.

## Challenge boundary

If login encounters:

- MFA;
- CAPTCHA;
- OAuth;
- SSO;
- unsupported identity-provider redirect;

L16 must classify and stop/pause according to a fail-closed contract. It must not bypass the challenge. L17 owns legitimate interactive continuation.

## Logout/revocation

Where provider behavior supports it, revoke/logout before or as part of local session deletion. Local revocation must at minimum make the session unusable by CIP immediately even when remote logout cannot be confirmed.

## Tests

Required controlled login fixture/account scenarios:

- successful login;
- wrong/missing delegated identity scope;
- secret unavailable;
- provider host/path mismatch;
- successful session storage/reuse;
- expired session;
- revoked session;
- deleted session;
- logout/revoke;
- MFA/CAPTCHA/SSO detection -> no bypass;
- logs/checkpoints/observations/screenshots contain no credential/session values;
- crash cleanup.

## Live validation

Use an explicitly authorized first-party/local/provider test account. The production browser path must prove:

```text
delegated identity
-> secret reference resolution
-> governed login
-> authenticated page retrieval
-> session reference persisted
-> second job/session reuse
-> revoke/delete
-> subsequent use denied
```

No real external account should be exercised without explicit provider/deployment authorization for that exact test.

## Exit gate

Authorized test-account live proof, zero-secret-leak assertions, session reuse/revocation proof, exact-head CI and normal merge/tree protocol.

---

# SA16-L17 — OAuth/SSO and resumable human MFA/CAPTCHA checkpoints

## Objective

Complete legitimate interactive authentication and challenge handling without defeating provider security controls.

## OAuth/SSO model

Implement reviewed provider-specific OAuth/SSO flows where the deployment is authorized to use them.

Required controls as applicable:

- approved authorization endpoint/origins;
- approved redirect URIs;
- state/correlation validation;
- nonce/PKCE where the provider protocol requires it;
- bounded redirect count;
- tenant/delegated-identity binding;
- secret/token material stored only through secret/session references;
- cancellation/expiry/revocation;
- audit of authentication state transitions without secret values.

Do not implement a generic "follow any identity provider" browser routine.

## Human checkpoint state machine

Legitimate CAPTCHA, MFA, terms-acceptance or equivalent human/provider-approved challenges become explicit resumable job states.

Required conceptual flow:

```text
RUNNING
-> challenge detected
-> browser/session state persisted securely
-> AWAITING_HUMAN_CHECKPOINT
-> controlled completion/resume operation
-> challenge/session transition verified
-> RUNNING (same governed job/session)
-> COMPLETED or FAILED/CANCELLED
```

## Same-job requirement

The resumed work must preserve:

- original job identity;
- delegated identity;
- source/provider/purpose;
- action-plan progress;
- browser/session reference;
- challenge correlation;
- audit history.

Do not create an unrelated fresh collection job that loses the challenge lineage.

## Worker restart resilience

Checkpoint state must survive worker/process restart. Tests must prove a job can pause, lose the worker, then resume using persisted state/session references without exposing secrets.

## Timeout/cancellation/revocation

Implement explicit behavior for:

- checkpoint expiry;
- user cancellation;
- provider session expiry during pause;
- delegated identity revocation during pause;
- repeated/changed challenge;
- invalid resume token/correlation;
- remote authentication rejection.

## No-bypass invariant

SA-16 never automatically solves CAPTCHA, bypasses MFA, guesses credentials, steals/replays another user's session or rotates accounts to evade provider controls.

The only supported route is legitimate user/provider-approved challenge completion and continuation.

## Tests

Required state-machine tests:

- OAuth state mismatch;
- redirect/origin mismatch;
- successful reviewed OAuth/SSO fixture;
- challenge detected;
- pause state persisted;
- worker restart;
- successful human completion and same-job resume;
- checkpoint timeout;
- cancellation;
- identity/session revoked while waiting;
- no secret material in audit/log/checkpoint payloads.

## Live validation

Use an authorized test identity. The controlled proof must demonstrate at least one legitimate human checkpoint or equivalent approved interactive step and continuation of the same job/session. If the selected provider test route uses OAuth/SSO, exercise that reviewed flow as well.

## Exit gate

Deterministic state-machine/restart tests, authorized interactive live proof, no-bypass evidence, exact-head CI and normal locked merge/tree protocol.

---

# SA16-L18 — Full SA-16 end-to-end proof and final closeout

## Objective

Close SA-16 only after proving the **complete normative capability on the final implementation tree**.

L18 is primarily a validation/audit/closeout lot. It may contain small integration corrections discovered by the final proof, but it should not silently defer a major missing capability to a later SA.

## Step 1 — Re-run the normative audit

Start from the exact final candidate `main` and re-read:

- `SA_15_20_FULL_ACTIVATION_ROADMAP.md` SA-16 section;
- `OSINT_FULL_IMPLEMENTATION_MANDATE.md` web/browser/account requirements;
- `OSINT_AUTOMATION_PIPELINES.md` automatic crawl/browser/extraction requirements;
- delegated-account/challenge requirements applicable from `SOCIAL_COMMUNITY_ACQUISITION_REQUIREMENTS.md`.

Update `SA_16_COMPLETION_AUDIT_AND_REMAINING_LOTS.md` so every row is either:

- **Covered**, with current production-path evidence; or
- explicitly removed from SA-16 scope by a documented product-owner decision.

The following are not acceptable terminal states for an in-scope capability:

- blocked;
- manual;
- planned;
- mock-only;
- adapter-only;
- not live tested;
- missing account/credential/entitlement with no owned prerequisite.

If an external prerequisite is genuinely missing, it remains open work unless the product owner explicitly removes that capability from SA-16 scope.

## Step 2 — Public end-to-end proof

The final public live workflow must exercise one coherent production path on the exact final head:

```text
organization/domain evidence
-> automatic governed target
-> automatic first schedule/job
-> robots policy
-> sitemap/feed/security.txt/seed discovery where present
-> recursive crawl within configured depth/page/byte/time/concurrency/freshness budgets
-> structured L10 surface inventory
-> static HTML/semantic/JSON-LD/OpenGraph/embedded JSON extraction
-> deterministic browser fallback on a rendered page
-> L11 rendered network JSON/script-state extraction
-> governed document acquisition
-> PDF/text/OOXML processing as applicable
-> versions/checkpoints/tombstones where applicable
-> provenance-backed canonical evidence
-> crawl metrics/health
```

The proof must be non-empty, bounded and replay/checkpoint aware.

## Step 3 — Authenticated end-to-end proof

Use an explicitly authorized test identity/account and demonstrate:

```text
CIP tenant/user/service principal
-> L15 delegated provider identity
-> secret/session reference isolation
-> L16 governed login or L17 OAuth/SSO route
-> human checkpoint when the selected legitimate flow requires one
-> same-job resume
-> authorized authenticated navigation/retrieval
-> structured rendered extraction
-> controlled screenshot and/or download where enabled by policy
-> provenance-backed evidence
-> session reuse
-> revoke/delete
-> subsequent access denied
```

The live evidence must prove zero secret leakage in logs, observations, screenshots, checkpoints and artifacts.

## Step 4 — Failure/recovery proof

Exercise representative operational failure paths on the final head:

- browser/process crash cleanup;
- crawl deadline/cancellation;
- retry/replay;
- stale/expired session;
- revoked identity;
- challenge timeout;
- oversized/off-origin resource denial;
- source-policy denial;
- artifact quarantine failure/cleanup.

## Step 5 — Operational/runbook closure

Ensure documentation records:

- how automatic company crawl is enabled/disabled;
- how organization targets are approved;
- browser fallback controls;
- crawl budget tuning;
- telemetry/health fields;
- action-plan enablement;
- artifact retention/quarantine behavior;
- delegated identity/session lifecycle;
- login/OAuth/SSO profile configuration;
- human checkpoint operator/user flow;
- kill switch/revocation;
- troubleshooting and recovery states;
- exact live-test workflows and approved test targets/accounts.

## Step 6 — Final exact-head protocol

The final candidate head must pass:

- complete backend/frontend CI;
- all applicable migrations/reversibility;
- public SA-16 end-to-end live workflow;
- authenticated SA-16 end-to-end live workflow;
- critical coverage targets;
- review/thread audit.

Then:

1. freeze the head;
2. record final head SHA and Git tree;
3. move PR Ready only after validation;
4. merge locked to the exact head SHA;
5. fetch merged commit tree;
6. prove merged Git tree equals validated Git tree;
7. re-read `main`;
8. update SA-16 status to complete only if the normative audit is fully satisfied.

## Final SA-16 completion statement

Only after all L18 conditions are met may the project state:

> SA-16 is complete for its current normative scope: approved company domains can be automatically researched across bounded static and rendered web paths, structured application/page state can be captured with provenance, documents/artifacts can be safely acquired, and explicitly authorized delegated accounts can support governed authentication and legitimate human challenge continuation without developer intervention or security-control bypass.

That statement applies to SA-16 only. SA-17 through SA-20 remain separate source-family/completeness programmes.

---

# Normative traceability matrix

This matrix prevents a required SA-16 capability from disappearing between roadmap and implementation.

## Automatic company crawl

| Normative capability | Owning lot(s) |
|---|---|
| automatic governed target creation after canonical domain resolution | L01 |
| first crawl scheduling without developer-edited YAML | L08 |
| robots policy evaluation | L01-L03 existing path |
| sitemap-index recursion | L03 |
| sitemap traversal | L03 |
| RSS/Atom discovery/traversal | L03 |
| security.txt discovery | L01/L03 existing path |
| homepage/seed discovery | L01 |
| same-origin link extraction | L02 |
| recursive crawl | L02 |
| configurable depth/page/byte budgets | L02 and later preserved |
| whole-crawl time budget | L12 |
| crawl concurrency budget | L12 |
| freshness/recrawl budget | L04/L08 |
| path/origin controls | L01-L09 existing path, preserved in later lots |
| incremental recrawl/change detection | L04 |
| tombstones/version history | L04 |
| provenance | L01-L10 existing path, preserved |
| crawl-health metrics | L12 |
| per-host/target shutdown controls | existing policy + L12/L15-L17 revocation/kill paths |

## Structured extraction

| Normative capability | Owning lot(s) |
|---|---|
| HTML DOM / visible content | L05/L07 existing path |
| semantic HTML metadata | L05 |
| JSON-LD | L05 |
| OpenGraph/public metadata | L05 |
| public embedded JSON application state | L05 |
| authorized structured JSON responses used by rendered applications | L11 |
| script-exposed public structured state | L11 |
| CSS/resource references for technology attribution | L10 |
| approved response headers | L10 |
| canonical links | L10 |
| alternate-language/generic alternate links | L10 |
| public forms/endpoints metadata | L10 |
| public form interaction where authorized | L13 |
| document links | L10 |
| media links | L10 |
| PDF/text/OOXML extraction | pre-L10 existing public-web/document paths |
| rendered structured-state capture | L11 |

## Generalized browser runtime

| Normative capability | Owning lot(s) |
|---|---|
| disposable isolated Chromium process/context | L07 |
| JavaScript rendering | L07 |
| navigation | L07, generalized by L13 |
| typed form interaction | L13 |
| authorized login | L16 |
| OAuth/SSO | L17 |
| human-assisted MFA/CAPTCHA | L17 |
| screenshots | L14 |
| DOM snapshots/capture | L07 |
| structured network/script state | L11 |
| controlled downloads | L14 |
| request interception/host/path allowlists | L07 onward preserved |
| resource/time budgets | L07 + L12 + L13/L14-specific budgets |
| crash cleanup | L07 onward preserved/tested |
| resumable non-auth browser actions | L13 |
| resumable auth/challenge jobs | L17 |
| complete auth-state audit | L15-L17 |

## User-delegated identities/accounts

| Normative capability | Owning lot(s) |
|---|---|
| provider identity bound to CIP tenant/user/service principal | L15 |
| provider account ID | L15 |
| purpose/source authorization scope | L15 |
| isolated secret reference | existing Provider Onboarding + L15 binding |
| isolated session reference | L15 |
| scopes/permissions | L15 |
| creation/renewal timestamps | L15 |
| expiry | L15 |
| revocation | L15/L16 |
| deletion | L15/L16 |
| audit history | L15-L17 |
| provider-approved service/test account compatibility | L15/L16 provider profiles as applicable |
| tenant-controlled aliases where provider permits | L15 lifecycle support; provider-specific implementation when applicable |
| legitimate login/session reuse | L16 |
| OAuth/SSO | L17 |
| MFA/CAPTCHA human checkpoint | L17 |
| same-job resume after challenge | L17 |
| no challenge/access-control bypass | global invariant, verified L16-L18 |

## Live validation and closure

| Normative capability | Owning lot(s) |
|---|---|
| real approved public/neutral sites | L01-L14 component proofs + L18 composite proof |
| organization/domain -> target -> schedule | L01/L08 + L18 |
| recursive static crawl | L02 + L18 |
| browser fallback | L09 + L18 |
| structured page surfaces | L10 + L18 |
| rendered JSON/script state | L11 + L18 |
| document acquisition | existing document paths + L14/L18 |
| provenance-backed evidence | all lots preserve; L18 proves composite chain |
| authenticated authorized test identity | L16/L17 + L18 |
| screenshot/download proof | L14 + L18 |
| session revocation/delete proof | L15-L17 + L18 |
| final exact-head public/auth workflows | L18 |
| every audit row Covered or explicitly product-owner removed | L18 |

---

# How to resume SA-16 work later

When a new development session starts:

1. read the normative SA-16 section in `SA_15_20_FULL_ACTIVATION_ROADMAP.md`;
2. read `SA_16_COMPLETION_AUDIT_AND_REMAINING_LOTS.md`;
3. read this execution roadmap;
4. identify the first lot in the tracking table that is not merged/closed;
5. read all closeouts for prior dependent lots;
6. fetch current `main` and verify it contains the expected prior lot merge;
7. create the next lot branch from that exact `main`;
8. implement only that lot's owned scope while preserving global invariants;
9. follow the lot completion protocol above;
10. update this tracking table/audit only with evidence from the actually merged tree.

Do not skip directly to L18 while a normative row remains Partial/Absent, and do not declare SA-16 complete based only on component CI or historical live proofs.