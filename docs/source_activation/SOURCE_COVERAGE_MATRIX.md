# Source Coverage Matrix

## Reading this matrix

This document is a human-readable projection of `policies/source_activation.yml`. The policy file and executable invariants are authoritative when prose and state disagree.

Symbols:

- `Y`: explicitly present/proven in the activation inventory;
- `-`: not yet proven;
- `N/A`: intentionally not required for this execution mode;
- `BLOCKED`: fail-closed with a recorded reason.

`Executable` does not imply `Live tested`. A source is fully integrated only when every required activation stage is present.

## Current core and activated sources

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
| Cloudflare DNS-over-HTTPS | SA-03 | Y | Y | Y | Y | N/A | - | target-driven A/AAAA passive lookup; checked-in target registry empty; live proof outstanding |
| Cert Spotter CT Search API | SA-03 | Y | Y | Y | Y | N/A | - | target-driven CT lookup; production API key/onboarding and deployment target required; live proof outstanding |
| SEC EDGAR cybersecurity disclosures | SA-04 | Y | Y | Y | Y | N/A | - | targeted Item 1.05 metadata capability; CIK target registry empty and deployment User-Agent required |
| PhishTank verified online phishing data | SA-04 | Y | Y | Y | Y | N/A | - | global URL telemetry capability; application key/onboarding and deployment User-Agent required |
| Licensed incident reporting | SA-07 | Y | - | - | - | - | - | concrete licensed provider/contract not selected |
| Licensed ransomware metadata | SA-07 | Y | - | - | - | - | - | provider licence/commercial-use path not selected; actor/victim content remains prohibited |
| Licensed STIX/TAXII | SA-07 | Y | - | - | - | - | - | concrete licensed CTI provider/tenant/marking scope not selected |
| Licensed phishing metadata | SA-07 | Y | - | - | - | - | - | PhishTank covers current public path; commercial augmentation deferred |
| Licensed malware metadata | SA-07 | Y | - | - | - | - | - | concrete licensed provider not selected; malware binaries remain prohibited |
| Licensed passive DNS | SA-07 | Y | - | - | - | - | - | concrete licensed provider/contract not selected |
| Licensed certificate telemetry | SA-07 | Y | - | - | - | - | - | concrete licensed provider/contract not selected |
| Licensed passive exposure | SA-07 | Y | - | - | - | - | - | concrete licensed provider/contract not selected |
| Licensed technography | SA-07 | Y | - | - | - | - | - | concrete licensed provider/contract not selected |
| Licensed cloud-asset observations | SA-07 | Y | - | - | - | - | - | concrete licensed provider/contract not selected |
| Generic company incident source family | SA-10 | Y | - | - | - | - | - | provider-specific decomposition required after SEC path |
| Generic regulator/CERT incident family | SA-10 | Y | - | - | - | - | - | concrete official endpoints and authorizations required |
| Generic vendor/Linux/package advisory families | SA-10 | Y | - | - | - | - | - | provider/ecosystem-specific decomposition required |
| Sherlock | SA-05 | - | - | - | - | N/A | - | explicit local OSINT capability planned |
| LinkedIn official API | SA-07 | - | - | - | - | N/A | - | BLOCKED pending approved official/licensed access and adapter |
| BrixHub | SA-08 | - | - | - | - | N/A | - | BLOCKED pending access/licence/data review |

## Known broader source families

The repository already models additional candidate families delivered in Lots 13–22: incident reporting, ransomware metadata, threat telemetry, passive exposure, advisory providers, corporate-change intelligence, relationship intelligence, professional context and conditional premium integrations. Candidate families remain non-executable until a concrete provider, method and authorization are selected.

SA-00 established the lifecycle and truth model. SA-01 through SA-04 promote only provider-specific paths whose implementation, authorization and runtime boundaries are explicit. Later waves must continue at provider level rather than hiding candidates behind family-level completion claims.

## Reconciliation invariant

Every `source_id` contained in every checked-in `source_portfolio*.yml` bundle must have an activation record. Repository tests enforce this invariant across the activation bundles added by each SA.

OSINT Framework synchronization remains candidate discovery only. An upstream entry can stay non-executable, but relevant candidates must eventually receive an explicit `active`, `planned`, `manual`, `blocked`, `replaced`, `duplicate`, or `not_relevant` disposition before SA-10 closes.

## SA-03 completion boundary

SA-03 is complete only when:

- Cloudflare DoH and Cert Spotter are registered in the shared collection runtime and map exclusively to immutable RawObservations plus Lot 16 passive snapshots;
- incremental collection and historical backfill persist those passive snapshots transactionally with their collection progress;
- the checked-in passive target registry is empty/disabled by default and no adapter performs network activity without an explicit enabled target;
- Cloudflare is restricted to bounded A/AAAA queries to the approved DoH provider host and never connects to returned addresses;
- Cert Spotter fails closed without deployment Provider Onboarding/API-key state and accepts only target-domain or subordinate-domain issuances;
- DNS answers remain review-required organization links with shared-infrastructure risk;
- certificate issuance remains review-required passive context and never proves endpoint deployment or exposure;
- no adapter assesses vulnerability applicability, verifies exposure, infers compromise, creates a need/opportunity, or performs outreach;
- the licensed passive providers remain planned for SA-07 instead of being falsely activated under `.example.invalid` placeholders;
- deterministic adapter/runtime/registry tests and the complete repository CI pass on one exact final SHA;
- `live_tested` remains false until separately authorized controlled provider validation is evidenced.

## SA-04 completion boundary

SA-04 is complete only when:

- SEC EDGAR and PhishTank are registered in the same shared collection runtime and emit immutable RawObservations plus the existing Lot 14/15 canonical projections;
- incremental collection and historical backfill persist `IncidentClaimSnapshot` and `IndicatorSnapshot` projections transactionally with collection progress;
- the SEC target registry is empty by default, accepts only exact 10-digit CIK bindings to canonical organization UUIDs, and performs no global issuer enumeration;
- SEC provider traffic fails closed without a descriptive deployment User-Agent and only targeted submissions metadata is retrieved;
- only non-amended Form 8-K family Item 1.05 metadata becomes an official company confirmation, without inventing occurrence dates, incident type, severity, victim counts or commercial urgency;
- PhishTank provider traffic fails closed without Provider Onboarding application-key state and a descriptive deployment User-Agent;
- PhishTank projects only verified-online URL telemetry, never visits the URL, never stores the key in RawObservation, and never converts the provider `target`/brand field into organization-compromise evidence;
- both checked-in SA-04 schedules remain disabled until deployment-specific prerequisites exist;
- community/commercial CTI ambiguity is fail-closed: ThreatFox/URLhaus Community and Ransomware.live are not treated as executable commercial sources;
- licensed incident/ransomware/STIX/phishing/malware sources remain assigned to SA-07, while generic provider-family placeholders remain assigned to SA-10 decomposition;
- no adapter creates commercial signals, needs, opportunities, contact targets or outreach;
- deterministic adapter/runtime/registry/persistence tests and the complete repository CI pass on one exact final SHA;
- `live_tested` remains false until separately authorized controlled provider validation is evidenced.
