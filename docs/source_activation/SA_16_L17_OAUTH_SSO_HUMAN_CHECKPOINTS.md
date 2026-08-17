# SA-16 L17 — OAuth/SSO and resumable human checkpoints

## Status

`FINAL_EXACT_HEAD_REVALIDATION_PENDING`

Implementation and strengthened security-regression candidate:

- branch: `agent/sa16-l17-oauth-sso-human-checkpoints`
- exact base: merged L16 `main` squash `4c7fc95feaf03d02bf0177de622598b27aca7eb2`
- validated pre-closeout head: `da007dd7c4c2ca17d168409d63f74de0834ad40c`
- validated pre-closeout tree: `104c64adc3d3aa12244a63c39a767cf122b658ac`
- standard CI: run `32025335698` / CI `#2438` — PASS
- controlled L17 OAuth/checkpoint validation: run `32025335500` / L17 Live Validation `#12` — PASS

This closeout document changes the branch head. The results above are therefore candidate evidence only. The exact documentation-complete head containing this file must repeat both the standard repository CI and the L17 controlled OAuth/checkpoint validation before the pull request may leave Draft, be squash-merged, or be used as the base for L18.

## Objective and delivered boundary

L17 extends the delegated identity and authenticated browser/session authority delivered by L15-L16 with legitimate reviewed federated authentication and durable human/provider-security checkpoints.

The implemented OAuth/OIDC path is:

```text
active delegated L15 identity
  -> exact tenant / owner / provider / purpose / scope execution grant
  -> reviewed provider-specific federated-auth profile
  -> PKCE S256 + cryptographic state (+ nonce for OIDC)
  -> secret-backed continuation material
  -> durable checkpoint tied to the existing collection job
  -> job state AWAITING_HUMAN_CHECKPOINT
  -> worker releases its lease
  -> legitimate human/provider approval step
  -> exact callback/profile/source/job/identity binding validation
  -> authorization-code token exchange
  -> replay-safe TOKEN_READY continuation state
  -> durable checkpoint resume
  -> attach governed session reference only after successful resume
  -> same job becomes claimable again without consuming retry budget
  -> authenticated provider access
```

The provider profile domain also models reviewed browser SSO routes. L17 does not implement a generic autonomous IdP crawler and does not follow arbitrary IdP redirects. The controlled executable route selected for L17 live proof is OAuth 2 authorization-code + PKCE, which exercises the federated checkpoint mechanics without depending on a third-party account or IdP.

## Reused authority model

L17 deliberately does not create another identity, account or scheduling authority.

It reuses:

- `DelegatedBrowserIdentity` and the L15 execution-grant lifecycle;
- the L16 governed authenticated-session reference model;
- Source Governance authorization before network execution;
- the existing durable collection-job scheduler and lease model;
- Provider Onboarding reviewed-profile and secret-reference boundaries.

The same `collection_jobs.id` survives the human wait. No second scheduler, shadow job or out-of-band retry engine is introduced.

A resumed operation must reacquire current delegated-identity authority. A checkpoint or stored material reference is never sufficient by itself to authorize provider use.

## Reviewed OAuth/OIDC/SSO profiles

`ProviderFederatedAuthProfile` supports three explicit reviewed flow kinds:

- OAuth 2 authorization-code + PKCE;
- OIDC authorization-code + PKCE;
- browser SSO.

A profile binds at least:

- source/provider identity;
- authorization URL;
- exact redirect URI;
- reviewed host/path/method transition rules;
- review reference and review time;
- request, redirect, timeout and material-TTL budgets;
- client ID, token URL and scopes for OAuth/OIDC;
- optional review expiry.

The domain fails closed for malformed or unreviewed contracts. In particular:

- OAuth/OIDC requires client ID, token URL and at least one scope;
- browser SSO may not smuggle OAuth token/client/scope fields;
- authorization and callback routes must be inside reviewed GET transitions;
- token exchange must be inside a reviewed POST transition;
- non-loopback callback URIs must use HTTPS;
- user-info and fragments are denied in governed URLs;
- profile scopes are unique and bounded;
- execution budgets and review validity are bounded.

## PKCE, state, nonce and callback binding

The authorization preparation service creates cryptographically random continuation material and uses PKCE S256 for OAuth/OIDC.

The callback path validates the exact continuation instead of treating the existence of an authorization code as authority. Security bindings cover the expected profile, source, delegated identity, job and redirect contract.

The callback rejects, among other cases:

- state mismatch;
- wrong or ambiguous callback;
- wrong redirect URI;
- provider OAuth error;
- source/profile/job/identity mismatch;
- duplicate or unusable authorization-code continuation;
- expired material/profile state.

OIDC requires nonce-aware verification through an injected cryptographic `OidcTokenVerifier`. Raw `id_token` bytes are not decoded and trusted as claims by the federated token runtime. If a required verifier is absent or verification fails, execution stops closed.

## Token exchange boundary

The federated token runtime performs an exact governed POST to the reviewed token endpoint.

Its fail-closed behavior includes:

- Source Governance authorization before network;
- redirects denied for token exchange;
- bounded response body;
- unexpected or malformed content rejected;
- token type validated;
- returned scopes may not exceed reviewed scopes;
- opaque access/refresh/ID token values excluded from object representations;
- network failure after a POST is treated as uncertain and is not automatically replayed as though the authorization code were certainly unused.

The unit tests use controlled transports and do not require a third-party OAuth provider.

## Replay-safe continuation state

L17 separates authorization continuation state from the L16 browser-session store.

The federated continuation bundle has two meaningful phases:

```text
authorization_pending
  -> provider consumes authorization code
  -> token_ready
  -> durable checkpoint resume / session handoff
```

This ordering handles the critical crash window where the provider may already have consumed the one-time authorization code but local persistence or transaction completion fails afterwards.

Once token material has been obtained, a retry resumes from the stored `token_ready` continuation instead of reposting the same authorization code. This prevents accidental code reuse and duplicate token exchange.

The session reference is attached to the delegated identity only after the durable human checkpoint successfully resumes. Persisting token-ready material alone therefore does not make the identity executable.

## Dedicated federated material store

Federated continuation material is kept behind an L17-specific secret-material port rather than widening or overwriting the L16 browser-session material contract.

The local implementation uses `file-secret://` references and provides:

- deterministic identity/checkpoint-scoped references;
- configured-root containment;
- path traversal and symlink-escape rejection;
- bounded material size;
- atomic replacement;
- restrictive file permissions;
- safe read/write/delete error translation;
- idempotent deletion of absent material.

Raw PKCE verifier, OAuth state, nonce and returned token material are not stored in ordinary PostgreSQL job/checkpoint columns.

## Durable same-job human checkpoint model

Migration `20260817_0032` adds the durable checkpoint persistence required for restart-safe continuation.

It adds:

- `collection_jobs.human_resume_pending`;
- `collection_human_checkpoints`;
- `collection_human_checkpoint_events`.

A checkpoint persists only governed non-secret control data such as:

- checkpoint/job/source/adapter/delegated-identity identifiers;
- purpose and checkpoint kind;
- lifecycle state;
- correlation digest rather than the raw correlation token;
- optional secret/session reference;
- creation/expiry/completion/cancellation/invalidation times.

The event table retains append-only lifecycle audit metadata such as event type, actor reference, time and bounded reason. It does not contain raw OAuth token material.

The checkpoint repository supports waiting, completion, cancellation, expiry and identity invalidation with explicit conflict/denial behavior.

## Worker pause/resume semantics

A provider or human security challenge is represented by a typed human-checkpoint interrupt rather than by a normal retryable source failure.

When such a checkpoint is raised:

1. the existing collection job becomes `AWAITING_HUMAN_CHECKPOINT`;
2. the checkpoint is persisted;
3. the worker lease is released;
4. ordinary source-health failure accounting is not incremented;
5. the normal retry budget is not consumed.

After legitimate completion, `human_resume_pending` makes that same job claimable again without incrementing its normal attempt counter.

Expired, cancelled, invalidated or binding-drifted checkpoints do not resume ambiguously.

During hardening, the project-wide `autoflush=False` SQLAlchemy configuration exposed an intra-transaction visibility defect for checkpoint transitions. Explicit `flush()` operations were added where the same transaction must immediately query the newly persisted state. This does not force a commit and preserves caller-controlled transaction boundaries.

## Expiry, cancellation and identity revocation

L17 fails closed when continuation authority becomes stale.

Covered lifecycle cases include:

- expired checkpoint;
- cancelled checkpoint;
- invalidated delegated identity;
- missing checkpoint;
- already-completed/non-waiting checkpoint;
- changed job state;
- changed source/adapter/identity/purpose binding;
- invalid actor/correlation/reason metadata;
- concurrent second waiting checkpoint conflicts.

Identity revocation/deletion is re-evaluated before resumed provider use. A revoked identity therefore cannot become executable merely because an OAuth continuation had been started earlier.

Historical lifecycle/audit state may remain, but continuation/session secret material is removed through its secret-material boundary when it is no longer valid for execution.

## Human/provider security boundary

L17 treats MFA, CAPTCHA, provider challenges, changed terms, identity checks and unexpected IdP transitions as stop/resume or deny boundaries.

It does not add:

- CAPTCHA solving or bypass;
- automated MFA completion;
- credential guessing;
- copied/stolen third-party sessions;
- arbitrary IdP following;
- account cycling or multiplication;
- proxy rotation, quota evasion or ban evasion;
- provider-security-control bypass.

A human checkpoint represents an approved pause for the legitimate user/provider action. It is not permission for CIP to defeat the challenge.

## Controlled Chromium OAuth validation

Workflow `.github/workflows/sa16-l17-live-validation.yml` executes the production L17 continuation path with real Playwright/Chromium against a repository-controlled first-party OAuth fixture.

The fixture verifies PKCE and models legitimate human consent without requiring a real third-party provider account or weakening provider controls.

On exact pre-closeout head `da007dd7c4c2ca17d168409d63f74de0834ad40c`, L17 Live Validation run `32025335500` / `#12` passed and reported:

```text
approvals=1
token_posts=1
private_hits=1
same_job_resume=1
retry_attempt_preserved=1
restart_resume=1
pkce_verified=1
revoked_access_denied=1
secret_leaks=0
```

The proof therefore exercises:

```text
reviewed OAuth profile
  -> PKCE authorization start
  -> durable human checkpoint
  -> first DB/worker session closed
  -> Chromium consent
  -> provider callback + token exchange
  -> checkpoint resume in a new DB session
  -> same job re-claimed without retry increment
  -> authenticated private request
  -> identity revoke / later access denied
```

This is a controlled production-path OAuth/checkpoint proof, not a claim that an external third-party provider or identity provider has been activated by L17.

## Deterministic and regression validation

Standard CI run `32025335698` / `#2438` passed on the same exact pre-closeout head.

Backend evidence:

- dependency consistency: PASS;
- installed dependency audit: PASS;
- Ruff: PASS;
- strict Mypy: PASS;
- architecture/release contracts: **36 passed**;
- PostgreSQL migration cycle `upgrade head -> downgrade base -> upgrade head`: PASS through new revision `20260817_0032`;
- full pytest: **2040 passed**, 0 failed, 0 errors, 0 skipped;
- aggregate line coverage: **93.68%**;
- aggregate branch coverage: **78.33%**;
- aggregate line+branch coverage: **90.89%**;
- frontend dependency audit: PASS;
- TypeScript typecheck: PASS;
- Next.js production build: PASS.

Critical new/changed L17 module coverage:

| Module | Lines | Branches | Combined line+branch |
| --- | ---: | ---: | ---: |
| `public_web/federated_checkpoint_flow.py` | **100.00%** | **95.45%** | **99.34%** |
| `public_web/federated_continuation.py` | **100.00%** | **100.00%** | **100.00%** |
| `public_web/federated_token_runtime.py` | **100.00%** | **100.00%** | **100.00%** |
| `collection_orchestration/application/worker.py` | **97.12%** | **90.00%** | **96.49%** |
| `collection_orchestration/domain/human_checkpoints.py` | **100.00%** | **100.00%** | **100.00%** |
| `collection_orchestration/infrastructure/repository_human_checkpoints.py` | **100.00%** | **100.00%** | **100.00%** |
| `provider_onboarding/application/federated_authorization.py` | **99.19%** | **97.73%** | **98.81%** |
| `provider_onboarding/application/federated_material.py` | **100.00%** | n/a | **100.00%** |
| `provider_onboarding/domain/federated_auth.py` | **98.46%** | **96.43%** | **97.85%** |
| `provider_onboarding/infrastructure/local_federated_material.py` | **97.30%** | **100.00%** | **97.62%** |

The coverage hardening explicitly exercised fail-closed and lifecycle branches rather than lowering repository thresholds, adding exclusions, or weakening assertions.

## Defects found during L17 hardening

L17 closeout work found and resolved several classes of defects:

1. early Ruff/Mypy findings in new registry/orchestration code were fixed without ignores;
2. an initial continuation bundle was placed in the wrong architectural layer because it imported an adapter token type from application code; it was deleted and moved to the public-web orchestration side before relying on architecture CI;
3. human-checkpoint persistence needed explicit `flush()` under the repository's `autoflush=False` session policy so same-transaction reads observe pause and terminal transitions correctly;
4. existing worker tests using deliberately tiny fake session objects needed isolation from the new expiry hook already tested independently;
5. persistence metadata tests were updated for the two L17 checkpoint tables;
6. coverage review showed the checkpoint repository below the preferred changed-critical-code target even though aggregate coverage was green, so focused fail-closed tests were added until it reached 100% lines and branches;
7. the final coverage test fixture initially passed retry fields directly to `SourceSchedule`; the test was corrected to use the real `SourceSchedule.retry_policy` contract/defaults. Runtime scheduling behavior was not weakened.

No production security policy, architecture contract, coverage threshold or assertion was disabled to make L17 pass.

## Persistence and migration boundary

L17 database head is `20260817_0032`, revising L16/L15 head `20260816_0031`.

The migration is reversible and preserves the secret-reference boundary:

- PostgreSQL stores durable checkpoint control state and audit events;
- it stores a correlation digest, not the raw correlation token;
- OAuth/PKCE/token continuation bytes remain behind the federated secret-material port;
- session material remains reference-based rather than copied into ordinary job rows.

The complete migration chain passes `upgrade -> downgrade -> upgrade` on the pre-closeout candidate.

## Explicit non-capabilities

L17 does not add:

- provider account registration;
- autonomous discovery/following of arbitrary OAuth or SSO providers;
- dynamic arbitrary IdP redirect trust;
- raw OIDC claim trust without cryptographic verifier injection;
- automated MFA completion;
- CAPTCHA solving or bypass;
- identity-check/account-lockout bypass;
- credential guessing;
- stolen/copied third-party sessions;
- account multiplication or cycling;
- proxy rotation, quota or ban evasion;
- autonomous commercial conclusions or outreach;
- automatic activation of third-party authenticated providers.

## L18 handoff

L18 must start only from the exact merged L17 squash on `main` after final documentation-head validation and post-squash Git-tree equality verification.

L18 is the composite SA-16 end-to-end closeout/proof lot. It must demonstrate the complete source-activation/browser acquisition stack across the relevant public and authenticated paths while preserving all earlier evidence/provenance, governance, budget, safety and human-control boundaries.

L18 must not reopen L17's authentication design unless a regression is discovered. It should compose the already validated L01-L17 capabilities and prove that the aggregate SA-16 system behaves correctly.

## Final exact-head completion rule

Because this closeout file changes the branch head, L17 is not merge-authorized by the pre-closeout results above.

Before PR #156 can leave Draft and be squash-merged:

1. no repository-content change may occur after the final documentation head unless a failing gate requires a corrective commit;
2. the standard repository CI must pass again on that exact head;
3. the dedicated L17 controlled OAuth/checkpoint validation must pass again on that exact head;
4. the final PR audit must show no unresolved blocking review, review thread or conversation comment;
5. the PR may be marked Ready only after those exact-head proofs are green;
6. squash merge must be locked to that exact head SHA;
7. the resulting squash commit's Git tree must equal the validated branch tree;
8. `main` must be reread and verified before L18 is created.

Until those conditions are satisfied, status remains `FINAL_EXACT_HEAD_REVALIDATION_PENDING`.
