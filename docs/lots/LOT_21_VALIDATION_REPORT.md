# Lot 21 — Validation report

## Status

`FUNCTIONAL_CANDIDATE_VALIDATED — FINAL RELEASE CI REQUIRED`

The integrated functional candidate passed every standard backend and frontend gate. This release synchronization changes the commit SHA, so the functional result is supporting evidence only; the exact final release head must pass the same complete CI before merge.

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

The persistence contract contains 12 Lot 21 tables spanning current projections, source lineage, service relevance and deletion audit. The functional CI validated PostgreSQL `upgrade head -> downgrade base -> upgrade head` through revision `0021`.

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

## Final release gate

The release commit must now prove, on one exact SHA after all version and documentation changes:

1. package and API version `0.22.0` are consistent;
2. README and the delivery roadmap identify lots `00–21` as implemented/validated and Lot 22 as next;
3. every standard backend and frontend CI gate passes again;
4. aggregate branch-aware coverage remains at or above 90%;
5. zero unresolved review threads remain;
6. PR #58 is marked ready only after the final exact-SHA CI is green;
7. squash merge uses the exact validated head SHA.

No later commit may be added after the final validation without rerunning the complete release gate.
