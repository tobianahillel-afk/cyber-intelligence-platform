# Lot 16 — Validation report

## Decision

- Technical implementation: **PASS**, subject to the final-head CI rule.
- Security and source-governance boundary: **PASS**.
- Production provider activation: **NOT AUTHORIZED**.
- Active probing, direct validation, applicability assessment and exposure verification: **FORBIDDEN**.
- Automatic opportunity creation, contact or outreach: **NOT IMPLEMENTED**.
- Target release: `0.17.0`.
- Authoritative pull request: #47.

Superseded pull requests #43, #44, #45 and #46 were closed without discarding implementation commits.

## Delivered scope

Lot 16 delivers:

- canonical passive assets for public domains, hostnames, globally routable IPv4 and IPv6 addresses, certificate fingerprints, ASNs and provider-qualified cloud resources;
- immutable passive observation snapshots with separate observation, publication, modification and expiration times;
- current, historical, expired, corrected, retracted, deleted and unknown states;
- source-aware reconciliation and idempotent projection;
- exact, candidate, review-required, rejected and unresolved organization links;
- explicit CDN, shared-hosting, reseller, subsidiary, abandoned-domain and reassigned-address risks;
- technology mention, passive observation and observed-version evidence levels;
- deterministic provider revisions, supersession ordering and cycle rejection;
- reversible migration `20260806_0016`;
- protected list and detail APIs;
- the `/passive-exposure` analyst workspace;
- deterministic provider metadata mappings;
- governed but unauthorized, unscheduled and non-executable provider candidates.

## Mandatory safety boundary

The release preserves all of the following:

- no active probe, scan or direct asset connection;
- no authentication, credential use or authenticated enumeration;
- no access-control bypass or exploitation;
- no binary payload collection;
- no vulnerability-applicability assessment in Lot 16;
- no verified-exposure or compromise conclusion;
- no automatic opportunity, contact or outreach;
- no provider execution without a separately approved authorization, host/path contract, quota, retention policy and schedule.

A passive observation, technology mention or observed version is not proof that a named organization is vulnerable, exposed or compromised.

## Non-regression corrections made during final validation

- combined six nested-condition patterns reported by Ruff without weakening validation behavior;
- normalized one set-containment assertion to the repository style contract;
- prioritized the specific name-only organization-link invariant before the general exact-link invariant;
- preserved the rule that name-only evidence remains review-required or rejected;
- did not disable or weaken a lint rule, type rule, architecture limit, migration check, test assertion, security audit or coverage threshold.

## Successful release-candidate evidence

PR head `dd0d6e38283c1929d35bb82990f58fb4e6ebcc46` passed GitHub Actions CI run `#806` (`31131886950`):

- dependency consistency: pass;
- Python dependency audit: no known vulnerabilities;
- Ruff: pass;
- Mypy strict: pass across **354 source files**;
- architecture, complexity, dependency, safety, release and roadmap contracts: **18 passed**;
- PostgreSQL `upgrade -> downgrade -> upgrade`: pass through migration `20260806_0016`;
- backend suite: **757 passed**, 0 failed;
- aggregate branch-aware coverage: **90.99%**, above the 90% gate;
- frontend dependency audit: pass;
- TypeScript typecheck: pass;
- Next.js production build: pass;
- backend diagnostic artifact: `backend-test-diagnostics`, artifact ID `8976348526`.

This run proves the functional release candidate. It is not by itself final merge authorization because this validation report and release-status documentation are committed afterward.

## Provider activation decision

Production activation of the Lot 16 provider candidates is **not authorized by this release**.

The checked-in provider entries remain metadata-only candidates with missing authorization, no approved hosts or paths, no registered adapters, no collection schedule and `executable: false`.

## Lot 17 handoff boundary

Lot 17 must start from the exact merged Lot 16 commit on `main`. It must preserve the distinction among:

```text
technology mention
!= passive observation
!= observed version
!= vulnerability applicability
!= verified exposure
```

Lot 17 may reconcile official vendor advisories and affected ranges with organization-specific technology evidence, but it still cannot actively validate a prospect system or present ambiguous applicability as verified exposure.

## Final-head rule

The exact final pull-request head must rerun and pass every backend and frontend gate after all release-documentation changes. The final SHA, CI run, test count, coverage, review-thread count and merge decision are recorded in pull request #47.

No commit may be added after that successful final run without invalidating the decision and requiring the complete validation chain again.
