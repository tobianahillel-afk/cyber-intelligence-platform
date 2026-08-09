# Lot 21 — Validation report

## Status

`FINAL_RELEASE_EVIDENCE_RECORDED — EXACT REPORT SHA CI REQUIRED`

The integrated functional candidate and the synchronized `0.22.0` release head have both passed every standard backend and frontend gate. This report-only commit records that release-head evidence and therefore creates one new SHA. No code, version, roadmap, README, migration, API, or UI content changes in this commit. The exact report SHA must now pass the same standard CI once more before merge.

## Scope validated

Lot 21 adds a bounded professional-context capability for analysts:

- source-qualified professional-person references that are never merged by display name alone;
- temporal role/team and direct reporting-line claims without transitive hierarchy inference;
- organization-level and public professional business-contact context;
- authorized public-community metadata only;
- explicit lawful-basis, purpose, retention, review, suppression, correction and deletion state;
- deterministic snapshot replay and current projections;
- HMAC-backed erasure audit with redaction of raw identifying values and replay-resurrection protection;
- service-family relevance that remains separate from signals, opportunities and outreach;
- protected persisted-data-only read APIs;
- analyst pages for professional references, evidence history and organization maps;
- three governed source-candidate families that remain non-executable.

## Non-negotiable boundaries

```text
same display name != same person
professional role claim != verified employment
public business contact != personal contact detail
public professional profile != platform automation authorization
public/consented community context != private-life profile
service relevance != need hypothesis != commercial signal != opportunity
contact relevance != authorization to contact
```

Lot 21 introduces no active scanning, browser automation, authenticated social-platform scraping, private-message access, friend-graph collection, credential handling, automatic opportunity creation or outreach. LinkedIn, Discord, BrixHub and other account/licence-dependent integrations remain Lot 22 and require their own positive approval dossiers before execution.

## Persistence and privacy validation

Migration: `20260809_0021_professional_context.py`.

The persistence contract contains 12 Lot 21 tables spanning current projections, source lineage, service relevance and deletion audit. CI validated PostgreSQL `upgrade head -> downgrade base -> upgrade head` through revision `0021`.

A valid professional-person erasure may tombstone raw identifying values in current projections and retained source-history rows while preserving pseudonymous technical lineage and the HMAC suppression audit. Deleted current records reject ordinary provider replay so erased values cannot be accidentally resurrected.

## Functional candidate evidence

Exact integrated functional SHA: `243a9d62acd77314cf7eca7f7c80415ecfa31696`.

GitHub Actions run: `31308364769` (CI #1182).

- `python -m pip check`: green;
- `pip-audit --skip-editable`: green, no known vulnerabilities;
- Ruff: green;
- strict Mypy: `484` source files, no issues;
- architecture/release contracts: `29 passed`;
- PostgreSQL reversible migration validation through `0021`: green;
- complete pytest suite: `917 passed`;
- aggregate branch-aware coverage: `90.37%`;
- `npm audit --audit-level=high`: green;
- TypeScript typecheck: green;
- Next.js production build: green.

Backend diagnostic artifact ID: `9036672075`.

## Synchronized release-head evidence

Exact synchronized release SHA: `3fb687a03a164304f6cdcc04abd0f807d93a718d`.

GitHub Actions run: `31309088139` (CI #1190).

- package build/install identifies `cyber-intelligence-platform==0.22.0`;
- `python -m pip check`: green;
- `pip-audit --skip-editable`: green, no known vulnerabilities;
- Ruff: green;
- strict Mypy: `484` source files, no issues;
- architecture/release contracts: `29 passed in 6.77s`;
- PostgreSQL `upgrade head -> downgrade base -> upgrade head` through `0021`: green;
- complete pytest suite: `917 passed, 1 warning in 88.88s`;
- aggregate branch-aware coverage: `90.37%` (`22580` statements, `4680` branches);
- `npm audit --audit-level=high`: green;
- TypeScript typecheck: green;
- Next.js production build: green.

Backend diagnostic artifact ID: `9036864675`.

README and `docs/PROJECT_DELIVERY_PLAN.md` on that release head identify version `0.22.0`, lots `00–21` as implemented/validated, and Lot 22 as the next locked lot.

## Exact report-SHA gate

This report-only evidence commit must now prove, on one final exact SHA:

1. every standard backend and frontend CI gate passes again;
2. aggregate branch-aware coverage remains at or above 90%;
3. zero unresolved review threads and no blocking review remain;
4. PR #58 is marked ready only after that exact-SHA CI is green;
5. squash merge uses that exact validated head SHA.

No later commit may be added after this validation without rerunning the complete release gate.
