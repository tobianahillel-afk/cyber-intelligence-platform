# Lot 22 — Conditional, premium, LinkedIn, Discord, and BrixHub integrations

## Status

Implemented and functionally validated on `agent/conditional-premium-integrations` from exact Lot 21 squash `f797128dd71eb1cbe5716e73478565e6942cb458`.

Release target: `0.23.0`.

Functional integrated candidate: `2182aa3ffeffff706129ce82c42cbc4116eb6da1`, CI #1270 fully green. Final release-SHA validation remains a separate gate and is recorded in `LOT_22_VALIDATION_REPORT.md`.

## Outcome

Lot 22 adds a provider-specific approval and runtime-control layer for sources whose use depends on licences, scopes, administrator consent, customer-provided access, or written authorization.

It does not weaken or replace Source Governance, Provider Onboarding, Source Portfolio, Data Governance, or the Lot 21 professional-context privacy boundary. Conditional execution is permitted only when the exact provider dossier and every shared persisted control plane are positive.

## Authorization boundary

```text
catalog candidate
!= approved provider

account availability
!= approved account or scope

licensed product
!= authorization for every field or purpose

public professional profile
!= platform automation authorization

configured secret reference
!= executable provider

positive provider approval dossier
+ valid persisted onboarding state
+ allowed Source Governance decision
+ executable Source Portfolio state
+ registered adapter capability
+ live quota/cost state
+ local pause/kill-switch state
= conditional execution eligibility

conditional execution eligibility
!= provider request
!= collection
!= commercial opportunity
!= outreach authorization
```

Eligibility preview is a local, persisted audit decision. It never performs provider login, HTTP collection, browser automation, outreach, or opportunity creation.

## Existing controls reused

Lot 22 composes existing control planes instead of duplicating them:

- **Source Governance:** source state, authorization document, purposes, data categories, host/path scope, automation, raw-storage, rate-limit and human-review requirements;
- **Provider Onboarding:** provider identity, onboarding state, service identity, secret references, verification, expiry, revocation and rotation;
- **Source Portfolio:** candidate/executable state, real adapter capability, freshness, quota, monthly cost, quality and health;
- **Data Governance:** retention, suppression and deletion obligations;
- **Lot 21 professional context:** professional evidence remains separated from private-life data and from outreach authorization.

The Lot 22 runtime resolver reconstructs these states from PostgreSQL and calls the canonical Source Governance and Source Portfolio decision functions. Browser-supplied booleans cannot substitute for persisted state.

## Provider-specific approval dossier

The current dossier projection is persisted together with immutable revisions. Each material revision includes `actor` and `change_reason` and records only references and approved capabilities, never raw secrets.

A dossier includes:

- source/provider identity and provider family;
- exact approved access method;
- draft, pending-review, approved, expired, revoked or paused state;
- authorization-document reference;
- licence/contract reference where applicable;
- reviewed terms reference and terms-review state;
- exact scopes and fields;
- approved purposes and data categories;
- explicit retention maximum;
- explicit automation permission;
- optional account/service-identity reference;
- review, review-due, expiry, revocation and pause metadata.

An approved dossier cannot be constructed without the required authorization reference, current terms review, reviewed timestamp, purposes/categories and explicit retention. Licensed access methods additionally require a licence reference.

## Provider method boundaries

The executable-method policy is deliberately conservative:

- **LinkedIn:** official API or separately licensed API only;
- **Discord:** administrator-installed connector or explicitly authorized export only;
- **BrixHub:** no permitted executable method in Lot 22;
- **premium CTI:** licensed API or authorized export;
- **commercial datasets:** licensed API, authorized export, or contract-bound customer-provided access;
- **other conditional providers:** still require a positive dossier and every shared runtime gate.

Lot 22 contains no fake-account path, copied cookies or browser sessions, self-bot path, CAPTCHA/MFA bypass, ban evasion, proxy-rotation bypass, private-message collection, credential validation, or private-portal scraping.

## Fail-closed persisted runtime resolver

`resolve_runtime_dependencies(...)` derives execution dependencies directly from persisted read models:

- `ProviderOnboardingRecord` for onboarding state;
- `SourceRecord` for Source Governance policy and authorization;
- `SourcePortfolioRecord` for candidate/executable and cost state;
- `SourceHealthRecord` for freshness, quota and observed cost;
- `AdapterCapabilityRecord` for registered capability.

It reconstructs the canonical `SourcePolicy`, evaluates the requested target URL, purpose, category, automation and raw-storage intent, and calls the canonical Source Portfolio execution check. Missing or invalid state is blocking by default.

The evaluator distinguishes at least:

- dossier not approved, expired, revoked or paused;
- terms review required;
- source/account/method mismatch;
- provider method prohibited;
- scopes, fields, purpose or category outside approval;
- retention outside approval;
- automation outside approval;
- onboarding not ready;
- Source Governance denied;
- Source Portfolio not executable;
- adapter capability missing;
- provider pause;
- kill switch active;
- quota exhausted;
- cost budget exhausted.

Each eligibility result records the request intent and the persisted dependency snapshot that produced the decision.

## Persistence and audit

Migration `20260809_0022` creates five governed tables:

- `conditional_provider_approvals` — current dossier projection;
- `conditional_provider_approval_revisions` — immutable dossier history with actor/reason;
- `conditional_provider_runtime_controls` — current pause/kill-switch projection;
- `conditional_provider_control_decisions` — append-only control history;
- `conditional_execution_decisions` — immutable eligibility audits.

Replaying the same dossier/control/execution decision is idempotent. A later revision never destroys earlier approval or revocation evidence. Backdated new control decisions are rejected while replay of an already-audited old decision is idempotent.

No conditional-integration table stores raw passwords, access tokens, cookies, secret values or browser-session material.

## Protected API

The `/v1/conditional-integrations` router uses the repository's canonical control-plane authentication and database session.

It exposes:

- provider list and detail;
- provider-specific dossier upsert with mandatory actor and change reason;
- pause/resume and kill-switch decisions;
- persisted-state eligibility preview and audit;
- immutable dossier/control/execution history;
- source-value evidence derived from the existing Source Portfolio value events.

The eligibility endpoint accepts only the intended access dimensions. Onboarding, source-policy decision, portfolio state, capability, quota, cost, pause and kill-switch state are resolved server-side from persisted state.

## Safe-default provider catalogues

Lot 22 makes conditional providers governable without making them executable.

Existing canonical source identities are reused for `linkedin-official-api` and `brixhub`. New governed candidates cover:

- `discord-authorized-integration`;
- `premium-cti-licensed`;
- `commercial-data-licensed`.

The corresponding Source Portfolio candidate set covers LinkedIn, Discord, premium CTI and commercial data, while the existing BrixHub candidate remains quarantined. Default entries have:

- missing authorization;
- no approved hosts/paths/purposes;
- no automation permission;
- no raw-storage permission;
- no runtime adapter capability;
- no collection schedule;
- candidate/quarantined state only.

The premium CTI and commercial-data entries deliberately use deployment-specific `.example.invalid` placeholders. They do not imply approval of any real vendor.

## Value evidence

Lot 22 reuses `source_value_events` from Source Portfolio rather than creating a second value system.

For a conditional provider the control plane reports:

- observed executions;
- modified executions;
- observations written;
- commercial projections;
- identity projections;
- observed request cost;
- the same aggregate for the portfolio excluding that source.

Zero executions means there is no execution-value evidence yet. The comparison is contribution/ablation evidence only; it is not proof of causal uniqueness, service need, opportunity, or authorization to contact.

## Next.js workspace

`/conditional-integrations` and `/conditional-integrations/[sourceId]` provide a protected, database-first workspace for:

- governed candidate visibility;
- dossier creation/revision;
- local pause/resume and kill switch;
- persisted-state eligibility preview;
- immutable review and eligibility history;
- source-value evidence.

The route is dynamically server-rendered so the production control-plane token is required at request time rather than during the static Next.js build. Production does not receive a fallback token.

The UI repeatedly preserves the boundary:

```text
candidate
!= approval
!= capability
!= execution
!= commercial opportunity
```

## Validation coverage

Regression tests cover:

- provider-specific method restrictions;
- positive approval artifacts and exact scopes/fields/purposes/categories/retention/account;
- expiry, revocation and terms changes;
- source mismatch vs account mismatch;
- onboarding, Source Governance, Source Portfolio, capability, quota, cost, pause and kill switch;
- immutable revision/control/execution history and replay idempotence;
- absence of raw secret/browser-session columns;
- protected API 401/404/422 behavior;
- persisted-state eligibility resolution including host denial and non-executable portfolio state;
- safe-default source/portfolio catalogues and absence of schedules/adapters;
- source-value evidence and portfolio-without-source comparison;
- frontend typecheck/build and runtime-only protected rendering.

The integrated functional candidate `2182aa3ffeffff706129ce82c42cbc4116eb6da1` passed 961 tests, 32 architecture/release contracts, strict Mypy over 503 source files, 90.44% aggregate branch-aware coverage, reversible PostgreSQL migrations through `0022`, and frontend audit/typecheck/build.

## Exit gate

Lot 22 satisfies its functional exit when a conditional source cannot become eligible until its exact provider dossier and every persisted shared runtime gate are positive; revocation, pause, expiry, terms change, Source Governance denial, non-executable portfolio state, missing capability, kill switch, quota exhaustion or cost exhaustion immediately blocks new eligibility without corrupting prior provenance or audit history.

Release `0.23.0` is not merge-complete until the final exact release SHA passes the standard repository CI and PR review gates.
