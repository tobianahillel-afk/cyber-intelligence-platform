# SA-16 L16 — Authorized provider login and governed session reuse

## Status

`FINAL_EXACT_HEAD_REVALIDATION_PENDING`

Implementation and strengthened security-regression candidate:

- branch: `agent/sa16-l16-authorized-login-session-reuse`
- exact base: merged L15 `main` squash `6da53c58a92878ce3a6915b47e0d0db696633945`
- validated pre-closeout head: `57fe0270e2fac89ff2cfe12eb8962f5f9dc56c13`
- validated pre-closeout tree: `4edda6665d047775be571c9703c0a6652de8c78e`
- standard CI: run `32014187501` / CI `#2401` — PASS
- controlled L16 browser validation: run `32014187662` / L16 Live Validation `#28` — PASS

This closeout document changes the branch head. The results above are therefore candidate evidence only. The exact documentation-complete head containing this file must repeat both the standard repository CI and the L16 controlled browser validation before the pull request may leave Draft, be squash-merged, or be used as the base for L17.

## Objective and delivered boundary

L16 consumes the delegated browser identity and secret/session-reference control plane delivered by L15 and adds legitimate reviewed username/secret provider login plus governed browser-session reuse.

The implemented path is:

```text
active delegated L15 identity
  -> exact tenant / owner / provider / purpose / scope execution grant
  -> JIT resolution of the approved secret reference
  -> reviewed provider-specific login profile
  -> isolated Playwright/Chromium browser context
  -> governed login navigation and form submission
  -> authenticated success sentinel / probe verification
  -> sanitized browser storage state
  -> L15-compatible session-material reference
  -> later exact-context session reuse
  -> read-only authenticated page access
  -> remote logout when supported
  -> local revocation and material deletion
```

L16 does not implement OAuth, SSO, human MFA/CAPTCHA continuation, provider account creation, identity-verification workflows, or challenge bypass. Those continuation flows belong to L17.

## Reused L15 authority model

L16 deliberately does not introduce another account, identity, credential or authorization plane.

Execution reuses:

- `DelegatedBrowserIdentity` and its tenant/owner/provider/purpose/scope lifecycle;
- L15 execution grants and reference-minimization rules;
- Provider Onboarding `SecretReference` contracts;
- Source Governance policy and authorization evaluation;
- the isolated public-web browser runtime boundary.

The login executor rejects a source/profile mismatch. The delegated session service requires `INTERACTIVE_SESSION` authentication mode and exact source identity before secret resolution or browser execution.

## Reviewed provider login profiles

Provider login mechanics are represented as explicit reviewed profiles rather than arbitrary browser scripts.

A profile binds at least:

- source/provider identity;
- exact login URL;
- username selector;
- password/secret selector;
- submit selector;
- authenticated success selector;
- authenticated probe URL;
- optional logout URL;
- approved host/path transitions and HTTP methods;
- known challenge signals;
- request, redirect, timeout and session-TTL budgets;
- review reference, review time and optional expiry.

Registry parsing is strict and fails closed for malformed types, duplicate profile IDs, invalid URLs, invalid methods, malformed review timestamps, impossible budgets or expired review state.

The runtime never accepts arbitrary JavaScript from a profile.

## Policy before network and per-request authority

The browser login runtime does not treat a successful first navigation as authority for later requests.

Every relevant request/transition remains constrained by:

- reviewed login-profile transitions;
- Source Governance host/path/purpose/method authorization;
- request and redirect budgets;
- browser resource controls;
- typed fail-closed network-denial state.

Navigation failures and submission failures are mapped to typed runtime errors. A policy denial takes precedence over a lower-level browser exception so unsafe navigation cannot be misreported as an ordinary transport failure.

## Secret handling

The provider secret is resolved only when the governed login operation reaches the credential-entry step.

The secret value is not persisted in:

- delegated identity records;
- Source Governance records;
- login profiles;
- RawObservation or Evidence records;
- checkpoints;
- screenshots;
- browser telemetry;
- logs or exception messages;
- pull-request or live-validation artifacts.

Only the secret reference is retained by the L15 control plane. Resolution failure is typed and stops execution before authentication is attempted.

## Governed browser-session material

L16 adds a local session-material implementation behind the session-material port. It maps L15 `file-secret://` references into a configured secret-material root instead of storing raw session state in ordinary PostgreSQL records.

Safety properties include:

- deterministic reference generation per delegated identity;
- configured-root containment and symlink-escape rejection;
- bounded session-material size;
- empty/oversized/unavailable material rejection;
- atomic temporary-file write followed by replacement;
- restrictive `0600` material permissions;
- temporary-file cleanup on failed writes;
- typed filesystem read/write/delete failures;
- idempotent delete of already-absent material.

A successful login writes the sanitized browser storage state first and then attaches the session reference to the delegated identity. If persistence of that reference fails, the newly written material is deleted rather than left orphaned.

## Session reuse and revocation

A reusable session requires a fresh L15 execution grant for the same exact tenant, delegated owner, source, purpose and scopes. A stored session reference alone is not execution authority.

Reuse restores the session into a new isolated browser context, verifies the authenticated probe/sentinel again, and refreshes the stored session material.

Revocation behavior is intentionally fail-safe:

- remote provider logout is attempted when a reviewed logout route exists and usable session material is available;
- remote logout failure does not preserve CIP access;
- local delegated-identity revocation always proceeds;
- local session material is deleted;
- subsequent execution-grant/session reuse is denied.

This gives local revocation immediate effect without pretending that a remote provider session was destroyed when the provider logout path failed.

## Challenge boundary

Known MFA/CAPTCHA/challenge signals are checked before credential submission and again at the relevant post-authentication/probe stages.

Challenge detection causes a typed hard stop. L16 does not:

- solve or bypass CAPTCHA;
- automate MFA completion;
- continue through OAuth or SSO;
- guess credentials;
- rotate identities/accounts to evade provider controls;
- bypass terms, account-security or identity-verification prompts.

L17 owns resumable human/provider-approved challenge continuation and OAuth/SSO flows.

## Controlled Chromium validation

Workflow `.github/workflows/sa16-l16-live-validation.yml` executes the production L16 login/session path with real Playwright/Chromium against a repository-controlled first-party HTTP provider fixture. The fixture is intentionally controlled so no third-party account, secret, prospect target or provider terms are required merely to prove the browser/authentication mechanics.

On exact pre-closeout head `57fe0270e2fac89ff2cfe12eb8962f5f9dc56c13`, L16 Live Validation run `32014187662` / `#28` passed and reported:

```text
login_submissions=1
private_hits=3
logout_hits=1
session_reuse=1
local_revoke=1
remote_logout=1
revoked_reuse_denied=1
mfa_hard_stop=1
mfa_post_attempts=0
```

The proof therefore exercises:

```text
delegated identity
  -> secret-reference resolution
  -> governed login
  -> authenticated page
  -> session-reference persistence
  -> second-job session reuse
  -> remote logout + local revoke
  -> later reuse denied
```

It also proves that an MFA signal causes a hard stop before credential submission in the challenge scenario (`mfa_post_attempts=0`).

This is a controlled production-path browser proof, not a claim that an external third-party provider has been activated by L16.

## Deterministic and regression validation

Standard CI run `32014187501` / `#2401` passed on the same exact pre-closeout head.

Backend evidence:

- dependency consistency: PASS;
- installed dependency audit: PASS, no known vulnerabilities;
- Ruff: PASS;
- strict Mypy: PASS across **771 source files**;
- architecture/release contracts: **36 passed**;
- PostgreSQL migration cycle `upgrade head -> downgrade base -> upgrade head`: PASS through existing revision `20260816_0031`;
- L16 adds no database migration and reuses L15 persistence/reference contracts;
- full pytest: **1905 passed**, 0 failed;
- aggregate line+branch coverage: **90.66%**;
- frontend dependency audit: PASS;
- TypeScript typecheck: PASS;
- Next.js production build: PASS.

Critical L16 module coverage after the strengthened security-edge tests:

| Module | Line+branch coverage |
| --- | ---: |
| `public_web/delegated_login_executor.py` | **100.00%** |
| `public_web/delegated_login_orchestrator.py` | **100.00%** |
| `public_web/delegated_login_runtime.py` | **99.10%** |
| `public_web/delegated_session_state.py` | **100.00%** |
| `provider_onboarding/domain/browser_login.py` | **97.71%** |
| `provider_onboarding/infrastructure/browser_login_registry.py` | **98.33%** |
| `source_governance/application/delegated_provider_session_service.py` | **100.00%** |
| `source_governance/application/provider_session_runtime.py` | **100.00%** |
| `source_governance/application/session_material.py` | **100.00%** |
| `source_governance/infrastructure/local_session_material.py` | **97.59%** |

The additional coverage work explicitly tests security/error branches rather than weakening the global threshold or excluding business logic.

## Defects found during closeout hardening

The first L16 full-suite candidate exposed three test-harness defects rather than production-policy defects:

1. two fake Playwright pages did not model the reviewed submit selector and therefore correctly triggered the production fail-closed selector guard;
2. one YAML edge test used a string replacement broad enough to corrupt `source_id` while intending to invalidate only the profile `id`.

The fixes were confined to tests. No production policy, architecture rule, assertion, lint rule or coverage threshold was weakened.

Coverage review then showed several new L16 security modules below the repository's preferred 95% changed-critical-code target even though aggregate coverage exceeded 90%. Additional deterministic tests were added for browser error translation, policy-denial precedence, login-registry validation, atomic session-material filesystem failures, symlink escape, orphan cleanup, remote-logout failure and delegated-session context guards. The resulting critical modules all exceed 95% line+branch coverage.

## Persistence and migration boundary

L16 introduces no SQL table and no Alembic revision.

L15 revision `20260816_0031` remains the database head. Raw browser session material remains outside ordinary database persistence behind the session-material port; PostgreSQL retains only the governed delegated identity/session reference and audit state established by L15.

The complete migration chain still passes `upgrade -> downgrade -> upgrade` on the L16 candidate.

## Explicit non-capabilities

L16 does not add:

- provider account registration;
- OAuth authorization-code flows;
- SSO/IdP flows;
- PKCE/state/nonce continuation;
- automated MFA completion;
- CAPTCHA solving or bypass;
- identity-check or account-lockout bypass;
- arbitrary browser scripting supplied by users/providers;
- stolen/copied third-party sessions;
- credential guessing;
- account multiplication, proxy rotation or ban/quota evasion;
- autonomous commercial conclusions or outreach;
- automatic activation of any third-party authenticated provider.

## L17 handoff

L17 must start only from the exact merged L16 squash on `main` after final documentation-head validation and post-squash Git-tree equality verification.

L17 owns:

- legitimate provider OAuth flows;
- SSO/IdP transitions under reviewed provider-specific contracts;
- state/correlation and nonce/PKCE where applicable;
- provider/human MFA and CAPTCHA checkpoints;
- persisted safe `AWAITING_HUMAN_CHECKPOINT`-style state;
- same-job resume after the approved human/provider action;
- challenge expiry/cancellation/revocation handling;
- no bypass or automated solving.

L18 remains the composite SA-16 end-to-end proof and closeout lot.

## Final exact-head completion rule

Because this closeout file changes the branch head, L16 is not merge-authorized by the pre-closeout results above.

Before PR #154 can leave Draft and be squash-merged:

1. no repository-content change may occur after the final documentation head unless a failing gate requires a corrective commit;
2. the standard repository CI must pass again on that exact head;
3. the dedicated L16 controlled Chromium validation must pass again on that exact head;
4. the final PR audit must show no unresolved blocking review, review thread or conversation comment;
5. the PR may be marked Ready only after those exact-head proofs are green;
6. squash merge must be locked to that exact head SHA;
7. the resulting squash commit's Git tree must equal the validated branch tree;
8. `main` must be reread and verified before L17 is created.

Until those conditions are satisfied, status remains `FINAL_EXACT_HEAD_REVALIDATION_PENDING`.
