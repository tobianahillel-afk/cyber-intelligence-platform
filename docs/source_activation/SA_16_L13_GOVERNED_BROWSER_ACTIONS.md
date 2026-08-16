# SA-16 L13 — Governed public browser action plans and forms

## Status

`FINAL_EXACT_HEAD_REVALIDATION_PENDING`

SA16-L13 closes the public-browser interaction gap identified by the SA-16 completion audit and execution roadmap. It adds immutable typed browser action plans, explicit host/path/method authorization, fail-closed form inspection, durable resumability, and safe handling of ambiguous non-idempotent effects without widening the source authority established by L01-L12.

Pre-documentation candidate:

`5eaad630729512fbcefd3752ebae85337e9b3464`

Candidate Git tree:

`8e29f5fc36f1f1e487be06c241ef6b63ebe6cb99`

Candidate base `main`:

`7dcce4d3026b72878c612bc72dfeb5fc30b997b0`

Candidate evidence:

- CI #2283 / run `31961368202`: **PASS** against the pull-request integration ref built from the unchanged L12 `main` base and candidate head;
- SA-16 L13 Live Validation #16 / run `31961368182`: **PASS** on the exact candidate pull-request head;
- tests: **1,749 passed, 0 failed, 0 errors**;
- repository combined line/branch coverage: **90.26%**, above the enforced 90% gate;
- `public_web/browser_action_authorization.py`: **100.00%**;
- `public_web/browser_action_executor.py`: **98.70%**;
- `public_web/browser_action_steps.py`: **98.97%**;
- `public_footprint/domain/browser_actions.py`: **99.16%**;
- `public_footprint/infrastructure/browser_action_models.py`: **100.00%**;
- `public_footprint/infrastructure/browser_action_persistence.py`: **98.77%**;
- source-governance domain models: **100.00%**;
- source-governance persistence: **100.00%**;
- Ruff: **PASS**;
- strict Mypy: **PASS, 744 source files**;
- architecture/release contracts: **PASS, 36/36**;
- reversible migrations `upgrade head -> downgrade base -> upgrade head`: **PASS** including `20260816_0028` and `20260816_0029`;
- normal runtime import before Playwright installation: **PASS**;
- dependency consistency and `pip-audit`: **PASS, no known vulnerabilities**;
- frontend audit, typecheck and production build: **PASS**;
- PR review audit before documentation: **0 reviews, 0 review threads**.

The closeout itself changes the pull-request tree. The evidence above is therefore candidate evidence only. Complete CI and the dedicated L13 live workflow must repeat after this documentation commit before the PR may be marked Ready or merged.

## Capability

L13 introduces reviewed, typed public-browser actions only. The plan vocabulary is intentionally closed and versioned:

- navigation to an authorized public URL;
- click of an explicitly selected public control;
- fill of an explicitly selected public non-secret field;
- select of a public value;
- check/uncheck of an allowed control;
- governed `submit_form`;
- bounded navigation and DOM waits.

There is no generic browser-command API and no caller-supplied JavaScript execution surface. Browser action plans are data, not executable scripts.

## Public-only values and actions

L13 remains an unauthenticated public-web capability.

Fill/select values must be classified as `PUBLIC_NON_SECRET`. The runtime does not introduce credential, token, password, delegated-session or secret injection.

DOM inspection fails closed for sensitive form controls. In particular:

- password fields are denied;
- file inputs are denied;
- hidden/sensitive fill targets are denied;
- form submission does not grant authority merely because a control exists in the DOM;
- selectors used for actions must resolve according to the typed-action safety contract rather than permitting arbitrary broad interaction.

Authentication and delegated browser identities remain future lots, not L13 behavior.

## Host, path and HTTP-method governance

L13 extends the existing source authorization model with explicit approved HTTP methods rather than creating browser-specific authority.

Migration `20260816_0028` adds persisted approved HTTP methods. Existing source configurations retain conservative historical compatibility through `GET` as the default. A public-browser `POST` requires explicit method authorization in addition to the existing source host/path/purpose rules.

For every governed transition, authorization combines:

- the selected source/target identity;
- target public-web scope;
- the action plan's transition allowlist;
- source-approved host;
- source-approved path prefix;
- source-approved purpose;
- source-approved HTTP method.

The DOM is never treated as an authorization source.

Unsupported browser request methods fail closed in the Playwright route guard: the request is aborted and recorded as a denial instead of allowing an exception to escape the route callback.

## Immutable plans and durable checkpoints

Migration `20260816_0029` adds:

- `browser_action_plans`;
- `browser_action_checkpoints`.

A plan is persisted as a canonical versioned payload with an integrity hash. Re-persisting the same `(plan_id, version)` with different content is rejected rather than mutating the approved plan in place.

Execution progress is stored separately in a typed checkpoint. Checkpoint state is constrained to valid execution order so impossible multi-active or contradictory states fail closed before execution.

## Replay and crash semantics

L13 explicitly models replay safety for every step.

A `POST` form submission cannot be declared blindly replay-safe. If execution is interrupted while a non-idempotent or otherwise ambiguous step is `EXECUTING`, recovery moves the step to `NEEDS_VERIFICATION` and stops automatic continuation.

Safe interrupted steps may be returned to `PENDING` where their declared replay policy permits it.

The key invariant is:

> an ambiguous completed-or-not-completed POST is never automatically submitted a second time merely because CIP crashed before persisting `COMPLETED`.

The live fixture counts requests and proves that recovery after the deliberately interrupted POST does not emit a second submission.

## Pre-action DOM and form inspection

Typed actions are inspected before execution.

For form submission the runtime verifies, before clicking the submit control:

- the selector resolves to a form;
- the form method is one of the supported typed methods;
- the actual form action resolves canonically;
- the actual action and method match the plan's expected metadata;
- the resulting destination is authorized by the plan and source governance;
- sensitive password/file fields are absent;
- the submit control is available under the bounded typed-action rules.

The expected metadata is therefore not inferred from a potentially changing DOM after the fact.

## Network interception and submission guard

Every browser request passes through Playwright request interception.

The route guard:

- counts requests against a bounded request budget;
- blocks selected non-essential resource types;
- canonicalizes and re-authorizes destination host/path/method;
- rejects unsupported HTTP methods;
- enforces the plan transition allowlist;
- enforces source authorization;
- aborts denied requests fail closed.

A temporary submission guard is installed around typed form submission. A navigation caused by that submission must still match the exact expected canonical destination and method, preventing a late DOM mutation from redirecting an otherwise approved form to a different route.

## Browser isolation posture

L13 uses the existing isolated Playwright posture rather than weakening it.

The action executor creates a disposable browser context with, among other existing controls:

- `accept_downloads=False`;
- `bypass_csp=False`;
- `ignore_https_errors=False`;
- service workers blocked;
- bounded typed actions only;
- network request interception.

The standard application runtime is still verified to import successfully before Playwright bindings are installed. Browser capability therefore remains an isolated optional execution path rather than an unconditional dependency of normal collection workers.

## Deterministic tests

L13 includes deterministic tests for the security and recovery boundaries, including:

- action-plan identity, version and budget validation;
- transition allowlist validation;
- public-only value rules;
- GET versus POST replay-policy constraints;
- checkpoint ordering and interrupted-step recovery;
- plan immutability and canonical persistence;
- malformed persisted payload rejection;
- source/target identity mismatches;
- target scope and plan-transition denials;
- unsupported network methods;
- request-budget denial;
- unique selector requirements;
- click denial for implicit form-submit controls;
- password/file/hidden-field rejection;
- form shape/action/method inspection;
- submission-guard matching;
- crash/recovery without blind POST replay.

The edge-test pass also exposed and closed a fail-closed route-callback issue: unsupported browser methods are now converted into explicit aborted denials inside the route guard.

No coverage, source-file-size, function-complexity, nesting or architecture threshold was weakened. An earlier oversized/deep executor implementation was instead decomposed into dedicated authorization, orchestration and DOM/form-step responsibilities until the existing architecture contracts passed.

## Live validation

The dedicated L13 workflow executes real Chromium against a controlled first-party fixture rather than relying on a third-party website.

The runner maps a reviewed fixture hostname to loopback and installs the isolated Chromium runtime. The production L13 execution path then proves:

1. a governed public GET action plan can navigate/interact within approved scope and produce final page evidence;
2. an explicitly authorized public POST form can be submitted through the typed form path;
3. the POST effect is observed by the fixture;
4. execution is deliberately interrupted in the ambiguous window after the effect but before durable completion;
5. checkpoint recovery moves the ambiguous step to verification-required state;
6. automatic continuation is blocked;
7. the fixture confirms that no second POST was emitted.

The candidate live workflow result is **PASS** on `5eaad630729512fbcefd3752ebae85337e9b3464`.

## Explicit exclusions

L13 does not add:

- arbitrary JavaScript evaluation or caller-supplied scripts;
- a generic browser-command endpoint;
- credentials, login or delegated browser identity;
- OAuth/SSO flows;
- MFA/CAPTCHA/terms bypass or automated resolution;
- password or secret-field handling;
- file upload;
- screenshots;
- controlled downloads;
- browser-session reuse across identities;
- any weakening of source host/path/purpose/method governance.

Screenshots and governed downloads belong to L14. Delegated browser identity/session governance belongs to L15. Provider login/session reuse belongs to L16, and OAuth/SSO with explicit human checkpoints belongs to L17.

## Continuation reference

The canonical remaining implementation plan is:

- `docs/source_activation/SA_16_EXECUTION_ROADMAP_L10_L18.md`.

The status/gap matrix remains:

- `docs/source_activation/SA_16_COMPLETION_AUDIT_AND_REMAINING_LOTS.md`.

After L13 is exact-head validated and merged, the next mandatory implementation lot is **SA16-L14 — Governed screenshots and controlled downloads**.

A future implementation session must re-read the normative SA-16 documents, the execution roadmap, this L13 closeout and the current merged `main` before starting L14.

L14 must build on the existing L12 deadline/budget controls and L13 browser authorization/action boundaries. It must not introduce unrestricted download behavior, secret handling or authentication features reserved for later lots.

## Completion rule

L13 may be closed only when the documentation head itself repeats:

- complete CI;
- dedicated exact-head L13 real-Chromium live validation;
- repository quality and coverage gates;
- critical L13 module coverage at or above the project's high-coverage target;
- ambiguous-POST recovery proof;
- dependency/security checks;
- reversible migration validation;
- review/thread audit;
- Ready transition only after those gates pass;
- locked squash merge against the validated head SHA;
- post-squash Git-tree equality;
- final `main` pointer verification.

Until those gates repeat on the documentation head, this document deliberately remains `FINAL_EXACT_HEAD_REVALIDATION_PENDING`.
