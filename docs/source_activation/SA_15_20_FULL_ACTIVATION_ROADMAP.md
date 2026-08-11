# SA-15 to SA-20 — Full OSINT Activation Roadmap

## Purpose

This roadmap turns every useful remaining source family into owned implementation work. It complements the completed historical SA-00 through SA-14 increments and implements the normative targets in:

- [`../OSINT_FULL_IMPLEMENTATION_MANDATE.md`](../OSINT_FULL_IMPLEMENTATION_MANDATE.md);
- [`../SOCIAL_COMMUNITY_ACQUISITION_REQUIREMENTS.md`](../SOCIAL_COMMUNITY_ACQUISITION_REQUIREMENTS.md);
- [`../OSINT_AUTOMATION_PIPELINES.md`](../OSINT_AUTOMATION_PIPELINES.md).

A provider that currently lacks a credential, entitlement, target, browser account, deployment connector, administrator installation or stable API remains unfinished work. The missing prerequisite must be tracked and resolved. `blocked`, `manual`, adapter-only or `not live tested` must not be used as a convenient terminal state for a useful capability.

This document assigns capability ownership to waves. It is **not** the final realistic implementation-lot decomposition. After the documentation review, these waves must be split into smaller independently implementable lots/SA increments with exact exit gates and exact-head live proof.

## Global exit rule for each SA

An SA may close only when every in-scope provider/capability has one of these outcomes:

1. fully integrated through a real production adapter and controlled live proof;
2. duplicate/replaced by a demonstrably equivalent canonical provider;
3. explicitly removed from product scope by product-owner decision.

A missing account, contract, API key, target, entitlement, provider approval or administrator installation is not an acceptable permanent closeout reason. It produces a prerequisite task that remains open until resolved or the capability is explicitly removed from scope.

---

## SA-15 — Search, SERP, dorks, news and deferred-provider live completion

### Required providers

- Mojeek Web Search: provision legitimate API access, confirm durable-result-storage rights, run production-adapter live proof and promote to `live_tested`.
- PatentsView: provision a legitimate current API key when provider access permits it, run production-adapter live proof and promote to `live_tested`.
- GDELT: implement the current supported GDELT API/data contract once provider documentation is stable; include provider-specific schemas, bounded collection, source governance, runtime registration and live proof.
- Brave Search: provision an approved deployment token and target/template set and perform controlled production-adapter live validation.
- Internet Archive CDX: perform controlled production-adapter live validation on an approved neutral or first-party target.
- Bing or another approved independent search API: implement one additional general web-search provider to avoid single-provider dependence.
- Google search/dork workflow: implement official programmable/search API paths where an entitlement supports automation, while retaining analyst/browser routes where provider rules allow them.
- Common Crawl: retain production live proof and integrate it into the normalized SERP/discovery pipeline.

### Normalized SERP pipeline

Implement a canonical search-result contract containing provider, query/template ID, rank, result URL, canonical URL, title, snippet/description, provider record ID, result type and timestamps.

Search providers must feed the same discovery/evidence-acquisition path rather than custom one-off downstream logic.

### Dork coverage

Versioned search templates must cover at least:

- `site:` company research;
- `filetype:` documents;
- `intitle:` and `inurl:` patterns;
- procurement and contracts;
- cyber products and providers;
- SOC/SIEM/MDR/XDR/SOAR;
- IAM/PAM/Zero Trust;
- cloud and Kubernetes;
- AppSec/DevSecOps/SAST/DAST/SCA/SBOM;
- pentest/red-team/purple-team;
- GRC/NIS2/DORA/ISO 27001/SOC 2/PCI DSS/HDS;
- incident/ransomware/breach/regulator;
- recruitment and security-team growth;
- architecture/migration/transformation;
- partner/customer/case-study evidence;
- annual reports, presentations, standards and technical publications;
- code/package/developer evidence.

### Exit gate

The platform has a normalized multi-provider SERP path with real production-adapter live proof from each available provider, and search results can drive governed evidence retrieval rather than remaining analyst-only links.

---

## SA-16 — Automatic company crawling, generalized browser, structured web extraction and authorized login

### Primary outcome

Turn the existing target-bound public-web collector into a deployment-grade automatic company-site acquisition system for approved organization domains.

### Required company-crawl capabilities

- automatic governed crawl-target creation after canonical domain resolution;
- first crawl scheduling without developer-edited YAML;
- robots policy evaluation;
- sitemap-index recursion;
- sitemap traversal;
- RSS/Atom discovery and traversal;
- security.txt discovery;
- homepage/seed discovery;
- same-origin link extraction;
- recursive crawling with configurable depth/page/byte/time/concurrency/freshness budgets;
- path and origin controls;
- incremental recrawl and change detection;
- tombstones and version history;
- provenance and crawl-health metrics.

### Structured extraction

Implement extraction from:

- HTML DOM;
- semantic HTML metadata;
- JSON-LD;
- OpenGraph/public metadata;
- public embedded JSON application state;
- authorized structured JSON responses used by rendered applications;
- script-exposed public structured state;
- CSS/resource references when useful for technology attribution;
- response headers;
- canonical/alternate links;
- public forms/endpoints;
- document/media links.

### Browser runtime

Implement generalized Playwright/Chromium workers with:

- isolated disposable process/context;
- JavaScript rendering;
- navigation and form interaction;
- authorized login;
- OAuth/SSO;
- screenshots;
- DOM/structured-state capture where permitted;
- controlled downloads;
- request interception and host/path allowlists;
- resource/time budgets;
- crash cleanup;
- resumable jobs.

### User-delegated accounts

Implement user-delegated provider identities tied to a real CIP tenant/user or deployment service principal, with isolated secret/session references, scopes, expiry, revocation/deletion and audit.

Where a provider permits automated registration, support tenant-controlled email aliases or provider-approved service accounts. Human/provider-approved CAPTCHA/MFA checkpoints must resume the same job automatically after completion.

### Live validation

Live-test the complete path against real approved first-party/neutral websites and an authorized authenticated test account:

`organization/domain -> automatic target -> recursive crawl -> browser fallback -> structured extraction -> document acquisition -> provenance-backed evidence`.

### Exit gate

The system can take an approved resolved company domain and automatically research it across static and rendered pages, recursively crawl within configured scope, process documents and persist versioned evidence without developer intervention.

---

## SA-17 — Passive infrastructure, Shodan/Censys/technography and local OSINT frameworks

### Open/public infrastructure providers

Live-validate and operationalize:

- Cloudflare DNS-over-HTTPS;
- Cert Spotter CT;
- IANA-bootstrapped RDAP;
- additional useful CT sources;
- ASN/BGP public datasets.

### Commercial/passive providers

Obtain the required commercial/product entitlements and implement or activate provider-specific adapters for:

- Shodan passive/indexed-data APIs;
- Censys search/platform APIs;
- SecurityTrails;
- urlscan existing-scan/search metadata;
- VirusTotal metadata within licensed scope;
- GreyNoise;
- AbuseIPDB;
- Spamhaus;
- Wappalyzer;
- BuiltWith;
- HTTP Archive or equivalent technography sources;
- licensed passive DNS/certificate/cloud-asset/exposure providers.

Provider onboarding must record exact plans, rights, secrets, quotas and retention constraints. Scan/exploitation APIs remain separate from passive OSINT and require their own explicit security-testing authorization.

### Local OSINT frameworks

Implement provider/module-aware execution for:

- Sherlock;
- OWASP Amass passive and explicitly authorized modules;
- theHarvester with governed upstreams;
- SpiderFoot with provider/module-level controls;
- Recon-ng with module-level source governance;
- Maltego approved transforms;
- additional useful OSINT Framework tools selected by source-catalog reconciliation.

Mixed frameworks must be decomposed so that one unavailable module does not block safe useful modules.

### Technology-fusion path

Combine passive provider metadata with:

- public-web fingerprints;
- headers/certificates/DNS;
- source-code/package metadata;
- public jobs;
- contracts/documents;
- public/consented community messages;
- vendor case studies;
- technical PDFs/presentations.

### Exit gate

Every named passive provider and local framework has a production execution path and real live proof where provider access is available, with technology observations preserving evidence class, confidence and chronology.

---

## SA-18 — Vulnerability, incident, CTI, ransomware and phishing full activation

### Vulnerability providers to live-validate

- CISA KEV;
- NVD;
- FIRST EPSS;
- GitHub Global Security Advisories;
- CVE Services;
- OSV;
- CIRCL Vulnerability-Lookup.

### Additional advisory providers

Implement provider-specific sources for:

- CERT-FR;
- ENISA;
- relevant national/sector CERT feeds;
- vendor PSIRTs;
- Linux distribution advisories;
- package ecosystem advisories;
- cloud/container advisories where useful.

### Incident and CTI providers

Operationalize and live-test:

- SEC EDGAR cybersecurity disclosures;
- official regulator and company incident feeds;
- public authority/law-enforcement notices;
- PhishTank or equivalent phishing metadata;
- STIX/TAXII providers;
- ransomware-claim metadata providers;
- phishing/malware/incident metadata providers;
- passive threat/IOC/malicious-infrastructure feeds;
- current GDELT/news evidence where relevant.

The platform must preserve claim state (`actor_claim`, `public_report`, `official_confirmation`, correction/retraction), source independence and chronology.

### Exit gate

All existing executable vulnerability/incident providers are genuinely live-tested and major concrete CERT/vendor/CTI/ransomware/phishing provider families have real provider-specific adapters rather than generic placeholders.

---

## SA-19 — LinkedIn, Reddit, Discord, BrixHub and professional/community activation

This SA is governed in detail by `../SOCIAL_COMMUNITY_ACQUISITION_REQUIREMENTS.md`.

### LinkedIn

LinkedIn is mandatory. Implement at least one legitimate executable production route and retain support for all obtainable legitimate routes:

- official API scopes;
- approved partner/licensed integration;
- written-authorized automated collection;
- provider-authorized user-delegated browser session;
- analyst-assisted verification while machine access prerequisites are being resolved.

For an authorized browser route, extract provider-approved rendered DOM and public structured state for company pages, professional profiles, current role/company, public professional posts, jobs, technologies/vendors/products and stable provider identifiers.

LinkedIn is not complete until a real route is live-tested.

### Reddit

Implement official/licensed API collection with:

- public communities;
- public posts/comments;
- chronology;
- pseudonymous provider identifiers;
- technology/vendor/product mention extraction;
- explicit self-declared professional affiliation candidates;
- edits/deletions;
- checkpoints/rate limits;
- live proof.

### Discord

Implement administrator-installed bot/connector and authorized-export paths.

For authorized servers/channels, the bot must support:

- guild/server metadata;
- channel enumeration;
- message history;
- threads;
- edits/deletions;
- server-scoped usernames/display names/member identifiers exposed by granted permissions;
- link/domain/attachment metadata;
- technology/vendor/tool mention extraction;
- team/project/role context;
- replay-safe checkpoints;
- server/channel kill switch;
- live proof on a consented test server.

Discord-derived commercial signals should focus on professional/technical context such as tooling, migrations, security-stack changes, integration issues, hiring/capability gaps and vendor evaluation/replacement discussions.

Provider-scoped pseudonyms remain pseudonymous unless self-declared, consented, administrator-mapped or explicitly linked by an authorized professional source.

### BrixHub.cc

BrixHub is mandatory and must not remain review-only.

Resolve and implement:

- operator/owner;
- current registration/access flow;
- terms/privacy;
- field/dataset inventory;
- API/export/browser paths;
- authentication/session model;
- automation rights;
- storage/commercial-use rights;
- quotas;
- retention/deletion;
- source IDs/provenance;
- provider-specific adapter;
- controlled live validation.

If API access exists, implement it. If the legitimate product path is browser-only, implement a provider-specific isolated browser adapter.

### Additional professional/community providers

Implement where useful:

- Stack Exchange API;
- Mastodon public APIs;
- Bluesky APIs;
- YouTube Data API and permitted metadata/transcript workflows;
- conference/event speaker directories;
- association and professional directories;
- vendor communities;
- licensed B2B contact-data provider(s).

### Exit gate

LinkedIn, Reddit, Discord and BrixHub each have a real provider-specific production path and controlled live proof or remain explicitly open implementation work; the SA must not declare them finished merely because an access prerequisite exists.

---

## SA-20 — Documents, OCR, reverse image, media, developer ecosystems and final live-completeness gate

### Document/media processing

Implement and validate:

- PDF parsing and extraction;
- Office Open XML parsing;
- Apache Tika or equivalent extraction where justified;
- ExifTool metadata extraction in isolation;
- OCR for scanned PDFs/screenshots/images;
- language detection;
- translation;
- image/document metadata normalization;
- archive/container inspection;
- file reputation/malware screening for downloaded artifacts;
- screenshot evidence;
- bounded raw-artifact retention only where source policy permits it.

### OCR pipeline

Record engine/version, page/image ID, detected language, confidence, source artifact hash, normalized text and provenance.

### Reverse-image/visual pipeline

Implement:

- perceptual hashing;
- exact hashing;
- OCR-derived visual search queries;
- image metadata;
- logo/product/vendor detection;
- screenshot similarity;
- provider-authorized reverse-image APIs;
- analyst review of ambiguous matches.

### Developer ecosystems

Live-validate current adapters and expand to:

- GitHub organization repository metadata;
- GitLab group/project metadata;
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
- vendor community portals.

### Identity/procurement/ATS residual live proof

Before SA-20 closes, perform controlled live validation or concrete prerequisite resolution for existing executable but non-live sources such as:

- Recherche d'entreprises;
- GLEIF;
- BODACC;
- TED;
- BOAMP;
- DECP;
- Greenhouse;
- Lever;
- SmartRecruiters;
- Teamtailor where account/token is provisioned.

### End-to-end live company research proof

Run at least one approved real-company/first-party validation proving a chain such as:

```text
company identity
-> domain
-> SERP/dork discovery
-> automatic recursive crawl
-> browser-rendered retrieval where needed
-> document acquisition/quarantine
-> OCR/structured extraction
-> technology/provider/community evidence
-> provenance-backed canonical evidence
```

### Final completeness audit

Generate a machine-derived matrix with separate fields for:

- adapter present;
- authorized deployment path;
- executable;
- scheduled/invokable;
- live tested;
- operational owner;
- remaining prerequisite;
- target remediation SA/lot.

No useful source may disappear behind a generic `blocked`, `manual`, `planned`, adapter-only or provider-family placeholder without owned implementation work.

### Exit gate

SA-20 is the current broad source-completeness gate. The project may claim broad OSINT/source readiness only when useful source coverage is provider-specific, executable where legitimate access exists, live-tested where legitimate exercise is possible, and every unresolved prerequisite remains explicit owned implementation work rather than terminal documentation state.

---

## Mandatory follow-up: realistic lot decomposition

Before coding all SA-15→SA-20 capabilities as one oversized programme, perform a dedicated roadmap review that decomposes the mandatory scope into realistically sized implementation units.

Each future lot/SA increment should ideally own one coherent vertical capability, have deterministic tests, one controlled live proof where external access exists, a reversible migration when needed, and one exact-head CI gate.

The decomposition must preserve every mandatory capability in this roadmap; it may change sequencing and lot boundaries, but it must not silently drop LinkedIn, Reddit, Discord, BrixHub, Shodan, local OSINT frameworks, SERP/dorks, automatic company crawling, generalized browser acquisition, CTI/ransomware/phishing, OCR or reverse-image work.
