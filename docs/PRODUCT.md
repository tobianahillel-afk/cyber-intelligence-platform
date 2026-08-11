# Product Definition

## Product statement

Cyber Intelligence Platform is a complete, standalone cyber revenue-intelligence and commercial-operations system. It discovers organizations with current or emerging cybersecurity needs, explains the evidence behind those needs, maps the relevant professional buying committee, and lets users manage the entire investigation and opportunity lifecycle inside the product.

The platform is evidence-first. Observations, source claims, corroborated facts, contradictions, inferences, need hypotheses, commercial signals and analyst decisions remain distinct and provenance-backed.

The product must pursue broad source completeness rather than accepting a documentation-only catalogue. Every useful public, licensed, customer-authorized or provider-authorized source must have a concrete path to a production adapter, runtime execution, controlled live validation and operational ownership. The normative implementation target is defined in [`OSINT_FULL_IMPLEMENTATION_MANDATE.md`](OSINT_FULL_IMPLEMENTATION_MANDATE.md).

## Primary users

- cybersecurity service providers and integrators;
- penetration-testing and audit firms;
- SOC, SIEM, MDR and incident-response teams;
- governance, risk and compliance teams;
- cloud, identity, application-security, resilience and OT-security specialists;
- cybersecurity product vendors;
- cyber revenue-intelligence and business-development analysts;
- independent cybersecurity consultants.

## Native product capabilities

### Opportunity discovery and alerts

Users define versioned rules and saved searches for:

- tenders, awards, contracts, framework agreements and renewals;
- cyber hiring and team growth;
- technology and provider evidence;
- public vulnerability/advisory context;
- incidents, ransomware claims and regulatory notices;
- corporate change, funding, M&A and transformation programmes;
- passive public infrastructure and technographic evidence;
- professional-role and buying-committee context;
- public documents discovered through search APIs, dorks, crawling, archives, repositories and community sources.

Alerts always remain linked to evidence and confidence.

### Company intelligence workspace

Each company record is intended to consolidate:

- legal entities, establishments, brands, subsidiaries, parent groups and identifiers;
- domains, public subdomains, certificates, passive assets and public web resources;
- current and historical public pages, documents, feeds, security.txt and archived resources;
- procurement, contracts, providers, awards and renewal timing;
- technologies, products and versions with source/time/confidence;
- vulnerability and advisory applicability hypotheses;
- incidents, public claims, corrections and official confirmations;
- recruitment and capability signals;
- corporate change, funding and regulatory context;
- partners, suppliers, integrators and customer relationships where supported;
- professional roles and permitted business contact channels;
- service-family matches and need hypotheses;
- source provenance, freshness, contradictions and analyst decisions.

### Automatic company research

When an organization is resolved to an approved canonical public domain, the platform must be able to generate a governed acquisition target and automatically collect the maximum useful evidence within the deployment-approved scope.

Required acquisition capabilities include:

- robots policy evaluation;
- sitemap and sitemap-index traversal;
- RSS/Atom discovery;
- security.txt discovery;
- same-origin link discovery;
- recursive crawling with configurable depth/page/byte/time/concurrency limits;
- HTML, structured-data and metadata extraction;
- public PDF and office-document acquisition through quarantine;
- JavaScript-rendered page collection through an isolated browser worker;
- legitimate authenticated collection for provider/customer-authorized accounts;
- incremental recrawl and change detection;
- immutable resource versions and tombstones;
- automatic freshness scheduling.

The target is broad automated organization research, not permanently empty checked-in target registries.

### Search, dorks and archives

The product must maintain provider-aware search and dork templates covering:

- contracts and procurement;
- cybersecurity technologies and providers;
- pentest/red-team/purple-team;
- SOC/SIEM/MDR/XDR/SOAR;
- IAM/PAM/Zero Trust;
- GRC/NIS2/DORA/ISO 27001/SOC 2/PCI DSS/HDS;
- cloud/Kubernetes;
- AppSec/DevSecOps/SAST/DAST/SCA/SBOM;
- incident/ransomware/breach/regulator;
- recruitment and leadership;
- architecture, migration and transformation;
- partners, case studies and customer references;
- annual reports, investor presentations, standards, patents and technical publications.

Provider coverage must include existing Brave/Common Crawl/Internet Archive/GitHub paths and future legitimate integrations such as Mojeek, GDELT, Bing or equivalent providers, plus Google analyst/API workflows where provider entitlement permits automation.

Search-result metadata is discovery context until the referenced resource is retrieved through an approved evidence path.

### Passive infrastructure and technography

The product must pursue complete lawful passive coverage through provider-specific integrations for:

- DNS and RDAP;
- Certificate Transparency;
- Shodan passive/indexed data APIs;
- Censys;
- SecurityTrails or equivalent passive-DNS data;
- urlscan existing-scan/search metadata;
- VirusTotal metadata within licensed scope;
- GreyNoise, AbuseIPDB, Spamhaus and equivalent reputation feeds;
- ASN/BGP data;
- Wappalyzer, BuiltWith, HTTP Archive or equivalent technography sources;
- licensed passive-exposure/certificate/cloud-asset providers.

A missing entitlement is an onboarding prerequisite to resolve, not a declaration that the provider is permanently outside the roadmap.

Passive-source activation does not silently authorize active scanning or exploitation. A separate explicit security-testing engagement is required for active testing.

### Local OSINT frameworks

The product must support useful local OSINT tools through provider/module-level controls, including:

- Sherlock;
- OWASP Amass passive modules;
- theHarvester with separately governed upstream providers;
- SpiderFoot approved modules;
- Recon-ng approved modules;
- Maltego approved transforms;
- additional high-value OSINT Framework tools after provider-specific review.

Mixed active/passive frameworks are decomposed so useful legitimate modules can be implemented independently.

### Incident, CTI, ransomware and phishing

The system must operationalize lawful public or licensed sources for:

- company incident statements;
- SEC/regulator/CERT/law-enforcement notices;
- PhishTank and equivalent lawful phishing metadata;
- licensed STIX/TAXII;
- licensed ransomware-claim metadata;
- licensed malware and IOC metadata;
- licensed incident/news providers;
- provider-specific threat telemetry.

Threat-actor allegations remain allegations until corroborated. Private victim material, stolen credentials, extorted datasets and private communications are not required inputs for the product.

### Professional and community intelligence

The platform must pursue legitimate executable integrations for:

- LinkedIn official APIs, authorized partner products or written-authorized automated access;
- Reddit official/licensed APIs;
- Discord administrator-installed bots/connectors or authorized exports;
- Stack Exchange;
- Mastodon;
- Bluesky;
- YouTube Data API and permitted transcript/metadata workflows;
- conference and association directories;
- licensed B2B professional-contact providers.

The product goal is to activate these categories through legitimate provider paths rather than leave them as documentation-only placeholders.

### Professional organization map

The platform builds an evidence-backed professional organization map containing:

- current and historical professional roles;
- role category, seniority, department and geography;
- documented business-unit/reporting relationships;
- likely buying-committee roles;
- public or licensed professional contact channels;
- source, collection date, confidence, permitted purpose, retention, correction and suppression state.

Private-life data remains outside normal B2B research scope.

### Native commercial operations

The product owns:

- organizations and account ownership;
- opportunities and qualification state;
- alerts and watchlists;
- tasks, reminders and assignments;
- research requests;
- analyst notes and immutable history;
- professional contacts and buying committees;
- interaction history through approved workflows;
- scoring explanations and overrides;
- source freshness/coverage dashboards;
- complete audit trails.

## Browser and authenticated acquisition

A generalized isolated Playwright/Chromium runtime is a required product capability and must not remain indefinitely deferred.

It must support:

- JavaScript-rendered sites;
- first-party interactions;
- provider-approved/customer-authorized login flows;
- source-specific cookies/sessions;
- OAuth/SSO where the deployment is authorized;
- analyst-assisted MFA checkpoints;
- screenshots;
- controlled downloads;
- request interception and source host allowlists;
- disposable browser contexts;
- full navigation/authentication audit.

Legitimate login requirements are implementation work, not a reason to permanently exclude a useful source.

## Access-control boundary

The product mandate is broad implementation, but normal OSINT acquisition does not require defeating security controls.

The following require a separate explicit security-testing authorization or remain outside acquisition scope:

- CAPTCHA/MFA/authentication/access-control bypass;
- credential guessing or validation;
- stealing/replaying another user's cookies or sessions;
- deceptive identities or disposable account farms used to evade controls;
- exploit-based acquisition of third-party data;
- private victim files, stolen credentials or private communications.

When a legitimate account presents CAPTCHA/MFA, the system supports a human/provider-approved checkpoint and resumes afterward.

## Provider onboarding

A provider requiring a key, paid plan, account, contract, service account or written permission remains mandatory implementation work when the source is useful.

Provider Onboarding must support:

- secret references;
- OAuth/service accounts;
- account-specific tenant configuration;
- entitlement/contract evidence;
- quotas and cost controls;
- revocation/rotation;
- human checkpoints where provider approval is required;
- live-validation readiness.

A source is not considered complete because the adapter exists while the required legitimate credential remains unprovisioned.

## Live-validation requirement

For every provider that can be legitimately exercised, full integration requires a controlled live run through the production adapter.

The proof must validate current connectivity, provider schema, authentication if applicable, bounded acquisition, canonical mapping, evidence boundaries and secret hygiene. Mocks, fixtures, skipped workflows and unit tests never count as live proof.

## Core workflows

### Investigate a company

Input may be a company name, legal identifier, domain, URL, technology, tender, incident, professional role, contract document or search result.

The platform then resolves identity, activates approved research targets, gathers public/licensed evidence, reconciles facts, generates service-need hypotheses and presents the complete research trail.

### Monitor markets and needs

Approved sources run continuously or on provider-appropriate schedules. Changes update existing canonical state rather than duplicating entities.

### Research public information

The product combines:

- official APIs;
- feeds and bulk datasets;
- automatic governed crawling;
- search providers and dorks;
- archive indexes;
- passive intelligence providers;
- local OSINT modules;
- isolated browser acquisition;
- legitimate authenticated workflows;
- analyst-assisted checkpoints;
- controlled imports and licensed connectors.

### Score and manage an opportunity

Opportunity scoring remains explainable and versioned and may consider evidence confidence, recency, buying intent, service fit, contract timing, technology relevance, incident urgency, professional context, uncertainty and contradictions.

## Product data model direction

The product owns canonical records for:

- organizations, establishments, brands, groups, domains, assets and relationships;
- people, professional identities, roles and permitted business contact channels;
- sources, authorizations, observations, claims, evidence, corrections and lineage;
- web resources, documents, versions, screenshots and acquisition history;
- technologies, products, versions, vendors, providers, contracts and tenders;
- vulnerabilities, advisories, incidents, regulatory events, recruitment and business events;
- service families, need hypotheses, commercial motions and signal mappings;
- rules, saved searches, alerts, watchlists, opportunities, stages, tasks, notes and engagement history;
- provider accounts, entitlements, secret references, suppression, retention and audit records.

## Product boundaries

The platform is expected to use every useful legitimate public/licensed/authorized acquisition path and to implement missing adapters rather than permanently stop at a catalogue entry.

Authorization and safety remain explicit. Active security testing, exploit validation or access-control testing is a separate capability requiring explicit target scope and engagement authorization.

## Success criteria

- Every material fact and alert links to provenance and observed time.
- Every useful source has a concrete implementation and live-validation path.
- Missing keys/contracts/accounts remain visible prerequisites, not hidden terminal statuses.
- Automatic governed company crawling is operational for approved domains.
- Recursive crawling, headless browser rendering and legitimate authenticated collection are production capabilities.
- Search/dork/archive coverage is multi-provider.
- Passive infrastructure, technography, CTI, professional/community and developer ecosystems are provider-specific rather than generic placeholders.
- Every real provider reported as fully integrated has a real production-adapter live proof.
- Company, person, role, technology, contract and provider identities are deduplicated without unsupported automatic claims.
- Every score and need hypothesis remains explainable and rejectable.
- Retention, correction, objection, suppression and authorization expiry propagate through derived state.