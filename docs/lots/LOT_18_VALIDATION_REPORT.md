# Lot 18 — Validation report

## Decision

- Technical implementation: **PASS**, subject to the final-head CI rule.
- Source-governance and copyright-minimization boundary: **PASS**.
- Production provider activation: **NOT AUTHORIZED**.
- Autonomous browsing, paywall/authentication bypass, and private-source access: **FORBIDDEN**.
- Automatic opportunity creation, contact enrichment, and outreach: **NOT IMPLEMENTED**.
- Target release: `0.19.0`.
- Authoritative pull request: #51.

## Delivered scope

Lot 18 delivers:

- canonical material-change events for acquisitions, leadership, funding, restructuring, geographic expansion, cloud/digital programs, regulatory actions, breaches, audits, certifications, and security commitments;
- immutable public claim revisions with separate event, publication, modification, expiry, and persistence times;
- official filing, regulator, company, media, analyst, and other source classifications;
- confirmation, report, speculation, dispute, correction, and retraction semantics;
- explicit under-review, speculative, reported, confirmed, disputed, corrected, retracted, and stale event states;
- syndication-aware independent-source counts;
- exact, candidate, review-required, unresolved, and rejected organization links;
- deterministic supersession handling without deleting historical evidence;
- bounded 500-character excerpts and metadata-only provider contracts;
- separate service-family mappings that do not mutate raw evidence;
- reversible migration `20260807_0018`;
- protected list/detail APIs;
- the `/corporate-changes` analyst workspace;
- three governed, unauthorized, unscheduled, non-executable source candidates.

## Mandatory evidence boundary

```text
public mention
!= independent corroboration
!= official confirmation
!= service need
!= opportunity
!= authorization to contact
```

A media or analyst report remains reporting even when widely syndicated. Only active official-filing, regulator, or company confirmation evidence can provide official confirmation in this lot.

## Mandatory safety boundary

The release preserves all of the following:

- no autonomous browsing;
- no paywall, CAPTCHA, MFA, authentication, or access-control bypass;
- no private-source or private-portal access;
- no active scanning, probing, authentication, exploitation, or credential use;
- no victim files, stolen datasets, or private communications;
- no full copyrighted article storage;
- no contact enrichment;
- no automatic opportunity creation;
- no autonomous outreach;
- no provider execution without separately approved authorization, hosts, paths, licence, fields, quota, retention, cost, and schedule.

## Non-regression work completed during implementation

- preserved immutable source/article revisions while allowing current-event supersession;
- prevented syndicated copies from inflating independent corroboration counts;
- kept event time, publication time, provider modification time, expiry, and persistence time separate;
- made conflicting exact organization identities converge to review-required instead of forcing a merge;
- isolated service-family mappings from raw evidence tables;
- kept source providers metadata-only and non-executable while loading their governance metadata into the common runtime;
- used short Alembic index names compatible with PostgreSQL identifier limits;
- split FastAPI filter dependencies below the repository review threshold for required parameters;
- split the corporate-change page and filter state so React components remain below the repository review threshold;
- renamed the Lot 18 reconciliation test module to avoid pytest basename collision with the incident-intelligence suite;
- did not disable or weaken lint, typing, architecture, migration, security, evidence, or coverage controls.

## Successful functional release-candidate evidence

An implementation head preceding release-documentation commits passed GitHub Actions CI run `#901` (`31192615444`):

- dependency consistency: pass;
- Python dependency audit: pass;
- Ruff: pass;
- Mypy strict: pass;
- architecture, complexity, dependency, safety, release, and roadmap contracts: **22 passed**;
- PostgreSQL `upgrade -> downgrade -> upgrade`: pass through migration `20260807_0018`;
- backend suite: **812 passed**, 0 failed;
- aggregate branch-aware coverage: **91.03%**, above the 90% gate;
- frontend dependency audit: pass;
- TypeScript typecheck: pass;
- Next.js production build: pass;
- backend diagnostic artifact: `backend-test-diagnostics`, artifact ID `8999527380`.

This proves the implemented vertical slice before final release/version/documentation synchronization. It is not merge authorization for a later head.

## Provider activation decision

Production activation of the three Lot 18 source families is **not authorized by this software release**.

The checked-in entries remain `draft`/`candidate`, with missing authorization, no approved hosts or paths, no schedules, no runtime adapters, and `executable: false`.

## Lot 19 handoff boundary

Lot 19 must start from the exact merged Lot 18 commit on `main`.

Its relationship model must preserve direction, role, time, source, confidence, and review state, while distinguishing claimed, observed, contracted, historical, and inferred relationships. Marketing claims cannot silently become contract evidence, and a historical provider cannot silently become a current incumbent.

## Final-head rule

The exact final pull-request head must rerun and pass every backend and frontend gate after all release, README, roadmap, and validation-document changes.

Transient release-finalization workflows are not part of the release boundary. The final validated head must contain the repository's standard CI workflow only, with all temporary Lot 18 synchronization/finalization workflows removed.

The final SHA, CI run, test count, coverage, review-thread count, and merge decision are recorded in pull request #51. Any commit added after that successful final run invalidates the decision and requires the complete validation chain again.
