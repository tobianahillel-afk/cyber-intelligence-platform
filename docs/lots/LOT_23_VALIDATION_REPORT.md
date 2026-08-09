# Lot 23 — Validation report

## Status

Functional integrated candidate: **PASS**.

Release candidate `0.24.0`: implementation, version metadata, README, authoritative roadmap and Lot 23 documentation are synchronized on the branch.

This report is intentionally the final repository-content change planned for Lot 23. Its exact commit head must pass the complete standard CI before PR #62 can be marked ready and squash-merged. No earlier green SHA is sufficient as final-head proof.

## Release identity

- Release: `0.24.0`
- Branch: `agent/governed-osint-research`
- Exact base: Lot 22 squash `10c547752ad12e76a61b394248960d4640bc0885`
- Migration: `20260809_0023`
- Checked: 2026-08-09
- Functional integrated SHA: `1e2f7d5ac627eaa2c7a2826a9130ed227fefcb66`
- Functional CI: run #1402, run ID `31330116985`
- Functional backend job: `93286956110`
- Final release proof: standard CI on the exact documentation-complete head containing this report

## Functional CI evidence

Exact functional SHA `1e2f7d5ac627eaa2c7a2826a9130ed227fefcb66` passed the complete standard repository workflow before release metadata and documentation synchronization.

### Backend — functional CI #1402

- dependency consistency: PASS (`pip check`)
- installed dependency audit: PASS (`pip-audit`, no known vulnerabilities)
- Ruff: PASS
- strict Mypy: PASS over **535 source files**
- architecture/release contracts: **34 passed**, 0 failures
- PostgreSQL 17 Alembic cycle: PASS (`upgrade head -> downgrade base -> upgrade head`), including `20260809_0023`
- pytest: **1027 passed**, 0 failures
- aggregate branch-aware coverage: **90.23%**

### Frontend — functional CI #1402

- npm dependency audit: PASS
- TypeScript typecheck: PASS
- Next.js production build: PASS

Because version metadata and documentation changed after that SHA, the functional CI is evidence of implementation correctness only. The exact report-complete `0.24.0` head must pass the same workflow again.

## Validated functional scope

Lot 23 validates the following behavior end to end:

- persisted research questions, plans, current state and immutable plan revisions;
- explicit plan budgets for steps, automated steps, total cost and per-step cost;
- exact source IDs, tool IDs, approved step keys, purpose, data category, HTTPS hosts, path prefixes and risk ceilings;
- ordered persisted research steps and analyst decisions;
- explicit `persisted_search`, `manual_link`, `automated_adapter` and `approved_ingestion` modes;
- deterministic research-source ranking after unsafe candidates are filtered;
- persisted source-value and freshness inputs used for ranking without turning ranking into authorization;
- runtime resolution from Source Governance, Provider Onboarding, Source Portfolio and exact Adapter Capability state;
- quota and cost checks from persisted source health/portfolio state;
- Lot 22 conditional-provider approval, expiry, pause and kill-switch checks when applicable;
- replay-safe persisted attempts with idempotence keys;
- interruption/retry handling without silently duplicating attempt identity;
- persisted research results separate from attempts and from Evidence;
- approved-ingestion path `existing-evidence-reference` limited to already persisted Evidence references;
- Evidence reference existence, expected-source and provenance validation;
- protected APIs for plans, revisions, decisions, steps, eligibility, attempts, results, usage and ranked source options;
- explicit registration of the `/v1/research/source-options` route in the protected research router;
- Next.js Research workspace with explicit manual-action state;
- UTC-safe persistence hydration across PostgreSQL and SQLite-backed tests;
- no automatic conversion of research output into a commercial conclusion or external communication.

## Fail-closed research boundary

The validated boundary is:

```text
research question
!= source authorization

catalog candidate
!= executable tool

ranked source
!= execution authorization

research plan
!= source authorization

manual link
!= automated provider execution

eligible step
!= successful evidence capture
!= commercial signal
!= need hypothesis
!= opportunity
!= outreach authorization
```

Automated eligibility requires every applicable gate to be positive at evaluation time:

- plan approved/in progress and not expired;
- exact step key approved;
- exact source and tool allowed by the plan;
- purpose and data category exactly match;
- risk remains below the plan ceiling;
- step, automated-step, total-cost and per-step budgets remain available;
- HTTPS target remains inside exact approved host/path scope;
- Source Governance source status and authorization permit the request;
- Provider Onboarding is ready where required;
- Source Portfolio is executable;
- exact Adapter Capability exists for the requested source/tool pair;
- quota remains available;
- cost budget remains available;
- applicable conditional-provider approval remains current;
- provider is not paused;
- kill switch is clear.

Missing, stale, expired, revoked, paused, out-of-scope, over-budget or capability-missing state fails closed.

## Source ranking boundary

The source-options path ranks candidates using existing governed state rather than inventing a second source registry.

Unsafe automated candidates are filtered before ranking. Automated candidates require authorization, executable capability and available quota. Manual-link candidates require a source type and policy that explicitly permit the manual path. Prohibited-risk candidates are excluded.

Remaining candidates are ranked deterministically using value, freshness, cost and risk. The ranking result is advisory only and never upgrades a source candidate into execution authorization.

## Attempt and replay safety

Research attempts are persisted before completion and carry stable idempotence identity. The API separates creation, execution state, completion and result capture.

Validated invariants include:

- retry does not silently create a second logical external action for the same idempotence key;
- attempt completion is persisted separately from result capture;
- usage accounting remains reconstructable;
- result references do not imply Evidence existence until validated;
- a successful attempt is not itself a commercial conclusion.

## Evidence and provenance handoff

Lot 23 does not create a parallel evidence store.

The built-in approved-ingestion path accepts an `evidence:<uuid>` reference only. Result validation verifies:

- the reference uses the expected Evidence identifier form;
- the Evidence record exists;
- an expected source identity matches the Evidence source when required;
- the Evidence preserves recognized provenance such as `source-record:` or `raw-observation:`.

Research result capture therefore reuses the canonical Evidence layer and does not treat a search result, provider response, attempt or analyst note as corroborated evidence automatically.

## Explicit non-capabilities

Lot 23 does **not** add:

- unrestricted autonomous browsing;
- an arbitrary HTTP/network tool;
- browser login automation;
- private portal access;
- active prospect scanning, probing or exploitation;
- CAPTCHA, MFA, paywall or access-control bypass;
- copied browser sessions or cookies;
- fake identities or account cycling;
- hidden automation behind a manual link;
- direct result-to-signal promotion;
- automatic opportunity creation;
- autonomous outreach.

No page render triggers external collection.

## Regression coverage

Regression and architecture tests cover, among other cases:

- denied automation before execution;
- plan state and expiry;
- exact source/tool/step-key matching;
- purpose and data-category mismatches;
- risk ceilings;
- total, per-step and automated-step budget exhaustion;
- HTTPS host/path boundaries;
- missing authorization;
- onboarding readiness;
- non-executable portfolio state;
- missing adapter capability;
- quota and cost exhaustion;
- conditional approval expiry/revocation;
- pause and kill-switch controls;
- deterministic ranking and prohibited-candidate filtering;
- manual-link versus automated-provider distinction;
- attempt idempotence and retry behavior;
- Evidence reference format, existence, source identity and provenance;
- UTC hydration portability;
- protected API behavior;
- source-options route availability;
- Research workspace typecheck and production build;
- architecture prohibition of network/browser/collector/opportunity/outreach shortcuts from the research bounded context.

## Final exact-head gate

The functional integrated SHA `1e2f7d5a...` is fully green, but release/version/documentation synchronization necessarily created later commits and invalidated it as the final-head proof.

Before PR #62 can be marked ready and squash-merged:

1. no repository file may change after this report commit unless a failing gate requires a corrective commit;
2. if any corrective commit is necessary, the complete workflow must rerun on the new exact head;
3. the exact report-complete head must pass dependency checks, security audit, Ruff, strict Mypy, architecture/release contracts, reversible PostgreSQL migrations, full pytest/coverage and frontend audit/typecheck/build;
4. review threads/reviews must contain no unresolved blocker;
5. PR metadata may be refreshed because that does not change the Git commit;
6. squash merge must target the exact fully green head.

## Release claim

**Lot 23 is functionally implemented and synchronized as release `0.24.0`. The release becomes merge-complete only when the exact documentation-complete head containing this report passes every standard repository gate and is squash-merged without any subsequent repository-content change.**
