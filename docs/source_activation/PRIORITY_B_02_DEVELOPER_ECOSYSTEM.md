# Priority B-2 — Developer Ecosystem and Package Metadata

## Objective

Complete the repository/package-registry portion of Priority B with provider-specific bounded metadata adapters while reusing the existing Lot 12 Public Footprint model.

## Runtime path

```text
explicit organization-bound target
  -> provider-specific public API
  -> minimal person-free provider schema
  -> sanitized RawObservation
  -> PublicResource(REPOSITORY | PACKAGE)
  -> PublicResourceVersion
  -> existing Lot 12 incremental/backfill persistence
```

No automatic `PublicClaim` is emitted by these adapters.

## Providers

- GitHub public organization repositories;
- GitLab public group projects;
- PyPI exact public package metadata;
- npm exact public package metadata;
- Maven Central exact group/artifact metadata.

## Targeting

`policies/developer_ecosystem_targets.yml` is checked in empty. A target is always bound to a canonical internal organization UUID and one exact provider identity:

- GitHub organization namespace;
- GitLab group namespace;
- PyPI project name;
- npm package name;
- Maven group ID + artifact ID.

Duplicate normalized targets are rejected. No adapter performs global search or discovery of new organizations/packages.

## Pagination and bounds

GitHub and GitLab use provider pagination with a maximum of 100 records per page and a per-target cursor. A full page continues the same target; a terminal short page clears its cursor and rotates to the next enabled target.

PyPI, npm and Maven are exact one-target lookups. Maven requests `rows=1` and requires exactly one response matching both configured coordinates.

## Privacy and artifact boundary

Provider schemas intentionally omit person-oriented structures. Unknown response fields are discarded before RawObservation hashing, including owners, users, members, contributors, authors, maintainers and email fields.

The capability does not download:

- repository source code or archives;
- releases or binary assets;
- PyPI distributions/wheels/sdists;
- npm tarballs;
- Maven JAR/POM/source/signature artifacts.

## Evidence semantics

Repository/package metadata is public engineering context only. It must not be visually or semantically presented as verified deployment, live technology exposure, vulnerability applicability, compromise or commercial need.

B-2 reuses `PublicResourceKind.REPOSITORY`, adds `PublicResourceKind.PACKAGE`, and uses `REPOSITORY_API` / `PACKAGE_REGISTRY_API` discovery methods. Persistence remains Lot 12.

## Completion gate

B-2 is complete only when:

- all five adapters are registered in the shared runtime;
- governance and portfolio entries are executable but target-bound;
- checked-in targets are empty and schedules disabled;
- provider response identity is validated where exact identity is returned;
- person metadata and downloadable artifact fields are absent from the sanitized models;
- no automatic claim/signal/need/opportunity/outreach is produced;
- deterministic provider/registry/runtime/reconciliation tests pass;
- Source Activation truth and Source Coverage Matrix agree;
- the complete repository backend and frontend CI pass on one exact final SHA;
- `live_tested` remains false until separately authorized controlled validation.
