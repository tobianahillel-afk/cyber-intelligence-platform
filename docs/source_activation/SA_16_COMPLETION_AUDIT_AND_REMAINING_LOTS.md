# SA-16 — Completion audit after L09 and remaining microlots

## Status

`AUDITED_NOT_COMPLETE`

Audit baseline:

- repository: `tobianahillel-afk/cyber-intelligence-platform`;
- `main`: `a68dcd12094430de4d561da07b4251940386dd56`;
- merged implementation increments: SA16-L01 through SA16-L09;
- normative scope: `docs/source_activation/SA_15_20_FULL_ACTIVATION_ROADMAP.md`.

This document is a derived implementation audit. It does not weaken or replace the normative SA-16 roadmap. A capability is marked **covered** only when the current `main` production path materially implements it. **Partial** means useful primitives exist but the normative capability is not complete. **Absent** means no SA-16 production implementation satisfying the requirement was found.

## Executive conclusion

SA16-L01 through L09 completed the unauthenticated automatic public-web core:

```text
approved organization domain
-> automatic governed target
-> automatic schedule
-> robots
-> sitemap / RSS / Atom / security.txt discovery
-> bounded recursive same-origin crawl
-> incremental recrawl / tombstones / versions
-> semantic HTML / JSON-LD / OpenGraph / embedded public JSON
-> PDF / text / DOCX / XLSX / PPTX extraction
-> deterministic static-first Chromium fallback
-> canonical projections / provenance / checkpoints
```

That is a deployment-grade public crawling foundation, but **SA-16 as a whole is not complete**. The largest remaining gaps are:

1. complete structured web-surface extraction beyond visible/embedded content;
2. captured rendered-app JSON/network state;
3. explicit crawl wall-clock/concurrency budgets and crawl-specific telemetry;
4. governed browser interactions and form submission;
5. screenshots and controlled downloads;
6. user/deployment-delegated browser identities and session governance;
7. authorized login, OAuth/SSO and human MFA/CAPTCHA checkpoints;
8. one exact-head end-to-end live proof covering the complete SA-16 chain, including an authorized authenticated test account.

## Audit matrix

### A. Automatic company crawl

| Roadmap capability | Status | Current evidence / gap |
|---|---|---|
| Automatic governed target creation after canonical domain resolution | **Covered** | L01 provisions `PublicWebTarget` from `Organization.website_url`, with organization-specific target identity and governed source identity. |
| First crawl scheduling without developer-edited YAML | **Covered** | L08 builds automatic adapters/schedules for explicitly approved organization UUIDs and wires them into the central runtime/scheduler. |
| Robots policy evaluation | **Covered** | `PublicWebClient.fetch_robots()` evaluates the public target's robots rules before page/sitemap/feed acquisition. |
| Sitemap-index recursion | **Covered** | L03 recursively traverses sitemap indexes with bounded sitemap count and depth. |
| Sitemap traversal | **Covered** | Sitemap URL entries become governed discovery candidates. |
| RSS/Atom discovery and traversal | **Covered** | Explicit feeds and HTML `rel=alternate` RSS/Atom discovery feed the same governed candidate path. |
| security.txt discovery | **Covered** | Automatic targets enable `/.well-known/security.txt`; the collector has dedicated parsing/mapping. |
| Homepage/seed discovery | **Covered** | L01 automatically seeds the canonical homepage. |
| Same-origin link extraction | **Covered** | Static/rendered HTML `<a href>` links are canonicalized, deduplicated and confined to the target origin/scope. |
| Recursive crawl with configurable depth/page/byte budgets | **Covered** | `max_link_depth`, `max_pages`, `max_total_bytes`, `max_resource_bytes`, and redirect limits are enforced. |
| Crawl wall-clock budget | **Partial** | Browser navigation has a timeout, but `PublicWebTarget` has no whole-crawl wall-clock/deadline budget. |
| Crawl concurrency budget | **Partial** | Current recursive collector is deterministic/serial; no target-level configurable crawl concurrency contract exists. |
| Freshness budget / recrawl interval | **Covered** | Automatic policy carries `refresh_interval_seconds`; conditional recrawl uses validators and checkpoints. |
| Path and origin controls | **Covered** | Canonical URL, same-origin and `CrawlScope` path checks are re-evaluated before network access. |
| Incremental recrawl and change detection | **Covered** | ETag/Last-Modified, HTTP 304 handling and content-version comparison are implemented. |
| Tombstones and version history | **Covered** | Missing/gone resources map to tombstones; durable page/version state is preserved through checkpoints/projections. |
| Provenance | **Covered** | Source/adapter/job identities and discovery/source locators flow into canonical public-footprint projections. |
| Crawl-health metrics | **Partial** | Generic worker/source health, success/failure/freshness/value events exist; dedicated crawl telemetry such as pages/bytes/discovery/fallback/policy-denial/request counts is not yet a first-class SA-16 result. |

### B. Structured extraction

| Roadmap capability | Status | Current evidence / gap |
|---|---|---|
| HTML DOM / visible content | **Covered** | Static HTML extraction is bounded; browser pages are rendered then projected through `page.content()` and the same HTML pipeline. |
| Semantic HTML metadata | **Covered** | L05 extracts bounded semantic metadata and publication/update timestamps. |
| JSON-LD | **Covered** | `application/ld+json` scripts are parsed with depth/scalar/value bounds and sensitive-key filtering. |
| OpenGraph/public metadata | **Covered** | OpenGraph/Twitter/description/author metadata is extracted. |
| Public embedded JSON application state | **Covered** | Bounded `application/json` script contents are parsed using a public structured-key allowlist. |
| Authorized structured JSON responses used by rendered applications | **Absent** | The browser route authorizes/intercepts requests but does not capture and normalize same-origin JSON response bodies. |
| Script-exposed public structured state | **Partial** | Typed embedded JSON scripts are supported, but dynamically exposed JS globals/state outside those script types are not captured. |
| CSS/resource references useful for technology attribution | **Absent** | Link discovery only models anchor links and RSS/Atom alternates; CSS/script/resource references are not emitted as structured technology-attribution observations. |
| Response headers | **Partial** | Content-Type, ETag, Last-Modified, Location and related headers are consumed for safety/recrawl, but no bounded governed header projection is persisted as evidence. |
| Canonical/alternate links | **Partial** | RSS/Atom `rel=alternate` is used for feed discovery; generic canonical and alternate-link metadata is not modeled. |
| Public forms/endpoints | **Absent** | Form action/method/input metadata and public endpoint discovery are not extracted. |
| Document links | **Partial** | Same-origin anchor links can naturally lead to PDFs/text/OOXML, which the collector parses, but links are not classified/persisted as a typed document-link surface before acquisition. |
| Media links | **Absent** | Media references are not extracted as structured surface metadata; browser image/media resource types are intentionally blocked. |
| PDF extraction | **Covered** | Existing public-web extraction handles `application/pdf` in addition to L06 OOXML. |
| DOCX/XLSX/PPTX extraction | **Covered** | L06 provides bounded macro-free OOXML parsing with ZIP/XML safety checks. |

### C. Generalized browser runtime

| Roadmap capability | Status | Current evidence / gap |
|---|---|---|
| Isolated disposable browser process/context | **Covered** | L07 launches a fresh sandboxed Chromium process/context and closes both in `finally`. |
| JavaScript rendering | **Covered** | Browser acquisition renders JS and returns the final bounded DOM. |
| Navigation | **Covered** | Governed `page.goto()` navigation is implemented. |
| Form interaction | **Absent** | No browser action/form-fill/submit execution contract exists. |
| Authorized login | **Absent** | L07/L09 explicitly exclude authenticated browsing. |
| OAuth/SSO | **Absent** | No delegated OAuth/SSO browser flow exists. |
| Screenshots | **Absent** | No screenshot capture/evidence path exists. |
| DOM capture | **Covered** | Rendered DOM is captured through `page.content()`. |
| Structured-state capture | **Partial** | DOM embedded JSON is processed, but rendered network JSON and general script-exposed state remain missing. |
| Controlled downloads | **Absent** | Chromium contexts are created with `accept_downloads=False`. |
| Request interception and host/path allowlists | **Covered** | Every browser request is intercepted and checked against same-origin, crawl scope and source authorization; selected resource classes are blocked. |
| Resource/time budgets | **Covered** | Browser request count, navigation timeout, settle timeout, redirects and rendered DOM byte budgets are bounded. |
| Crash cleanup | **Covered** | Browser/context cleanup is guarded by nested `finally` blocks. |
| Resumable browser jobs | **Partial** | Public crawl checkpoints restore previously known page candidates, but there is no persisted browser action/session checkpoint capable of resuming an interrupted interaction/login workflow. |

### D. User-delegated accounts and authenticated acquisition

| Roadmap capability | Status | Current evidence / gap |
|---|---|---|
| Provider identity tied to a real CIP tenant/user or deployment service principal | **Absent** | Provider Onboarding is source-scoped; it does not model a delegated browser identity owner/binding required by SA-16. |
| Isolated secret references | **Partial foundation** | Provider Onboarding already provides validated env/vault/file-secret references. They are not yet bound to a delegated browser identity/session. |
| Session references | **Absent** | No governed browser-session reference model exists. |
| Scopes | **Absent** | No per-delegated-browser-identity scope model exists. |
| Expiry / revocation | **Partial foundation** | Provider Onboarding has expiry and `REVOKED` state, but not a complete delegated browser-session lifecycle. |
| Deletion | **Absent** | No delegated session/identity deletion lifecycle satisfying SA-16 was found. |
| Audit | **Partial foundation** | Existing onboarding/source execution records provide general auditability, but no dedicated delegated-session audit trail exists. |
| Provider-approved automatic registration / service-account support | **Absent** | No browser-account registration/service-account execution path is implemented. |
| Tenant-controlled provider email aliases | **Absent** | No implementation found. |
| Human/provider-approved CAPTCHA/MFA checkpoint | **Partial foundation** | Provider Onboarding has `AWAITING_MFA` / `COMPLETE_MFA` concepts, but the browser runtime cannot pause and resume the same job around a human checkpoint. |
| Resume same job after challenge completion | **Absent** | No persisted interactive browser action state/session restoration path exists. |

### E. Live validation and SA-16 closure

| Roadmap capability | Status | Current evidence / gap |
|---|---|---|
| Real approved public/neutral websites | **Covered in component proofs** | L01-L09 have exact-head real-network validation, including 20-target L08/L09 suites. |
| Static -> recursive -> browser fallback | **Covered in production-path live proof** | L09 proves the automatic fallback-capable runtime and a forced Chromium render on Selenium. |
| Structured extraction | **Covered for current extraction profile** | L05/L09 validate current semantic/embedded structured extraction, but not the missing network/script-state surfaces. |
| Document acquisition | **Covered separately** | Public PDF/text exists and L06 live-validates OOXML acquisition; it has not yet been proven inside one final SA-16 composite run. |
| Provenance-backed evidence | **Covered for current paths** | Current public-web observations/projections preserve source/adapter/job provenance. |
| Single complete public end-to-end chain | **Partial** | Capabilities have exact-head proofs across separate microlots; there is no final one-run chain exercising recursive crawl + rendered fallback + structured surface + document acquisition together. |
| Authorized authenticated test account | **Absent** | No live authenticated browser proof exists. |
| Overall SA-16 exit gate | **Not met** | The unauthenticated public-web core is strong, but mandatory generalized browser/authenticated/delegated-account capabilities remain incomplete. |

## Remaining implementation decomposition

The remaining work is decomposed into nine independently reviewable microlots. Lot boundaries may be restacked if implementation evidence shows a smaller safe split is necessary, but no roadmap capability listed above may be silently dropped.

### SA16-L10 — Structured web-surface inventory

**Goal:** close the remaining static/rendered page-surface extraction gaps without adding browser interaction.

Implement bounded typed extraction for:

- response headers approved for evidence/technology attribution;
- `<link rel=canonical>`;
- non-feed alternate links;
- stylesheet/script/resource references useful for technology attribution;
- form action/method metadata and public endpoint candidates;
- typed document links;
- typed media links;
- source locators and provenance for every extracted surface item.

Safety/invariants:

- never submit a form in L10;
- never follow a newly recognized endpoint unless it re-enters ordinary source authorization/crawl scope;
- bounded counts/value sizes and sensitive field-name filtering;
- do not infer technology deployment solely from one resource reference.

Exit gate:

- deterministic parser/projection tests;
- critical changed modules >=95% line/branch target;
- exact-head CI;
- controlled live proof on neutral/first-party pages containing canonical, alternate, form, stylesheet/script and document links.

### SA16-L11 — Rendered public JSON and script-state capture

**Goal:** capture public structured state used by rendered applications while preserving the browser's authorization boundary.

Implement:

- same-origin authorized JSON response capture from the browser request/response lifecycle;
- MIME/status/byte/request-count bounds;
- fixed, reviewed script-state extractors for public application state that is not already represented by typed JSON script tags;
- sensitive-key suppression consistent with L05;
- explicit provenance tying structured records to page URL and network/script locator;
- no arbitrary caller-supplied JavaScript evaluation.

Exit gate:

- deterministic fixture with JS `fetch()`/XHR plus public client state;
- off-origin JSON remains blocked/not captured;
- secrets/session/cookie-like fields are not promoted;
- exact-head CI and sandboxed Chromium live proof.

### SA16-L12 — Crawl deadline, concurrency and crawl telemetry

**Goal:** finish the operational-budget and crawl-health requirements.

Implement:

- target-level wall-clock crawl deadline;
- explicit bounded crawl concurrency setting;
- deterministic admission/order semantics under concurrency;
- synchronized page/byte budgets with no oversubscription;
- crawl metrics including attempted/fetched/not-modified/tombstoned pages, bytes, links discovered/admitted, browser fallbacks, policy denials, redirects and elapsed time;
- persistence/health integration through existing source portfolio/value-event primitives.

Exit gate:

- deterministic concurrency/budget tests including race/oversubscription cases;
- deadline cancellation/cleanup proof;
- source-health metrics persisted through the production worker;
- exact-head CI plus controlled multi-page live crawl.

### SA16-L13 — Governed browser action plans and forms

**Goal:** add bounded browser interaction without introducing authentication yet.

Implement a typed action plan supporting only reviewed operations such as:

- navigate;
- click;
- fill a non-secret field;
- select/check;
- submit an explicitly authorized public form;
- wait for bounded navigation/DOM condition.

Required controls:

- no arbitrary JavaScript supplied by callers;
- selector/action count/value-length budgets;
- same-origin and source authorization before resulting navigation/request;
- form action/method inspection before submit;
- deny file upload, credential fields and hidden secret material in this lot;
- persisted action-step checkpoint sufficient to retry/resume an interrupted non-authenticated action plan safely.

Exit gate:

- deterministic local/neutral form fixture;
- crash/retry resumes at a safe deterministic checkpoint without duplicate unsafe submission;
- exact-head CI and browser live proof.

### SA16-L14 — Controlled screenshots and downloads

**Goal:** satisfy the browser screenshot/download requirements while preserving artifact governance.

Implement:

- bounded screenshots with content hash, page/source provenance and policy-controlled retention;
- controlled downloads only from authorized requests initiated by an explicit action plan or governed link;
- MIME/extension/size/count validation;
- quarantine before parsing;
- no executable content execution;
- S3 artifact persistence only when the source/data-governance policy explicitly permits raw artifact retention;
- ephemeral processing + derived evidence only when raw retention is not allowed;
- integration with existing PDF/text/OOXML processing where applicable.

Exit gate:

- safe test fixtures for screenshot and document download;
- malicious/oversized/off-origin download denial tests;
- exact-head CI and controlled live proof.

### SA16-L15 — Delegated browser identity and session governance

**Goal:** create the missing account/session control plane before login automation.

Reuse Provider Onboarding primitives rather than creating a competing secret system.

Implement:

- delegated provider identity bound to CIP tenant/user or deployment service principal;
- provider/source identity;
- approved scopes/purpose;
- secret references;
- browser session reference, never raw session secret in normal relational fields/logs;
- reviewed/created/last-used/expires timestamps;
- revoke/delete lifecycle;
- audit events;
- one identity cannot be reused across unauthorized tenants/providers/purposes.

Exit gate:

- reversible migration;
- domain/application/infrastructure tests;
- authorization and tenant-isolation tests;
- revocation/deletion destroys future executable access;
- exact-head CI.

### SA16-L16 — Authorized login and governed session reuse

**Goal:** execute legitimate provider-approved login for an explicitly delegated identity, excluding OAuth/SSO and human challenges until L17.

Implement:

- browser action plan capable of consuming secret references only at execution time;
- provider-specific/login-profile allowlist rather than arbitrary credential submission;
- exact approved login hosts/paths;
- secret values never appear in observations, logs, checkpoints or screenshots;
- authenticated session stored only through the L15 session-reference mechanism;
- explicit session expiry/revocation and logout/delete path;
- fail closed when MFA/CAPTCHA/SSO is encountered instead of bypassing it.

Exit gate:

- authorized local/first-party test account live proof;
- credential non-disclosure tests;
- session reuse and revocation proof;
- exact-head CI.

### SA16-L17 — OAuth/SSO and resumable human MFA/CAPTCHA checkpoints

**Goal:** complete legitimate interactive authentication without challenge bypass.

Implement:

- provider-specific OAuth/SSO authorization flows with reviewed redirect/origin scopes;
- state/nonce/correlation handling where applicable;
- human checkpoint states for provider-approved MFA/CAPTCHA/terms acceptance;
- pause the same collection/browser job before the challenge;
- expose a controlled completion/resume operation;
- resume the same job/session after the human/provider-approved step;
- timeout/expiry/cancellation/revocation paths;
- no CAPTCHA/MFA bypass or credential guessing.

Exit gate:

- deterministic state-machine tests;
- resumability across worker/process restart;
- authorized test identity demonstrating one human checkpoint and same-job continuation;
- exact-head CI and controlled live proof.

### SA16-L18 — Full SA-16 end-to-end live proof and closeout

**Goal:** prove the complete normative SA-16 path on the final implementation tree and close only if every requirement is covered.

Required public proof:

```text
organization/domain
-> automatic target
-> automatic schedule
-> recursive crawl
-> structured surface extraction
-> static-to-browser fallback
-> rendered JSON/script-state extraction
-> document acquisition
-> versioned provenance-backed evidence
```

Required authenticated proof:

```text
delegated authorized test identity
-> governed login / OAuth or SSO route as appropriate
-> human checkpoint when required
-> same-job resume
-> authorized rendered retrieval
-> controlled screenshot/download where enabled
-> provenance-backed evidence
-> revocation/delete proof
```

Final closeout requirements:

- every row in this audit becomes **Covered** or is explicitly removed from SA-16 by a documented product-owner scope decision;
- exact final head passes normal CI;
- exact final head passes public and authenticated live workflows;
- no blocking/unresolved review threads;
- merge locked to validated head;
- squash-merged Git tree equals the validated Git tree.

## Dependency order

Recommended order:

```text
L10 -> L11
  \      \
   -> L12  -> L18

L09 -> L13 -> L14
          \
Provider Onboarding -> L15 -> L16 -> L17 -> L18
```

L10/L11 and L12 can proceed independently of delegated-account work. L13 must precede login because authentication should consume a reviewed browser action model rather than inventing a one-off automation path. L15 must precede L16 so login never creates an unmanaged secret/session model. L17 must build on an already governed login/session lifecycle. L18 is validation/closeout, not a place to hide missing implementation.

## Truth boundary

The following statements are valid after L09:

- the unauthenticated automatic company-site crawler is production-integrated and live-tested;
- static-first browser fallback is production-integrated and live-tested;
- public HTML/semantic/embedded JSON and bounded PDF/text/OOXML extraction exist;
- SA-16 is **not** globally complete;
- authenticated browsing, OAuth/SSO, forms, screenshots, controlled downloads and delegated browser sessions must remain open until their own production paths and live proofs exist.
