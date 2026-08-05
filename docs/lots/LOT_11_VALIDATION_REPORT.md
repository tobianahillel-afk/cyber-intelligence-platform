# Lot 11 — Validation Report

## Decision

`PASS`

Lot 11 is implemented and functionally validated on commit:

```text
df1db1364fec4b7a52f597f658c9958e665acc35
```

Validated by GitHub Actions CI run:

```text
run number: 517
run id: 31025684920
```

The validated release version is `0.12.0`.

## Scope validated

The validation covers the complete Lot 11 delivery:

- canonical procurement procedures;
- immutable source publications and revisions;
- contract projections and lifecycle status;
- buyers, published awardees, consortium members, and unresolved-provider identity;
- amount and ISO currency handling;
- award, conclusion, notification, start, end, and renewal dates;
- explicit published, derived, estimated, and unknown date bases;
- complete cyber-service-family classification;
- TED award and result history;
- BOAMP result, award, amendment, and cancellation history;
- official DECP contracts and modifications through a bounded API adapter;
- historical backfill that reconstructs contracts without fabricating current opportunities;
- protected read-only procurement API;
- Contracts frontend workspace and official-publication timeline;
- release version `0.12.0`.

## CI evidence

### Dependency and security checks

- editable Python package installation: PASS;
- dependency consistency with `pip check`: PASS;
- installed Python dependency audit with `pip-audit --skip-editable`: PASS;
- no known Python dependency vulnerability reported;
- frontend dependency installation and audit: PASS.

### Static quality

- Ruff: PASS;
- strict Mypy: PASS;
- Mypy scope: 241 source files;
- frontend TypeScript typecheck: PASS;
- frontend production build: PASS.

### Architecture and release contracts

- architecture/release test suite: 13 passed;
- package and declared project versions agree on `0.12.0`;
- source, portfolio, and schedule registries remain machine-readable;
- duplicate IDs across registry bundles are rejected;
- protected API wiring and module boundaries pass the repository contracts.

### Database migrations

The PostgreSQL migration gate executed the complete cycle:

```text
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

Result: PASS.

Lot 11 migrations validated:

- `20260805_0010` — procurement procedures, publications, contracts, parties, and service classifications;
- `20260805_0011` — explicit contract notification date and proof basis.

Both migrations upgrade and downgrade successfully as part of the complete migration chain.

### Backend tests and coverage

```text
568 passed
1 warning
41.65 seconds
branch coverage: 91.65%
required coverage: 90.00%
```

The single warning is a third-party Starlette deprecation notice concerning the legacy `httpx` TestClient integration. It is non-blocking and does not represent a Lot 11 failure.

## Critical vertical proofs

### BOAMP

The BOAMP worker proof validates:

```text
official simulated HTTP response
  -> raw observation
  -> buyer organization
  -> immutable procurement publication
  -> contract projection
  -> unresolved published awardee
```

An historical award creates neither a current commercial signal nor an opportunity.

### TED

The TED worker proof validates:

```text
official simulated Search API response
  -> selected award fields
  -> raw observation
  -> buyer organization
  -> immutable award publication
  -> contract projection
  -> unresolved winner with published identifier
```

The test confirms amount, currency, conclusion date, checkpoint advancement, and zero current opportunities for the historical award.

### DECP

The DECP tests validate:

- official Explore API path;
- selected fields only;
- maximum 100 records per page;
- page-boundary enforcement;
- schema and content-type rejection;
- published buyer and awardee identifiers;
- amount in EUR;
- notification date kept separate from contract start;
- end date derived from published duration;
- renewal timing explicitly marked estimated;
- modification publication retained immutably while updating the same contract.

### Historical backfill

The adversarial backfill proof supplies both:

- valid procurement organizations and contract history;
- an intentionally invalid current commercial projection.

The validated result is:

- raw observation persisted;
- buyer persisted;
- procurement publication persisted;
- contract persisted;
- current commercial signal count remains zero;
- current opportunity count remains zero;
- source value event records zero current commercial projections.

This proves that historical reconstruction does not fabricate present buying intent.

### Protected API

The API integration proof validates:

- control-plane authentication;
- bounded pagination;
- filters by status, cyber-service family, buyer, and renewal window;
- rejection of an invalid renewal window;
- contract not-found response;
- published provider identity and identifier;
- multi-source chronology ordered deterministically;
- visibility of estimated renewal timing.

### Frontend

The frontend build validates:

- Contracts navigation;
- contract list and detail routes;
- server-side protected API access;
- no control-plane token exposed to browser code;
- status, buyer, provider, amount, source, and service-family presentation;
- visible published/derived/estimated/unknown badges;
- immutable official-publication timeline;
- responsive contract workspace styles.

## Invariants confirmed

1. An open notice is not an award or confirmed contract.
2. An award publication is not a resolved canonical provider identity.
3. Source publications are immutable and idempotent by revision.
4. Older publications cannot roll back a newer contract projection.
5. Amounts require an ISO alpha-3 currency.
6. Conclusion, notification, start, end, and renewal dates are not conflated.
7. Derived or estimated dates are never exposed as published facts.
8. Name-only providers remain unresolved or candidate.
9. Active notices may create current commercial signals; historical results and awards do not.
10. Backfill persists procurement history but ignores current commercial and identity projections.
11. Observation, organization, publication, contract, health, cursor, and audit writes share the relevant worker transaction.
12. API access is read-only and protected by the existing control-plane authentication.

## Source-governance confirmation

- TED uses the official anonymous Search API and selected metadata fields.
- BOAMP uses the official DILA Explore API and bounded windows.
- DECP uses the official `decp-2022-marches-valides` Explore API dataset and bounded pagination.
- Full procurement documents and bulk data exports are not mirrored by these adapters.
- Private portals and unauthorized authenticated areas remain outside scope.
- BrixHub remains quarantined and non-executable.

## Remaining non-blocking work

The following items are intentionally outside Lot 11 or non-blocking:

- global provider entity resolution beyond published identifiers;
- final multi-source signal fusion and calibrated scoring;
- Company 360 completion;
- replacement of the upstream Starlette TestClient deprecation path;
- activation of conditional or premium sources without approved authorization.

## Final conclusion

Lot 11 meets its exit gate. The implementation is suitable for pull-request review and integration into `main`, subject to the repository's normal review and merge process.
