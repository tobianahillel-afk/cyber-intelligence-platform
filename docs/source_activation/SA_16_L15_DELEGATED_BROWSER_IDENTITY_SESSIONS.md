# SA-16 L15 — Delegated browser identity and session governance

## Status

`FINAL_EXACT_HEAD_REVALIDATION_PENDING`

SA16-L15 establishes the account/session control plane required before any authenticated provider browsing. It binds delegated browser identities to tenant + owner/principal + provider/source + purpose + scope, stores only secret/session references, enforces expiry/revocation/deletion, and exposes reference-safe operator/audit views. It intentionally does not perform provider login or resolve credential/session values.

Pre-documentation candidate:

`b5f4fe5d2262c7da260263358f5ee0c59add503b`

Candidate Git tree:

`af51259bddcc0b1e77d148b22b77a14dce1fd76b`

Candidate base `main`:

`ff35ccbd9e2d117f893c4386a1911f6f71c660bd`

Candidate evidence:

- CI #2352 / run `31971147356`: **PASS** backend + frontend;
- SA-16 L15 Identity Validation #11 / run `31971147384`: **PASS** on the exact candidate head;
- tests: **1,845 passed, 0 failed, 0 errors**;
- repository combined line/branch coverage: **90.50%**, above the enforced 90% gate;
- `source_governance/application/delegated_identity_contracts.py`: **97.37% combined line/branch**;
- `source_governance/application/delegated_identity_service.py`: **98.46% combined line/branch**;
- `source_governance/domain/delegated_browser_identity.py`: **96.21% combined line/branch**;
- `source_governance/infrastructure/delegated_identity_models.py`: **100.00%**;
- `source_governance/infrastructure/delegated_identity_persistence.py`: **100.00% combined line/branch**;
- Ruff: **PASS**;
- strict Mypy: **PASS**;
- architecture/release contracts: **PASS, 36/36**;
- reversible migration `upgrade head -> downgrade base -> upgrade head`: **PASS**, including `20260816_0031`;
- normal runtime import before Playwright installation: **PASS**;
- dependency consistency and `pip-audit`: **PASS**;
- frontend audit/typecheck/build: **PASS**;
- candidate PR audit: **0 reviews, 0 review threads, 0 conversation comments**.

This documentation commit changes the pull-request head and tree. The evidence above is therefore candidate evidence only. Full CI and the dedicated L15 identity validation must repeat on the documentation head before Ready/merge.

## Reused control-plane foundations

L15 does not create a second provider-account model or a second secret-reference mechanism.

It reuses:

- `SourceAccount` as the provider/account lifecycle nucleus;
- `SourceAccountStatus` for pending, active, expiry/lock/revocation states;
- `SourceAccountAuthMode` for provider authentication mode metadata;
- Provider Onboarding `SecretReference` validation;
- Provider Onboarding `SecretReferenceResolver.is_available()` to verify configured references without reading their values.

Raw credential/session value resolution is deliberately not used by L15. That just-in-time value resolution belongs to L16.

## Delegated identity model

A `DelegatedBrowserIdentity` has one stable identity ID inherited from its `SourceAccount` and binds:

- provider/source ID;
- provider-native account identifier;
- tenant ID;
- owner kind: user, service principal, or deployment service;
- owner subject ID;
- approved purpose;
- approved scopes;
- authorization-document reference;
- account auth mode and status;
- account expiry and last-used metadata;
- authorization/review/renewal/reference-rotation timestamps;
- revocation/deletion timestamps;
- session expiry;
- reference version;
- optional login-secret reference;
- optional session-state reference.

Secret and session fields use `repr=False`. The ordinary domain representation therefore does not expose their values.

## Execution eligibility

Every delegated execution request is evaluated fail-closed against:

- exact tenant;
- exact owner kind and owner subject;
- exact source/provider;
- exact approved purpose;
- required scope subset;
- account active state;
- account expiry;
- authorization-document presence;
- revocation/deletion state;
- explicitly requested secret-reference availability;
- explicitly requested session-reference availability;
- session expiry.

Cross-tenant, cross-owner, cross-provider, cross-purpose and out-of-scope reuse is rejected before an execution grant is issued.

Execution grants implement least privilege: a login-secret or session reference is included only when the caller explicitly requests that reference class. Unrequested references are neither resolved for availability nor returned in the grant.

The execution-grant `repr` reports only `has_secret_reference` / `has_session_reference` booleans, never reference strings.

## Reference lifecycle

References can be attached or rotated only while the delegated identity is ACTIVE and neither revoked nor deleted.

Reference attachment validates the reference syntax and asks the configured `SecretReferenceResolver` only whether it is available. L15 does not call a value resolver and does not read the referenced secret/session material.

Session-reference expiry, when supplied, must be later than the rotation time. Reference version increments on each successful secret/session reference update.

## Lifecycle

The implemented lifecycle is:

`register -> authorize/review -> attach/rotate references -> use -> renew -> revoke -> delete`

Key invariants:

- registration starts from `PENDING_VERIFICATION`;
- authorization transitions the account to ACTIVE and records verification/review time;
- renewal requires a non-revoked/non-deleted identity and a future expiry;
- successful execution records `last_used_at` and a `USED` audit event;
- revocation blocks all future execution grants immediately;
- deletion is terminal, ensures the account is revoked and clears secret/session references plus session-expiry metadata;
- revoked/deleted identities cannot rotate references, renew, or be marked used.

## Persistence

Migration `20260816_0031` adds:

- `delegated_browser_identities`;
- `delegated_browser_identity_audit`.

The identity table stores control-plane metadata and reference strings only. It does not store raw passwords, tokens, cookies, browser storage state, or other resolved secret material.

Identity ownership is uniquely constrained across:

`tenant + owner kind + owner subject + source + purpose + provider-native account identifier`

The audit table stores lifecycle event type, actor identity, tenant, reference version and event timestamp. It does not store secret/session references or resolved values.

## Operator-safe views

Normal get/list views intentionally expose:

- identity/account/provider ownership metadata;
- purpose/scopes;
- lifecycle timestamps;
- status/expiry;
- reference version;
- `has_secret_reference`;
- `has_session_reference`.

They do not expose the actual secret/session reference strings.

Audit views likewise contain event metadata only.

## Controlled integration validation

The dedicated L15 workflow uses the real `LocalSecretReferenceResolver` with two repository-controlled environment references:

- one login-secret reference;
- one browser-session reference.

The controlled proof never reads either value. It verifies only reference availability and the L15 control plane.

The scenario proves:

1. a controlled provider/source record exists;
2. a service-principal-owned delegated identity is registered;
3. review/authorization activates it;
4. existing secret and session references are validated and attached;
5. an exact-scope execution grant can be issued;
6. grant representation does not expose references;
7. a cross-tenant request is rejected;
8. revocation immediately blocks subsequent grants;
9. deletion clears references from the persisted record;
10. the full seven-event lifecycle audit is present;
11. no external provider login occurs;
12. no raw secret or session value is read.

The candidate exact-head L15 Identity Validation #11 is **PASS** on `b5f4fe5d2262c7da260263358f5ee0c59add503b`.

## Security-focused tests

L15 tests cover, among other cases:

- tenant mismatch;
- user/service-principal owner mismatch;
- source/provider mismatch;
- purpose mismatch;
- scope mismatch;
- account expiry;
- session expiry;
- required secret/session reference missing;
- unavailable/invalid reference;
- no resolver call for unrequested references;
- reference attachment before authorization denied;
- stale session-expiry declaration denied;
- cross-owner operator reads denied;
- reference-safe view serialization;
- reference-safe domain/grant representations;
- source record missing at registration;
- duplicate identity registration;
- persistence missing-record handling;
- aware/naive DB timestamp coercion;
- revoke/delete terminal behavior;
- reference removal on deletion;
- audit lifecycle ordering;
- service-principal ownership.

No architecture, coverage, size, nesting, parameter-count, migration or dependency guard was weakened.

## Explicit exclusions

L15 does not add:

- provider login execution;
- username/password form filling;
- raw password/token/cookie/session-state resolution;
- real third-party authenticated browsing;
- OAuth/SSO;
- MFA/TOTP/email/SMS/push completion;
- CAPTCHA solving or bypass;
- account creation, credential guessing or lockout bypass;
- arbitrary JavaScript;
- secret/session values in Postgres, API views, logs, traces or audit rows.

## Continuation reference

The canonical remaining sequence is:

`L16 -> L17 -> L18`

The next lot is **SA16-L16 — Legitimate provider login and session reuse**.

L16 must consume only L15 identities that are active and execution-eligible. It may resolve approved secret/session references just-in-time through the existing secret-value abstraction, create a disposable browser context, restore an approved reusable session or execute a provider-specific approved login plan, verify an authenticated sentinel, return new session state to a secret/session-store adapter, and then perform read-only authenticated collection under the existing browser network/action controls.

L16 must hard-stop on MFA, CAPTCHA, identity-verification challenges, lockout/risk warnings, password reset, terms acceptance requiring human confirmation, or unexpected cross-origin identity-provider redirects. Those human checkpoints belong to L17 and must never be bypassed in L16.

## Completion rule

L15 may be closed only when this documentation head itself repeats:

- full CI;
- dedicated exact-head L15 Identity Validation;
- repository quality and coverage gates;
- critical L15 module combined line/branch coverage >=95%;
- reversible migration validation;
- dependency/security checks;
- review/thread/comment audit;
- Ready transition only after those gates pass;
- locked squash merge against the validated head SHA;
- post-squash Git-tree equality;
- final `main` pointer verification.

Until those gates repeat on the documentation head, this document deliberately remains `FINAL_EXACT_HEAD_REVALIDATION_PENDING`.
