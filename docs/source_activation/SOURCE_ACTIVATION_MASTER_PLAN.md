# Source Activation Master Plan

## Purpose

The Source Activation programme closes the gap between a source being named or modelled and a source being genuinely usable by Cyber Intelligence Platform.

A source is **not integrated** merely because it appears in documentation, a Source Portfolio bundle, a provider schema, a mapper, or an approval dossier. The platform may report a source as fully integrated only when the machine-readable activation inventory proves the required runtime stages.

This programme is a delivery axis alongside product Lots 00–32. It does not reuse or renumber completed lots.

## Canonical activation lifecycle

```text
catalogued
  -> reviewed
  -> mapped
  -> adapter_present
  -> authorized
  -> executable
  -> scheduled (when periodic collection is required)
  -> live_tested
  -> fully integrated
```

The lifecycle is intentionally stricter than Source Portfolio `status`. Existing validated lots remain valid for the software capabilities they delivered, but their provider integrations are not retroactively labelled live-tested without evidence.

## Dispositions

Every known source must end in one explicit disposition:

- `active`: intended runtime source; full integration still requires all mandatory stages;
- `planned`: implementation or activation work remains;
- `manual`: analyst-only access is the approved method;
- `blocked`: a concrete legal, provider, security, privacy or technical dependency prevents activation;
- `replaced`: another source provides the approved capability;
- `duplicate`: the entry is redundant with another canonical source;
- `not_relevant`: reviewed and intentionally excluded from the product mission.

Terminal non-executable dispositions require a reason. Replaced and duplicate entries require a valid canonical source reference.

## Non-negotiable boundaries

Source Activation does not authorize collection. Network execution still requires positive Source Governance, Provider Onboarding where applicable, Source Portfolio capability, quota/cost controls and runtime registration.

```text
catalogued != reviewed
reviewed != authorized
mapped != adapter present
adapter present != executable
executable != scheduled
scheduled != live-tested
OSINT Framework entry != approved tool
search result != evidence
manual link != automated execution
```

The `source_activation` bounded context is prohibited from importing HTTP clients, browser runtimes, provider adapters, collection orchestration, Opportunities or Outreach. Architecture tests enforce this boundary.

## Wave A sequencing

Lot 23 is merged and validated as release `0.24.0` on `main`. Wave A is therefore delivered as three separately reviewable SA units **merged sequentially**, not as a permanent stacked branch chain:

1. SA-00 starts from the validated Lot 23 squash and is fully validated, then squash-merged to `main`;
2. SA-01 is rebuilt from the merged SA-00 `main` commit, fully validated, then squash-merged;
3. SA-02 is rebuilt from the merged SA-01 `main` commit, fully validated, then squash-merged;
4. SA-03 does not start until SA-02 is merged and the Wave A activation truth is coherent.

This sequencing prevents stale Lot 23 ancestry, makes each SA diff independently reviewable, and gives each unit one exact final SHA for CI evidence.

### SA-00 — Exhaustive source activation audit

Outcome:

- machine-readable activation truth layer;
- deterministic lifecycle invariants;
- OSINT Framework JSON normalization without execution;
- explicit future local-tool capability family including Sherlock;
- coverage matrix distinguishing modelled from genuinely executable sources;
- architecture and unit tests.

Clean restack base: Lot 23 squash `56944513fb4b30adbd40c02865f1a3e1899cb0d4` (`0.24.0`).

### SA-01 — Official vulnerability and open-data providers

In scope:

- NVD CVE API 2.0;
- FIRST EPSS;
- GitHub Global Security Advisories;
- CVE Services;
- OSV API;
- CIRCL Vulnerability-Lookup.

List/incremental providers receive governed runtime adapters, checkpointing and schedules. Query-oriented providers receive bounded target-driven adapters and remain unscheduled unless a safe provider-supported periodic model exists.

All data continues through the existing immutable SourceRecord and `vulnerability_knowledge` persistence path. Global vulnerability knowledge cannot create organization exposure or opportunities by itself.

### SA-02 — Governed web, search and archives

Outcome:

- real activation path for `public-web-sitemap` on explicitly enabled authorized targets;
- a real search-provider runtime path producing discovery leads only;
- a bounded public-archive discovery path preserving historical provenance;
- search/archive execution fail-closed when authorization, onboarding or required secrets are absent;
- no arbitrary browser, recursive crawler, login automation, CAPTCHA/MFA/paywall bypass or page-view-triggered collection.

## Later waves

- SA-03: domain, infrastructure and passive intelligence;
- SA-04: CTI, incidents, ransomware and telemetry;
- SA-05: identity and local OSINT tools, including Sherlock and reviewed equivalents;
- SA-06: corporate news, relationships and public business context;
- SA-07: LinkedIn, Discord and licensed/premium providers through approved methods only;
- SA-08: dedicated BrixHub access-path review and implementation;
- SA-09: isolated browser only for approved sources that cannot use API/static HTTP;
- SA-10: final source-completeness and live-validation gate.

## OSINT Framework synchronization contract

OSINT Framework is treated as a continuously reviewable candidate catalogue. Structured upstream JSON is normalized into `(name, url, category_path)` candidates. Importing a candidate does not create an adapter, authorize collection, schedule traffic or promote data into evidence.

New, changed or removed entries must be compared against the local source catalogue and assigned a disposition. Useful duplicates should reference the existing canonical capability instead of creating parallel adapters.

## Testing and validation

Each SA must satisfy the same repository development standards as numbered lots:

1. Ruff;
2. strict Mypy;
3. architecture tests;
4. migration upgrade/downgrade/upgrade when persistence changes;
5. complete backend regression suite with branch instrumentation and the repository `90%` coverage gate;
6. frontend audit/typecheck/build when frontend files or contracts are affected;
7. provider adapter contract tests and deterministic fixtures;
8. no live-network unit tests;
9. controlled live validation only after positive authorization;
10. exact final SHA CI before an SA can be considered validated.

Any code or documentation commit after the validated SHA invalidates the validation and requires a new full run.

## Definition of source completeness

At SA-10, no useful source may remain in an unknown state. Every candidate must be one of:

```text
fully integrated
manual with reason
blocked with reason
replaced by canonical source
duplicate of canonical source
not relevant with reason
```

A final percentage is calculated from machine-readable records, never from lot titles or documentation claims.
