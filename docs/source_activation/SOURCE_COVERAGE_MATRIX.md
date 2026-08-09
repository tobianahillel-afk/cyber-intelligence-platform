# Source Coverage Matrix

## Reading this matrix

This document is a human-readable projection of `policies/source_activation.yml`. The policy file and executable invariants are authoritative when prose and state disagree.

Symbols:

- `Y`: explicitly present/proven in the activation inventory;
- `-`: not yet proven;
- `N/A`: intentionally not required for this execution mode;
- `BLOCKED`: fail-closed with a recorded reason.

`Executable` does not imply `Live tested`. A source is fully integrated only when every required activation stage is present.

## Current core and Wave A sources

| Source | Wave | Mapped | Adapter | Authorized | Executable | Scheduled | Live tested | Current result |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| CISA KEV | legacy validation | Y | Y | Y | Y | Y | - | executable, live proof outstanding |
| TED Search | legacy validation | Y | Y | Y | Y | Y | - | executable, live proof outstanding |
| BOAMP | legacy validation | Y | Y | Y | Y | Y | - | executable, live proof outstanding |
| Greenhouse | legacy validation | Y | Y | Y | Y | Y | - | executable, live proof outstanding |
| Lever | legacy validation | Y | Y | Y | Y | Y | - | executable, live proof outstanding |
| SmartRecruiters | legacy validation | Y | Y | Y | Y | Y | - | executable, live proof outstanding |
| Recherche d'entreprises | target activation | Y | Y | - | - | N/A | - | paused until explicit identity target |
| GLEIF | target activation | Y | Y | - | - | N/A | - | paused until explicit LEI target |
| BODACC identity | target activation | Y | Y | - | - | N/A | - | paused until explicit French SIREN target |
| Synthetic reference | test reference | Y | Y | Y | Y | N/A | Y | fully integrated test capability |
| OSINT Framework import | SA-00 | - | - | - | - | N/A | - | catalogue normalization implemented; runtime sync still to validate |
| public-web-sitemap | SA-02 | Y | Y | - | - | - | - | implementation exists, real target activation missing |
| NVD | SA-01 | Y | - | - | - | - | - | mapper/schema only at SA-00 baseline |
| FIRST EPSS | SA-01 | Y | - | - | - | - | - | mapper/schema only at SA-00 baseline |
| GitHub Global Advisories | SA-01 | Y | - | - | - | - | - | mapper/schema only at SA-00 baseline |
| CVE Services | SA-01 | Y | - | - | - | N/A | - | query adapter required |
| OSV | SA-01 | Y | - | - | - | N/A | - | query adapter required |
| CIRCL Vulnerability-Lookup | SA-01 | Y | - | - | - | N/A | - | query adapter required |
| Brave Search API | SA-02 | - | - | - | - | - | - | real provider integration planned |
| Internet Archive CDX | SA-02 | - | - | - | - | - | - | bounded archive discovery planned |
| Sherlock | SA-05 | - | - | - | - | N/A | - | explicit local OSINT capability planned |
| LinkedIn official API | SA-07 | - | - | - | - | N/A | - | BLOCKED pending approved official/licensed access and adapter |
| BrixHub | SA-08 | - | - | - | - | N/A | - | BLOCKED pending access/licence/data review |

## Known broader source families

The repository already models additional candidate families delivered in Lots 13–22: incident reporting, ransomware metadata, threat telemetry, passive exposure, advisory providers, corporate-change intelligence, relationship intelligence, professional context and conditional premium integrations. Most remain candidate/non-executable.

SA-00 establishes the lifecycle and truth model. The subsequent source-activation waves must enumerate each provider-level entry rather than hiding these candidates behind a family-level completion claim.

## Required reconciliation before SA-00 is review-ready

The final SA-00 head must reconcile every `source_id` contained in all checked-in `source_portfolio*.yml` bundles against the activation inventory. Any source that exists in a portfolio bundle but has no activation record is a gate failure.

Likewise, OSINT Framework synchronization must produce candidate records that are explicitly classified before SA-10. An upstream entry may remain non-executable, but it may not remain unclassified if it is relevant to the product.

## Wave A completion target

At the end of SA-02:

- the six SA-01 vulnerability providers have real runtime adapters or an explicit provider-specific block reason;
- query-only providers use explicit target partitions and do not gain fake schedules;
- public web collection is executable for authorized configured targets;
- search and archive integrations have actual runtime adapters and fail closed when deployment authorization/secrets are absent;
- every new adapter is covered by deterministic contract tests and the full repository regression gate;
- the activation inventory is updated from implementation evidence, not aspiration.
