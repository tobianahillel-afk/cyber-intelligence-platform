# Lot 23 — Analyst research and governed OSINT catalog orchestration

## Status

Implementation-complete release candidate on `agent/governed-osint-research` from exact Lot 22 squash `10c547752ad12e76a61b394248960d4640bc0885`.

Target release: `0.24.0`.

The integrated functional candidate passed the complete repository CI on exact SHA `1e2f7d5ac627eaa2c7a2826a9130ed227fefcb66` before the release/documentation synchronization commits. The final documentation-complete head must pass the same CI again before merge.

## Outcome

Lot 23 turns the broad OSINT and source catalog into reproducible analyst research plans rather than unrestricted autonomous browsing.

The lot orchestrates previously governed capabilities. It does not create a second collection engine, a general-purpose web agent, or a bypass around Source Governance, Provider Onboarding, Source Portfolio, Lot 22 conditional-provider controls, or approved ingestion paths.

## Governance boundary

```text
research question
!= permission to use every source

catalog entry
!= executable tool

analyst search link
!= automated provider execution

research plan
!= authorization

approved research step
+ exact plan source/tool/purpose/category scope
+ bounded host/path/budget/risk
+ positive persisted runtime controls when automated
= eligible step

eligible step
!= successful evidence capture
!= commercial signal
!= need hypothesis
!= opportunity
!= outreach authorization
```

## Step modes

Lot 23 keeps execution modes explicit:

- `persisted_search`: searches already-stored platform evidence and requires no external network path;
- `manual_link`: creates an analyst-visible HTTPS link and results in `manual_action_required`, never hidden browser automation;
- `automated_adapter`: can only use an already-registered governed adapter and requires positive authorization, executable source state, adapter capability, quota and applicable conditional-provider controls;
- `approved_ingestion`: accepts an existing evidence reference only through an explicitly approved ingestion-path identifier.

There is no unrestricted browser or arbitrary HTTP mode.

The only built-in approved-ingestion path in this lot is `existing-evidence-reference`. It does not fetch external content: result completion must reference an already persisted `Evidence` object and the referenced evidence must expose a compatible source identity and provenance reference.

## Research plan contract

A research plan binds:

- a research question;
- exact purpose and data category;
- plan state and expiry;
- maximum steps and automated steps;
- total and per-step cost limits;
- exact allowed source IDs;
- exact allowed tool IDs;
- exact approved step keys;
- allowed HTTPS hosts and path prefixes;
- maximum risk level.

A step binds source, tool, mode, purpose, category, sequence, estimated cost, risk and where applicable the target URL, query text or approved ingestion path.

Plan persistence keeps immutable revision history and decisions separate from mutable current state. Ordered steps, attempts and results are persisted independently so history can be reconstructed without treating the current projection as the audit log.

## Fail-closed eligibility

Before a step can be considered eligible, the evaluator checks:

- plan approved/in progress and not expired;
- step explicitly approved by key;
- source and tool included in the plan;
- purpose and data category exactly match the plan;
- risk is at or below the plan ceiling;
- plan step, automation and cost budgets remain available;
- URL steps use HTTPS and remain inside approved host/path scope;
- automated steps have positive source authorization, executable source state, exact adapter capability and quota;
- persisted onboarding state is ready where required;
- conditional-provider approval is current where applicable;
- provider pause and kill-switch state permit execution;
- manual links have an explicitly allowed manual-link path;
- ingestion steps use an approved ingestion path.

Blocked reasons are preserved individually rather than collapsed into a generic denial.

## Persisted runtime resolution

Automated runtime state is resolved from the existing control planes rather than copied into the research module:

- Source Governance for source status, authorization, approved purposes/categories and exact URL scope;
- Provider Onboarding for connection/readiness state;
- Source Portfolio for executable state, freshness, quota and cost budget;
- exact `AdapterCapability` registration for the requested source/tool pair;
- Lot 22 conditional-provider approval dossiers when the provider has a conditional integration contract;
- persisted pause and kill-switch controls.

Missing or incompatible state fails closed. Research planning never upgrades a catalog candidate into an executable source.

## Governed source ranking

The protected source-options API builds candidates from persisted source-governance, onboarding, portfolio, capability, health, conditional-control and source-value state.

Research-source candidates are ranked only after unsafe choices are filtered. Automated candidates must be authorized, executable and have quota. Manual links must be explicitly allowed. Prohibited-risk candidates are removed.

Remaining candidates are ordered deterministically using observed/source-defined value, freshness, cost and risk. Ranking does not authorize execution; final step eligibility is still required.

## Attempts, retries and interruption safety

Step execution records use persisted attempts with idempotence keys. The API separates attempt creation from completion and result capture so a retry or process interruption does not silently duplicate an external action.

Attempt/result persistence preserves:

- attempt identity and idempotence key;
- execution mode and state;
- completion/failure state;
- result references;
- usage/cost accounting;
- immutable research history.

A successful attempt is not itself evidence. Evidence capture still requires a valid evidence reference and provenance validation.

## Evidence and provenance handoff

Research results do not duplicate the Evidence store. A captured result must provide an `evidence:<uuid>` reference to an existing evidence record. The validation path verifies:

- the reference format;
- that the evidence record exists;
- that its source identity matches the research result when an expected source is present;
- that the evidence retains a recognized provenance reference such as `source-record:` or `raw-observation:`.

No research result is promoted directly to a `CommercialSignal`, `NeedHypothesis`, `Opportunity`, contact target or outreach authorization.

## Protected API

The research API is mounted under `/v1/research` and inherits the control-plane dependency. It exposes governed operations for:

- plan creation/upsert and listing/detail;
- immutable plan revisions and decisions;
- ordered steps;
- eligibility evaluation;
- attempt creation and completion;
- result capture;
- usage state;
- ranked source options.

The ranked `/source-options` route is explicitly included in the research router and is covered by integration tests.

## Analyst workspace

The Next.js research workspace exposes plans, states, budgets, step modes, decisions, execution eligibility, attempts, results and explicit manual-action states. It does not execute a provider from a page render and does not turn a manual-link workflow into hidden browser automation.

## Architecture boundary

The `research_orchestration` domain remains isolated from provider transports and commercial outcomes. Architecture tests prevent the bounded context from becoming an HTTP/browser/collector/opportunity/outreach shortcut.

The intended dependency direction remains:

```text
API / composition
  -> application / infrastructure orchestration
  -> research domain contracts

provider adapters / HTTP / browser
  X-> research domain

research domain
  X-> opportunities / outreach
```

## Explicit non-goals

Lot 23 does not add:

- unrestricted autonomous browsing;
- arbitrary HTTP/network tools;
- browser login automation;
- private portal access;
- active scanning, probing or exploitation;
- CAPTCHA/MFA/paywall/access-control bypass;
- copied cookies or authenticated browser sessions;
- fake identities or account cycling;
- autonomous opportunity creation;
- autonomous outreach.

## Implemented scope

The release candidate includes:

- `research_orchestration` bounded context and domain contracts;
- research plan, budget, usage, step, runtime-state and decision models;
- explicit persisted-search/manual-link/automated-adapter/approved-ingestion modes;
- deterministic source ranking after safety filtering;
- PostgreSQL persistence for plans, revisions, steps, decisions, attempts and results;
- reversible Alembic migration `20260809_0023`;
- persisted runtime resolution from Source Governance, Provider Onboarding, Source Portfolio and conditional-provider controls;
- exact adapter-capability, quota, cost, pause and kill-switch gating;
- replay-safe attempt/idempotence handling;
- Evidence-reference/provenance validation without duplicate evidence storage;
- protected plan/step/attempt/result/usage/source-options APIs;
- Next.js research workspace with explicit manual-action state;
- UTC-safe hydration across PostgreSQL and SQLite-backed tests;
- architecture, unit, integration, API, UI and full-regression coverage.

## Functional validation candidate

Exact functional SHA `1e2f7d5ac627eaa2c7a2826a9130ed227fefcb66` passed standard CI run #1402 (`31330116985`) before the release metadata/documentation synchronization:

- dependency consistency: PASS;
- installed dependency audit: PASS, no known vulnerabilities;
- Ruff: PASS;
- strict Mypy: PASS across 535 source files;
- architecture/release contracts: 34 passed;
- PostgreSQL 17 migration cycle: PASS through `20260809_0023`, including downgrade to base and upgrade to head;
- full pytest: 1027 passed, 0 failed;
- aggregate branch-aware coverage: 90.23%;
- frontend dependency audit: PASS;
- frontend TypeScript typecheck: PASS;
- frontend Next.js production build: PASS.

Because the release/version/documentation synchronization changes the branch head, these results are functional-candidate evidence only. The exact final `0.24.0` head must pass the complete workflow again before merge.

## Exit gate

Lot 23 is complete only when the documentation-complete `0.24.0` head passes every standard repository gate on one exact SHA and no subsequent repository commit changes that head before squash merge.

At that point analysts can run reproducible governed research while every automated step remains bounded by executable policy and authorization; manual search/dork links remain explicit analyst actions; retries do not duplicate external actions or evidence references; captured evidence retains provenance; and research output is not promoted directly to commercial conclusions.
