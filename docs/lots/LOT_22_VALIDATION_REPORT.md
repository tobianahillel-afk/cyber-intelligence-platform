# Lot 22 — Validation report

## Status

Functional integrated candidate: **PASS**.

Synchronized release candidate `0.23.0`: **PASS** on exact SHA `a88468a4d2590763e2aae7d5b74ab875c57ade60`, standard CI #1276.

This report update creates the final documentation-complete SHA. One final standard CI run on that exact new head is therefore still required before PR #60 can be marked ready and squash-merged.

## Release identity

- Release: `0.23.0`
- Branch: `agent/conditional-premium-integrations`
- Exact base: Lot 21 squash `f797128dd71eb1cbe5716e73478565e6942cb458`
- Migration: `20260809_0022`
- Checked: 2026-08-09
- Functional integrated SHA: `2182aa3ffeffff706129ce82c42cbc4116eb6da1`
- Functional CI: run #1270, run ID `31315615232`
- Synchronized release SHA: `a88468a4d2590763e2aae7d5b74ab875c57ade60`
- Release CI: run #1276, run ID `31316196327`
- Release diagnostics artifact: `backend-test-diagnostics`, artifact ID `9038848302`

## Functional and release CI evidence

Both the integrated functional candidate and the synchronized release candidate pass the standard repository workflow. Release metadata, README and the authoritative roadmap are therefore covered by an executable release-contract run rather than inferred from the functional candidate.

### Backend — release CI #1276

- dependency consistency: PASS (`pip check`)
- installed dependency audit: PASS (`pip-audit`, no known vulnerabilities)
- Ruff: PASS
- strict Mypy: PASS over **503 source files**
- architecture/release contracts: **32 passed**, 0 failures/errors/skips
- PostgreSQL 17 Alembic cycle: PASS (`upgrade head -> downgrade base -> upgrade head`), including `20260809_0022`
- pytest: **961 passed**, 0 failures/errors/skips
- aggregate branch-aware coverage: **90.44%**
  - lines: 22,007 covered / 23,528 valid
  - branches: 3,664 covered / 4,858 valid

### Frontend — release CI #1276

- npm dependency audit: PASS
- TypeScript typecheck: PASS
- Next.js production build: PASS

The conditional-integration workspace is dynamically server-rendered; production does not receive a fallback control-plane token during build.

## Validated functional scope

Lot 22 validates the following behavior end to end:

- immutable provider-specific approval dossiers with exact authorization, licence, terms, scopes, fields, purposes, categories, retention, automation and account boundaries;
- mandatory `actor` and `change_reason` for material dossier revisions;
- provider-method restrictions for LinkedIn, Discord, BrixHub, premium CTI and licensed commercial datasets;
- current approval projection plus immutable revision history;
- append-only pause/resume and kill-switch history;
- immutable, idempotent execution-eligibility audits;
- persisted-state runtime dependency resolution from Provider Onboarding, Source Governance and Source Portfolio;
- canonical host/path/purpose/category/raw-storage/automation evaluation through Source Governance;
- canonical Source Portfolio executable/freshness/quota/cost gating;
- explicit separation of Source Governance denial, non-executable portfolio state and missing adapter capability;
- protected list/detail/write/control/eligibility/value APIs;
- safe-default conditional source catalogues with missing authorization, no runtime adapter and no collection schedule;
- existing canonical LinkedIn and BrixHub source identities reused instead of duplicated;
- source-value evidence derived from the existing `source_value_events` model;
- Next.js analyst/admin workspace for dossier review, local control, eligibility preview, audit history and observed value evidence.

## Fail-closed boundary

The validated boundary is:

```text
catalog candidate
!= approved provider
!= approved account/scope
!= registered runtime capability
!= execution eligibility
!= provider request
!= collection
!= commercial opportunity
!= outreach authorization
```

Execution eligibility requires all applicable conditions to be positive at evaluation time:

- exact provider dossier approved and current;
- exact provider/access method permitted;
- exact scope, field, purpose, category, retention and account compatible;
- persisted onboarding ready where required;
- Source Governance decision allowed for the exact target URL and request intent;
- Source Portfolio executable;
- real adapter capability registered;
- provider not paused;
- kill switch clear;
- quota available;
- cost budget available.

Missing, malformed, revoked, expired, paused, out-of-scope or stale control state blocks eligibility.

## Explicit non-capabilities

Lot 22 does **not** add:

- a real LinkedIn, Discord, BrixHub, premium-CTI or commercial-data network adapter;
- browser scraping of LinkedIn, Discord or private portals;
- fake accounts, copied cookies/sessions, self-bots or credential reuse;
- CAPTCHA/MFA bypass, ban evasion or bypass proxy rotation;
- private-message collection;
- credential validation or raw secret storage;
- automatic opportunity creation;
- autonomous outreach.

BrixHub remains quarantined and has no permitted execution method in the Lot 22 provider policy.

## Regression coverage

Regression tests cover, among other cases:

- provider/method correctness;
- approval-artifact requirements;
- exact scopes, fields, purposes, categories, retention and account matching;
- source mismatch distinct from account mismatch;
- expiry, revocation, pause and changed/review-due terms;
- onboarding not ready;
- Source Governance host denial;
- Source Portfolio non-executable state;
- missing adapter capability;
- quota exhaustion and cost exhaustion;
- pause and kill switch;
- dossier replay and immutable history;
- backdated control rejection and old-decision replay idempotence;
- execution-decision idempotence;
- absence of password/token/cookie/session-value columns;
- 401 protected-control-plane behavior;
- 404 fail-closed provider behavior;
- 422 invalid approval behavior;
- safe-default source/portfolio registry loading and no enabled schedules;
- observed source-value evidence vs portfolio-without-source baseline;
- frontend typecheck and production build.

## Final exact-head gate still required

The synchronized release SHA `a88468a4d2590763e2aae7d5b74ab875c57ade60` is fully green. Recording that evidence in this report necessarily creates one last documentation-only SHA and invalidates `a88468a...` as the final-head proof.

Before PR #60 can be marked ready and squash-merged:

1. no repository file may change after this report commit;
2. the standard CI workflow must pass on the exact documentation-complete head;
3. review threads/reviews must contain no unresolved blocker;
4. the PR body may be refreshed because that does not change the Git commit;
5. squash merge must use the exact final head SHA as `expected_head_sha`.

## Release claim

**Lot 22 is functionally implemented and the synchronized `0.23.0` release candidate is validated. It is not yet merge-complete at this report revision because this final documentation commit itself must pass the standard CI on its exact SHA.**
