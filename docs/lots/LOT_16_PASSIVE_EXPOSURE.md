# Lot 16 — Passive exposure and technographic observations

## Status

Implementation complete pending final CI validation and release merge.

## Objective

Lot 16 provides a canonical, temporal and source-aware layer for passive public or licensed observations about technical assets, services, technologies and cloud resources.

It does not actively inspect a prospect. It does not determine whether an observed product is vulnerable. It does not prove that a system is exposed or that an organization is compromised.

## Canonical assets

The domain normalizes the following asset classes:

- public domains and hostnames using deterministic IDNA normalization;
- globally routable IPv4 and IPv6 addresses;
- certificate fingerprints;
- autonomous system numbers;
- provider-qualified cloud-resource identifiers.

Local, internal, private, loopback, link-local, multicast, reserved and otherwise non-global addresses are rejected. Local-domain suffixes are rejected.

Each canonical identity is represented as:

```text
asset kind + normalized value -> canonical asset key
```

## Immutable observations

Every provider record becomes an immutable passive observation snapshot containing:

- provider and provider-record identity;
- HTTPS source URL;
- observation kind and explicit state;
- distinct observation, publication, modification and expiration times;
- source-independence key and confidence;
- optional port and protocol metadata;
- optional technology evidence;
- organization-link evidence and attribution risks;
- correction or supersession reference;
- explicit passive-only and metadata-only safety flags.

The supported states are:

- `current`;
- `historical`;
- `expired`;
- `corrected`;
- `retracted`;
- `deleted`;
- `unknown`.

A replay of the same immutable snapshot is idempotent. A provider revision creates a new snapshot and preserves the earlier version.

## Technology evidence levels

Technology information is deliberately separated into three levels:

1. `technology_mention`: a provider mentions a product;
2. `passive_observation`: provider metadata supports a passive product observation;
3. `observed_version`: provider metadata includes a product and version.

None of these levels is vulnerability applicability. An observed version is never transformed into an affected-range decision in Lot 16.

## Organization attribution

Organization attribution is represented independently from the passive observation itself.

Link states are:

- `unresolved`;
- `exact`;
- `candidate`;
- `review_required`;
- `rejected`.

Exact links require exact official-domain or official-identifier evidence. Name-only evidence cannot become exact.

The following attribution risks are first-class data:

- shared hosting;
- CDN infrastructure;
- reseller infrastructure;
- subsidiary ambiguity;
- abandoned domains;
- reassigned addresses.

Any attribution risk prevents an exact link. Conflicting organization identifiers are reconciled to `review_required`, never silently selected.

Provider payloads cannot directly manufacture an internal organization identity. A separately governed resolution step must supply any canonical organization link.

## Reconciliation

Reconciliation operates only over the latest revision of each provider record while preserving all immutable snapshots for history.

The canonical projection exposes:

- current effective state and all observed states;
- first and last observation times;
- expiration and last-update times;
- source count and independent-source count;
- active and historical-only flags;
- state conflicts;
- exact or candidate organization identifiers;
- organization-link reasons and attribution risks;
- merged technology and service observations.

An expired current observation becomes effectively expired at reconciliation time without modifying its historical snapshot.

## Persistence

Migration `20260806_0016` creates:

- `passive_assets` for the current source-aware projection;
- `passive_observation_snapshots` for immutable provider history;
- `passive_technologies` for snapshot-scoped technology evidence.

The migration is designed for the repository's mandatory PostgreSQL:

```text
upgrade head -> downgrade base -> upgrade head
```

## Protected API

The control-plane-protected read API exposes persisted data only:

- `GET /v1/passive-assets`;
- `GET /v1/passive-assets/{asset_id}`.

List filters include:

- asset kind;
- observation state;
- organization-link status;
- attribution risk;
- canonical organization identifier;
- active, historical-only and conflict flags;
- bounded text search;
- bounded pagination.

An API request never initiates provider collection or probes an asset.

## Analyst workspace

The `/passive-exposure` workspace provides:

- a filterable passive-asset inventory;
- explicit observation and organization-link states;
- attribution-risk badges;
- source and independent-source counts;
- immutable observation chronology;
- link reasons and confidence;
- observed services and technology evidence;
- permanent messaging that exposure and applicability are not assessed.

## Provider candidates

Lot 16 defines three distinct candidates:

- licensed passive-exposure observations;
- licensed technographic observations;
- licensed cloud-asset observations.

All candidates are:

- `draft` in source governance;
- `candidate` in the source portfolio;
- unauthorized;
- hostless and pathless;
- unscheduled;
- non-executable;
- without registered runtime adapters.

The shared runtime loads their policy and portfolio metadata so governance is visible, but it cannot execute them.

## Structural safety boundaries

The passive-exposure module cannot import:

- network clients or socket libraries;
- collection adapters;
- opportunity modules;
- vulnerability-applicability modules.

Domain and provider schemas reject records indicating:

- active probes or scans;
- direct service connection;
- credential use or authenticated enumeration;
- access-control bypass;
- exploitation;
- direct validation;
- vulnerability-applicability assessment;
- exposure verification;
- binary payloads or credentials.

The module has no opportunity creation or outreach path.

## Validation scope

The Lot 16 suite covers:

- domain, IP, ASN, certificate, cloud and service normalization;
- invalid and non-public assets;
- timestamp ordering and expiration;
- correction, retraction, deletion and replay;
- exact, candidate, conflicting and unresolved organization links;
- CDN, shared-hosting and reassignment risks;
- provider mapping safety;
- source and portfolio non-executability;
- persistence metadata and reversible migration;
- protected list and detail API behavior;
- frontend type checking and production build;
- full repository non-regression and aggregate coverage gate.

## Release boundary

The target release is `0.17.0`.

Merging this software does not authorize any provider. Provider activation requires a separate review of the exact legal basis, licence, contract, fields, hosts, paths, credentials, quotas, retention, cost, security controls and collection schedule.
