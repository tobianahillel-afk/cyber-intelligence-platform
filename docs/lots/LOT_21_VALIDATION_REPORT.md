# Lot 21 — Validation report

## Status

`PENDING FUNCTIONAL CI`

This report must not be changed to `IMPLEMENTED_VALIDATED` until one exact functional candidate SHA passes every standard backend and frontend gate. Release documentation changes after that candidate require a second exact-SHA CI run before merge.

## Scope under validation

Lot 21 adds a bounded professional-context capability for analysts:

- source-qualified professional-person references that are never merged by display name alone;
- temporal role/team and direct reporting-line claims;
- organization-level and public professional business-contact context;
- authorized public-community metadata only;
- explicit lawful-basis, purpose, retention, review, suppression, correction and deletion state;
- deterministic snapshot replay and current projections;
- HMAC-backed erasure audit with redaction of raw identifying values;
- service-family relevance that is separate from signals, opportunities and outreach;
- protected persisted-data-only read APIs;
- analyst pages for professional references, evidence history and organization maps;
- three non-executable governed source-candidate families.

## Non-negotiable boundaries

```text
same display name
!= same person

professional role claim
!= verified employment

public business contact
!= personal contact detail

public professional profile
!= platform automation authorization

public/consented community context
!= private-life profile

service relevance
!= need hypothesis
!= commercial signal
!= opportunity

contact relevance
!= authorization to contact
```

Lot 21 introduces no active scanning, browser automation, authenticated social-platform scraping, private-message access, friend-graph collection, credential handling, automatic opportunity creation or outreach.

LinkedIn, Discord and other account/licence-dependent integrations remain Lot 22 and may execute only after their exact approval dossiers and scopes are positive.

## Persistence and privacy validation targets

Migration: `20260809_0021_professional_context.py`

Required migration gate:

```text
upgrade head
-> downgrade base
-> upgrade head
```

The persistence contract contains separate current projections and source snapshots for people, roles, reporting lines, contacts and community context. Replays are digest-idempotent and current state is reconciled from retained history.

A valid professional-person erasure is allowed to tombstone raw identifying values in both the current projections and retained source-history rows. The technical lineage, pseudonymous keys and HMAC suppression audit may remain so the system can prove that deletion occurred without retaining the erased raw identifier. Deleted current records reject ordinary provider replay, preventing accidental resurrection.

## Required functional evidence

The functional candidate is not accepted until all of the following pass on one exact SHA:

- `python -m pip check`;
- `pip-audit --skip-editable`;
- Ruff;
- strict Mypy;
- architecture and release contracts;
- PostgreSQL reversible migration validation through revision `0021`;
- complete pytest suite with aggregate branch-aware coverage >= 90%;
- `npm audit`;
- TypeScript typecheck;
- Next.js production build.

Lot-specific regression coverage must include:

- same-name people remain distinct;
- stale and historical employment transitions;
- direct reporting lines without transitive inference;
- business/personal contact separation;
- corrections, disputes and retractions;
- deterministic replay idempotence;
- public-community authorization boundaries;
- no source candidate can execute;
- suppression/deletion redacts raw values and cannot be undone by ordinary replay;
- API authentication and persisted-data-only reads;
- frontend production build.

## Current evidence

No final functional candidate is recorded yet. CI results from earlier partial heads do not validate this full vertical slice and must not be cited as release evidence.

## Release gate

After a functional candidate is fully green:

1. bump package/API release metadata to `0.22.0`;
2. synchronize README and the delivery roadmap so Lot 21 is `IMPLEMENTED_VALIDATED` and Lot 22 is next;
3. record the functional SHA, run ID and exact test/type/coverage metrics here;
4. run the complete standard CI again on the final documentation/release SHA;
5. confirm zero unresolved review threads;
6. mark PR #58 ready and squash-merge only with the exact final head SHA.
