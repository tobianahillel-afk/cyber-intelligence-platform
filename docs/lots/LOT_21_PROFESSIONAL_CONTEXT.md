# Lot 21 — Professional organization maps, contacts, and public community signals

## Status

Release candidate `0.22.0` is implemented on `agent/professional-organization-maps` from exact Lot 20 squash `108144a9ad52805c6127dfffb3b31050313e8070`.

The integrated functional candidate `243a9d62acd77314cf7eca7f7c80415ecfa31696` passed every standard backend and frontend gate in CI run `31308364769`. The lot still requires the same complete CI on the exact final release/documentation SHA before squash merge.

## Outcome

Lot 21 adds source-aware professional context for analysts: professional people references, employment and role chronology, teams and reporting-line claims, published business contact channels, and bounded public-community context.

It is deliberately not a private-life people graph. Same names never create an automatic person merge. Public profile or community evidence never authorizes automation of the source platform. Contact relevance never creates an opportunity or authorizes outreach.

## Privacy and evidence boundary

```text
professional role claim
!= verified employment

same display name
!= same person

public business contact channel
!= personal contact detail

public professional profile reference
!= authorization to automate the platform

public or consented community context
!= private-life profile

service-family relevance
!= cyber need

contact relevance
!= opportunity
!= outreach authorization
```

## Canonical controls reused

Lot 21 reuses the repository's existing governance primitives instead of creating a parallel privacy system:

- `DataCategory.PROFESSIONAL_CONTACT` for professional contact processing;
- canonical prohibited categories including `PRIVATE_PERSONAL_DATA` and `PRIVATE_COMMUNICATION`;
- `RetentionPolicy` and the checked-in `policies/retention.yml` rule for professional contacts;
- HMAC-based suppression channels for email, phone, professional profile, and organization;
- the canonical `CyberServiceFamily` taxonomy for role/service relevance;
- source authorization, approved-purpose, host/path, review, retention, and execution gates from source governance.

The current policy retains `professional_contact` for 1095 days with a 180-day review interval. Suppression identifiers remain hashed and the raw suppression identifier is not stored.

## Bounded context

The `professional_context` module owns:

1. source-aware professional-person references;
2. immutable employment/role/team claims;
3. immutable reporting-line claims;
4. public business contact-channel evidence;
5. public/consented community-context evidence;
6. separate service-family relevance mappings;
7. current read projections and analyst review state.

It does not own organization identity, opportunity creation, outreach, browser automation, or source collection runtime.

## Person identity rule

A `person_key` is source-qualified or analyst-issued. It is never derived from a display name alone. Two sources containing the same name therefore remain separate references until an explicit reviewed identity decision exists.

Lot 21 does not introduce fuzzy automatic cross-source person resolution.

## Employment and organization map

Role evidence records organization linkage separately from the raw professional claim. Claims carry title, optional team, source lineage, confidence, review state, validity, freshness, correction/retraction state, processing context, and retention deadline.

Reporting-line claims are separate directed evidence records. They cannot self-reference and are never transitively inferred into a hierarchy. A weak reporting claim remains weak evidence in the organization map.

## Business contact channels

Only these channel families are modeled:

- published business email;
- business email pattern;
- organization switchboard;
- organization contact form;
- public professional profile reference.

The model contains no personal-address or private-message channel. A switchboard is organization-level public contact context, not a personal phone. A profile reference is navigation/evidence metadata only and cannot authorize automated collection.

## Community context

Community evidence is accepted only with an explicit authorized acquisition mode such as an approved API, administrator-installed integration, authorized export, or reviewed manual import. It is bounded metadata and cannot contain private-message content or sensitive private-life attributes.

LinkedIn, Discord, premium, account-scoped, and other conditional execution paths remain Lot 22 concerns. Lot 21 models evidence contracts and non-executable source candidates but does not activate those integrations.

## Service relevance

Professional role/team evidence may map to canonical `CyberServiceFamily` values with a rationale and confidence. This mapping is a navigation aid only:

```text
role relevance -> analyst context
role relevance != commercial signal
role relevance != need hypothesis
role relevance != opportunity
```

## Persistence

The implemented persistence slice uses current projections plus source evidence snapshots, with explicit correction/suppression/deletion state and reversible migration `20260809_0021`.

A validated erasure may tombstone raw identifying values in current projections and retained source-history rows while preserving pseudonymous lineage and the HMAC suppression audit. Deleted projections reject ordinary provider replay so erased values are not accidentally resurrected.

Normal API/UI reads are persisted-data only. No analyst page view launches external collection.

## Regression evidence

The integrated functional candidate validated:

- same-name people never merge by name;
- stale and historical employment are distinct from current employment;
- conflicting/corrected/retracted role claims preserve history;
- reporting lines remain directed and non-transitive;
- business channels cannot be represented as personal channels;
- professional profile references do not authorize automation;
- retention, suppression, correction, and deletion states propagate;
- community evidence requires an approved acquisition mode/reference;
- service relevance remains separate from opportunities and outreach;
- protected API, UI, migration, architecture, typing, dependency audit, coverage, and full regression gates.

The exact final release/documentation SHA must repeat all standard gates before merge.
