# SA-16 L18 — Composite end-to-end proof and final closeout

## Status

`FINAL_EXACT_HEAD_REVALIDATION_PENDING`

L18 starts from exact merged L17 `main` commit:

- base commit: `e8b0f9a980db336f1566ade8182a4f35d7f9ee00`;
- L17 validated/merged tree: `1a6d4959bc910e40ff50a6a72450ea9a72592c6a`;
- branch: `agent/sa16-l18-composite-e2e-closeout`;
- PR: `#157`.

L18 is the final SA-16 integration/audit lot. It does not redesign the L01-L17 capabilities. It composes them, fixes only integration defects revealed by the composite proof, closes the operational documentation, and requires a fresh exact-head certification before merge.

## Delivered closure

L18 delivers:

1. a refreshed normative SA-16 completion audit with no stale post-L09 `Partial`/`Absent` terminal rows;
2. one coherent controlled public production-path E2E workflow;
3. one coherent controlled authenticated production-path E2E workflow;
4. a canonical evidence bridge for authenticated rendered pages that does not misclassify them as public resources;
5. representative failure/recovery coverage assembled from the already-certified L07/L12/L14/L16/L17 safety paths plus L18 replay/revoke/quarantine assertions;
6. a single SA-16 operational runbook;
7. final exact-head certification rules for CI, both composite workflows, coverage, review audit and locked merge.

## Integration defects found and corrected

### 1. Browser-fallback crawl telemetry was dropped

The common public-web collector already computed the L12 crawl telemetry envelope when browser fallback was used, but `execute_public_web_fallback()` did not carry those metrics into its `AdapterCollectionBatch`.

That meant a fallback crawl could produce L10/L11 evidence while losing the L12 health snapshot in the same worker execution.

L18 fixed this by reusing one shared crawl-metric mapping for the static and fallback execution paths. The fallback path now preserves:

- normal crawl metrics;
- configured/effective concurrency;
- browser fallback count;
- not-modified/gone/failure counters;
- deadline state;
- partial progress metrics when `AdapterPartialExecutionError` is raised.

Focused regression tests cover both the normal metric propagation and the partial-deadline path. No source authority, timeout, coverage threshold or error classification was weakened.

### 2. Authenticated rendered pages lacked a canonical evidence handoff

L16 correctly returned `DelegatedAuthenticatedPage`, but directly feeding that object through the public-page mapper would have falsely classified authenticated content as a fetched `PublicResource` with public access semantics.

L18 deliberately did not weaken the `PublicResource` access invariant.

Instead `delegated_authenticated_evidence.py` creates a canonical internal `RawObservation` with:

- delegated source/provider provenance;
- collection job identity;
- delegated identity in the source record key;
- final authenticated URL;
- SHA-256 of the rendered representation;
- bounded retention/classification metadata;
- no raw HTML payload reference.

It reuses the existing semantic/structured sanitizer and exposes only bounded counts/hashes of allowed extracted text. Token/secret/password/session/cookie-style structured keys are excluded before the evidence summary is produced.

This gives authenticated acquisition canonical provenance without pretending it is public and without persisting raw secret-bearing browser state.

## Public composite E2E

Workflow:

`.github/workflows/sa16-l18-public-e2e-validation.yml`

Controlled fixture:

`scripts/sa16_l18_public_fixture.py`

Runner:

`scripts/sa16_l18_public_e2e.py`

Support:

`scripts/sa16_l18_public_support.py`

The workflow installs the normal project plus the isolated pinned Playwright runtime, configures the repository-owned first-party fixture hostname to loopback and checks out the exact pull-request head SHA.

The production path is:

```text
Organization.website_url
-> build_automatic_public_web_runtime
-> Source Portfolio target registration
-> schedule_due_jobs
-> run_worker_once
-> governed robots
-> sitemap index -> child sitemap
-> RSS feed
-> security.txt
-> recursive same-origin links
-> static acquisition
-> deterministic browser fallback
-> L10 structured web-surface inventory
-> L11 network JSON / XHR + script state
-> document/tombstone projections
-> durable checkpoint
-> public_web.crawl.v1 source-health metrics
-> second scheduled conditional crawl / HTTP 304
-> reviewed browser action plan
-> element screenshot
-> controlled HTTP download
-> quarantine + safe parser
-> artifact metadata/document projection
-> quarantine cleanup
```

The fixture intentionally includes sensitive structured keys such as `accessToken`, `sessionId` and `password`; the proof rejects persistence of those markers in the L11 structured-state records.

It also verifies the distinction between configured static concurrency and browser-safe effective concurrency rather than hiding the serialized fallback behavior.

### Pre-documentation exact-head evidence

Public E2E #14 / run `32035151472` passed on exact implementation head:

`f07a84c54575be5875fe25a1d7de1836f1c7cf18`

The composite reported:

```text
automatic_target=1
automatic_schedule=1
robots=1
sitemap_index=1
feed=1
security_txt=1
recursive=1
surfaces=1
browser_fallback=1
network_json=1
script_state=1
document=1
tombstone=1
checkpoint=1
recrawl_304=1
health=1
screenshot=1
download=1
quarantine_leaks=0
```

This proof is pre-documentation evidence only because the audit/runbook/closeout commits change the branch tree. The finalized documentation head must repeat the same workflow before merge.

## Authenticated composite E2E

Workflow:

`.github/workflows/sa16-l18-authenticated-e2e-validation.yml`

Runner:

`scripts/sa16_l18_authenticated_e2e.py`

The proof reuses the reviewed controlled L16 provider profile and the production L15/L16 identity/session/login services. It uses a generated ephemeral controlled secret and real Chromium; no external provider credential is stored in the repository.

The production path is:

```text
tenant service principal
-> L15 delegated browser identity
-> authorize identity + attach secret reference
-> JIT secret resolution
-> reviewed L16 provider login profile
-> establish_delegated_provider_session
-> real Chromium login
-> authenticated rendered page
-> L18 sanitized authenticated-evidence bridge
-> canonical internal RawObservation persistence
-> no raw authenticated page retained
-> second execution grant
-> reuse_delegated_provider_session
-> authenticated probe + page
-> RawObservation deduplication
-> reviewed remote logout
-> authoritative local revoke + session-material deletion
-> later session reuse denied
-> delegated identity deletion
```

The controlled private page deliberately contains a `sessionToken` and `password` value inside structured JSON. The allowed structured values are extracted/summarized through the existing sanitizer while the secret values and private HTML remain absent from ordinary representations and database payload references.

### Pre-documentation exact-head evidence

Authenticated E2E #3 / run `32035151250` passed on exact implementation head:

`f07a84c54575be5875fe25a1d7de1836f1c7cf18`

The composite reported:

```text
tenant_service_principal=1
delegated_identity=1
secret_reference=1
governed_login=1
rendered_structured=1
raw_observation=1
raw_body_retained=0
session_reuse=1
replay_dedup=1
remote_logout=1
local_revoke=1
revoked_reuse_denied=1
secret_leaks=0
```

This proof is also pre-documentation evidence only. The final documentation head must repeat it.

## Failure and recovery matrix

L18 does not implement a parallel synthetic failure engine. Representative failure/recovery behavior is exercised through the production modules and deterministic suites that normal CI executes, with the previously certified microlot proofs retained as design evidence.

| Required scenario | Production behavior / proof |
|---|---|
| Browser crash/runtime failure | L07 browser/context lifetime uses nested `finally` cleanup; navigation/render/policy failures fail closed rather than returning false evidence. |
| Crawl deadline/cancel | L12 shares one whole-crawl deadline, persists only completed partial work/checkpoint/metrics and returns retryable `crawl_deadline_exceeded` without a success value event. |
| Retry after partial progress | L12 retries from partial state and proves already persisted observations are not double counted. |
| Browser fallback partial deadline | L18 regression test preserves the fallback batch/metrics inside `AdapterPartialExecutionError` instead of dropping progress. |
| Authenticated replay | L18 second authenticated page maps to the same canonical observation identity and persistence deduplicates it. |
| OAuth one-time-code crash/replay | L17 `authorization_pending -> token_ready` continuation resumes from stored token material instead of reposting an uncertain consumed authorization code. |
| Stale/missing session material | L16 session material availability/read/probe guards fail closed; raw session references are not sufficient authority. |
| Revoked identity/session | L16/L18 local revoke removes session material and later reuse is denied; L17 also reauthorizes identity on checkpoint resume. |
| Human checkpoint timeout/expiry/cancel | L17 expired/cancelled/invalidated/non-waiting/binding-drifted checkpoints do not resume. |
| MFA/CAPTCHA/provider challenge | L16 controlled proof stops before credential POST on challenge; L17 pauses for legitimate human/provider action and never solves/bypasses. |
| Oversized/off-origin/invalid acquisition | L02/L07/L12/L14 page/body/aggregate-byte/origin/path/redirect/MIME/magic guards fail closed. |
| Source-policy denial | Static/browser/action/artifact/login/token execution rechecks Source Governance before network/transition authority. |
| Quarantine cleanup | L14 removes private temporary bytes on parser success/failure; L18 Public E2E asserts no leaked `cip-artifact-*` file. |

## Operational closure

The final runbook is:

`docs/source_activation/SA_16_OPERATIONAL_RUNBOOK.md`

It covers:

- automatic crawl enable/disable and target approval;
- browser fallback;
- crawl budgets and `public_web.crawl.v1` telemetry;
- typed browser action plans;
- screenshots/downloads/quarantine/raw retention;
- delegated identity/session create/revoke/delete lifecycle;
- username/secret reviewed login profiles;
- OAuth/OIDC/SSO profile requirements;
- durable human checkpoints;
- kill-switch/revocation behavior;
- deadline, browser, session, OAuth and quarantine recovery;
- exact final validation workflow and controlled-account rules.

## Final audit result

`docs/source_activation/SA_16_COMPLETION_AUDIT_AND_REMAINING_LOTS.md` is updated from the historical post-L09 audit to the final L01-L18 normative matrix.

Every in-scope terminal capability is Covered or explicitly excluded/conditional by the safe product contract. The provider-account auto-registration/alias row is conditional and is not triggered because no current reviewed SA-16 provider profile permits automatic signup. L18 does not fabricate a generic account-creation flow merely to turn that row green.

## Security boundary retained

L18 does not add or claim:

- CAPTCHA solving or bypass;
- automated MFA completion;
- credential guessing;
- copied/stolen third-party sessions;
- arbitrary IdP following;
- account cycling/multiplication;
- proxy rotation, quota evasion or ban evasion;
- arbitrary caller-supplied JavaScript;
- native uncontrolled browser downloads;
- direct commercial conclusions/outreach from provider or crawl results.

Provider/human security controls remain hard stop/resume boundaries. Source Governance remains authoritative before network use. Session/token/secret values stay outside ordinary evidence/log/database paths; references/digests are retained only where required by the governed lifecycle.

## Pre-documentation quality state

Before the documentation batch, CI #2463 / run `32035151269` on `f07a84c54575be5875fe25a1d7de1836f1c7cf18` had passed:

- frontend dependency audit/typecheck/build;
- dependency consistency and Python dependency audit;
- Ruff;
- strict Mypy;
- architecture/release contracts 36/36;
- reversible migration validation.

Its full pytest/coverage step was intentionally superseded/cancelled by the documentation push and is therefore **not** claimed as a completed CI proof.

The documentation-complete head must execute a fresh full CI. No cancelled/superseded test run authorizes merge.

## Final exact-head completion rule

After this closeout/audit/runbook content is committed, no further repository-content change may occur unless a failing gate requires a corrective commit.

PR #157 may leave Draft only after the exact final documentation head has all of the following:

1. standard CI completed successfully, including dependency/security checks, Ruff, Mypy, 36/36 architecture/release contracts, reversible migrations, full pytest/branch-aware coverage and frontend gates;
2. `SA-16 L18 Public E2E Validation` successful on that exact head;
3. `SA-16 L18 Authenticated E2E Validation` successful on that exact head;
4. global branch-aware coverage remains above the enforced repository threshold and the new authenticated-evidence bridge plus changed critical fallback integration meet the project's high-coverage expectation;
5. final PR review audit shows no unresolved blocking review, review thread or conversation comment;
6. final head commit and Git tree are frozen and recorded;
7. PR is marked Ready only after items 1-6;
8. squash merge is executed with `expected_head_sha` equal to the validated head;
9. squash commit Git tree exactly equals the validated branch Git tree;
10. `main` is reread and confirmed at the squash before SA-17 begins.

Only after these gates are completed is SA-16 closed.
