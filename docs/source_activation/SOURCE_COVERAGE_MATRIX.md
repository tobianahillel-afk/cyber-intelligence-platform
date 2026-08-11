# Source Coverage Matrix

## Reading this matrix

This document is a human-readable projection of the Source Activation bundle rooted at `policies/source_activation.yml` plus additive `policies/source_activation.*.yml` files. The machine-readable activation bundle and executable invariants are authoritative when prose and state disagree.

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
| Ashby Public Job Postings API `ashby-job-board` | SA-13 | Y | Y | Y | Y | Y | Y | fully integrated; controlled live adapter proof retrieved 59 public jobs |
| Recruitee Careers Site API `recruitee-careers-site` | SA-13 | Y | Y | Y | Y | Y | Y | fully integrated; controlled live adapter proof retrieved 1 public job |
| Teamtailor Public Read Jobs API `teamtailor-public-jobs` | SA-13 | Y | Y | Y | - | - | - | real adapter present; account-specific Public Read token/account required before executable, scheduled and live-tested stages |
| Recherche d'entreprises `recherche-entreprises` | target activation | Y | Y | - | - | N/A | - | MANUAL until an explicit canonical organization target and deployment authorization exist |
| GLEIF `gleif` | target activation | Y | Y | - | - | N/A | - | MANUAL until an analyst/deployment-selected LEI target exists |
| BODACC identity `bodacc-identity` | target activation | Y | Y | - | - | N/A | - | MANUAL until an explicit organization/SIREN target and reviewed deployment authorization exist |
| Synthetic reference | test reference | Y | Y | Y | Y | N/A | Y | fully integrated test capability |
| OSINT Framework import `osint-framework-import` | SA-00 | - | - | - | - | N/A | - | MANUAL analyst catalogue-discovery input only; listings never grant execution authority |
| public-web sample `public-web-example-fr-organization` | SA-02 / Priority B-3 | Y | Y | - | - | N/A | - | NOT_RELEVANT as a production source; checked-in sample remains disabled/unauthorized |
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
| Censys Platform passive data `censys-platform-passive` | Priority B-4 / SA-07 | Y | - | - | - | N/A | - | BLOCKED pending compatible Enterprise/written product-integration entitlement |
| Shodan passive indexed data `shodan-passive-data` | Priority B-4 / SA-07 | Y | - | - | - | N/A | - | BLOCKED pending separate customer-facing commercial agreement; scan APIs prohibited |
| SecurityTrails passive data `securitytrails-passive-data` | Priority B-4 / SA-07 | Y | - | - | - | N/A | - | BLOCKED pending contract/licence evidence for customer-facing incorporation |
| urlscan passive existing-scan search `urlscan-passive-search` | Priority B-4 / SA-07 | Y | - | - | - | N/A | - | BLOCKED pending commercial product-integration permission; scan submission prohibited |
| Wappalyzer technographics `wappalyzer-technographics` | Priority B-4 / SA-07 | Y | - | - | - | N/A | - | BLOCKED pending explicit written Enterprise/custom embedding rights |
| BuiltWith technographics `builtwith-technographics` | Priority B-4 / SA-07 | Y | - | - | - | N/A | - | BLOCKED pending written clarification of customer-facing/product-use rights |
| SEC EDGAR cybersecurity disclosures | SA-04 | Y | Y | Y | Y | N/A | - | targeted Item 1.05 metadata capability; CIK target registry empty and deployment User-Agent required |
| PhishTank verified online phishing data | SA-04 | Y | Y | Y | Y | N/A | - | global URL telemetry capability; application key/onboarding and deployment User-Agent required |
| Licensed incident reporting `licensed-incident-reporting` | SA-07 | Y | - | - | - | N/A | - | BLOCKED pending concrete provider, customer-facing rights, approved fields and runtime onboarding |
| Licensed ransomware metadata `licensed-ransomware-metadata` | SA-07 | Y | - | - | - | N/A | - | BLOCKED pending licensed metadata provider; actor/victim/private content remains prohibited |
| Licensed STIX/TAXII `licensed-stix-taxii` | SA-07 | Y | - | - | - | N/A | - | BLOCKED pending provider, tenant/collection scope, markings, commercial rights and adapter |
| Licensed phishing metadata `licensed-phishing-metadata` | SA-07 | Y | - | - | - | N/A | - | BLOCKED; PhishTank remains the current governed public path |
| Licensed malware metadata `licensed-malware-metadata` | SA-07 | Y | - | - | - | N/A | - | BLOCKED pending licensed metadata provider; binaries/download paths prohibited |
| Licensed passive DNS `licensed-passive-dns` | SA-07 | Y | - | - | - | N/A | - | BLOCKED pending provider contract, permitted fields, retention, quotas and adapter |
| Licensed certificate telemetry `licensed-certificate-telemetry` | SA-07 | Y | - | - | - | N/A | - | BLOCKED pending commercial entitlement beyond the governed public CT path |
| Licensed passive exposure `licensed-passive-exposure` | SA-07 | Y | - | - | - | N/A | - | BLOCKED pending provider-specific customer-facing data rights and onboarding |
| Licensed technography `licensed-technographic-observations` | SA-07 | Y | - | - | - | N/A | - | BLOCKED pending explicit embedding/redistribution rights and onboarding |
| Licensed cloud-asset observations `licensed-cloud-asset-observations` | SA-07 | Y | - | - | - | N/A | - | BLOCKED pending concrete provider, field scope, commercial rights and adapter |
| Generic company incident family `official-company-incident-disclosures` | SA-10 | Y | - | - | - | N/A | - | NOT_RELEVANT as an executable source; provider-specific decomposition required beyond SEC |
| Generic regulator/CERT incident family `regulator-cert-incident-notices` | SA-10 | Y | - | - | - | N/A | - | NOT_RELEVANT as an endpoint; concrete official provider records are required |
| Generic vendor PSIRT family `official-vendor-psirt` | SA-10 | Y | - | - | - | N/A | - | NOT_RELEVANT as an executable source; concrete vendor feeds/APIs are required |
| Generic Linux advisory family `official-linux-security-advisories` | SA-10 | Y | - | - | - | N/A | - | NOT_RELEVANT as an executable source; distro-specific provider records are required |
| Generic package advisory family `official-package-security-advisories` | SA-10 | Y | - | - | - | N/A | - | NOT_RELEVANT as an executable source; ecosystem-specific provider records are required |
| Official corporate disclosures `official-corporate-disclosures` | SA-06 | Y | - | - | - | N/A | - | MANUAL bounded first-party acquisition + Lot 18 analyst-reviewed mapping |
| Official regulatory change notices `official-regulatory-change-notices` | SA-06 | Y | - | - | - | N/A | - | MANUAL source-specific regulator review + Lot 18 evidence classification |
| Licensed corporate news `licensed-corporate-news-metadata` | SA-07 | Y | - | - | - | N/A | - | BLOCKED pending concrete licensed provider, customer-facing rights and runtime onboarding |
| Official relationship disclosures `official-relationship-disclosures` | SA-06 | Y | - | - | - | N/A | - | MANUAL Lot 19 review; marketing claim is not contracted/current incumbency evidence |
| Public partner directories `public-partner-directory-metadata` | SA-06 | Y | - | - | - | N/A | - | MANUAL review-required relationship metadata; no current-contract inference |
| Public case studies `public-case-study-metadata` | SA-06 | Y | - | - | - | N/A | - | MANUAL bounded historical-capable evidence; no current-incumbency inference |
| Public certificate relationship metadata `public-certificate-relationship-metadata` | SA-06 | Y | - | - | - | N/A | - | MANUAL only where relationship semantics are explicit; issuance alone proves nothing |
| Sherlock `sherlock-local` | SA-05 | Y | Y | - | - | N/A | - | MANUAL governed local adapter; empty target registry; deployment binary/version + analyst-reviewed sites/target required |
| OWASP Amass `amass-local` | SA-05 | Y | - | - | - | N/A | - | BLOCKED as blanket executor; passive modules require provider-specific governance and active enumeration/probing is prohibited |
| theHarvester `theharvester-local` | SA-05 | Y | - | - | - | N/A | - | BLOCKED as blanket executor; each search/API upstream requires separate authorization |
| SpiderFoot `spiderfoot-local` | SA-05 | Y | - | - | - | N/A | - | BLOCKED as blanket executor; mixed passive/active modules require provider-level decomposition |
| Recon-ng `recon-ng-local` | SA-05 | Y | - | - | - | N/A | - | BLOCKED as blanket executor; marketplace modules are independent acquisition paths |
| Maltego `maltego-local` | SA-05 | Y | - | - | - | N/A | - | MANUAL analyst visualization/investigation over already authorized evidence; transforms require separate review |
| LinkedIn official API `linkedin-official-api` | SA-07 | Y | - | - | - | N/A | - | BLOCKED pending approved official/licensed access and adapter |
| Discord authorized integration `discord-authorized-integration` | SA-07 | Y | - | - | - | N/A | - | BLOCKED pending administrator-installed connector or authorized export and exact scope |
| Premium CTI `premium-cti-licensed` | SA-07 | Y | - | - | - | N/A | - | BLOCKED pending concrete licensed provider, contract-bound scopes and deployment approval |
| Commercial dataset `commercial-data-licensed` | SA-07 | Y | - | - | - | N/A | - | BLOCKED pending concrete dataset, approved fields, lawful purpose and customer-facing rights |
| BrixHub `brixhub` | SA-08 | Y | - | - | - | N/A | - | BLOCKED pending access/licence/data review |

## Known broader source families

The repository already models candidate families delivered in Lots 13–22: incident reporting, ransomware metadata, threat telemetry, passive exposure, advisory providers, corporate-change intelligence, relationship intelligence, professional context and conditional premium integrations. SA-10 resolves family placeholders as non-executable terminal records; a future useful source must be introduced provider-specifically rather than reopening a generic family as an adapter.

SA-00 established the lifecycle and truth model. SA-01 through SA-04 promote only provider-specific paths whose implementation, authorization and runtime boundaries are explicit. Priority B and SA-05 through SA-09 preserve the same provider-level discipline. SA-13 extends that same provider-specific model with separately evidenced live ATS integrations.

## Reconciliation invariant

Every `source_id` contained in every checked-in `source_portfolio*.yml` bundle must have an activation record. Repository tests enforce this invariant across the activation bundles added by each SA/Priority-B increment.

OSINT Framework synchronization remains candidate discovery only. Its import record is terminal `manual`; every discovered candidate still requires its own provider-specific `active`, `manual`, `blocked`, `replaced`, `duplicate`, or `not_relevant` decision before execution can exist.

## SA-10 final source completeness and live-validation gate

SA-10 separates classification completeness from controlled live validation:

- no activation record may remain `planned`;
- `recherche-entreprises`, `gleif` and `bodacc-identity` are terminal `manual` because their adapters require deployment-specific organization/identifier targets and authorization;
- `osint-framework-import` is terminal `manual` as analyst catalogue-discovery input only;
- `public-web-example-fr-organization` is terminal `not_relevant` as a production source while the checked-in sample remains disabled and unauthorized;
- `official-company-incident-disclosures`, `regulator-cert-incident-notices`, `official-vendor-psirt`, `official-linux-security-advisories` and `official-package-security-advisories` are terminal `not_relevant` as generic executable sources; any useful future provider must receive a concrete source record;
- terminal non-executable records require reasons and never gain authorization/execution/live stages for completeness metrics;
- active real sources missing any mandatory integration stage remain unresolved by `audit_inventory` even when unit/integration CI is green;
- `reference-synthetic`, `ashby-job-board` and `recruitee-careers-site` are currently fully integrated checked-in records; future provider-specific controlled live evidence may extend this set;
- CI must not be reinterpreted as provider live validation;
- activation truth, this matrix and `SA_10_FINAL_SOURCE_COMPLETENESS_AUDIT.md` must agree on the classification-complete but live-validation-open state;
- one exact final SHA must pass the complete backend and frontend CI before an SA increment is merged;
- issue SA-10 remains open until the outstanding active-source controlled live-validation set is empty.

## SA-13 extended ATS activation boundary

SA-13 is complete only when:

- `ashby-job-board` and `recruitee-careers-site` have provider-specific Source Governance, target registries, real adapters, canonical job mapping, executable portfolio entries, enabled schedules and controlled live provider proof;
- the dedicated live workflow executes the production `AshbyAdapter` and `RecruiteeAdapter`, not synthetic provider clients, and requires non-empty provider checkpoints;
- successful controlled provider proof has demonstrated actual public acquisition (59 Ashby jobs and 1 Recruitee job in the recorded proof) while preserving zero commercial projections when those real jobs contain no canonical cyber match;
- Recruitee's observed `YYYY-MM-DD HH:MM:SS UTC` timestamp form is normalized explicitly and locked by a deterministic regression test rather than weakening timezone requirements;
- `teamtailor-public-jobs` has a real JSON:API Public Read adapter with regional host, API-version and bounded pagination controls, but remains non-executable/non-scheduled/non-live until one approved account and Public Read token exist through Provider Onboarding;
- no ATS path accesses applications, resumes, screening data, candidate records or write endpoints;
- all three adapters reuse the existing collection scheduler/worker and `CanonicalPublicJob` path; no ATS-specific scheduler, health subsystem or persistence silo is introduced;
- Source Activation bundle truth, this matrix, `SA_13_ATS_EXPANSION.md`, deterministic tests and the live workflow agree on the exact stages;
- the normal repository CI and the dedicated live workflow both pass on the exact final PR head before squash merge.

## SA-05 governed local OSINT completion boundary

SA-05 is complete only when:

- `sherlock-local` has a concrete local adapter, bounded subprocess runner, strict native-CSV parser, Lot 21 `PublicCommunityContext` mapping and an empty checked-in target registry;
- Sherlock execution is always analyst-target-bound, site-allowlisted, lawful-basis/retention-bound, version-pinned by deployment and `REVIEW_REQUIRED` at the evidence layer;
- the checked-in activation record stays `manual`, not `authorized` or `executable`, because repository defaults contain neither an approved deployment binary/version nor an approved target/site set;
- username presence never creates or merges a person identity and never authorizes outreach or commercial inference;
- `amass-local`, `theharvester-local`, `spiderfoot-local` and `recon-ng-local` remain terminal `blocked` as blanket executors because their modules/upstreams have independent authorization and active/passive semantics;
- `maltego-local` remains `manual` analyst visualization/investigation over already authorized evidence and does not grant server-side transform authority;
- none of the local frameworks gains Tor/proxy/quota-bypass, private-data, de-anonymization, active prospect probing or arbitrary-module authority;
- activation truth, this matrix and deterministic reconciliation/privacy/runtime tests agree on all six tool records;
- one exact final SHA passes the complete backend and frontend CI;
- `live_tested` remains false unless a separately authorized controlled live proof is recorded.

Any future automation of a Sherlock target or a framework module requires a separate reviewed deployment/source activation change. Tool availability alone never grants network authorization.

## SA-06 corporate-change and relationship completion boundary

SA-06 is complete only when:

- `official-corporate-disclosures` and `official-regulatory-change-notices` are terminal `manual` paths through the existing bounded public-web/search/archive acquisition plus Lot 18 review/mapping;
- `official-relationship-disclosures`, `public-partner-directory-metadata`, `public-case-study-metadata` and `public-certificate-relationship-metadata` are terminal `manual` paths through existing bounded acquisition plus Lot 19 review/mapping;
- `licensed-corporate-news-metadata` is terminal `blocked` and explicitly owned by SA-07 until a concrete provider and customer-facing commercial entitlement are approved;
- no generic family gains `adapter_present`, `authorized`, `executable`, `scheduled` or `live_tested` merely because reusable public-web or canonical mapper capabilities exist;
- a page, feed item, certificate, partner directory entry or case study remains source material and never automatically becomes a confirmed material change, contracted relationship, active incumbent, service need, opportunity or outreach target;
- first-party marketing statements remain claimed evidence unless stronger evidence exists, historical case studies remain historical-capable, and certificate issuance remains separate from relationship proof;
- source activation truth, this matrix and deterministic SA-06 reconciliation tests agree on all seven families;
- the complete repository backend and frontend CI pass on one exact SHA before SA-07 begins.

## SA-07 licensed and premium provider completion boundary

SA-07 is complete only when:

- every record with `activation_wave: SA-07` is terminal `blocked`, has a non-empty provider/deployment reason and is listed explicitly in this matrix;
- no SA-07 record remains `planned`;
- no blocked SA-07 record has `adapter_present`, `authorized`, `executable`, `scheduled` or `live_tested` merely because an API, account, trial, free tier or sales page exists;
- the eleven generic licensed families, the six Priority B-4 providers, LinkedIn, Discord, premium CTI and commercial data all remain fail-closed until provider-specific commercial rights and deployment onboarding are proven;
- LinkedIn is limited to official/licensed access and Discord to administrator-installed connectors or authorized exports; scraping, copied browser sessions, self-bots, member scraping and private-message collection are not activation methods;
- licensed ransomware/malware families do not authorize actor portals, victim/private/leaked content, malware binaries or sample downloads;
- Lot 22 conditional-provider controls remain the required future execution gate: approval dossier, Provider Onboarding, Source Governance, executable Source Portfolio state, adapter capability, quotas/cost and pause/kill-switch controls;
- provider evidence never by itself proves organization ownership, deployment, applicability, exposure, compromise, commercial need, opportunity or outreach authorization;
- activation truth, this matrix, `SA_07_LICENSED_PREMIUM_PROVIDER_DECISIONS.md` and deterministic reconciliation tests agree on the complete SA-07 inventory;
- the complete repository backend and frontend CI pass on one exact final SHA before SA-08 begins.

## Priority B-4 passive-provider completion boundary

Priority B-4 is complete only when:

- `censys-platform-passive`, `shodan-passive-data`, `securitytrails-passive-data`, `urlscan-passive-search`, `wappalyzer-technographics` and `builtwith-technographics` each have an explicit provider-level activation record;
- each record identifies its concrete provider/product path, current commercial-entitlement dependency, onboarding/secret model, prohibited methods, unique evidence value and canonical mapping in `PRIORITY_B_04_PASSIVE_PROVIDER_DECISIONS.md`;
- none is made executable from a free, research, community, trial or ordinary subscription whose rights do not prove customer-facing incorporation into this standalone commercial product;
- all six remain terminal `blocked` SA-07 licensed dependencies until a compatible written entitlement is reviewed and deployment onboarding exists;
- no B-4 record has `adapter_present`, `authorized`, `executable`, `scheduled` or `live_tested` while blocked;
- no provider-specific adapter, credential, schedule, active scan/probe or prospect scan-submission path is created by B-4;
- Censys/Shodan/SecurityTrails/urlscan are mapped only as potential future passive provider observations, and Wappalyzer/BuiltWith only as potential future passive technographic observations;
- provider evidence never by itself proves organization ownership, production deployment, vulnerability applicability, verified exposure, compromise or commercial need;
- activation truth, this matrix and deterministic reconciliation tests agree on all six terminal records;
- the complete repository backend and frontend CI pass on one exact final SHA.

Any later SA-07 provider activation must separately implement Source Governance, Provider Onboarding, secrets, quotas/cost, portfolio registration, shared runtime integration, canonical projections and controlled live validation before changing the terminal state.

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
- licensed passive providers are terminalized under SA-07 as blocked dependencies rather than falsely activated under `.example.invalid` placeholders;
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
