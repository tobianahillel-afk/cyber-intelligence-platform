# Lot 14 — Validation Report

## Decision

- Technical implementation: `PASS` subject to the final-head CI rule.
- Security and source-governance boundary: `PASS`.
- Production source activation: `NOT AUTHORIZED`.
- Threat-actor interaction or victim-content collection: `FORBIDDEN`.
- Autonomous incident-to-opportunity or outreach action: `NOT IMPLEMENTED`.
- Release candidate: `0.15.0`.

## Delivered scope

- canonical public incident records;
- immutable source claim revisions;
- attacker allegation, media, researcher, company, regulator, CERT, provider, denial, correction, and retraction states;
- independent-source and syndication handling;
- exact, candidate, review-required, unresolved, and rejected organization links;
- separated occurrence, discovery, publication, modification, and confirmation dates;
- correction, retraction, replay, and historical-backfill behavior;
- reversible migration `20260806_0014`;
- protected list and detail APIs;
- `/incidents` analyst inventory and immutable chronology;
- governed, non-executable incident source candidates;
- backend and frontend non-regression coverage.

## Safety findings

### Allegation and confirmation

An attacker allegation cannot set `confirmed_at` and cannot independently produce the `confirmed` status. Official confirmation requires an active company confirmation, regulator notice, or CERT notice.

### Organization identity

A claimed organization name does not create an exact link. Exact links require a canonical organization UUID. Conflicting exact identifiers remove the resolved link and produce `review_required`.

### Syndication

Syndicated reports share an independence key. Multiple publications of the same upstream report count as one independent positive source.

### Ransomware metadata

Ransomware provider metadata maps only to a low-confidence attacker allegation. The schema rejects `.onion` URLs and stores no victim file, stolen data, credentials, or private communication.

### Commercial separation

The incident module does not import or write opportunity persistence. Historical or current incident metadata cannot autonomously create an opportunity, contact action, or outreach.

## Non-regression corrections made during implementation

- grouped FastAPI filters to remain below the ten-parameter architecture limit;
- registered incident models in the authoritative SQLAlchemy metadata;
- registered the incident API explicitly in application composition;
- added source and portfolio paths to typed settings;
- loaded incident catalogs through the common governance and source-portfolio bundles;
- extended authoritative metadata-table tests;
- gave the incident reconciliation test module a unique pytest import name;
- kept every incident source candidate non-executable and unscheduled.

No lint rule, type rule, architecture limit, migration check, test assertion, security audit, or coverage threshold was disabled or weakened.

## Test coverage

The lot adds tests for:

- attacker allegation versus official confirmation;
- syndicated versus independent sources;
- conflicting exact organization links;
- denial, correction, and retraction chronology;
- immutable replay and snapshot idempotence;
- historical-only incident filtering;
- metadata-only enforcement;
- official, public-report, and ransomware mappings;
- `.onion` rejection;
- protected API authentication, filters, detail, and missing records;
- non-executable source policies and portfolios;
- SQLAlchemy metadata registration and foreign keys;
- PostgreSQL upgrade, downgrade, and upgrade;
- frontend typecheck and production build.

## Successful release-candidate evidence

Before the release-documentation commits, PR head `6af0d989fd548a8a40d9e934de74447ab87c8e28` passed GitHub Actions CI run `#713` (`31110224814`):

- dependency consistency: pass;
- Python dependency audit: no known vulnerabilities;
- Ruff: pass;
- Mypy strict: 307 source files;
- architecture and release contracts: 13 passed;
- PostgreSQL `upgrade -> downgrade -> upgrade`: pass;
- backend suite: 638 passed, 0 failed;
- aggregate coverage: 91.09% with a 90% gate;
- frontend dependency audit: pass;
- TypeScript typecheck: pass;
- Next.js production build: pass.

This run proves the functional release candidate but is not the final merge authorization because version and documentation commits followed it.

## Final-head rule

The exact final pull-request head must rerun and pass every backend and frontend gate after all version and documentation changes. The final SHA, CI run, test count, coverage, review-thread count, and merge decision are recorded in pull request `#39`.

No commit may be added after that successful final run without invalidating the decision and rerunning all gates.
