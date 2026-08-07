# Lot 17 — Vendor advisories, product versions, and vulnerability applicability

## Status

`IMPLEMENTED_VALIDATED` for release `0.18.0`, subject to the final pull-request head passing every repository gate before merge.

## Objective

Lot 17 reconciles official vendor advisories, product identities, version ranges, support lifecycle, fixes, mitigations, and organization-specific passive technology evidence.

The result is an explainable and reversible applicability assessment. It is not an active validation, verified exposure, proof of compromise, commercial opportunity, or authorization to contact an organization.

## Evidence boundary

```text
technology mention
!= passive observation
!= observed version
!= affected-range applicability
!= verified exposure
!= compromise
!= current commercial opportunity
```

An assessment requires evidence from both sides:

1. a canonical vulnerability and official advisory revision with affected-product and version-range evidence;
2. an organization-linked passive technology observation with adequate product and version precision.

Global CVE, CVSS, EPSS, PoC, KEV, IOC, advisory, or product-family data cannot independently produce organization applicability.

## Canonical product model

Products are normalized across:

- vendor;
- product;
- component;
- edition;
- package ecosystem;
- platform or distribution;
- CPE, package URL, ecosystem, and vendor identifiers;
- support status and end-of-support time.

The canonical product key is provider-independent and keeps component, edition, ecosystem, and platform distinctions. A name-only family match cannot silently become a version-precise match.

## Version and range semantics

The domain supports:

- semantic, numeric, calendar, vendor, RPM, DEB, and unknown version schemes;
- introduced boundaries;
- fixed boundaries;
- last-affected boundaries;
- explicit limits;
- inclusive and exclusive bounds;
- branch metadata;
- backported-fix flags;
- exact, product, component, edition, and version precision.

RPM, DEB, vendor-specific, ambiguous, and backported-fix cases remain `review_required` when deterministic comparison is not justified.

## Advisory revisions

Every provider record becomes an immutable advisory revision with:

- source and source-record identity;
- advisory identifier and HTTPS provenance URL;
- publication and modification time;
- current, corrected, superseded, withdrawn, or deleted state;
- vulnerability identifiers;
- affected product ranges;
- fixed versions and workarounds;
- supersession reference;
- metadata-only and safety flags.

Corrections and withdrawals create new revisions. Earlier revisions remain available for chronology and audit.

## Applicability states

The current projection uses explicit states:

- `unknown`;
- `not_applicable`;
- `potentially_applicable`;
- `applicable`;
- `review_required`;
- `withdrawn`;
- `superseded`.

An applicable decision records the matched product, observed version, affected range, precision, confidence, reason, organization, passive asset, vulnerability, advisory revision, and technology snapshot.

Unknown and review-required states are first-class outcomes, not failures to be hidden.

## Persistence

Migration `20260807_0017` creates:

- `vendor_products`;
- `vendor_advisory_revisions`;
- `vendor_advisory_ranges`;
- `applicability_assessment_snapshots`;
- `vulnerability_applicability_assessments`.

Advisory revisions and assessment snapshots are immutable. The current assessment projection advances only when an equally recent or newer decision is persisted. Replays are idempotent.

The migration must pass:

```text
upgrade head -> downgrade base -> upgrade head
```

## Protected API

The deployment-protected API exposes persisted data only:

- `GET /v1/vulnerability-applicability`;
- `GET /v1/vulnerability-applicability/{assessment_id}`.

Filters include:

- decision state;
- match precision;
- organization;
- vulnerability;
- vendor;
- product;
- bounded text search;
- bounded pagination.

An API request never launches provider collection or probes an asset.

## Analyst workspace

The `/vulnerability-applicability` workspace provides:

- a filterable assessment inventory;
- vulnerability, advisory, vendor, product, component, observed version, state, precision, confidence, and assessment time;
- organization technology evidence;
- official advisory source and chronology;
- affected ranges;
- fixed versions and workarounds;
- immutable assessment history;
- permanent messaging that applicability is not verified exposure or compromise.

## Provider candidates

Lot 17 registers three candidate families:

- official vendor PSIRT advisories;
- official Linux distribution security advisories;
- official package-ecosystem security advisories.

Every candidate is:

- `draft` in source governance;
- `candidate` in the source portfolio;
- unauthorized;
- hostless and pathless;
- unscheduled;
- non-executable;
- without a registered runtime adapter.

The common runtime loads their governance metadata but cannot execute them.

## Safety boundaries

The module contains no path for:

- active probing or scanning;
- direct service connection;
- authentication or credential use;
- access-control bypass;
- exploitation;
- binary or malware retrieval;
- exposure verification;
- compromise inference;
- opportunity creation;
- contact enrichment;
- outreach.

Architecture tests prohibit network clients, source adapters, opportunity modules, and contact-oriented modules from the applicability package. The domain remains independent from FastAPI, SQLAlchemy, and persistence implementations.

## Validation scope

The lot tests:

- product, component, edition, ecosystem, platform, CPE, and package identity normalization;
- exact, inclusive, exclusive, open-ended, fixed, and last-affected boundaries;
- unknown versions and non-comparable schemes;
- backported fixes;
- product mismatch and false-merge prevention;
- advisory correction and supersession;
- expired technology evidence and assessment withdrawal;
- immutable snapshots and replay idempotence;
- same range across several advisory revisions;
- source and portfolio non-executability;
- protected API list and detail behavior;
- frontend type checking and production build;
- reversible migration and full repository regression.

## Release boundary

Release `0.18.0` does not authorize any advisory provider. Production activation requires a separate reviewed authorization covering the exact owner, licence, terms, fields, hosts, paths, credentials, quotas, retention, costs, security controls, schedule, corrections, deletion, and revocation behavior.
