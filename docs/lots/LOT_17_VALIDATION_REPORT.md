# Lot 17 — Validation report

## Decision

- Technical implementation: **PASS**, subject to the final-head CI rule.
- Security and source-governance boundary: **PASS**.
- Production provider activation: **NOT AUTHORIZED**.
- Active probing, direct validation and exposure verification: **FORBIDDEN**.
- Automatic opportunity creation, contact enrichment or outreach: **NOT IMPLEMENTED**.
- Target release: `0.18.0`.
- Authoritative pull request: #49.

## Delivered scope

Lot 17 delivers:

- canonical vendor, product, component, edition, ecosystem, platform, package identifier, support-status, and lifecycle models;
- immutable official advisory revisions and affected-version ranges;
- explicit current, corrected, superseded, withdrawn, and deleted advisory states;
- semantic, numeric, calendar, vendor, RPM, DEB, and unknown version schemes;
- introduced, fixed, last-affected, and limit boundaries;
- exact, product, component, edition, and version match precision;
- unknown, not-applicable, potentially-applicable, applicable, review-required, withdrawn, and superseded assessment states;
- evidence-backed assessments referencing organization, passive asset, technology snapshot, vulnerability, and advisory revision;
- immutable assessment history and idempotent current projections;
- correction and withdrawal propagation without destroying earlier evidence;
- reversible migration `20260807_0017`;
- protected list and detail APIs;
- the `/vulnerability-applicability` analyst workspace;
- three governed, unauthorized, unscheduled, and non-executable advisory candidates.

## Mandatory safety boundary

The release preserves all of the following:

- no active probe, scan, direct asset connection, or service validation;
- no authentication, credential use, or authenticated enumeration;
- no access-control bypass or exploitation;
- no binary or malware retrieval;
- no verified-exposure or compromise conclusion;
- no automatic opportunity, contact enrichment, or outreach;
- no provider execution without separately approved authorization, hosts, paths, licence, fields, quota, retention, cost, and schedule.

```text
technology mention
!= passive observation
!= observed version
!= affected-range applicability
!= verified exposure
!= compromise
!= current commercial opportunity
```

## Non-regression corrections made during final validation

- modernized SQLAlchemy row type aliases to the Python 3.12 syntax required by Ruff;
- aligned the SQLAlchemy result tuple with the non-null columns selected by the query;
- shortened the generated PostgreSQL index name that exceeded the 63-byte identifier limit;
- replaced reserved `.test` integration hostnames with syntactically valid public-domain fixtures without weakening passive-exposure validation;
- added the Lot 17 tables to the authoritative persistence metadata contract;
- normalized timestamps returned by persistence backends before comparing them with aware UTC domain timestamps;
- kept all domain timestamps strictly timezone-aware;
- added an integration scenario proving that an advisory correction advances the same current assessment projection while preserving immutable assessment history;
- did not disable or weaken a lint rule, type rule, architecture rule, migration check, security audit, domain invariant, or coverage threshold.

## Successful release-candidate evidence

PR head `6b85ffb2fbbc57292512212faa08f47c1d829c4c` passed GitHub Actions CI run `#872` (`31188055437`):

- dependency consistency: pass;
- Python dependency audit: no known vulnerabilities;
- Ruff: pass;
- Mypy strict: pass across **373 source files**;
- architecture, complexity, dependency, safety, release and roadmap contracts: **21 passed**;
- PostgreSQL `upgrade -> downgrade -> upgrade`: pass through migration `20260807_0017`;
- backend suite: **791 passed**, 0 failed;
- aggregate branch-aware coverage: **91.05%**, above the 90% gate;
- frontend dependency audit: pass;
- TypeScript typecheck: pass;
- Next.js production build: pass;
- backend diagnostic artifact: `backend-test-diagnostics`, artifact ID `8997664457`.

This run proves the functional release candidate. It is not by itself final merge authorization because this validation report and release-status documentation are committed afterward.

## Provider activation decision

Production activation of the three advisory candidate families is **not authorized by this software release**.

The checked-in entries remain metadata-only candidates with missing authorization, no approved hosts or paths, no registered runtime adapters, no schedules, and `executable: false`.

## Lot 18 handoff boundary

Lot 18 must start from the exact merged Lot 17 commit on `main`. It may add public news, regulatory, company-disclosure and change-event evidence, while preserving the distinctions among original disclosures, regulator statements, company statements, reporting, commentary and speculation.

Lot 18 must not turn a reported or speculative corporate change into a confirmed fact without source-aware evidence, and service-family mappings must remain separate from raw change events.

## Final-head rule

The exact final pull-request head must rerun and pass every backend and frontend gate after all release-documentation changes. The final SHA, CI run, test count, coverage, review-thread count and merge decision are recorded in pull request #49.

No commit may be added after that successful final run without invalidating the decision and requiring the complete validation chain again.
