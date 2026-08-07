# Lot 17 — Validation report

## Decision status

Final release decision: **PENDING FINAL CI**.

Target release: `0.18.0`.

Authoritative pull request: #49.

This report records the validation boundary for vendor advisories and organization-specific vulnerability applicability. It must be updated with the exact final pull-request head, GitHub Actions run identifier, test count, coverage, review state, and merge decision before release.

## Scope under validation

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
- reversible migration `20260807_0017`;
- protected list and detail APIs;
- the `/vulnerability-applicability` analyst workspace;
- three governed, unauthorized, unscheduled, and non-executable advisory candidates.

## Mandatory safety boundary

The release must preserve all of the following:

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

## Required final evidence

The exact final pull-request head must pass:

1. dependency consistency;
2. Python dependency audit;
3. Ruff;
4. strict Mypy;
5. architecture, complexity, dependency, safety, release, and roadmap contracts;
6. PostgreSQL `upgrade -> downgrade -> upgrade` through migration `20260807_0017`;
7. complete backend tests with aggregate branch-aware coverage at or above 90 percent;
8. frontend dependency audit;
9. TypeScript type checking;
10. Next.js production build;
11. zero unresolved review threads.

## Evidence table

| Gate | Result |
| --- | --- |
| Final pull-request head | Pending |
| GitHub Actions run | Pending |
| Dependency consistency | Pending |
| Python dependency audit | Pending |
| Ruff | Pending |
| Mypy strict | Pending |
| Architecture and release contracts | Pending |
| Reversible PostgreSQL migrations | Pending |
| Backend tests | Pending |
| Aggregate coverage | Pending |
| Frontend dependency audit | Pending |
| TypeScript typecheck | Pending |
| Next.js production build | Pending |
| Unresolved review threads | Pending |

## Provider activation decision

Production activation of the three advisory candidate families is **not authorized by this software release**.

The checked-in entries remain metadata-only candidates with missing authorization, no approved hosts or paths, no registered runtime adapters, no schedules, and `executable: false`.

## Merge rule

PR #49 must not merge until this report is updated from a successful GitHub Actions run on the exact final head. Any later commit invalidates earlier evidence and requires the complete validation chain to run again.
