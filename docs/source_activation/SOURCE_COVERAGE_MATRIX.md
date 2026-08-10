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
| public-web target path | SA-02 / Priority B-3 | Y | Y | - | - | - | - | bounded sitemap + RSS/Atom + security.txt + public-document capability; checked-in example remains disabled/unauthorized |
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
| IANA-bootstrapped public RDAP | Priority B-1 | Y | Y | Y | Y | N/A | - | target-driven public registration/allocation metadata; checked-in target registry empty; live proof outstanding |
| GitHub public organization repositories | Priority B-2 | Y | Y | Y | Y | N/A | - | exact configured organization metadata only; target registry empty; live proof outstanding |
| GitLab public group projects | Priority B-2 | Y | Y | Y | Y | N/A | - | exact configured public group metadata only; target registry empty; live proof outstanding |
| PyPI public package metadata | Priority B-2 | Y | Y | Y | Y | N/A | - | exact configured project metadata only; no distributions downloaded; live proof outstanding |
| npm public package metadata | Priority B-2 | Y | Y | Y | Y | N/A | - | exact configured package metadata only; no tarballs downloaded; live proof outstanding |
| Maven Central public artifact metadata | Priority B-2 | Y | Y | Y | Y | N/A | - | exact configured group/artifact metadata only; no JAR/POM downloads; live proof outstanding |
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

SA-00 established the lifecycle and truth model. SA-01 through SA-04 promote only provider-specific paths whose implementation, authorization and runtime boundaries are explicit. Priority B completion continues the same provider-level discipline for passive organization and technology evidence. Later waves must continue at provider level rather than hiding candidates behind family-level completion claims.

## Reconciliation invariant

Every `source_id` contained in every checked-in `source_portfolio*.yml` bundle must have an activation record. Repository tests enforce this invariant across the activation bundles added by each SA/Priority-B increment.

OSINT Framework synchronization remains candidate discovery only. An upstream entry can stay non-executable, but relevant candidates must eventually receive an explicit `active`, `planned`, `manual`, `blocked`, `replaced`, `duplicate`, or `not_relevant` disposition before SA-10 closes.

## Priority B-3 public web/feed/document completion boundary

Priority B-3 is complete only when:

- the existing Lot 12 bounded public-web collector remains the single implementation and gains RSS 2.0, Atom, `/.well-known/security.txt`, public PDF and bounded plain-text support without a parallel crawler;
- every feed URL is explicitly configured on an organization-bound target, same-origin, path-scoped and subject to the existing robots, page, byte and redirect budgets;
- feed XML is byte-bounded before parsing, rejects DTD/entities, accepts only RSS 2.0 or Atom and emits only canonical in-scope links;
- feed entries are discovery lineage only and are never counted as independent corroboration for their linked pages;
- `security.txt` is fetched only from the canonical well-known path, requires at least one supported `Contact`, validates any `Canonical` field against that exact target path and remains a disclosure/contact resource rather than vulnerability or commercial-need evidence;
- public PDF extraction is byte- and page-bounded, rejects malformed and encrypted documents, never executes document content and only emits bounded text/title metadata into the existing Public Footprint mapping;
- plain-text extraction is byte-bounded, UTF-8 only and rejects NUL content;
- sitemap-, feed-, direct- and document-discovered resources reuse the existing Lot 12 `PublicResource` / `PublicResourceVersion` / provenance path and the existing collection runtime, worker and persistence path;
- the checked-in public-web example remains disabled and unauthorized; B-3 extends the adapter capability but does not manufacture authorization or `live_tested` status;
- no crawl-on-page-view, authentication bypass, CAPTCHA/MFA handling, private portal access, arbitrary user URL fetch, active probing or raw-body retention is introduced;
- `security.txt`, feed metadata and document presence do not directly create commercial signals, need hypotheses, scores, opportunities, contact targets or outreach;
- deterministic XML entity/size, malformed/oversize PDF, target-registry, client-policy, runtime/provenance and Source Activation reconciliation tests pass;
- Source Activation truth and this matrix continue to agree that the checked-in public-web example is mapped/adapter-present but not authorized/executable;
- the complete repository backend and frontend CI pass on one exact final SHA;
- `live_tested` remains false until separately authorized controlled provider validation is evidenced.

## Priority B-2 developer ecosystem completion boundary

Priority B-2 is complete only when:

- GitHub organization repositories, GitLab group projects, PyPI projects, npm packages and Maven Central coordinates are registered in the shared collection runtime;
- every lookup is bound to an explicit canonical organization UUID plus an exact provider identity from the checked-in target registry;
- the checked-in target registry is empty and all five checked-in schedules remain disabled;
- no provider performs global organization, repository, project, package or person discovery;
- provider schemas exclude users, owners, members, contributors, commit authors, maintainers, author emails and other person-oriented metadata before RawObservation hashing;
- repository source code, archives, releases, package distributions, tarballs, JARs, POMs, source artifacts and signatures are never downloaded by this capability;
- provider-returned exact identities are revalidated before persistence where the provider exposes them;
- projections reuse Lot 12 `PublicResource` / `PublicResourceVersion` with `REPOSITORY` or `PACKAGE` rather than creating a developer-intelligence persistence silo;
- repository or package presence remains public engineering context and never proves production deployment, exposure, vulnerability applicability, compromise or a commercial need;
- no automatic `PublicClaim`, `CommercialSignal`, `NeedHypothesis`, score, opportunity, contact target or outreach action is produced;
- deterministic provider, target-registry, no-target/no-network, runtime and Source Activation reconciliation tests pass;
- the complete repository backend and frontend CI pass on one exact final SHA;
- `live_tested` remains false until separately authorized controlled provider validation is evidenced.

## Priority B-1 RDAP completion boundary

Priority B-1 is complete only when:

- `iana-rdap-public` is registered in the shared collection runtime and maps to immutable sanitized RawObservations plus Lot 16 passive snapshots;
- the checked-in RDAP target registry is empty and the checked-in schedule is disabled;
- only explicit organization-bound domain, globally routable IPv4/IPv6 and ASN targets are accepted;
- the first hop is restricted by Source Governance to IANA RFC 9224 bootstrap data under `data.iana.org/rdap/`;
- the second hop is an HTTPS authoritative base URL selected from the matching IANA bootstrap service and cannot be supplied by a user or redirect;
- domain suffix, IP longest-prefix and ASN narrowest-range matching are deterministic;
- authoritative RDAP responses are revalidated to cover the exact requested domain/IP/ASN before persistence;
- RDAP entities, vCards, emails, telephone numbers and other contact/person fields are not materialized into the provider schema or RawObservation;
- nonpublic RDAP/RDRS access and authenticated enumeration remain outside scope;
- registration/allocation evidence is `review_required` passive correlation and never proves current operational ownership, deployment, exposure or compromise;
- incremental and historical backfill reuse the existing Lot 16 transactional persistence path;
- deterministic registry/adapter/runtime/reconciliation tests and full repository CI pass on one exact final SHA;
- `live_tested` remains false until separately authorized controlled provider validation is evidenced.

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
