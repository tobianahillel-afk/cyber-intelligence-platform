# Lots 11–15 recovery code surface and test map

Status: **AUDIT_SIGNED_OFF_IMPLEMENTATION_PENDING**  
Recovery: **R03**  
Issue: **#177**

This is the implementation navigation map. Candidate new filenames are suggestions; maintain bounded-context conventions if a better local layout exists. Findings/invariants may not be dropped.

## R03-L01 — ownership registry

**Existing:**
- `docs/lots/lots_11_15_recovery_findings.yml`
- all R03 docs.

**Create:**
- `tests/architecture/test_lots_11_15_recovery_ownership.py`

Assertions: unique IDs, one owner, exact later tracker, forbidden placeholder rejection, F16 ownership, premature-closeout rejection.

## R03-L02 — procurement revision/amendment semantics

**Existing code:**
- `src/cip/modules/procurement_history/domain/models.py`
- `src/cip/modules/procurement_history/infrastructure/models.py`
- `src/cip/modules/procurement_history/infrastructure/projections.py`
  - `_upsert_procedure`
  - `_upsert_contract`
  - `_publication_is_newer`
  - `_contract_values`
- `src/cip/adapters/sources/decp/mapper.py`
  - `map_decp_contract`
  - `_amount`
- `src/cip/adapters/sources/decp/schemas.py`
  - `DecpContract.duration_months`
  - `DecpContract.amount_value`
  - `DecpContract.notification_timestamp`
- `src/cip/adapters/sources/boamp/mapper.py`
- `src/cip/adapters/sources/ted_search/`

**Likely create/modify:**
- `src/cip/modules/procurement_history/domain/revision_lineage.py` (candidate)
- typed amendment delta/effective-state merger;
- persistence models for predecessor/current head/source sequence/field provenance.

**Tests:**
- extend procurement mapper/persistence/API integration suites;
- add PostgreSQL concurrent-head tests;
- shuffled replay/equal-time/stale-backfill;
- sparse amendment matrix and explicit clear.

**Migration:** required if head/lineage/field provenance is persisted; include deterministic legacy data rebuild.

## R03-L03 — procurement identity and buyer binding

**Existing:**
- `src/cip/adapters/sources/decp/mapper.py`
- `src/cip/adapters/sources/boamp/mapper.py`
- `src/cip/adapters/sources/ted_search/`
- procurement procedure/contract/publication persistence;
- `src/cip/modules/organizations/application/identity.py`
- organization identity domain/persistence under `src/cip/modules/organizations/`.

**Likely create:**
- `src/cip/modules/procurement_history/domain/identity_resolution.py` (candidate)
- procurement native-identifier assertion record;
- procurement identity decision/audit table;
- buyer source-party assertion and Lot08 binding application port.

**Tests:**
- source-pair duplicate matrices;
- false near-duplicate;
- reviewed match/reject/split;
- exact SIREN/SIRET and name-only buyer;
- concurrent arrivals/replay.

## R03-L04 — public-footprint head/current claims

**Existing:**
- `src/cip/modules/public_footprint/domain/models.py`
- `src/cip/modules/public_footprint/infrastructure/models.py`
- `src/cip/modules/public_footprint/infrastructure/projections.py`
  - `persist_public_footprint_projections`
  - `_insert_version`
  - `_validated_predecessor`
  - `_upsert_claim`
- `src/cip/modules/public_footprint/infrastructure/queries.py`
  - `_claim_exists`
  - `_list_item`
  - `get_public_resource_detail`
- public-web/archive/search adapters and bridges.

**Likely create/modify:**
- resource current-head model/CAS service;
- `src/cip/modules/public_footprint/domain/version_lineage.py` (candidate);
- claim support-version/currentness model;
- desired current-claim reconciler;
- explicit current/history query contracts.

**Tests:**
- `tests/integration/test_public_footprint_persistence.py`
- `tests/integration/test_public_footprint_api.py`
- PostgreSQL head races;
- claim removal/tombstone/reappearance;
- old backfill and replay.

## R03-L05 — vulnerability identity/lifecycle/source-record heads

**Existing:**
- `src/cip/modules/vulnerability_knowledge/domain/models.py`
- `src/cip/modules/vulnerability_knowledge/domain/reconciliation.py`
  - `_STATUS_PRIORITY`
  - `_reconcile_group`
- `src/cip/modules/vulnerability_knowledge/infrastructure/projections.py`
  - `_resolve_vulnerability`
  - `_sync_snapshot_aliases`
  - `_refresh_reconciled_record`
- `src/cip/modules/vulnerability_knowledge/infrastructure/projection_hydration.py`
  - `latest_vulnerability_snapshots` **(F16 root cause)**
  - `_hydrate_snapshot`
  - `_aliases`
- `src/cip/modules/vulnerability_knowledge/infrastructure/models.py`
- `src/cip/adapters/sources/vulnerability_catalogs/advisory_mappers.py`
  - `map_osv_record`
  - `map_ghsa_record`
- `src/cip/modules/collection_orchestration/application/vulnerability_list_adapters.py`
  - `GithubAdvisoryAdapter`
  - `NvdVulnerabilityAdapter`
- `src/cip/modules/collection_orchestration/application/vulnerability_query_adapters.py`
  - `OsvVulnerabilityAdapter`
  - `CveOrgVulnerabilityAdapter`
  - `EpssLookupAdapter`

**Likely create:**
- `src/cip/modules/vulnerability_knowledge/domain/identity.py` (candidate)
- `src/cip/modules/vulnerability_knowledge/domain/authority.py` (candidate)
- `src/cip/modules/vulnerability_knowledge/domain/source_record_lineage.py` (candidate)
- alias-assertion model/table;
- identity decision/history;
- source-record predecessor/current-head metadata.

**Tests:**
- extend `tests/integration/test_vulnerability_knowledge_api.py`;
- unit authority/identity tests;
- two GHSAs same CVE, two OSVs same CVE;
- update/withdraw one sibling;
- alias bridge/concurrency/split;
- CVE.org vs advisory lifecycle conflicts;
- PostgreSQL current-head races.

**Migration:** likely required for alias assertions, identity decisions and provider-record current heads.

## R03-L06 — incident authority/supersession/type

**Existing:**
- `src/cip/modules/incident_intelligence/domain/models.py`
  - `_OFFICIAL_CLAIM_TYPES`
  - `IncidentClaimSnapshot.is_official_confirmation`
  - `supersedes_record_key`
- `src/cip/modules/incident_intelligence/domain/reconciliation.py`
  - `_TYPE_PRIORITY`
  - `_latest_claim_revisions`
  - `_reconcile_incident`
- incident persistence/hydration/queries;
- `src/cip/adapters/sources/incident_catalogs/mappers.py`
- `tests/integration/test_incident_intelligence_api.py`

**Likely create:**
- `src/cip/modules/incident_intelligence/domain/authority.py` (candidate)
- `src/cip/modules/incident_intelligence/domain/claim_lineage.py` (candidate)
- type assertion/decision metadata.

**Tests:**
- source-kind/claim-type matrix;
- true cross-key A→B correction/retraction (not same-key only);
- cycle/fork/stale/concurrency;
- weak severe allegation vs official lower-severity type;
- replay.

## R03-L07 — incident identity

**Existing:**
- incident claim/canonical persistence and read models;
- `reconcile_incident_claims` grouping by `incident_key`;
- incident catalog mappers passing provider `incident_key`;
- organization links/independence keys.

**Likely create:**
- `src/cip/modules/incident_intelligence/domain/identity.py` (candidate)
- native incident identity assertion;
- canonical incident group/decision tables;
- review endpoint/read model if analyst review infrastructure requires one.

**Tests:** different native IDs same event; same victim separate events; merge/reject/split/review; independence preservation; PostgreSQL concurrency.

## R03-L08 — IOC lineage and expiry

**Existing:**
- `src/cip/modules/threat_telemetry/domain/models.py`
  - `IndicatorSnapshot.supersedes_record_key`
  - `expires_at`
- `src/cip/modules/threat_telemetry/domain/reconciliation.py`
  - `latest_indicator_snapshots`
  - `_reconcile_indicator`
- `src/cip/modules/threat_telemetry/infrastructure/projections.py`
- `src/cip/modules/threat_telemetry/infrastructure/projection_hydration.py`
- `src/cip/modules/threat_telemetry/infrastructure/queries.py`
  - `list_threat_indicators`
  - `_apply_filters`
- `tests/integration/test_threat_telemetry_api.py`

**Likely create:**
- `src/cip/modules/threat_telemetry/domain/lineage.py` (candidate)
- `src/cip/modules/threat_telemetry/domain/expiry.py` (candidate)
- source-record head metadata / next-expiry metadata where needed;
- local integration contract used by Lot28 time reconciliation.

**Tests:** true cross-key supersession; exact expiry boundary; no-write passage; multi-source TTL; reactivation; update-vs-expiry race; replay.

## R03-L09 — Campaign/Malware threat-entity completion

**Existing:**
- `src/cip/modules/threat_telemetry/domain/models.py`
  - `TelemetryRelationType`
  - `TelemetryRelation(target_key)`
- `src/cip/modules/threat_telemetry/infrastructure/models.py`
- `src/cip/modules/threat_telemetry/infrastructure/queries.py`
- `src/cip/modules/threat_telemetry/api/routes.py` (indicator-only router)
- `src/cip/modules/threat_telemetry/api/schemas.py`
- `src/cip/modules/threat_telemetry/application/view_models.py`
- `src/cip/adapters/sources/threat_catalogs/`
- vulnerability knowledge for canonical vulnerability targets.

**Likely create/extend:**
- `src/cip/modules/threat_telemetry/domain/threat_entities.py` (candidate)
- Campaign/Malware source assertion and identity decision models;
- typed temporal relation assertion persistence;
- campaign/malware query/view/schema/routes;
- migration(s);
- frontend threat-intelligence views if required by product workspace contract.

**Tests:** identity/review/split, relation provenance/currentness, correction/retraction/expiry, campaign timeline, malware-vulnerability relation, protected API search/detail/auth, migration reversal.

## R03-L10 — qualification

One exact implementation SHA must run:

- R03 architecture/no-orphan guard;
- all affected unit/integration suites;
- PostgreSQL concurrency/replay/order tests;
- migration up/down/up;
- backend lint/type/full regression/coverage;
- frontend audit/type/test/build if touched;
- security/redaction gates;
- review-thread audit;
- exact-head CI.

## Explicitly outside R03

Do not implement here:

- Lot19 incumbent/renewal relationship inference;
- Lot20 global corporate/entity graph engine;
- a second global outbox/reconciliation framework beside Lot28;
- SA21 provider/source activation work;
- active IOC validation, exploit activity, prospect scans or malware binary retrieval;
- Lot30 DNS/address-safety framework;
- Lot31 privacy deletion engine.
