# Governed OSINT Collection Catalog

## Purpose

This document defines the OSINT capabilities that Cyber Intelligence Platform must implement end-to-end.

The product goal is no longer merely to catalogue tools or classify providers. Every useful public, licensed, customer-authorized or provider-authorized capability must have a provider-specific activation path to production execution and controlled live validation.

The normative target is [`OSINT_FULL_IMPLEMENTATION_MANDATE.md`](OSINT_FULL_IMPLEMENTATION_MANDATE.md). The delivery sequence is [`source_activation/SA_15_20_FULL_ACTIVATION_ROADMAP.md`](source_activation/SA_15_20_FULL_ACTIVATION_ROADMAP.md).

Historical Source Activation records remain truthful snapshots of prior state, but a historical `blocked`, `manual`, adapter-only or non-live status does not mean a useful capability is considered finished forever.

## Mandatory lifecycle

For every useful provider or tool:

```text
catalogued
-> provider identified
-> access path reviewed
-> source governance
-> provider onboarding / entitlement
-> target model
-> production adapter
-> deterministic tests
-> runtime registration
-> schedule or explicit invocation
-> canonical evidence mapping
-> controlled live production-adapter proof
-> operational support
```

A missing key, contract, provider account, deployment target, written permission or stable API is a prerequisite to resolve, not a completion condition.

## Acquisition modes

The platform must support all legitimate acquisition modes required by useful sources:

| Mode | Meaning |
| --- | --- |
| `official_api` | Provider-documented API with the required access scope. |
| `open_data` | Official reusable dataset/feed/bulk export. |
| `licensed_api` | Contracted API/dataset whose licence covers the deployment use. |
| `static_http` | Ordinary approved public-page/document retrieval. |
| `recursive_web` | Governed recursive crawl inside approved origin/path/resource budgets. |
| `authorized_browser` | Isolated Playwright/Chromium rendering and first-party interaction. |
| `authorized_authenticated_web` | Legitimate provider/customer-authorized account/session workflow. |
| `consented_connector` | Administrator/customer-installed application, bot, export or workspace connector. |
| `local_tool_module` | Local OSINT framework module whose upstream behavior is separately governed. |
| `manual_import` | Approved export/import path through quarantine. |

`manual_review` may exist as a temporary fallback but must not hide a useful executable provider path that should be implemented.

## Global safety and authorization boundary

The product is required to implement broad acquisition capabilities, including recursive crawling, browser rendering and legitimate authenticated workflows.

Normal OSINT acquisition does not require defeating access controls. The product must not use:

- CAPTCHA/MFA/authentication bypass to obtain unauthorized access;
- stolen/replayed third-party sessions;
- credential guessing or validation;
- deceptive identities/account farms to evade provider controls;
- exploit-based collection against third parties;
- private victim files, stolen credentials, extorted datasets or private communications.

CAPTCHA/MFA encountered by a legitimate authorized account is handled through a human/provider-approved checkpoint and resume flow.

Active scanning/exploitation is a separate security-testing capability requiring explicit target/technique/time authorization. Passive OSINT approval never silently grants it.

---

# 1. Company identity, establishments, groups and registries

## Required providers/capabilities

- API Recherche d'entreprises;
- Sirene direct path where it adds provider value;
- BODACC;
- GLEIF LEI and relationships;
- BRREG / Brønnøysundregistrene;
- INPI/RNE when legitimate account credentials are provisioned;
- OpenCorporates or equivalent licensed global company data;
- European Business Register/national registries where legitimate machine access exists;
- official corporate filings and annual reports.

## Required outputs

- legal entity and establishment identity;
- authoritative identifiers;
- aliases/prior names;
- status/activity/address;
- parent/subsidiary/group claims;
- canonical domain candidates;
- source conflicts;
- non-diffusion/suppression constraints.

## Activation rule

Target-dependent adapters must gain real deployment target provisioning and controlled live proof rather than remain permanently dormant.

Target SA: residual completion in **SA-20**.

---

# 2. Procurement, contracts, suppliers, grants and renewal timing

## Required providers

- TED Search;
- BOAMP;
- DECP;
- PLACE;
- CORDIS;
- ADEME;
- useful national/regional procurement portals;
- EU/national funding transparency datasets;
- public framework agreements;
- official award/contract notices;
- supplier/partner/customer directories;
- case studies and official relationship publications.

## Required outputs

- buyer/authority;
- awardee/provider;
- procedure/lot identifiers;
- subject/taxonomy;
- amount/currency;
- publication/deadline/award/start/end/modification dates;
- incumbent/provider hypotheses;
- renewal windows;
- exact distinction among contract evidence, public relationship publication and inference.

Existing executable TED/BOAMP/DECP paths without current `live_tested` evidence must receive controlled live validation.

Target SA: **SA-20** for residual live proof and portal expansion.

---

# 3. Hiring, cyber teams and ATS

## Required provider coverage

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
- company-specific public career feeds/pages.

## Required outputs

- role/title/team;
- location;
- seniority/job family;
- explicit technologies;
- cyber service/capability terms;
- programme/migration/transformation language;
- first/last seen;
- withdrawn/current status;
- organization target linkage.

Existing Ashby/Recruitee live proofs remain valid historical evidence. Teamtailor and additional ATS remain mandatory activation work.

Target SA: residual completion in **SA-20**.

---

# 4. Search engines, dorks, archives and web discovery

## Required providers

- Brave Search API;
- Mojeek Web Search;
- Bing or equivalent approved independent search API;
- Google analyst dorks and official Google API products where valid entitlement permits automation;
- Common Crawl URL Index;
- Internet Archive/Wayback CDX;
- approved archived-body retrieval where separately governed;
- GDELT current supported stack;
- GitHub Code Search;
- GitLab search/API paths;
- publication, patent, standards and documentation search providers;
- Crossref;
- W3C;
- PatentsView.

## Mandatory dork families

### Contracts/procurement

```text
"{organization}" (marché OR accord-cadre OR contrat OR attributaire OR titulaire OR renouvellement)
"{organization}" (appel d'offres OR consultation OR CCTP OR DCE) cybersecurity
site:{organization_domain} (contrat OR prestataire OR fournisseur OR intégrateur) filetype:pdf
```

### Cyber service needs

```text
"{organization}" (pentest OR "test d'intrusion" OR "red team" OR "purple team")
"{organization}" (SOC OR SIEM OR MDR OR XDR OR SOAR OR "threat hunting")
"{organization}" (IAM OR IGA OR PAM OR "Zero Trust")
"{organization}" (NIS2 OR DORA OR "ISO 27001" OR "SOC 2" OR "PCI DSS" OR HDS)
"{organization}" (CSPM OR CNAPP OR Kubernetes OR "cloud security")
"{organization}" (AppSec OR DevSecOps OR SAST OR DAST OR SCA OR SBOM)
"{organization}" (DFIR OR forensic OR ransomware OR "incident response")
```

### Domain-focused research

```text
site:{organization_domain} (cybersécurité OR sécurité OR risque OR conformité) filetype:pdf
site:{organization_domain} (architecture OR migration OR transformation) (cloud OR IAM OR SOC OR sécurité)
site:{organization_domain} (prestataire OR partenaire OR intégrateur OR fournisseur)
site:{organization_domain} (incident OR ransomware OR indisponibilité OR "violation de données")
site:{organization_domain} (recrutement OR carrière OR jobs) (pentest OR GRC OR AppSec OR SOC OR IAM)
```

Search metadata is a discovery lead until the referenced resource is acquired through an approved evidence path.

Target SA: **SA-15**.

---

# 5. Automatic corporate website crawling

## Required product behavior

For every organization with a resolved canonical public domain and deployment-approved research scope, the platform must be able to create a governed crawl target automatically and collect the maximum useful public evidence inside that scope.

## Required crawler capabilities

- automatic `robots.txt` discovery/evaluation;
- sitemap and sitemap-index recursion;
- RSS/Atom discovery;
- security.txt;
- same-origin link extraction;
- recursive traversal;
- configurable depth/page/byte/time/concurrency budgets;
- approved-origin/path filtering;
- canonical URL/deduplication;
- HTML/structured data/JSON-LD;
- public PDF/Office document discovery;
- document text extraction through quarantine;
- JavaScript-rendered browser fallback;
- legitimate authenticated paths for exact authorized accounts;
- ETag/Last-Modified/hash incremental refresh;
- resource versioning and tombstones;
- crawl freshness schedules;
- complete provenance.

Recursive crawling is required; “unlimited” resource consumption is not. Bounds are operational/safety controls.

Target SA: **SA-16**.

---

# 6. Headless browser and legitimate login

A generalized Playwright/Chromium runtime is mandatory.

It must support:

- JavaScript rendering;
- first-party navigation/interactions;
- source-specific cookies;
- provider-approved service/test accounts;
- OAuth/SSO when authorized;
- administrator-installed integrations;
- analyst-assisted MFA;
- screenshots;
- controlled downloads;
- disposable contexts/processes;
- request interception;
- audit of all browser/auth transitions.

A useful source must not be permanently excluded solely because it requires browser execution or a legitimate login.

Target SA: **SA-16**.

---

# 7. Domains, DNS, certificates, passive exposure and technography

## Mandatory open/public coverage

- Cloudflare DNS-over-HTTPS;
- IANA-bootstrapped RDAP;
- Certificate Transparency;
- Cert Spotter;
- ASN/BGP public data.

## Mandatory commercial/provider activation targets

- Shodan passive/indexed APIs;
- Censys;
- SecurityTrails;
- urlscan existing-scan/search;
- VirusTotal metadata within licensed scope;
- GreyNoise;
- AbuseIPDB;
- Spamhaus;
- Wappalyzer;
- BuiltWith;
- HTTP Archive/equivalent technography;
- licensed passive DNS;
- licensed certificate telemetry;
- licensed passive exposure;
- licensed cloud-asset metadata.

Every useful commercial provider must have an onboarding/entitlement plan and live-validation target. Lack of current commercial rights is a prerequisite to resolve.

Target SA: **SA-17**.

---

# 8. Local OSINT frameworks and OSINT Framework catalogue

## Mandatory local-tool coverage

- Sherlock;
- OWASP Amass passive modules;
- theHarvester approved upstream providers;
- SpiderFoot approved modules;
- Recon-ng approved modules;
- Maltego approved transforms;
- additional useful OSINT Framework entries.

## Module decomposition rule

A framework is not treated as one binary authorization decision. Each module/provider is classified by:

- target type;
- upstream host/provider;
- passive/active behavior;
- credential requirements;
- data category;
- network behavior;
- quota;
- output mapping;
- deployment authorization.

Legitimate useful modules proceed independently even when another module requires a different authorization or is not selected.

## OSINT Framework import

OSINT Framework remains a discovery taxonomy, but every useful imported candidate must eventually receive:

- canonical provider/tool identity;
- implementation owner;
- target SA;
- provider/module access plan;
- adapter/runtime design;
- live-test plan.

Target SA: **SA-17**, with residual final audit in **SA-20**.

---

# 9. Technologies, public code and developer ecosystems

## Existing/required providers

- GitHub organization repositories;
- GitHub Code Search;
- GitLab groups/projects;
- PyPI;
- npm;
- Maven Central;
- NuGet;
- crates.io;
- RubyGems;
- public container registries;
- SBOM/release feeds;
- public issue trackers;
- technical documentation indexes;
- Stack Exchange;
- vendor community portals.

## Required outputs

- official organization repositories/projects;
- package/artifact identity;
- release cadence;
- declared technology/dependency evidence;
- public documentation;
- security advisories;
- organization-level technical hypotheses.

Personal developer identity correlation is not required for ordinary organization research.

Target SA: **SA-20**.

---

# 10. Vulnerabilities and advisories

## Mandatory providers

- CISA KEV;
- NVD;
- FIRST EPSS;
- GitHub Security Advisories;
- CVE Services;
- OSV;
- CIRCL Vulnerability-Lookup;
- vendor PSIRTs;
- CERT-FR;
- ENISA;
- national/sector CERT feeds;
- Linux distribution advisories;
- package/ecosystem advisories;
- cloud/container advisories where useful.

Existing executable providers must receive real controlled live proof.

Global vulnerability data remains separate from organization-specific technology/applicability evidence.

Target SA: **SA-18**.

---

# 11. Incidents, CTI, ransomware and phishing

## Mandatory provider families

- organization incident statements/status pages;
- SEC EDGAR cyber disclosures;
- regulator/data-protection notices;
- CERT/law-enforcement/public authority notices;
- PhishTank;
- licensed incident/news APIs;
- licensed STIX/TAXII;
- licensed ransomware-claim metadata;
- licensed phishing metadata;
- licensed malware/IOC metadata;
- passive threat/infrastructure feeds.

## Claim states

- `actor_claim`;
- `public_report`;
- `official_confirmation`;
- `regulatory_notice`;
- `analyst_inference`;
- `retracted_or_disputed`;
- `false_attribution`.

Threat-actor/public-source claims must not be silently promoted to official facts.

Private victim files, stolen credentials, extorted datasets and private negotiations are not required acquisition targets.

Target SA: **SA-18**.

---

# 12. LinkedIn, Reddit, Discord and professional/community intelligence

## LinkedIn

The project must pursue an executable legitimate path through one or more of:

- official LinkedIn API scopes actually granted;
- authorized LinkedIn partner/product integration;
- written-authorized automated collection for exact scope;
- analyst-link/manual verification while machine access is being provisioned.

A missing current LinkedIn entitlement is an activation prerequisite, not a declaration that professional-network intelligence is unimportant.

## Reddit

Implement official/licensed API collection for approved public communities and organization-level signals.

## Discord

Implement administrator-installed bot/connector and authorized-export paths with exact server/tenant scope.

## Additional providers

- Stack Exchange;
- Mastodon;
- Bluesky;
- YouTube Data API and permitted transcript/metadata workflows;
- conference/event speaker directories;
- professional associations;
- licensed B2B professional-contact providers.

Private messages and unrelated private-life data remain outside ordinary product research.

Target SA: **SA-19**.

---

# 13. Corporate news, regulatory and market-change intelligence

Required sources include:

- official company newsrooms/feeds;
- regulator/CERT/court/public-authority feeds;
- licensed news APIs;
- GDELT current supported stack;
- industry associations;
- standards bodies;
- M&A/funding/restructuring/leadership/new-site/data-centre/cloud/transformation announcements.

Every extracted event preserves publication time, event time, source type, claim type, organization-resolution confidence and correction state.

Target SA: **SA-15/SA-18** depending provider family.

---

# 14. Documents, files, metadata, OCR and translation

## Mandatory safe processing capabilities

- PDF parsing;
- Office Open XML parsing;
- Apache Tika or equivalent extraction;
- ExifTool metadata extraction in isolation;
- OCR;
- translation;
- image/document metadata normalization;
- archive/container inspection;
- safe screenshot evidence;
- file reputation/malware screening;
- bounded extraction and page references.

All downloaded artifacts are quarantined and parsed in disposable workers.

Target SA: **SA-20**.

---

# 15. BrixHub

`https://brixhub.cc/` remains a mandatory provider assessment/implementation candidate.

Required work:

1. identify owner/operator;
2. verify terms/privacy;
3. verify data provenance;
4. enumerate datasets/fields/countries;
5. determine account/payment/API/browser/export methods;
6. determine automation/commercial-reuse rights;
7. document quotas/rate limits;
8. determine retention/correction/deletion obligations;
9. obtain a legitimate reviewed sample when permitted;
10. implement source governance and Provider Onboarding;
11. implement exact schemas/adapter;
12. run controlled live production-adapter validation.

If no useful legitimate access path ultimately exists, the product owner must explicitly reject the source; uncertainty alone is not completion.

Target SA: prerequisite work begins immediately, final residual gate **SA-20**.

---

# 16. Provider onboarding, accounts and credentials

Useful providers requiring accounts/keys must be operationalized through Provider Onboarding.

Supported patterns must include:

- API keys;
- OAuth;
- service accounts;
- paid subscriptions;
- tenant/account identifiers;
- provider-approved service/test accounts;
- browser account sessions;
- administrator-installed connectors;
- approved organization-controlled verification mailbox/alias;
- human checkpoints for KYC/payment/contract/MFA.

Raw secrets never enter Git or ordinary application persistence.

Disposable mailboxes, fake identities and account multiplication to evade provider controls are not required implementation techniques.

---

# 17. Controlled live-validation standard

For every legitimately exercisable provider, live proof must use the production adapter and establish:

- current connectivity;
- provider schema compatibility;
- authentication path where applicable;
- policy-before-network;
- bounded collection;
- canonical RawObservation/evidence mapping;
- checkpoint/idempotency behavior;
- secret hygiene;
- evidence boundary;
- expected non-empty data for the chosen validation target/provider.

Mocks, fixtures, skipped workflows and deterministic CI never count as live provider evidence.

---

# 18. Implementation waves

| SA | Mandatory outcome |
| --- | --- |
| SA-15 | Search/news completion: Mojeek, PatentsView, GDELT, Brave/IA live proof, additional search provider, Google official path where entitled. |
| SA-16 | Automatic company crawl, recursive crawling, generalized headless browser, legitimate authenticated login, OAuth/SSO, analyst-assisted MFA. |
| SA-17 | Passive infrastructure/technography + Shodan/Censys/SecurityTrails/urlscan/VT/GreyNoise/etc. + local OSINT frameworks. |
| SA-18 | Vulnerability live proof, vendor/CERT advisories, incidents, CTI, ransomware, phishing, STIX/TAXII. |
| SA-19 | LinkedIn legitimate path, Reddit, Discord consented connector, professional/community sources. |
| SA-20 | Documents/media, developer ecosystems, residual identity/procurement/ATS live proof, final broad completeness gate. |

## Final definition of completeness

At SA-20, every useful source must be one of:

```text
fully integrated
replaced by a fully integrated canonical source
duplicate of a fully integrated canonical source
explicitly excluded by product-owner decision
```

A useful provider that merely lacks a key, entitlement, account, target, browser workflow, stable API or controlled live proof remains unfinished work.