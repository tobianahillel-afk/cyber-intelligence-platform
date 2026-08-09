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
| CISA KEV | legacy validation | Y | Y | Y | Y | Y | - | executable, controlled live proof outstanding |
| TED Search | legacy validation | Y | Y | Y | Y | Y | - | executable, controlled live proof outstanding |
| BOAMP | legacy validation | Y | Y | Y | Y | Y | - | executable, controlled live proof outstanding |
| DECP | legacy validation | Y | Y | Y | Y | Y | - | executable, controlled live proof outstanding |
| Greenhouse | legacy validation | Y | Y | Y | Y | Y | - | executable, controlled live proof outstanding |
| Lever | legacy validation | Y | Y | Y | Y | Y | - | executable, controlled live proof outstanding |
| SmartRecruiters | legacy validation | Y | Y | Y | Y | Y | - | executable, controlled live proof outstanding |
| Recherche d'entreprises | target activation | Y | Y | - | - | N/A | - | paused until explicit identity target |
| GLEIF | target activation | Y | Y | - | - | N/A | - | paused until explicit LEI target |
| BODACC identity | target activation | Y | Y | - | - | N/A | - | paused until explicit French SIREN target |
| Synthetic reference | test reference | Y | Y | Y | Y | N/A | Y | fully integrated test capability |
| OSINT Framework import | SA-00 | - | - | - | - | N/A | - | catalogue normalization implemented; no execution authority |
| public-web target path | SA-02 | Y | Y | - | - | - | - | adapter exists; checked-in example target remains disabled/unauthorized |
| NVD | SA-01 | Y | Y | Y | Y | Y | - | governed paginated adapter; live proof outstanding |
| FIRST EPSS | SA-01 | Y | Y | Y | Y | N/A | - | bounded explicit-CVE lookup; live proof outstanding |
| GitHub Global Advisories | SA-01 | Y | Y | Y | Y | Y | - | governed paginated adapter; live proof outstanding |
| CVE Services | SA-01 | Y | Y | Y | Y | N/A | - | bounded explicit-CVE lookup; live proof outstanding |
| OSV | SA-01 | Y | Y | Y | Y | N/A | - | bounded explicit-OSV lookup; live proof outstanding |
| CIRCL Vulnerability-Lookup | SA-01 | Y | Y | Y | Y | N/A | - | bounded explicit-CVE lookup; live proof outstanding |
| Brave Search API | SA-02 | Y | Y | Y | Y | N/A | - | adapter executable; schedule disabled until deployment onboarding/secret activation; live proof outstanding |
| Internet Archive CDX | SA-02 | Y | Y | Y | Y | Y | - | bounded weekly historical metadata discovery; live proof outstanding |
| Sherlock | SA-05 | - | - | - | - | N/A | - | explicit local OSINT capability planned |
| LinkedIn official API | SA-07 | - | - | - | - | N/A | - | BLOCKED pending approved official/licensed access and adapter |
| BrixHub | SA-08 | - | - | - | - | N/A | - | BLOCKED pending access/licence/data review |

## Known broader source families

The repository already models additional candidate families delivered in Lots 13–22: incident reporting, ransomware metadata, threat telemetry, passive exposure, advisory providers, corporate-change intelligence, relationship intelligence, professional context and conditional premium integrations. Most remain candidate/non-executable and are assigned to later source-activation waves.

SA-00 established the lifecycle and truth model. SA-01 and SA-02 promote only providers whose implementation, authorization and runtime boundaries are explicit. Later waves must continue at provider level rather than hiding candidates behind family-level completion claims.

## Reconciliation invariant

Every `source_id` contained in every checked-in `source_portfolio*.yml` bundle must have an activation record. The repository test `test_every_checked_in_source_portfolio_entry_has_activation_record` enforces this invariant and includes the SA-02 search/archive portfolio bundle.

OSINT Framework synchronization remains candidate discovery only. An upstream entry can stay non-executable, but relevant candidates must eventually receive an explicit `active`, `planned`, `manual`, `blocked`, `replaced`, `duplicate`, or `not_relevant` disposition before SA-10.

## Wave A completion target

At the end of SA-02:

- all six SA-01 vulnerability providers have real governed adapters;
- NVD and GitHub Global Advisories use bounded schedules/checkpoints through the shared collection runtime;
- query-oriented CVE/EPSS/OSV/CIRCL paths require explicit targets and do not gain fake schedules;
- the public-web adapter remains executable only for explicitly enabled targets with exact target policies;
- Brave Search is a real provider adapter but remains deployment-fail-closed without connected secret state and its checked-in schedule is disabled;
- Internet Archive CDX is a bounded historical-metadata adapter and is a no-op without enabled targets;
- search-result and archive-index metadata remain quarantined discovery resources with zero claims;
- every new adapter is covered by deterministic contract tests and the full repository regression gate;
- `live_tested` remains false until controlled real-provider validation is separately evidenced.
