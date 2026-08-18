# Lots 11–15 recovery code surface and test map

Status: **PLANNED_LOCKED_AFTER_DEEP_AUDIT**  
Recovery: **R03**  
Issue: **#177**

This document is the implementation navigation map. Paths may be refactored to preserve bounded-context conventions, but findings/invariants cannot be dropped or reassigned to vague future work.

## R03-L01 — ownership registry

Existing/new:
- `docs/lots/lots_11_15_recovery_findings.yml`
- all R03 documents.

Create:
- `tests/architecture/test_lots_11_15_recovery_ownership.py`.

## R03-L02 — procurement revision/amendment semantics

Existing:
- `src/cip/modules/procurement_history/domain/models.py`
- `src/cip/modules/procurement_history/infrastructure/models.py`
- `src/cip/modules/procurement_history/infrastructure/projections.py`
- `src/cip/adapters/sources/decp/mapper.py`
- `src/cip/adapters/sources/decp/schemas.py`
- BOAMP/TED procurement mappers.

Modify/create:
- explicit procurement revision lineage/current-head service;
- source revision metadata mapping;
- amendment-delta/effective-state merger;
- field provenance/explicit-clear representation if needed.

Tests:
- extend procurement persistence/API mapper integration;
- add replay-order and PostgreSQL concurrent-head tests;
- sparse amendments and explicit clears.

Migration likely if current-head/revision lineage/field provenance requires new columns/tables.

## R03-L03 — procurement identity and Lot08 buyer binding

Existing:
- DECP/BOAMP/TED mappers;
- procurement procedure/contract/publication persistence;
- `src/cip/modules/organizations/application/identity.py`
- organization identity persistence/claims;
- `src/cip/modules/organizations/infrastructure/persistence.py`.

Modify/create:
- procurement native-identifier assertion model;
- canonical procedure/contract identity decision service;
- durable merge/reject/split audit;
- buyer source-party→Lot08 organization binding port.

Tests:
- source-pair duplicate publications;
- false near-duplicate;
- buyer exact official ID vs name-only;
- reviewed resolution/reversal;
- PostgreSQL concurrent arrivals.

## R03-L04 — public-footprint head/current claims

Existing:
- `src/cip/modules/public_footprint/domain/models.py`
- `src/cip/modules/public_footprint/infrastructure/models.py`
- `src/cip/modules/public_footprint/infrastructure/projections.py`
- `src/cip/modules/public_footprint/infrastructure/queries.py`
- public-web/archive/search mappers and collection bridges.

Modify/create:
- resource causal-head persistence/validator;
- claim assertion support-version link/current validity;
- current desired-claim reconciliation;
- historical vs current query contracts.

Tests:
- `tests/integration/test_public_footprint_persistence.py`
- `tests/integration/test_public_footprint_api.py`
- PostgreSQL head races, tombstone/removal/reappearance, replay/backfill.

Migration likely for resource head and/or claim validity/support-version metadata.

## R03-L05 — vulnerability identity/lifecycle

Existing:
- `src/cip/modules/vulnerability_knowledge/domain/models.py`
- `src/cip/modules/vulnerability_knowledge/domain/reconciliation.py`
- `src/cip/modules/vulnerability_knowledge/infrastructure/projections.py`
- `src/cip/modules/vulnerability_knowledge/infrastructure/projection_hydration.py`
- `src/cip/modules/vulnerability_knowledge/infrastructure/models.py`
- vulnerability catalog mappers/query/list adapters.

Modify/create:
- alias assertion table/model with source/snapshot provenance;
- canonical vulnerability identity decision/history;
- lifecycle authority policy by identifier namespace/source;
- supersession target resolver/cycle guard.

Tests:
- extend `tests/integration/test_vulnerability_knowledge_api.py`;
- alias bridge after duplicates;
- concurrent bridge;
- OSV/GHSA withdrawal vs CVE.org state;
- authoritative rejection/supersession.

## R03-L06 — incident authority/supersession/type

Existing:
- `src/cip/modules/incident_intelligence/domain/models.py`
- `src/cip/modules/incident_intelligence/domain/reconciliation.py`
- incident persistence/hydration/queries;
- `src/cip/adapters/sources/incident_catalogs/`;
- `tests/integration/test_incident_intelligence_api.py`.

Modify/create:
- claim-type/source-kind authority matrix;
- source-local claim lineage/supersession resolver;
- incident type assertion/conflict model and authority-aware primary selection.

Tests:
- official mismatch rejection;
- cross-key correction/retraction;
- cycles/forks;
- allegation vs official type conflict;
- shuffled replay/concurrency.

Migration may add explicit claim-head/predecessor/type-decision metadata.

## R03-L07 — incident identity

Existing:
- incident claim/canonical persistence;
- organization identity links;
- corroboration/contradiction logic.

Modify/create:
- source-native incident identity assertion;
- canonical incident identity decision/group;
- durable merge/reject/split/review history;
- canonical identity lookup used before incident reconciliation.

Tests:
- different source IDs same event;
- same organization distinct incidents;
- reversible reviewed merge;
- independence preserved;
- PostgreSQL concurrent grouping.

## R03-L08 — threat indicator supersession/expiry

Existing:
- `src/cip/modules/threat_telemetry/domain/models.py`
- `src/cip/modules/threat_telemetry/domain/reconciliation.py`
- `src/cip/modules/threat_telemetry/infrastructure/projections.py`
- `src/cip/modules/threat_telemetry/infrastructure/projection_hydration.py`
- `src/cip/modules/threat_telemetry/infrastructure/queries.py`
- threat catalog adapters/mappers.

Modify/create:
- source-local indicator lineage/current-head semantics;
- clock-aware current assertion selector;
- local expiry reconciliation/sweep integration point;
- time-correct API filtering.

Tests:
- unit threat reconciliation;
- `tests/integration/test_threat_telemetry_api.py`;
- no-write time passage;
- independent source TTL;
- cross-key supersession and concurrency.

Migration may add current-head/expiry scheduling metadata.

## R03-L09 — campaign/malware threat-entity completion

Existing:
- threat telemetry module;
- `src/cip/modules/threat_telemetry/api/routes.py` currently indicator-only;
- threat relation records/snapshots;
- STIX/TAXII/threat-catalog mappings where present;
- vulnerability knowledge for typed vulnerability targets.

Create/extend:
- campaign domain entity/snapshot/assertion;
- malware-family domain entity/snapshot/assertion;
- alias/identity/review persistence;
- typed temporal relation persistence and hydration;
- protected campaign/malware list/detail/timeline routes/schemas/view models;
- frontend views only if the historical analyst UI contract is implemented in this product surface.

Tests:
- campaign/malware identity and relations;
- source provenance;
- current/historical chronology;
- retraction/expiry;
- API authorization/list/detail/search;
- migration reversibility.

## R03-L10 — qualification

One exact implementation SHA must run:
- architecture/no-orphan guard;
- all affected unit/integration suites;
- PostgreSQL concurrency/replay suites;
- migration up/down/up;
- backend lint/type/full regression/coverage;
- frontend gates if touched;
- security/secret/redaction gates;
- review-thread audit;
- exact-head CI.

## Explicitly out of R03

Do not add:
- Lot19 relationship/incumbent/renewal inference;
- Lot20 global corporate/entity graph engine;
- second global outbox/reconciliation system beside Lot28;
- SA21 provider activation work;
- active IOC probing, malware download/execution or prospect scanning;
- DNS/address safety framework owned by Lot30;
- privacy deletion engine owned by Lot31.
