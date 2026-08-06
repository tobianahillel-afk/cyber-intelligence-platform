# Lot 15 — Validation Report

## Decision

- Technical implementation: `PASS` subject to the final-head CI rule.
- Security and source-governance boundary: `PASS`.
- Production provider activation: `NOT AUTHORIZED`.
- Direct indicator connection, active scanning, or binary retrieval: `FORBIDDEN`.
- Organization compromise or exposure inference from global telemetry: `FORBIDDEN`.
- Autonomous opportunity creation or outreach: `NOT IMPLEMENTED`.
- Release candidate: `0.16.0`.

## Delivered scope

- canonical IPv4, IPv6, domain, URL, file-hash, certificate-fingerprint, and email indicators;
- deterministic public-safe normalization;
- immutable source snapshots and current source-aware projections;
- malicious, suspicious, historical, expired, sinkholed, benign, shared-infrastructure, unknown, and retracted states;
- source independence and sensor scope;
- first-seen, last-seen, expiration, correction, supersession, and replay history;
- campaign, malware-family, vulnerability, phishing-kit, and infrastructure relations;
- reversible migration `20260806_0015`;
- protected list and detail APIs;
- `/threat-intelligence` analyst inventory and immutable source history;
- selected STIX/TAXII, phishing, passive-DNS, certificate, and malware-metadata mappings;
- governed, non-executable source candidates;
- explicit architecture tests forbidding network, organization, and opportunity dependencies;
- backend and frontend non-regression coverage.

## Safety findings

### No organization attribution

The threat-telemetry domain contains no organization identifier. It cannot independently identify a prospect asset, claim an organization is exposed, or claim an organization is compromised.

### No active validation

The module imports no HTTP client, socket client, subprocess facility, organization module, or opportunity module. Snapshots reject any claim that direct validation was performed.

### No binary collection

The domain accepts metadata only. Provider schemas reject binary payloads, malware sample availability, and sample download URLs.

### Public-safe normalization

Private, loopback, link-local, multicast, unspecified, and other non-global IP addresses are rejected. Local and internal domain suffixes are rejected. URLs require HTTP or HTTPS and reject embedded credentials.

### Source independence

Republished or syndicated records share an independence key and count once. Independent positive-source counts therefore do not increase merely because the same upstream feed appears in multiple providers.

### Contradiction and reclassification

Benign, sinkholed, expired, or retracted revisions do not erase prior malicious or suspicious revisions. The current projection exposes observed states and an explicit conflict flag.

## Provider activation boundary

Installed source candidates are:

- licensed STIX/TAXII;
- licensed phishing metadata;
- licensed passive DNS;
- licensed certificate telemetry;
- licensed malware metadata.

Every candidate remains:

- `draft` in source governance;
- authorization `missing`;
- automated collection `false`;
- approved hosts and paths empty;
- raw-content storage disabled;
- portfolio status `candidate`;
- `executable: false`;
- unscheduled.

The common runtime synchronizes these catalog entries but registers no adapter. No credential, licence interpretation, provider agreement, quota, target, tenant, or production schedule was invented.

## Non-regression corrections made during implementation

- simplified temporal validation to satisfy the executable style contract;
- corrected a formatting-only Ruff failure in relation assertions;
- corrected the expected immutable relation-history cardinality;
- added explicit UTC normalization for persisted SQLite timestamps while preserving strict UTC-aware domain requirements;
- registered threat tables in authoritative SQLAlchemy metadata;
- registered the protected API in application composition;
- loaded source and portfolio candidates through common registry bundles;
- extended typed settings and authoritative metadata-table tests;
- added structural tests forbidding network and commercial dependencies;
- kept all new sources non-executable and unscheduled.

No lint rule, type rule, architecture limit, migration check, test assertion, security audit, or coverage threshold was disabled or weakened.

## Test coverage

The lot adds tests for:

- IPv4, IPv6, IDNA domains, URLs, hashes, certificates, and email normalization;
- malformed, private, local, internal, and credential-bearing indicators;
- source syndication and independent-source counting;
- benign conflict, sinkhole, expiration, retraction, and historical states;
- shared infrastructure and relation reconciliation;
- binary and direct-validation rejection;
- STIX revocation, phishing-kit, and malware-family mappings;
- sample and download-path rejection;
- non-executable source governance and portfolio state;
- replay idempotence and immutable relation history;
- protected API authentication, filters, detail, and missing records;
- SQLAlchemy metadata registration and foreign keys;
- PostgreSQL upgrade, downgrade, and upgrade;
- frontend typecheck and production build;
- architecture-level network and commercial dependency exclusion.

## Successful release-candidate evidence

Before release-documentation commits, PR head `790194ba57a3d00d75c81a708e36d098161cd39d` passed GitHub Actions CI run `#769` (`31115694480`):

- dependency consistency: pass;
- Python dependency audit: no known vulnerabilities;
- Ruff: pass;
- Mypy strict: pass;
- architecture and release contracts: 15 passed;
- PostgreSQL `upgrade -> downgrade -> upgrade`: pass through migration `20260806_0015`;
- backend suite: 662 passed, 0 failed;
- aggregate coverage: 91.07% with a 90% gate;
- line coverage: 93.90%;
- branch coverage: 78.25%;
- frontend dependency audit: pass;
- TypeScript typecheck: pass;
- Next.js production build: pass.

This run proves the functional release candidate but is not final merge authorization because version and documentation commits followed it.

## Final-head rule

The exact final pull-request head must rerun and pass every backend and frontend gate after all version and documentation changes. The final SHA, CI run, test count, coverage, review-thread count, and merge decision are recorded in pull request `#41`.

No commit may be added after that successful final run without invalidating the decision and rerunning all gates.
