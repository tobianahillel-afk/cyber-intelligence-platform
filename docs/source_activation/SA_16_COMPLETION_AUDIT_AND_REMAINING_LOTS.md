# SA-16 — Final normative completion audit

## Status

`IMPLEMENTATION_COVERED_FINAL_HEAD_CERTIFICATION_PENDING`

Audit baseline:

- repository: `tobianahillel-afk/cyber-intelligence-platform`;
- SA16-L18 base: merged L17 `main` squash `e8b0f9a980db336f1566ade8182a4f35d7f9ee00`;
- implementation increments: SA16-L01 through SA16-L18;
- normative execution scope: `docs/source_activation/SA_16_EXECUTION_ROADMAP_L10_L18.md` plus the higher-precedence source-activation rules it references.

This document replaces the historical post-L09 audit. It does not weaken the normative roadmap. A row is **Covered** only when the production path materially implements the requirement. A conditional row is not treated as implemented when its provider precondition is absent.

## Executive conclusion

The SA-16 implementation now provides the complete governed company-web/browser/authentication acquisition layer intended by the roadmap:

```text
organization/domain
-> automatic governed target and schedule
-> static public crawl/discovery
-> incremental recrawl/versioning/checkpoints
-> semantic + structured public extraction
-> bounded Chromium fallback
-> rendered network/script-state extraction
-> crawl deadline/concurrency/health telemetry
-> reviewed browser actions
-> screenshots/downloads/quarantine
-> delegated identities/session references
-> reviewed username/secret login and session reuse
-> reviewed OAuth/OIDC/SSO contracts
-> durable same-job human checkpoints
-> canonical provenance/evidence
-> revoke/delete denial
```

L18 additionally composes these primitives through exact-head controlled public and authenticated production-path workflows. No SA-16 terminal requirement remains deferred as a planned or mock-only capability.

The only conditional product requirement is provider-approved automatic account registration/alias provisioning. No reviewed SA-16 provider profile permits that action. CIP therefore does not invent a generic signup flow. If a future provider explicitly permits automatic registration, that provider-specific capability requires its own reviewed profile and authorization before execution.

## A. Automatic public company acquisition

| Normative capability | Final status | Production evidence |
|---|---|---|
| Canonical organization domain -> governed crawl target | **Covered** | L01 provisions organization-bound `PublicWebTarget` and governed source authority. |
| First automatic schedule/job without developer-edited target YAML | **Covered** | L08 runtime composition plus L18 `schedule_due_jobs()` proof. |
| robots policy | **Covered** | Governed robots acquisition/evaluation precedes crawl acquisition. |
| Sitemap discovery and sitemap-index recursion | **Covered** | L03 bounded recursive sitemap traversal; L18 controlled sitemap-index proof. |
| RSS/Atom discovery and traversal | **Covered** | L03 feed discovery/parsing; L18 RSS proof. |
| `security.txt` discovery | **Covered** | Dedicated parser/mapping; L18 valid `Contact:` fixture path. |
| Homepage/seed discovery | **Covered** | Canonical homepage automatically seeded. |
| Recursive same-origin link discovery | **Covered** | L02 bounded canonical same-origin recursive frontier. |
| Depth/page/resource/total-byte/redirect budgets | **Covered** | L02/L03/L07 controls remain authoritative for static and browser paths. |
| Whole-crawl deadline | **Covered** | L12 shared monotonic deadline, streaming checks and typed deadline failure. |
| Crawl concurrency budget | **Covered** | L12 deterministic bounded concurrency with synchronized global budgets; browser fallback explicitly reports safe effective concurrency `1`. |
| Freshness/recrawl interval | **Covered** | Automatic schedule refresh interval and checkpoint-driven incremental recrawl. |
| Path/origin/source-policy enforcement | **Covered** | Re-evaluated before static/browser/action/download network execution. |
| Conditional recrawl / HTTP 304 | **Covered** | L04 validators/checkpoints; L18 performs a real second scheduled 304 crawl. |
| Tombstones and version history | **Covered** | Gone/missing resources map to durable tombstone/version state; L18 verifies a 410 tombstone. |
| Canonical provenance | **Covered** | Organization/source/adapter/job/URL/source-locator provenance is retained through canonical projections/observations. |
| Crawl-health telemetry | **Covered** | L12 `public_web.crawl.v1` metrics persist through Source Portfolio; L18 verifies fallback, concurrency and 304 health values. |

## B. Structured and document extraction

| Normative capability | Final status | Production evidence |
|---|---|---|
| Bounded visible/semantic HTML | **Covered** | L05 semantic extraction and canonical public resource/version path. |
| JSON-LD | **Covered** | L05 bounded structured extraction with sensitive-key filtering. |
| OpenGraph/Twitter/public metadata | **Covered** | L05 metadata extraction; L18 fixture exercises OpenGraph. |
| Embedded public JSON | **Covered** | L05 bounded `application/json` extraction and allowlisted scalar projection. |
| Response headers | **Covered** | L10 bounded response-header surface inventory. |
| Canonical/alternate links | **Covered** | L10 typed link surfaces. |
| CSS/script/resource references | **Covered** | L10 stylesheet/script/resource-reference surfaces; L18 exercises a manifest resource. |
| Public form endpoints | **Covered** | L10 typed form endpoint/method surface inventory. |
| Document links | **Covered** | L10 typed document-link surface plus governed document acquisition. |
| Media links | **Covered** | L10 typed media-link inventory without widening browser media fetch authority. |
| Rendered same-origin JSON/XHR state | **Covered** | L11 network JSON capture under browser request governance; L18 exercises fetch + XHR. |
| Rendered script-exposed state | **Covered** | L11 bounded script-state capture with sensitive-key filtering; L18 exercises `window.__INITIAL_STATE__`. |
| PDF/text extraction | **Covered** | Existing bounded public-document extraction reused by crawl/download paths. |
| DOCX/XLSX/PPTX extraction | **Covered** | L06 bounded OOXML parsing with package/path/macro/encryption/expansion guards. |
| Sensitive structured-key suppression | **Covered** | L05/L11 sanitizers remove token/secret/password/session/cookie-style values before evidence; L18 auth bridge reuses this boundary. |

## C. Generalized governed browser runtime

| Normative capability | Final status | Production evidence |
|---|---|---|
| Sandboxed disposable Chromium context | **Covered** | L07 sandboxed headless Chromium; context/browser cleanup in `finally`. |
| JavaScript rendering and DOM capture | **Covered** | L07 rendered HTML returned through existing collector contract. |
| Static -> browser fallback | **Covered** | L09 deterministic fallback policy; L18 proves one fallback in the same automatic crawl. |
| Request interception / host/path allowlists | **Covered** | L07/L09 per-request origin/scope/source-policy checks. |
| Browser request/time/redirect/body budgets | **Covered** | L07 plus L12 whole-crawl budget. |
| Reviewed navigation/click/type/select/check/wait/form submit | **Covered** | L13 typed browser action plans with transition/method/purpose limits. |
| Arbitrary caller-supplied JavaScript | **Excluded by design** | SA-16 explicitly uses typed reviewed actions; arbitrary JS is not a required safe capability. |
| Screenshots | **Covered** | L14 reviewed viewport/element screenshots with sensitive-surface guards. |
| Controlled downloads | **Covered** | L14 exact-HREF/expected-URL governed HTTP download path; native uncontrolled Chromium downloads stay disabled. |
| Quarantine and parser reuse | **Covered** | L14 private temporary quarantine, bounded safe parser routing and cleanup on success/failure. |
| Raw artifact retention policy | **Covered** | Opt-in only when source policy + authorization + deployment artifact store permit it. |
| Crash/failure cleanup | **Covered** | Browser contexts close in `finally`; artifact quarantine is removed on success/failure. |
| Resumable browser/auth jobs | **Covered** | L13 plan checkpoints plus L17 durable same-job human checkpoint/restart continuation. |

## D. Delegated identity and authenticated acquisition

| Normative capability | Final status | Production evidence |
|---|---|---|
| Tenant/user/service-principal delegated identity | **Covered** | L15 identity ownership model supports user, service principal and deployment service contexts. |
| Purpose/scope binding | **Covered** | L15 execution grants require exact tenant/owner/source/purpose/scopes. |
| Isolated secret references | **Covered** | Provider Onboarding secret references; values resolved just in time rather than stored in ordinary database rows. |
| Governed session references | **Covered** | L15/L16 reference-only session control plane and isolated session-material store. |
| Expiry / revoke / delete / audit | **Covered** | L15 lifecycle and audit; L16/L17 reauthorize before use/resume. |
| Reviewed username/secret login | **Covered** | L16 provider-specific login profiles and production Chromium login path. |
| Authenticated page retrieval | **Covered** | L16 governed authenticated page runtime; L18 converts the authenticated page to canonical internal `RawObservation` provenance without pretending it is public. |
| Authenticated structured extraction | **Covered** | L18 authenticated evidence bridge reuses bounded semantic/structured sanitization; raw HTML is not retained in PostgreSQL. |
| Session reuse | **Covered** | L16 exact-context session restore/probe/refresh; L18 proves second access without second login. |
| Remote logout / local revoke | **Covered** | L16 best-effort reviewed logout plus authoritative local revoke/material deletion; L18 proves both. |
| Post-revoke access denial | **Covered** | L16/L18 reauthorization denies later session reuse. |
| OAuth 2 authorization-code + PKCE | **Covered** | L17 reviewed profile, state, PKCE S256, callback binding and governed token exchange. |
| OIDC nonce/verification boundary | **Covered** | L17 nonce plus injected cryptographic verifier required; no naive token decoding. |
| Reviewed SSO profile contract | **Covered** | L17 provider-specific browser SSO transition model; arbitrary IdP following remains denied. |
| Human MFA/CAPTCHA/provider-security checkpoint | **Covered** | L17 durable `AWAITING_HUMAN_CHECKPOINT` pause/resume; human/provider action only, no automated solving/bypass. |
| Same-job restart/resume without retry consumption | **Covered** | L17 durable checkpoint + `human_resume_pending`; controlled OAuth proof closes/reopens DB session and reclaims same job. |
| OAuth replay/crash window safety | **Covered** | L17 `authorization_pending -> token_ready` continuation prevents uncertain authorization-code repost. |
| Automatic provider account registration/alias | **Conditional — not triggered** | No current reviewed SA-16 provider profile permits automatic signup/alias creation. CIP intentionally has no generic account-creation automation. |

## E. Failure and recovery audit

| Failure/recovery requirement | Final status | Evidence |
|---|---|---|
| Browser crash/runtime failure cleanup | **Covered** | L07 disposable context/browser nested `finally` cleanup and fail-closed browser-error tests. |
| Crawl deadline/cancellation boundary | **Covered** | L12 `crawl_deadline_exceeded`, partial checkpoint/observations, no false success event, retryable recovery. |
| Retry/replay without double counting | **Covered** | L12 partial retry and L18 authenticated observation deduplication. |
| OAuth one-time-code replay safety | **Covered** | L17 token-ready continuation resumes without reusing consumed authorization code. |
| Stale/invalid session | **Covered** | L16 session availability/probe validation and typed material failures. |
| Revoked identity | **Covered** | L16/L17/L18 later access denied after revoke. |
| Challenge timeout/expiry/cancel | **Covered** | L17 checkpoint expiry/cancel/invalidation/binding-drift fail closed. |
| MFA/CAPTCHA/security challenge | **Covered** | L16 hard stop before credential POST; L17 human checkpoint, never solver/bypass. |
| Oversized/invalid/off-origin content | **Covered** | L02/L07/L12/L14 byte/origin/MIME/magic/redirect/action authorization denial. |
| Source-policy denial | **Covered** | Network/action/artifact/login/token routes reauthorize against Source Governance before execution. |
| Quarantine cleanup | **Covered** | L14 deterministic cleanup on parser success/failure and L18 live proof verifies zero leaked quarantine files. |

## F. L18 composite integration proof

The L18 public controlled workflow composes the real production path in one coherent execution:

```text
Organization
-> automatic public runtime
-> schedule_due_jobs
-> collection worker
-> robots + sitemap index + sitemap + RSS + security.txt + links
-> static + browser fallback collection
-> L10 surfaces
-> L11 network/script state
-> canonical public evidence + checkpoint + source health
-> second scheduled conditional recrawl / 304
-> reviewed screenshot + controlled download
-> artifact metadata + document projection + quarantine cleanup
```

The L18 authenticated controlled workflow composes:

```text
tenant service principal
-> L15 delegated identity
-> JIT secret reference
-> reviewed L16 Chromium login
-> authenticated rendered page
-> sanitized structured extraction
-> canonical internal RawObservation provenance, no raw page retention
-> session reuse without second login
-> observation deduplication
-> reviewed remote logout + local revoke
-> session-material deletion
-> later reuse denied
```

These controlled first-party fixtures prove production mechanics without requiring a third-party provider account, violating provider terms, solving CAPTCHA/MFA, copying sessions or following arbitrary IdPs.

## Security conclusions

SA-16 does **not** equate acquisition with commercial truth and does not directly write signals, needs or opportunities from browser/provider responses. It does not add CAPTCHA solving, MFA bypass, credential guessing, stolen session use, account cycling, proxy/ban evasion, arbitrary JavaScript execution or uncontrolled downloads.

Provider and human security controls remain hard stop/resume checkpoints. Source Governance remains authoritative before network execution. Secret/token/session values remain outside ordinary PostgreSQL evidence and logs; references and digests are retained where required for lifecycle/provenance.

## Remaining release gate

Implementation coverage is complete. L18 itself is not merge-authorized until its finalized documentation head independently passes:

1. complete repository CI including full branch-aware coverage and reversible migrations;
2. exact-head L18 public composite workflow;
3. exact-head L18 authenticated composite workflow;
4. critical changed-code coverage review;
5. clean PR review/thread/conversation audit;
6. Ready transition only after all gates are green;
7. squash merge locked to the exact validated head SHA;
8. squash Git tree exactly equal to the validated branch tree;
9. reread of `main` confirming the squash before SA-17 begins.

After those release gates pass, SA-16 is complete and the source-activation programme may continue to SA-17 from the exact merged `main` commit only.
