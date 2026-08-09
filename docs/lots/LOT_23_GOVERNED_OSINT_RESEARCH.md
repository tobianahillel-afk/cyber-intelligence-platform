# Lot 23 — Analyst research and governed OSINT catalog orchestration

## Status

Implementation in progress on `agent/governed-osint-research` from exact Lot 22 squash `10c547752ad12e76a61b394248960d4640bc0885`.

Target release: `0.24.0`, not bumped until a complete functional candidate is green.

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
- `automated_adapter`: can only use an already-registered governed adapter and requires positive authorization, executable source state, adapter capability and quota;
- `approved_ingestion`: accepts evidence only through a separately approved ingestion path.

There is no unrestricted browser or arbitrary HTTP mode.

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

## Fail-closed eligibility

Before a step can be considered eligible, the evaluator checks:

- plan approved/in progress and not expired;
- step explicitly approved by key;
- source and tool included in the plan;
- purpose and data category exactly match the plan;
- risk is at or below the plan ceiling;
- plan step, automation and cost budgets remain available;
- URL steps use HTTPS and remain inside approved host/path scope;
- automated steps have positive source authorization, executable source state, adapter capability and quota;
- manual links have an explicitly allowed manual-link path;
- ingestion steps use an approved ingestion path.

Blocked reasons are preserved individually rather than collapsed into a generic denial.

## Governed source ranking

Research-source candidates are ranked only after unsafe choices are filtered. Automated candidates must be authorized, executable and have quota. Manual links must be explicitly allowed. Prohibited-risk candidates are removed.

Remaining candidates are ordered deterministically using observed/source-defined value, freshness, cost and risk. Ranking does not authorize execution; final step eligibility is still required.

## Explicit non-goals

Lot 23 does not add:

- unrestricted autonomous browsing;
- browser login automation;
- private portal access;
- active scanning, probing or exploitation;
- CAPTCHA/MFA/paywall/access-control bypass;
- arbitrary provider HTTP clients;
- copied cookies or authenticated browser sessions;
- autonomous opportunity creation;
- autonomous outreach.

## Current first slice

Implemented first:

- `research_orchestration` bounded context;
- research plan, budget, usage, step, runtime-state and decision contracts;
- explicit persisted-search/manual-link/automated-adapter/approved-ingestion modes;
- host/path/purpose/category/risk/budget fail-closed eligibility;
- deterministic governed source ranking;
- architecture contracts forbidding network/browser/collector/opportunity/outreach imports;
- unit tests for denied automation, manual-action distinction, budget boundaries, domain/path restrictions and governed ranking.

## Next implementation slices

The next slices will add:

- PostgreSQL persistence for plans, immutable revisions, ordered steps, decisions and results;
- persisted runtime resolution from the existing source-governance/onboarding/portfolio/conditional-provider read models;
- replay-safe step attempts and interruption handling;
- evidence capture references that point into approved existing ingestion/provenance paths rather than duplicating evidence storage;
- protected APIs for plans, steps, approvals, attempts, results and handoff;
- a research workspace with explicit manual-action states;
- full migration/API/UI/regression validation.

## Exit gate

Analysts can run reproducible governed research while every automated step remains bounded by an executable policy and authorization. Manual search/dork links remain explicit analyst actions, retries do not duplicate external actions or evidence references, and captured evidence retains provenance without being promoted directly to commercial conclusions.
