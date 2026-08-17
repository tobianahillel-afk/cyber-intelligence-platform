# SA-16 — Operational runbook

## Purpose

This runbook is the operational companion to the SA-16 implementation and closeout. It describes how to enable, govern, observe, stop and recover the automatic public-web and delegated authenticated acquisition paths without bypassing Source Governance or provider security controls.

Normative implementation details remain in the SA16-L01 through SA16-L18 documents. This runbook does not grant new collection authority.

## 1. Automatic company crawl lifecycle

### Enable

Automatic public-web execution is deployment/configuration driven. An organization must have a canonical `website_url`, the automatic public-web runtime must be enabled, and the organization must be explicitly included in the configured organization set.

The automatic policy must carry a non-empty authorization reference and review timestamp. The runtime provisions an organization-bound target and central `SourceSchedule`; operators do not create a second scheduler or hand-edit a target merely to force execution.

### Target approval

Before activation verify:

- the canonical organization website is correct;
- approved host is the organization first-party host;
- allowed path prefixes are intentional;
- approved purpose is `corporate-public-footprint`;
- automation is permitted by the source authorization;
- review/expiry timestamps are current;
- page, byte, redirect, depth, deadline and concurrency budgets are bounded.

Do not broaden host/path scope to make a crawl pass.

### Disable / kill switch

Disable the automatic runtime or remove the organization from the approved configured organization set. Source Portfolio/source-governance execution denial remains authoritative at worker claim time. Do not delete historical evidence merely to stop future execution.

If source authority is revoked, workers must observe the current authority before later execution; a previous checkpoint is not permission to continue.

## 2. Crawl discovery and recrawl

The automatic public path may use:

- canonical homepage seed;
- robots rules;
- sitemap and sitemap-index discovery;
- RSS/Atom feeds;
- `/.well-known/security.txt`;
- same-origin HTML links;
- bounded documents.

All discovered URLs remain subject to canonical URL, origin, path, robots, source-policy and global budget checks.

Incremental recrawl uses durable checkpoints and HTTP validators where available. HTTP 304 is a normal not-modified outcome, not a failure. Tombstones/version state must be retained according to the canonical evidence lifecycle rather than overwritten by an empty successful result.

## 3. Static-to-browser fallback

Browser fallback is enabled only when the automatic browser-fallback policy has its own authorization reference/review and target binding.

The fallback is deterministic and static-first. It must not be used as a generic way to evade static-policy denial, robots, origin/path scope or provider controls.

Browser contexts are disposable and sandboxed. Browser fallback may intentionally report effective concurrency `1` even when static crawl concurrency is higher. That value is an explicit safety reduction and should not be “fixed” by parallelizing a shared synchronous Chromium context.

Troubleshooting rule: if static succeeds but rendered content is required, inspect the fallback reason/telemetry and reviewed browser policy. Do not lower the static-text threshold solely to manufacture browser usage in production.

## 4. Crawl budgets and telemetry

Key target budgets include:

- maximum link depth;
- maximum pages;
- maximum total bytes;
- maximum resource bytes;
- maximum redirects;
- whole-crawl deadline;
- configured crawl concurrency.

The public crawl operational metrics namespace is:

`public_web.crawl.v1`

Operationally useful values include attempted/fetched/not-modified/gone/failed pages, bytes, discovered/admitted/denied links, browser fallback count, robots/source-policy denials, redirects, elapsed time, deadline/cancel state and configured/effective/max-observed concurrency.

Metrics are health/operations data, not commercial evidence or a reason to create an opportunity.

### Deadline recovery

On `crawl_deadline_exceeded`, safely completed partial observations/checkpoint state may be persisted while the job remains a failure/retry path. Do not relabel a deadline as success. A later retry resumes from durable state and must not double count the already persisted observation/value event.

## 5. Governed browser action plans

Stateful browser work uses reviewed typed action plans. Allowed transitions bind host, path prefix and HTTP method. Plans are versioned and checkpointed.

Permitted actions are the typed vocabulary implemented by L13/L14. Do not add caller-supplied arbitrary JavaScript or generic remote-browser commands.

Before approving a plan confirm:

- target/source/provider identities match;
- purpose is authorized;
- every transition is explicit and minimal;
- action/value/request/redirect budgets are bounded;
- form submission is genuinely required and approved;
- sensitive/challenge surfaces are not targeted for capture or bypass.

## 6. Screenshots and controlled downloads

Screenshots are limited to reviewed viewport/element scopes. Password/file/OTP/CAPTCHA or explicitly sensitive surfaces fail closed.

Native Chromium downloads remain disabled. A download action must resolve exactly one reviewed link whose canonical href matches the plan's expected download URL. Redirects are reauthorized one hop at a time.

Admitted downloads are limited to safe supported document families and validated through MIME/extension/magic/package rules. Executables, unknown binaries and inconsistent content fail closed.

### Quarantine

Download bytes enter a private temporary quarantine only long enough for bounded parser execution. Quarantine files must be removed on both parser success and failure.

If an operator sees leftover `cip-artifact-*` quarantine files after a run, stop/review the artifact worker path before further activation. Do not treat a stale quarantine file as durable evidence storage.

### Raw retention

Raw screenshot/download retention is opt-in only when the action requests it, source policy and authorization permit it, and a deployment-owned artifact store is injected. PostgreSQL stores artifact metadata/provenance, not raw artifact bytes.

## 7. Delegated identity lifecycle

Authenticated acquisition starts from an L15 delegated identity bound to:

- tenant;
- owner kind/subject (`USER`, service principal or deployment service as supported);
- provider/source;
- purpose;
- scopes;
- expiry/review lifecycle.

A session or secret reference alone never grants execution. Every use must reacquire current execution authority.

### Create/authorize

Register the delegated identity under the correct operator context, authorize it after review, and attach only an approved secret reference. Do not place raw passwords, cookies or OAuth tokens in ordinary database fields, YAML profiles, logs or issue/PR text.

### Revoke

Use the delegated identity/session revoke path. If a reviewed remote logout exists, attempt it, but local revocation and local session-material deletion remain authoritative even if remote logout fails.

### Delete

Delete only through the delegated identity lifecycle so active continuation/session material is invalidated/removed as required while historical audit state is preserved where the model requires it.

A revoked/deleted identity must fail later execution even when an old session/checkpoint reference still exists.

## 8. Username/secret provider login

L16 login requires a reviewed provider-specific profile that defines exact login URL, selectors, authenticated sentinel/probe, optional logout route, transition rules and budgets.

Secrets are resolved just in time from the approved reference. They must not be copied into the profile or persisted after resolution.

Known MFA/CAPTCHA/account-security challenges are hard stops. Do not modify selectors or challenge detection to submit credentials through a provider security prompt.

Session reuse restores isolated session material into a fresh browser context, rechecks current delegated authority and re-probes authenticated state. A stale/invalid session must be treated as unavailable/failed, not as proof of authentication.

## 9. OAuth/OIDC/SSO

Federated authentication requires a reviewed L17 provider profile.

OAuth/OIDC profiles must bind:

- authorization endpoint;
- exact redirect URI;
- client ID;
- token endpoint;
- scopes;
- reviewed GET/POST transition rules;
- review and execution budgets.

OAuth/OIDC uses PKCE S256 and cryptographic state. OIDC additionally requires nonce-aware cryptographic verification through the configured verifier. Never decode an ID token and trust unverified claims.

Token endpoint redirects are denied. A network failure after the token POST is uncertain; do not blindly retry a one-time authorization code.

Browser SSO is profile-bound. Do not follow arbitrary IdPs outside reviewed transitions.

## 10. Human security checkpoints

MFA, CAPTCHA, changed terms, identity checks, provider challenges and unexpected IdP/security transitions are pause-or-deny boundaries.

A human checkpoint:

1. pauses the existing collection job as `AWAITING_HUMAN_CHECKPOINT`;
2. persists non-secret binding/audit state;
3. releases the worker lease;
4. does not consume the normal retry budget;
5. waits for the legitimate human/provider action;
6. revalidates source/job/identity/purpose/correlation and current authority before resume;
7. reclaims the same job after completion.

Never implement CAPTCHA solving, automated MFA completion, credential guessing, stolen-session reuse, account cycling, arbitrary IdP following or provider-control bypass.

Expired, cancelled, invalidated or binding-drifted checkpoints do not resume.

## 11. Recovery and troubleshooting

### Source policy denial

Treat it as authoritative. Verify the reviewed host/path/purpose/method and source state. Do not broaden authorization simply because the operation was desired.

### Browser failure/crash

The disposable context/browser must close through the runtime cleanup path. Retry only through the normal classified job semantics and current authority. Never disable the Chromium sandbox to recover a hosted-runner incompatibility.

### Off-origin / redirect denial

Inspect the requested/final URL and reviewed transition. An unexpected host is not automatically safe because it was reached by redirect or JavaScript.

### Oversized content

Keep page/resource/aggregate byte limits. If a legitimate provider artifact needs a different bound, make an explicit reviewed configuration change with tests; do not disable streaming or size checks.

### Session reuse fails

Check identity status/expiry, source authority, required scopes, session-reference availability and authenticated probe. Re-login only through the reviewed profile when legitimate; never copy a browser session from another account/context.

### OAuth continuation fails

Inspect checkpoint lifecycle/bindings and continuation phase. `token_ready` resumes without reposting the authorization code. A missing/expired/cancelled checkpoint or revoked identity is terminal until the legitimate flow is restarted under current authority.

### Quarantine/parser failure

Confirm temporary bytes are removed, inspect the typed artifact failure and validate MIME/magic/package constraints. Do not persist rejected bytes as a workaround.

## 12. Validation workflows

The normal pull-request CI remains mandatory for dependency audit, Ruff, Mypy, architecture/release contracts, reversible migrations, full pytest/coverage, frontend audit/typecheck/build.

L18 final composite workflows are:

- `.github/workflows/sa16-l18-public-e2e-validation.yml`;
- `.github/workflows/sa16-l18-authenticated-e2e-validation.yml`.

They explicitly check out the pull-request head SHA and use repository-controlled first-party fixtures. The authenticated proof uses a generated ephemeral controlled secret; no real provider credential belongs in the repository.

Before an SA-16 closeout merge:

1. freeze the candidate head;
2. require normal CI + Public E2E + Authenticated E2E success on that exact head;
3. inspect backend test/coverage diagnostics and critical changed-module coverage;
4. audit PR reviews, review threads and conversation comments;
5. mark Ready only after the audit is clean;
6. squash merge with `expected_head_sha` equal to the validated head;
7. verify the squash Git tree exactly equals the validated branch tree;
8. reread `main` before starting the next source-activation lot.

## 13. Provider account creation rule

SA-16 supports delegated ownership, username/secret login and reviewed federated authentication. It does not contain a generic provider signup/alias engine.

Automatic account registration is a conditional provider-specific capability only where the provider explicitly permits it and a reviewed profile/authorization exists. No current SA-16 reviewed provider profile declares that permission. Operators must not reinterpret the absence of a generic signup engine as permission to automate account creation.
