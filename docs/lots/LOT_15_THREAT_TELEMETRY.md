# Lot 15 — Malicious Infrastructure, Phishing, IOC, and Attack Telemetry

## Status

`IMPLEMENTED_VALIDATED`

## Primary business outcome

Provide analysts with canonical, temporal, source-aware defensive telemetry for indicators, infrastructure, campaigns, phishing context, file metadata, certificates, and vulnerability relations without scanning prospects or treating a global IOC as proof that an organization is compromised or exposed.

The capability is a global knowledge layer. It does not identify an affected organization, create an opportunity, authorize outreach, connect to an indicator, or retrieve a binary.

## Dependencies

- Lot 01 — persistence, provenance, and UTC contracts;
- Lot 02 — durable orchestration and replay safety;
- Lot 10 — source governance, portfolio, backfill, health, quota, and activation boundaries;
- Lot 13 — canonical vulnerability knowledge;
- Lot 14 — public incident claims and official confirmation.

## Canonical distinctions

```text
provider indicator metadata
  != direct observation by this platform
  != organization asset evidence
  != proof of exposure
  != proof of compromise
  != current commercial opportunity
```

A repeated upstream feed uses one independence key and counts once. A shared CDN, hosting provider, resolver, certificate, or sinkhole remains explicitly qualified. A later benign, sinkhole, expired, or retracted classification remains visible beside earlier classifications.

## Indicator identity

Implemented indicator types are:

- IPv4;
- IPv6;
- domain;
- URL;
- file hash;
- certificate fingerprint;
- email address.

Normalization is deterministic:

- IPv4 and IPv6 use compressed canonical forms;
- only globally routable IP addresses enter the global catalog;
- domains use lower-case IDNA and reject local or internal suffixes;
- URLs allow only HTTP or HTTPS, remove fragments, reject embedded credentials, canonicalize ports, and sort query parameters;
- hashes are normalized as MD5, SHA-1, or SHA-256 with explicit file or certificate prefixes;
- email domains use the same public-domain normalization.

The canonical key combines the indicator type and normalized value. No organization identifier exists in the threat-telemetry domain.

## Immutable source snapshots

Every source revision becomes an immutable `IndicatorSnapshot` containing:

- source identity, source kind, record key, and published source URL;
- canonical indicator type and value;
- explicit classification state;
- publication and modification timestamps;
- first seen, last seen, and expiration timestamps;
- source-independence key;
- sensor scope;
- confidence and source precedence;
- active, shared-infrastructure, and historical-only flags;
- optional supersession reference;
- campaign, malware-family, vulnerability, phishing-kit, or infrastructure relations;
- mandatory metadata-only, no-binary, and no-direct-validation safety state.

Snapshots reject binary payloads, sample download paths, and any claim that the platform directly validated an indicator.

## Classification states

Implemented states are:

- malicious;
- suspicious;
- historical;
- expired;
- sinkholed;
- benign;
- shared infrastructure;
- unknown;
- retracted.

The current projection selects one source-aware state while preserving every observed state. Benign or retracted authoritative revisions can supersede an earlier positive classification without deleting history. Conflicting classifications remain explicitly visible.

## Source independence and sensor scope

Positive source counts use independence keys rather than raw publication counts. Syndicated or republished upstream data therefore counts once.

Sensor scopes are:

- global;
- regional;
- sector;
- customer tenant;
- provider aggregate;
- unknown.

Sensor scope is context, not organization attribution. A customer-tenant observation would still require a separately governed tenant and organization-resolution path in a future lot.

## Relationships

Snapshots can carry bounded, source-proven relations to:

- campaigns;
- malware families;
- vulnerabilities;
- phishing kits;
- infrastructure groups.

When multiple sources publish the same relation, the canonical view retains the highest-confidence relation while immutable source revisions preserve all original values.

## Persistence and migration

Migration `20260806_0015` creates:

- `threat_indicators` — current reconciled indicator records;
- `threat_indicator_snapshots` — immutable source revisions;
- `threat_indicator_relations` — source-revision relations.

Snapshot digests make replay idempotent. The projection recalculates only touched indicators from the latest revision of every source record. Empty batches are a no-op. Persisted timestamps are normalized to aware UTC for PostgreSQL and SQLite test compatibility.

The migration supports PostgreSQL `upgrade -> downgrade -> upgrade` without residual objects.

## Protected API

Implemented endpoints:

- `GET /v1/threat-indicators`;
- `GET /v1/threat-indicators/{indicator_id}`.

The list endpoint supports persisted-data filters for indicator type, current state, source kind, sensor scope, active state, shared infrastructure, historical-only state, conflicting classifications, and local text search.

The detail endpoint exposes immutable source history and relations. Neither endpoint initiates source collection or contacts the indicator.

## Analyst workspace

The `/threat-intelligence` workspace provides:

- canonical indicator inventory;
- current and observed classification states;
- source and independent-positive-group counts;
- first seen, last seen, expiration, and last-update times;
- shared-infrastructure, historical, active, and conflict indicators;
- filtered persisted-data search;
- source-level immutable history;
- sensor scope, confidence, precedence, supersession, and relations;
- a permanent safety disclaimer.

The workspace is database-first and never performs on-demand collection.

## Selected source mappings

Deterministic metadata schemas and mappings are implemented for:

- STIX/TAXII indicators;
- phishing metadata;
- passive DNS metadata;
- certificate and infrastructure metadata;
- malware family and file-hash metadata.

A revoked STIX indicator maps to `retracted`. Phishing metadata can add a phishing-kit relation. Malware metadata can add a malware-family relation, but the schema rejects sample availability, binary payloads, and download URLs.

## Governance boundary

Five source contracts are installed as non-executable candidates:

- licensed STIX/TAXII;
- licensed phishing metadata;
- licensed passive DNS;
- licensed certificate telemetry;
- licensed malware metadata.

For every candidate:

- source status is `draft`;
- authorization is missing;
- automated collection is disabled;
- approved hosts and paths are empty;
- raw-content storage is disabled;
- portfolio status is `candidate`;
- `executable` is `false`;
- no collection schedule exists;
- direct indicator connection is forbidden;
- binary collection is forbidden;
- organization-compromise inference is forbidden;
- autonomous outreach is forbidden.

The common runtime loads and synchronizes these catalog entries, but registers no adapter for them.

## Structural safety controls

Architecture tests enforce that the threat-telemetry module does not import:

- HTTP or socket clients;
- subprocess execution;
- organization modules;
- opportunity modules.

The domain is also checked for the absence of `organization_id` and commercial opportunity concepts.

## Prohibited actions and data

The implementation excludes:

- active scanning or probing;
- direct connections to a suspicious or malicious indicator;
- malware or file-sample download;
- binary payload storage;
- credentials or credential validation;
- victim files or stolen data;
- private communications or private-life data;
- restricted content;
- organization compromise or exposure claims from telemetry alone;
- autonomous opportunity creation, contact action, or outreach.

## Historical backfill

Historical metadata can be persisted with `historical_only=true`. Expired or inactive indicators remain searchable with their original timelines. Backfill collection time never becomes a new first-seen or current-urgency event.

## Exit decision

Lot 15 is complete when the final pull-request head passes dependency audits, Ruff, Mypy strict, architecture and safety contracts, reversible PostgreSQL migrations, the complete backend suite with configured coverage, frontend audit, TypeScript typecheck, and production build.

Exact final-head evidence is recorded on pull request `#41`. Any later commit invalidates an earlier result and requires every gate to run again.
