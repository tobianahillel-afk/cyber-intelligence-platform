# Full OSINT Implementation Mandate

## Status

This document is normative for future source-activation and acquisition work. Historical lot and SA closeout documents remain truthful records of what was implemented at the time they were merged, but they do not limit the future target state described here.

Detailed mandatory behavior is further defined by:

- [`SOCIAL_COMMUNITY_ACQUISITION_REQUIREMENTS.md`](SOCIAL_COMMUNITY_ACQUISITION_REQUIREMENTS.md);
- [`OSINT_AUTOMATION_PIPELINES.md`](OSINT_AUTOMATION_PIPELINES.md).

## Product mandate

Cyber Intelligence Platform must pursue complete implementation of every useful public, licensed, customer-authorized, or provider-authorized acquisition capability that materially improves organization, procurement, technology, cyber-risk, incident, professional-context, market, or commercial intelligence.

A useful source must not be abandoned merely because it currently needs an API key, paid plan, provider account, written permission, target registry, browser workflow, service account, contract review, administrator installation, user-delegated session or provider-specific onboarding. Those conditions are implementation prerequisites to resolve and track. They are not a reason to pretend the capability is finished.

The target state for each useful source is:

```text
catalogued
-> reviewed
-> mapped
-> adapter_present
-> authorized for the deployed scope
-> executable
-> scheduled or explicitly invokable
-> controlled live tested
-> observable and supportable
-> fully integrated
```

## Completion rule

A source is not complete because it appears in documentation, has a schema, has a mock, passes unit tests, has a manual analyst link, or has a non-executable source record.

For a useful source, completion requires all applicable items below:

1. provider-specific source identity and owner;
2. current access path and provider contract documentation;
3. source-governance policy for exact hosts, paths, methods, purposes and data classes;
4. provider-onboarding profile and secret references where authentication is required;
5. target registry or global collection scope as appropriate;
6. production adapter with provider-specific schemas;
7. deterministic unit and contract tests with no live-network dependency;
8. runtime registration, checkpoints, retry, quota, circuit, freshness and source-health handling;
9. canonical RawObservation and downstream evidence mapping;
10. schedule or analyst/runtime invocation path;
11. controlled production-adapter live validation against a legitimate real provider and approved target;
12. exact-head CI after the live-proof state is recorded;
13. operational runbook and failure/recovery behavior.

## Temporary prerequisite state

A useful provider may be temporarily unable to reach `live_tested` because an external prerequisite is missing. Examples include:

- API key or paid subscription;
- enterprise entitlement;
- written product-integration permission;
- provider approval;
- administrator-installed connector;
- customer authorization;
- account-specific tenant identifier;
- service-account provisioning;
- approved authenticated browser account;
- current provider API contract not yet published.

Such a provider must have a named owner, exact missing prerequisite, target SA, and acceptance test. A temporary prerequisite state must not be treated as permanent source completion.

## Web acquisition mandate

The public-web subsystem must evolve from target-specific sitemap collection into a complete organization-web acquisition capability for approved organizations.

For every organization whose canonical public domain has been resolved and whose collection scope is approved, the platform must support automatic collection of the maximum useful public evidence within that approved scope.

Required capabilities include:

- automatic `robots.txt` discovery and policy evaluation;
- sitemap and sitemap-index traversal;
- RSS and Atom discovery and traversal;
- `/.well-known/security.txt` discovery;
- same-origin link discovery;
- recursive crawling with configurable depth, page, byte, time, concurrency and freshness budgets;
- canonical URL normalization and duplicate suppression;
- HTML DOM extraction;
- semantic metadata extraction;
- JSON-LD extraction;
- public embedded JSON/application-state extraction;
- authorized collection of structured JSON responses used by rendered applications;
- public CSS/resource references where useful for technology attribution;
- public PDF and office-document discovery through the quarantine pipeline;
- document text and metadata extraction;
- JavaScript-rendered page collection through the isolated browser runtime;
- authenticated collection for accounts and sessions explicitly authorized for the exact source and purpose;
- incremental recrawl through ETag, Last-Modified, hashes, source timestamps and change detection;
- content versioning, tombstones and provenance;
- automatic crawl scheduling for approved company targets;
- crawl observability, per-host budgets and shutdown controls.

Recursive crawling is therefore a required capability. It is not required to be unlimited in resource consumption: runtime budgets and policy scope remain mandatory engineering controls.

## Automatic company crawl

When an organization is resolved to a canonical public domain, the system must be able to create or update a governed crawl target automatically from a deployment-approved organization-research policy.

The target-generation path must:

1. preserve the organization/domain evidence used to create the target;
2. apply tenant and deployment authorization;
3. determine allowed origins and path scope;
4. create crawl budgets and freshness rules;
5. schedule the first crawl;
6. feed discovered resources into the normal evidence pipeline;
7. stop or quarantine collection when scope, ownership, authorization, or provider behavior materially changes.

The goal is broad automatic company-site coverage, not a permanently empty checked-in target registry.

## Browser and authenticated-web mandate

A generalized isolated headless-browser runtime is mandatory and must not remain indefinitely deferred.

It must support:

- Playwright/Chromium execution in disposable workers;
- JavaScript-rendered websites;
- first-party navigation and interaction;
- screenshots where evidentially useful;
- DOM/structured-state capture where permitted;
- controlled downloads through quarantine;
- source-specific cookies and session state;
- provider-approved or customer-authorized login workflows;
- OAuth and SSO flows where the deployment is authorized to use them;
- analyst-assisted MFA/CAPTCHA when the legitimate account requires a human factor;
- provider-approved service/test accounts;
- user-delegated provider accounts tied to a real CIP tenant/user or deployment service identity;
- tenant-controlled email aliases where the provider permits automated account lifecycle;
- deterministic browser adapters with stable extraction contracts;
- request interception, host allowlists and network isolation;
- complete audit of navigations and authentication state transitions.

A legitimate authenticated workflow is an implementation target, not a reason to permanently exclude a source.

## Access-control boundary

The full-implementation mandate does not require defeating security controls. The following are outside the product's acquisition authority unless an explicit security-testing engagement separately authorizes them:

- bypassing CAPTCHA, MFA, authentication, paywalls or provider access controls;
- stealing or replaying another user's cookies or sessions;
- credential guessing, credential stuffing or password validation;
- creating deceptive identities or disposable-account farms to evade provider controls;
- evading bans, quotas or rate limits through account rotation;
- exploiting third-party systems to obtain data;
- collecting private communications, stolen credentials, leaked victim files or extorted datasets.

When a legitimate provider workflow contains CAPTCHA or MFA, the product must support a human or provider-approved completion step and resume afterward.

## Search, SERP and dorking mandate

The platform must maintain and execute, where an authorized provider path exists, a comprehensive search and dork library for organization research.

A normalized SERP pipeline is mandatory. It must persist provider, query/template identity, rank, URL, canonical URL, title, snippet/description, provider record ID, result type, timestamps and source scope.

Mandatory provider/capability coverage includes:

- Brave Search API;
- Mojeek Web Search;
- Bing or equivalent approved web-search API;
- Google analyst links and Google API products where a valid entitlement permits automation;
- provider-authorized browser search execution where a deployment is permitted to automate it;
- Common Crawl URL Index;
- Internet Archive/Wayback CDX and approved archived-content retrieval paths;
- GDELT current supported API stack;
- GitHub REST Code Search and organization/repository APIs;
- GitLab public APIs;
- publication, patent, standards and documentation search APIs;
- organization-domain searches for contracts, tenders, technologies, incidents, hiring, providers, architecture, migration and security documents.

The versioned dork library must cover `site:`, `filetype:`, `intitle:`, `inurl:` and equivalent provider syntax for procurement, contracts, security tooling, cloud, IAM, SOC/SIEM/MDR, AppSec, DevSecOps, GRC, incidents, ransomware, hiring, partners, case studies, technical documents and code/package evidence.

Search metadata remains discovery context until the referenced resource is acquired through an approved evidence path.

## Company identity and corporate-record mandate

The platform must pursue provider-specific integrations for useful official or licensed company registries, including:

- Recherche d'entreprises / Sirene paths;
- BODACC;
- GLEIF;
- BRREG and additional national registries;
- INPI/RNE when credentials are provisioned;
- OpenCorporates or equivalent licensed global company datasets;
- European and national business-register access paths where available.

Target-dependent adapters must gain deployment target provisioning rather than remain permanently dormant.

## Procurement, funding and relationship mandate

The platform must fully operationalize procurement and funding coverage, including:

- TED;
- BOAMP;
- DECP;
- PLACE;
- CORDIS;
- ADEME;
- additional useful national/regional procurement portals;
- EU and national grant/funding transparency datasets;
- official partner directories, case studies, framework agreements and public award notices.

Existing executable providers without live proof must receive controlled production-adapter live validation.

## Hiring and ATS mandate

The platform must expand and live-validate useful official public ATS paths including:

- Greenhouse;
- Lever;
- SmartRecruiters;
- Ashby;
- Recruitee;
- Teamtailor;
- Workday;
- iCIMS;
- Taleo;
- SuccessFactors;
- company-specific public career feeds.

Account/token prerequisites must be resolved through Provider Onboarding and must not be treated as permanent exclusions.

## Passive infrastructure and technography mandate

The platform must pursue complete lawful passive coverage for:

- DNS and RDAP;
- Certificate Transparency;
- Censys approved APIs;
- Shodan approved passive/indexed-data APIs;
- SecurityTrails or equivalent passive DNS/provider data;
- urlscan existing-scan/search APIs;
- VirusTotal licensed/public metadata within approved scope;
- GreyNoise;
- AbuseIPDB;
- Spamhaus;
- ASN/BGP data;
- Wappalyzer, BuiltWith, HTTP Archive or equivalent technography sources;
- licensed passive-exposure, certificate and cloud-asset providers.

No useful commercial provider is considered finished merely because its entitlement is not yet provisioned. The missing entitlement becomes an onboarding deliverable.

Active security testing is a separate capability and requires explicit target authorization; passive OSINT activation does not silently grant scanning or exploitation authority.

## Local OSINT-tool mandate

The platform must support useful local OSINT frameworks through provider-aware modules rather than permanently excluding the framework as a whole.

Mandatory implementation coverage includes:

- Sherlock;
- OWASP Amass passive and explicitly authorized modules;
- theHarvester with each upstream provider governed independently;
- SpiderFoot with provider/module-level capability controls;
- Recon-ng with module-level source governance;
- Maltego transforms where the transform and upstream source are authorized;
- additional high-value OSINT Framework entries after provider-specific review.

A mixed passive/active framework must be decomposed into capabilities. Safe/authorized modules should be implemented even when other modules remain unavailable for the deployment.

## Vulnerability and advisory mandate

Existing providers must be live-validated and extended with concrete vendor and CERT sources:

- CISA KEV;
- NVD;
- FIRST EPSS;
- CVE Services;
- OSV;
- GitHub Security Advisories;
- CIRCL Vulnerability-Lookup;
- vendor PSIRTs;
- CERT-FR, ENISA and other relevant national/sector CERT feeds;
- ecosystem and distribution advisory feeds.

Global vulnerability knowledge remains distinct from organization-specific applicability.

## Incident, CTI, ransomware and phishing mandate

The platform must implement all useful lawful public/licensed incident and CTI paths, including:

- SEC and regulator incident disclosures;
- official company incident statements and status pages;
- CERT and law-enforcement publications;
- PhishTank and equivalent lawful phishing metadata;
- licensed STIX/TAXII collections;
- licensed ransomware-claim metadata providers;
- licensed malware metadata without malware-body ingestion where not required;
- licensed incident/news datasets;
- provider-specific IOC and malicious-infrastructure feeds.

Threat-actor claims must remain claims. Private victim material, stolen credentials and extorted datasets are not required product inputs.

## Professional and community-source mandate

The product must actively pursue executable integrations for professional and community context.

Mandatory source families include:

- LinkedIn through official APIs, authorized partner products, written-authorized automation or another legitimate executable route;
- Reddit official/licensed APIs for public communities;
- Discord administrator-installed bots/connectors and authorized exports;
- Stack Exchange APIs;
- public Mastodon APIs;
- Bluesky APIs;
- YouTube Data API and permitted transcript/metadata workflows;
- conference, association and professional-directory sources;
- licensed B2B professional-contact providers;
- public/authorized vendor communities;
- BrixHub.cc.

For consented Discord servers, the production connector must be able to retrieve authorized channel/message history, server-scoped member identifiers and message chronology, then extract organization-level professional technology/vendor/tool signals with full provenance.

Provider-scoped pseudonymous handles must remain pseudonymous unless the user self-declares another professional identity, consents to linking, an administrator provides a mapping, or an authorized professional source provides an explicit identifier match.

LinkedIn activation is not complete until at least one legitimate real deployment access route is production-wired and live-tested. Reddit and Discord likewise require real provider/connector live proof.

## BrixHub.cc mandate

`https://brixhub.cc/` is a mandatory provider-specific activation target.

The project must determine the current owner/operator, terms, privacy policy, datasets, fields, registration flow, authentication/session model, API/export/browser paths, automation rights, storage/reuse rights, quotas, retention/deletion obligations and a controlled validation target.

If an API exists, implement the API adapter. If an authorized browser-only path is the real product interface, implement a provider-specific isolated browser adapter. If both exist, use the API as the primary stable acquisition path and retain browser acquisition for legitimately available browser-only fields.

BrixHub must not remain a generic review-only placeholder. It remains unfinished work until the provider-specific implementation and real live proof are complete, or the product owner explicitly removes it from scope.

## User-delegated provider-account mandate

Where an external provider requires an account, CIP must support provider-approved account lifecycle tied to the real CIP tenant/user or a deployment service principal.

The model must include:

- owning CIP tenant/user/service principal;
- provider account ID;
- purpose and authorization scope;
- isolated secret/session reference;
- scopes/permissions;
- creation and renewal timestamps;
- expiration/revocation/deletion;
- complete audit history.

Where the provider supports automated registration, CIP may automate it using tenant-controlled aliases or provider-approved service-account mechanisms. Ephemeral aliases may be used for lifecycle isolation only when they remain controlled by the real deployment and do not evade provider controls.

## Document, OCR and media mandate

The safe document-processing stack must expand to include, where useful:

- PDF parsing;
- Office Open XML parsing;
- Apache Tika or equivalent type-specific extraction;
- ExifTool metadata extraction in isolation;
- OCR;
- language detection and translation;
- image/document metadata normalization;
- archive-container inspection;
- malware/file reputation checks for downloaded artifacts;
- evidence-safe screenshots and page references.

OCR must support scanned PDFs, screenshots and images and retain engine/version, source artifact hash, page/image identity, language, confidence and provenance.

## Reverse-image and visual-research mandate

An automated reverse-image/visual-research pipeline is mandatory where images materially contribute evidence.

It should combine provider-authorized reverse-image APIs and local methods such as:

- perceptual hashes;
- exact hashes;
- OCR-derived queries;
- logo/product/vendor detection;
- screenshot similarity;
- image metadata;
- analyst review for ambiguous matches.

Visual matches remain evidence candidates and do not independently prove organization identity or technology deployment.

## Developer-ecosystem mandate

The platform must expand beyond current GitHub/GitLab/PyPI/npm/Maven metadata to useful provider-specific integrations including:

- NuGet;
- crates.io;
- RubyGems;
- container registries;
- official SBOM feeds;
- release feeds;
- public issue trackers;
- technical documentation indexes;
- Stack Exchange and official vendor communities.

## Live-validation mandate

For every provider that can be legitimately exercised, a controlled live test using the production adapter is required before the source may be presented as fully integrated.

A live test must prove at least:

- current provider connectivity;
- real provider schema compatibility;
- authentication path where required;
- browser/session flow where required;
- bounded collection behavior;
- canonical mapping;
- checkpoint/idempotency behavior where applicable;
- zero secret leakage;
- evidence-boundary compliance;
- real non-empty data when the selected validation target/provider is expected to return data.

For automatic company research, live proof must eventually cover an end-to-end chain from company/domain resolution through search/crawl/browser/document/OCR extraction into provenance-backed evidence.

Skipped workflows, mocks, fixtures and documentation checks never count as live proof.

## Roadmap ownership

The implementation sequence after SA-14 is currently defined in [`source_activation/SA_15_20_FULL_ACTIVATION_ROADMAP.md`](source_activation/SA_15_20_FULL_ACTIVATION_ROADMAP.md).

That document is a capability-wave plan, not the final realistic implementation-lot decomposition. A dedicated follow-up roadmap review must split these mandatory capabilities into realistically sized lots/SA increments with exact exit gates.

No later product milestone may claim complete OSINT/source readiness while useful providers remain without a concrete activation plan, production adapter, or legitimate controlled live proof.
