# SA-15 to SA-20 — Full OSINT Activation Roadmap

## Purpose

This roadmap turns every useful remaining source family into owned implementation work. It complements the completed historical SA-00 through SA-14 increments and implements the normative target in [`../OSINT_FULL_IMPLEMENTATION_MANDATE.md`](../OSINT_FULL_IMPLEMENTATION_MANDATE.md).

A provider that currently lacks a credential, entitlement, target, browser account, deployment connector, or stable API remains unfinished work. The missing prerequisite must be tracked and resolved. `blocked`, `manual`, or `not live tested` must not be used as a convenient terminal state for a useful capability.

Safety and authorization remain runtime preconditions. This roadmap does not authorize CAPTCHA/MFA/access-control bypass, stolen credentials, private victim data, deceptive identities, or exploitation of third-party systems.

## Global exit rule for each SA

An SA may close only when every in-scope provider has one of these outcomes:

1. fully integrated through a real production adapter and controlled live proof;
2. duplicate/replaced by a demonstrably equivalent canonical provider;
3. explicitly rejected by the product owner as no longer useful.

A missing account, contract, API key, target or entitlement is not an acceptable permanent closeout reason. It produces a prerequisite task that remains open until resolved or explicitly rejected by the product owner.

---

## SA-15 — Search, news and deferred-provider live completion

### Required providers

- Mojeek Web Search: provision legitimate API access, confirm durable-result-storage rights, run production-adapter live proof and promote to `live_tested`.
- PatentsView: provision a legitimate current API key when provider access permits it, run production-adapter live proof and promote to `live_tested`.
- GDELT: implement the current supported GDELT API/data contract once provider documentation is stable; include provider-specific schemas, bounded collection, source governance, runtime registration and live proof.
- Brave Search: provision an approved deployment token and target/template set and perform controlled production-adapter live validation.
- Internet Archive CDX: perform controlled production-adapter live validation on an approved neutral or first-party target.
- Bing or another approved search API: implement one additional independent general web-search provider to avoid single-provider dependence.
- Google search/dork workflow: keep analyst links mandatory and implement an official programmable/search API path wherever a valid entitlement supports automation.

### Dork coverage

Versioned search templates must cover at least:

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
- annual reports, presentations, standards and technical publications.

### Exit gate

All implemented search providers have real runtime proof or an explicitly open prerequisite task. GDELT is no longer a documentation-only candidate.

---

## SA-16 — Automatic company web crawling, headless browser and authorized login

### Primary outcome

Turn the existing target-bound public-web collector into a deployment-grade automatic company-site acquisition system for approved organization domains.

### Required capabilities

- automatic governed crawl-target creation after canonical domain resolution;
- robots policy evaluation;
- sitemap-index recursion;
- sitemap traversal;
- RSS/Atom discovery and traversal;
- same-origin link extraction;
- recursive crawling with configurable depth/page/byte/time/concurrency budgets;
- path and origin controls;
- incremental recrawl and change detection;
- HTML and structured-data parsing;
- public PDF and office-document routing to quarantine;
- JavaScript-rendered page support;
- generalized Playwright/Chromium worker runtime;
- screenshots where evidence requires rendered state;
- controlled browser downloads;
- source-specific browser adapters;
- provider-approved/customer-authorized login workflows;
- OAuth/SSO support where legitimate deployment credentials exist;
- analyst-assisted MFA checkpoints that resume the same governed job afterward;
- automatic scheduling and freshness rules per organization;
- live validation against approved first-party/neutral websites and authenticated test accounts.

### Explicit non-goal

The crawler must not defeat CAPTCHA, MFA, authentication or provider restrictions. A challenge creates a human/provider-approved checkpoint, not an evasion workflow.

### Exit gate

The system can take an approved organization with a resolved public domain, generate a governed crawl target, crawl recursively within configured scope, switch to headless rendering when needed, process documents, and persist provenance-backed resources through a real end-to-end live proof.

---

## SA-17 — Passive infrastructure, technography and local OSINT frameworks

### Open/public infrastructure providers

Live-validate and operationalize:

- Cloudflare DNS-over-HTTPS;
- Cert Spotter CT;
- IANA-bootstrapped RDAP;
- additional approved CT sources where useful;
- ASN/BGP public datasets.

### Commercial/passive providers

Obtain the required commercial/product entitlements and implement or activate provider-specific adapters for:

- Shodan passive/indexed data APIs;
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

Provider onboarding must record exact plans, rights, secrets, quotas and retention constraints. Scan/exploitation APIs are separate from passive OSINT and require their own explicit security-testing authorization.

### Local OSINT frameworks

Implement provider/module-aware execution for:

- Sherlock;
- OWASP Amass passive modules;
- theHarvester approved upstreams;
- SpiderFoot approved passive modules;
- Recon-ng approved modules;
- Maltego approved transforms;
- additional useful OSINT Framework tools selected by the source-catalog reconciliation process.

Mixed frameworks must be decomposed so that one unavailable module does not block safe useful modules.

### Exit gate

Every named passive provider and local framework has a production execution path, live proof, duplicate/replacement decision, or an open concrete prerequisite owned by the same SA until resolved.

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
- PhishTank;
- licensed STIX/TAXII;
- licensed ransomware-claim metadata;
- licensed phishing/malware/incident metadata;
- licensed passive threat/IOC feeds.

The platform must preserve claim state (`actor_claim`, `public_report`, `official_confirmation`, correction/retraction) and must not require private victim data, stolen credentials or attacker interaction.

### Exit gate

All existing executable vulnerability/incident providers are genuinely live-tested and the major concrete CERT/vendor/licensed provider families have real provider-specific adapters rather than generic placeholders.

---

## SA-19 — Professional, LinkedIn, Reddit, Discord and community activation

### LinkedIn

The product must pursue a legitimate executable LinkedIn path through one or more of:

- official API scopes actually granted;
- authorized LinkedIn partner/product integration;
- written-authorized automated collection path for exact hosts/fields/purpose;
- analyst-link/manual verification as fallback while machine access is being provisioned.

Normal user-session scraping, access-control bypass and deceptive account creation are not required or authorized by this roadmap.

### Reddit

Implement an official/licensed API adapter for approved public communities and organization-level signals with provenance, deletion and retention behavior.

### Discord

Implement administrator-installed bot/connector and authorized-export ingestion paths with tenant/server scope, permission checks, audit and retention.

### Additional professional/community providers

Implement where useful:

- Stack Exchange API;
- Mastodon public APIs;
- Bluesky APIs;
- YouTube Data API and permitted metadata/transcript workflows;
- conference/event speaker directories;
- association and professional directories;
- licensed B2B contact-data provider(s).

### Exit gate

Professional/community categories are no longer documentation-only. At least one legitimate executable path exists for LinkedIn professional context, Reddit, Discord and the other high-value community sources selected for production.

---

## SA-20 — Documents, media, developer ecosystems and final live-completeness gate

### Document/media processing

Implement and validate:

- PDF parsing and extraction;
- Office Open XML parsing;
- Apache Tika or equivalent extraction where justified;
- ExifTool metadata extraction in isolation;
- OCR;
- translation;
- image/document metadata normalization;
- archive/container inspection;
- file reputation/malware screening for downloaded artifacts;
- screenshot evidence;
- bounded raw-artifact retention only where source policy permits it.

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

### Final completeness audit

Generate a machine-derived matrix with separate fields for:

- adapter present;
- authorized deployment path;
- executable;
- scheduled/invokable;
- live tested;
- operational owner;
- remaining prerequisite;
- target remediation date/SA.

No useful source may disappear behind a generic `blocked`, `manual`, `planned`, or provider-family placeholder without an owned activation plan.

### Exit gate

SA-20 is the new full-source-completeness gate. The project may claim broad OSINT/source readiness only when useful source coverage is provider-specific, executable where legitimate access exists, live-tested where legitimate exercise is possible, and all remaining prerequisites are explicit operational work rather than terminal documentation states.