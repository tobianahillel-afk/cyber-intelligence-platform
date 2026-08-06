# Lot 16 — Validation report

## Decision status

Final release decision: **PENDING FINAL CI**.

Target release: `0.17.0`.

PR #47 is the authoritative Lot 16 pull request. Superseded PRs #43, #44, #45, and #46 were closed without discarding any implementation commit.

This report records the exact validation boundary for Lot 16. It must be updated with the final pull-request head, GitHub Actions run identifier, test counts, coverage and review state before the pull request can merge.

## Scope under validation

Lot 16 delivers:

- canonical passive assets for public domains, hostnames, globally routable IP addresses, certificate fingerprints, ASNs and provider-qualified cloud resources;
- immutable passive observation snapshots with separate observation, publication, modification and expiration times;
- current, historical, expired, corrected, retracted, deleted and unknown states;
- source-aware reconciliation and idempotent projection;
- exact, candidate, review-required, rejected and unresolved organization links;
- explicit CDN, shared-hosting, reseller, subsidiary, abandoned-domain and reassigned-address risks;
- technology mention, passive observation and observed-version evidence levels;
- reversible migration `20260806_0016`;
- protected list and detail APIs;
- the `/passive-exposure` analyst workspace;
- deterministic provider metadata mappings;
- governed but unauthorized and non-executable provider candidates.

## Mandatory safety boundary

The release must preserve all of the following:

- no active probe, scan or direct asset connection;
- no authentication, credential use or authenticated enumeration;
- no access-control bypass or exploitation;
- no binary payload collection;
- no vulnerability-applicability assessment in Lot 16;
- no verified-exposure or compromise conclusion;
- no automatic opportunity, contact or outreach;
- no provider execution without a separately approved authorization, host/path contract, quota, retention policy and schedule.

A passive observation, technology mention or observed version is not proof that a named organization is vulnerable, exposed or compromised.

## Required final evidence

The exact final pull-request head must pass:

1. dependency consistency;
2. Python dependency audit;
3. Ruff;
4. strict Mypy;
5. architecture, complexity, dependency, safety, release and roadmap contracts;
6. PostgreSQL `upgrade -> downgrade -> upgrade` through migration `20260806_0016`;
7. the complete backend suite with aggregate branch-aware coverage at or above 90 percent;
8. frontend dependency audit;
9. TypeScript type checking;
10. Next.js production build.

## Evidence table

| Gate | Result |
| --- | --- |
| Final pull-request head | Pending |
| GitHub Actions run | Requested; no run indexed yet |
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
| Unresolved review threads | 0 at last inspection |

## Provider activation decision

Production activation of the Lot 16 provider candidates is **not authorized by this release**.

The checked-in provider entries remain metadata-only candidates with missing authorization, no approved hosts or paths, no registered adapters, no collection schedule and `executable: false`.

## Current validation state

GitHub Status currently reports Actions and Webhooks operational. PR #47 was opened on the complete implementation history after earlier pull-request events failed to create a run. This report update requests a fresh `synchronize` event on the authoritative branch; the lot remains blocked from merge until a complete run is attached to the resulting exact head.

## Merge rule

PR #47 must not merge until this report is updated from a successful GitHub Actions run on the exact final head. Any later commit invalidates earlier evidence and requires the complete validation chain to run again.
