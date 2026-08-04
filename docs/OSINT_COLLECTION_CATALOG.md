# Governed OSINT Collection Catalog

## Purpose

This document defines the OSINT source families, tools, collection modes, evidence rules, and safety boundaries required by Cyber Intelligence Platform.

The objective is to discover and qualify organizations that may need cybersecurity services or products by collecting lawful public or licensed evidence about:

- legal identity, establishments, groups, subsidiaries, brands, and domains;
- public contracts, suppliers, integrators, customers, partners, incumbents, and renewal timing;
- cyber hiring, teams, roles, projects, technologies, and buying committees;
- public internet assets, certificates, DNS, exposed services, and externally visible technologies;
- vulnerabilities, advisories, exploitation status, and product risk;
- incidents, ransomware claims, official confirmations, regulatory notices, and public reporting;
- professional organization roles and public or licensed business contact channels.

This is a source catalog and implementation standard. It is not permission to crawl every listed website. The source registry and its authorization decision remain authoritative before any network request.

## Governing rule

A resource appearing in OSINT Framework, an OSINT blog, a GitHub list, a search result, or a commercial catalog means only that the resource exists. It does not establish that automated collection, commercial reuse, personal-data processing, storage, or republication is permitted.

Every candidate must be assigned exactly one collection mode:

| Mode | Meaning |
|---|---|
| `official_api` | Official documented API or feed approved for the exact fields and purpose. |
| `open_data` | Official downloadable dataset or open-data endpoint with compatible reuse terms. |
| `licensed_api` | Contracted provider whose licence covers the intended B2B intelligence use. |
| `bounded_web` | Public website crawl explicitly approved after terms, robots, privacy, copyright, rate, and retention review. |
| `manual_review` | The platform generates an analyst link or search query; no automated extraction. |
| `authorized_browser` | Browser workflow covered by written authorization for exact hosts, paths, fields, and purpose. |
| `consented_connector` | Data accessed through an administrator-installed application, customer-controlled workspace, authorized export, or equivalent consented integration. |
| `quarantined` | Potentially useful but identity, owner, terms, licence, access method, or data provenance is not validated. No network execution. |
| `blocked` | Collection would require circumvention, deception, private communications, stolen data, prohibited scraping, intrusive testing, or unjustified personal profiling. |

## OSINT Framework integration

OSINT Framework is used as a discovery and taxonomy feed, not as an executable collector list.

The platform should periodically import the public OSINT Framework catalog into a non-executable candidate registry and record:

- category and subcategory;
- tool name and canonical URL;
- declared input and output;
- API, registration, installation, dork, and editable-URL indicators;
- active or passive network behavior;
- last catalog observation;
- current availability;
- owner and terms URL when discoverable;
- proposed project use case;
- legal, privacy, security, and commercial review status;
- approved collection mode or rejection reason.

No imported tool becomes executable automatically. New and changed entries create review tasks. Dead, redirected, ownership-changed, compromised, or materially changed tools return to quarantine.

The relevant OSINT Framework branches are covered below. Categories aimed primarily at private-life investigation, dating profiles, residential information, personal phone enrichment, friendship mapping, or de-anonymization are not product requirements and must remain blocked.

## Collection architecture

```text
organization or domain seed
  -> collection requirement
  -> candidate-source selector
  -> source-policy preflight
  -> approved adapter or analyst task
  -> bounded transport and provider schema
  -> evidence metadata and content hash
  -> canonical observation
  -> organization and asset resolution
  -> corroboration and conflict detection
  -> confidence-scored fact or hypothesis
  -> human review where required
  -> retention, correction, objection, and deletion lifecycle
```

Every adapter must implement:

1. approved host and path allowlists;
2. explicit purpose and allowed data categories;
3. GET-only operation unless a reviewed official API requires another method;
4. authentication through secret references only;
5. MIME type, response size, pagination, date-window, concurrency, and rate limits;
6. retries, backoff, circuit breaking, checkpoints, leases, and idempotency;
7. source timestamps, retrieval timestamps, canonical URL, evidence hash, and provenance;
8. provider-specific strict schemas and normalized output contracts;
9. no storage of raw HTML or documents unless separately approved;
10. redaction and minimization before persistence;
11. retention deadlines and deletion support;
12. automatic shutdown when authorization expires or the source changes materially.

## Priority source families

### 1. Company identity, establishments, groups, and public records

**Primary sources**

- API Recherche d'entreprises;
- Sirene, subject to the approved direct-access mode;
- INPI / Registre national des entreprises, subject to approved fields and access;
- BODACC;
- GLEIF LEI and relationship data;
- European Business Register and national company registries where licensed or openly reusable;
- OpenCorporates or equivalent licensed company-data provider;
- official annual reports, registration documents, regulatory filings, and company publications.

**Required outputs**

- legal-unit and establishment identity;
- official identifiers and validation state;
- legal names, trading names, aliases, and prior names;
- status, activity, addresses, headquarters, and establishment relationships;
- direct and ultimate parent claims;
- source-specific claims and conflicts;
- non-diffusion and suppression constraints.

**Restrictions**

Do not collect beneficial-owner, shareholder, director, or personal-address information unless the exact dataset, field, purpose, and legal basis have been separately approved. Do not use name-only matching to merge organizations automatically.

### 2. Procurement, contracts, suppliers, integrators, customers, and renewals

**Primary sources**

- TED Search API;
- BOAMP / DILA Explore API;
- French DECP and official award datasets;
- PLACE and other official procurement portals through approved APIs, feeds, or bounded public metadata access;
- national and regional procurement portals;
- EU funding and grant transparency datasets;
- official award notices, contract notices, modifications, cancellations, and results;
- public framework agreements;
- official supplier, technology-partner, marketplace, and customer-reference directories;
- annual reports and regulatory filings that name material customers or suppliers;
- published case studies from vendors, integrators, MSSPs, SOC providers, and customers.

**Required outputs**

- buyer, beneficiary, contracting authority, awardee, consortium, and subcontractor;
- tender and lot identifiers;
- subject, taxonomy, technologies, services, and quantities;
- publication, deadline, award, start, end, renewal, and modification dates;
- amounts, currencies, durations, options, and framework limits;
- incumbent and provider hypotheses;
- evidence-backed renewal window;
- explicit distinction between confirmed contract, published relationship, case-study claim, and analyst inference.

### 3. Hiring, roles, teams, and project signals

**Primary sources**

- Greenhouse public Job Board API;
- Lever public Postings API;
- SmartRecruiters public Posting API;
- additional official ATS APIs such as Workday, Ashby, Teamtailor, Recruitee, iCIMS, Taleo, SuccessFactors, and company-specific career feeds after separate review;
- official career pages through sitemap, structured data, RSS, or bounded crawling when terms permit;
- public conference speaker biographies and professional event programs;
- official company team, governance, leadership, and contact pages.

**Required outputs**

- organization, location, team, role, seniority, and job family;
- cyber domain such as SOC, SIEM, detection engineering, incident response, GRC, IAM, cloud security, application security, or vulnerability management;
- technologies explicitly named in the posting;
- project, migration, deployment, managed-service, or transformation language;
- first seen, updated, withdrawn, and freshness state;
- evidence that a role is currently public.

Candidate forms, applicant data, resumes, screening questions, private emails, and write endpoints are excluded.

### 4. Search engines, dorks, document discovery, and web archives

**Candidate providers and tools**

- Brave Search API;
- Bing Web Search or another contractually approved search API;
- Google searches and dorks as analyst-generated links unless an approved API or written crawling authorization covers the use;
- Google Programmable Search only where an existing approved entitlement and its current terms permit it;
- Common Crawl indexes and datasets;
- Internet Archive Wayback Machine APIs and approved CDX access;
- Archive.today for manual review only unless explicit reuse and automation terms are validated;
- GDELT, Media Cloud, RSS, Atom, sitemaps, and official newsroom feeds;
- GitHub code search and official APIs;
- GitLab, package registries, documentation indexes, and public code-hosting APIs;
- academic, patent, standards, and publication search APIs.

**Dork families to maintain**

- official-domain documents and subdomains;
- public tenders, awards, contracts, statements of work, and framework agreements;
- SIEM, SOC, EDR, XDR, MDR, IAM, PAM, firewall, cloud, and security-product names;
- architecture, migration, deployment, outsourcing, managed service, renewal, and support terms;
- job titles and cyber-team terms;
- public incident, ransomware, breach, regulator, and notification terms;
- vendor case studies, partner directories, customer stories, and marketplace listings;
- annual reports, sustainability reports, investor presentations, and regulatory filings;
- conference slides, webinars, podcasts, and technical presentations.

Example analyst queries:

```text
site:example.com (SIEM OR SOC OR EDR OR XDR) filetype:pdf
"Example Company" (attributaire OR marché OR accord-cadre OR renouvellement)
"Example Company" (Splunk OR Sentinel OR Sekoia OR QRadar OR Elastic)
"Example Company" (ransomware OR cyberattack OR data breach OR regulator)
site:careers.example.com (SOC OR SIEM OR detection OR incident response)
```

Search results are discovery metadata. They are not evidence until the referenced source is retrieved through an approved path and preserved with provenance.

### 5. Corporate websites, documents, blogs, forums, and technical publications

**Approved collection patterns**

- official RSS or Atom feeds;
- official APIs;
- sitemaps and structured data;
- bounded public-page crawling after terms and robots review;
- manual review for ambiguous or copyrighted long-form content;
- short factual snippets and extracted claims with canonical URLs rather than wholesale content replication.

**Useful sources**

- company newsrooms and blogs;
- vendor, integrator, MSSP, and partner blogs;
- public engineering blogs;
- public documentation and support portals;
- standards bodies and industry associations;
- public webinars, podcasts, conference programs, and slide decks;
- public GitHub and GitLab organizations;
- Stack Exchange / Stack Overflow APIs for public organization-relevant technical discussion when the attribution is explicit and the use is approved;
- Reddit official API for approved public communities and organization-level signals;
- public Mastodon and Bluesky APIs where their terms and server policies permit the exact use;
- YouTube Data API for public channel, video, description, and transcript metadata where licensing permits.

A personal post or alias must not be treated as proof of an employer's technology. At most it can create a low-confidence review lead when the professional affiliation is self-declared, current, relevant, and corroborated.

### 6. Professional people, organization charts, and business contacts

**Preferred sources**

- official company leadership, team, governance, and contact pages;
- official press releases and appointment notices;
- annual reports and regulatory filings;
- conference and webinar speaker pages;
- public professional association directories;
- licensed B2B contact-data providers whose contract covers the intended use;
- LinkedIn official APIs or specifically authorized partner products for the exact approved fields and purpose;
- analyst-generated LinkedIn links for manual verification when automated access is not authorized.

**Permitted data**

- professional name;
- current organization and public professional role;
- department, seniority, and buying-committee role;
- public business email, role mailbox, switchboard, direct business number, or contact form where collection and reuse are permitted;
- source, collection date, confidence, legal basis, notice, objection, suppression, and retention state.

**Prohibited behavior**

- scraping LinkedIn profiles, posts, connections, search results, or messages without express permission;
- creating false accounts, impersonating people, or using deceptive personas;
- bypassing rate limits, authentication, CAPTCHA, MFA, or access controls;
- collecting private messages, connection graphs, private groups, personal emails, private phones, home addresses, family data, or sensitive traits;
- inferring a person's identity from a pseudonym or correlating aliases across platforms to de-anonymize them;
- collecting an individual's full posting or message history to profile interests, behavior, beliefs, vulnerabilities, or private life;
- treating unverified social activity as an employer fact.

### 7. Reddit, Discord, communities, and pseudonymous content

#### Reddit

Permitted only through the official API or another licensed route for approved public subreddits and fields. The principal use is organization-level and market-level signal discovery, for example:

- public discussion of a product migration or outage;
- recurring implementation problems;
- vendor sentiment aggregated across a community;
- public links to official documents or announcements;
- explicit public statements by verified organization accounts.

Do not build dossiers on individual Reddit users, link their pseudonyms to real identities, or infer their employer's technology from personal discussions without explicit self-attribution and independent corroboration.

#### Discord

Discord data may be processed only through a `consented_connector`, such as:

- a bot installed by the server owner or administrator for a documented purpose;
- an authorized export supplied by the server owner or customer;
- an official API workflow whose permissions and data handling have been reviewed.

No self-bots, automated user accounts, covert joining, invite harvesting, member scraping, private-message collection, or bulk history extraction are permitted. Public visibility does not authorize mass scraping or commercial profiling.

The allowed output should normally be aggregated community or organization-level trends. Individual-level attribution requires explicit professional relevance, a valid basis, minimization, and human review.

### 8. Domains, DNS, certificates, passive internet exposure, and technology detection

**Primary sources and tools**

- RDAP and official registry services;
- DNS and passive-DNS providers such as SecurityTrails or an equivalent licensed service;
- Certificate Transparency through crt.sh or an approved CT provider;
- Censys official APIs;
- Shodan official APIs;
- urlscan.io official API;
- VirusTotal official APIs within the licensed scope;
- GreyNoise, AbuseIPDB, Spamhaus, and other approved reputation feeds;
- official ASN and BGP datasets;
- Wappalyzer, BuiltWith, HTTP Archive, or equivalent licensed technography sources;
- passive metadata from public code, package manifests, SBOMs, headers, certificates, DNS, and vendor case studies;
- Amass, theHarvester, SpiderFoot, Recon-ng, Maltego, and similar frameworks only through reviewed modules and approved upstream sources.

**Restrictions**

- passive collection only for prospects;
- no port scanning, vulnerability scanning, authentication tests, credential validation, exploitation, or intrusive probing;
- no direct requests to candidate assets beyond separately approved ordinary public-page retrieval;
- observed technology and observed version must be timestamped and may be stale;
- a hostname or certificate relationship is a claim until organization ownership is resolved.

MAC-address intelligence is generally irrelevant to external B2B organization research and must not be collected from individuals.

### 9. Technologies, products, versions, and stack inference

The platform must combine independent evidence instead of relying on a single detector.

**Evidence sources**

- official contracts and award notices;
- official customer stories and partner directories;
- current job postings;
- official engineering repositories and package manifests;
- public architecture presentations and documentation;
- externally visible headers, certificates, DNS, scripts, and service metadata;
- licensed technography providers;
- current support or migration tenders;
- public vendor marketplaces and integration directories.

**Fact and hypothesis states**

- `confirmed_current`;
- `confirmed_historical`;
- `strongly_corroborated`;
- `probable`;
- `weak_lead`;
- `conflicted`;
- `unknown`.

An exact current contract or official case study may support a high-confidence relationship. A single old job posting cannot prove current production use. A personal forum message cannot prove employer use.

### 10. Vulnerabilities, advisories, exploitation, and product risk

**Primary sources**

- CVE.org;
- NVD API;
- CISA KEV;
- FIRST EPSS;
- OSV;
- GitHub Security Advisories;
- official vendor PSIRTs and advisory feeds;
- CERT-FR, ENISA, national CERTs, and sector advisories;
- approved threat-intelligence feeds.

**Required outputs**

- canonical vulnerability identity;
- affected products, versions, configurations, and ecosystems;
- fixed versions and mitigations;
- CVSS, CWE, EPSS, KEV, exploit maturity, and vendor status;
- publication, modification, and ingestion timestamps;
- product-to-organization applicability confidence.

The platform must not state that an organization is vulnerable unless an applicable product and version are supported by sufficiently precise, fresh evidence. Otherwise the result is a review hypothesis.

### 11. Incidents, breaches, ransomware claims, and regulatory reporting

**Preferred sources**

- organization statements and status pages;
- regulator and data-protection authority notices;
- stock-exchange and financial filings;
- court and public-authority records;
- national CERT and law-enforcement publications;
- reputable licensed news sources;
- approved ransomware-claim aggregators that expose metadata only;
- official post-incident reports and public notifications.

**Claim states**

- `actor_claim`;
- `public_report`;
- `official_confirmation`;
- `regulatory_notice`;
- `analyst_inference`;
- `retracted_or_disputed`;
- `false_attribution`.

Do not access victim portals, interact with threat actors, download leaked documents, ingest stolen credentials, retain private victim communications, or store extorted datasets.

Have I Been Pwned domain-level searches may be used only for a domain controlled by the customer or organization that has authorized the assessment and completed the provider's domain-verification process.

### 12. Images, videos, documents, metadata, translation, and archives

**Candidate tools and services**

- official document repositories and search APIs;
- ExifTool, Apache Tika, pdf parsers, office-document parsers, and file-type validators in an isolated processing environment;
- OCR and translation services covered by an approved data-processing agreement;
- reverse-image search as an analyst workflow where automated terms are unclear;
- Wayback Machine, Common Crawl, and approved archive providers;
- URL and file reputation services such as urlscan.io and VirusTotal within licence limits.

**Outputs**

- document title, publisher, date, language, canonical URL, hash, and extraction quality;
- organization, product, contract, person-role, and incident mentions;
- redacted factual snippets and page references;
- image or document metadata relevant to provenance.

Do not persist unnecessary personal metadata, raw copyrighted corpora, or documents containing exposed confidential information. Suspicious documents are quarantined and never opened in the collection worker.

### 13. Code, developer ecosystems, and public technical activity

**Sources**

- GitHub official API, code search, releases, advisories, organization repositories, and public events;
- GitLab official API;
- public package registries such as PyPI, npm, Maven Central, NuGet, crates.io, RubyGems, and container registries;
- official SBOM and release feeds;
- public issue trackers and technical documentation;
- Stack Exchange APIs;
- official vendor community portals.

**Permitted uses**

- identify technologies published by an official organization account;
- discover open-source projects, release cadence, dependency families, and security advisories;
- locate official documentation and implementation evidence;
- create organization-level technology hypotheses.

Do not map developers' personal accounts to employers by hidden identifiers, historical emails, SSH keys, or username correlation unless the relationship is explicitly public, professionally relevant, and required for an authorized investigation. Private repositories, tokens, secrets, accidental exposures, and commit data outside the approved purpose are excluded.

### 14. News, market, regulatory, and industry change signals

**Sources**

- official company newsrooms and RSS;
- regulator, CERT, court, procurement, and public-authority feeds;
- licensed press and news APIs;
- GDELT and other approved event-data providers;
- industry associations, standards bodies, and analyst publications;
- mergers, acquisitions, funding, leadership, restructuring, new-site, data-center, cloud, and digital-transformation announcements.

Each extracted statement must preserve publication date, event date, source type, claim type, organization resolution, and confirmation status.

## BrixHub requirement

`https://brixhub.cc/` is a mandatory candidate for source assessment because the product owner has identified it as potentially valuable.

It remains `quarantined` until the following are verified and documented:

1. legal owner and operator;
2. official terms of service and privacy notice;
3. data provenance and whether the provider is authorized to redistribute it;
4. exact available datasets, fields, countries, and update cadence;
5. account, payment, API, browser, export, and download methods;
6. permission for automated collection and commercial reuse;
7. robots and technical access rules;
8. rate limits and quotas;
9. retention, correction, objection, deletion, and audit requirements;
10. whether personal, breach, credential, victim, private-message, or restricted data is present;
11. a reviewed sample obtained through a legitimate authorized workflow;
12. security review of downloads and provider connectivity.

Before approval, no account creation, login automation, payment, crawl, scrape, download, import, or live connectivity test is permitted. If approved, the adapter must use secret references, exact host/path allowlists, provider-specific schemas, bounded pagination, no raw secret storage, and a documented retention policy.

## LinkedIn requirement

LinkedIn is a high-value professional source but is not a general-purpose crawl target.

Allowed integration paths are:

- official LinkedIn API scopes actually granted to the application;
- a licensed LinkedIn product or authorized partner workflow whose contract covers the exact use;
- written crawling authorization covering exact hosts, paths, fields, rate, storage, and purpose;
- analyst-generated links and manual verification without automated extraction.

Until one of these paths is approved, LinkedIn remains non-executable. The system must never use a normal user account, browser session, cookie, self-created persona, extension, proxy pool, or anti-bot bypass to scrape profiles, posts, connections, groups, search results, or messages.

## Confidence and corroboration

Every material output must expose its evidence and confidence components. The scoring model should consider:

- source authority;
- directness of the statement;
- entity-match quality;
- temporal freshness;
- field specificity;
- independent corroboration;
- contradictions;
- source incentives and possible bias;
- whether the evidence is current or historical.

Suggested evidence hierarchy:

| Evidence | Typical maximum confidence before conflict adjustment |
|---|---:|
| Official current contract, filing, regulator notice, or organization statement | 0.95 |
| Official vendor/customer case study or current authoritative registry | 0.90 |
| Current tender or award naming an exact product/provider | 0.90 |
| Current official job posting naming an exact technology | 0.75 |
| Official organization repository or architecture publication | 0.80 |
| Passive technology detection with current timestamp | 0.65 |
| Reputable licensed news report | 0.70 |
| Public forum or social post with verified professional attribution | 0.45 |
| Unverified pseudonymous statement | 0.20 and review-only |

Scores are not facts. They must be calibrated against labelled outcomes and shown with the underlying reasons.

## Source-catalog record

Every candidate source or tool must record at least:

```yaml
id: string
name: string
canonical_url: string
owner: string | null
osint_framework_category: string | null
project_use_cases: []
collection_mode: official_api | open_data | licensed_api | bounded_web | manual_review | authorized_browser | consented_connector | quarantined | blocked
status: proposed | reviewing | approved | disabled | quarantined | blocked | retired
terms_url: string | null
privacy_url: string | null
licence: string | null
api_documentation_url: string | null
authentication_modes: []
approved_hosts: []
approved_path_prefixes: []
allowed_data_categories: []
prohibited_data_categories: []
automated_collection_allowed: boolean
raw_storage_allowed: boolean
human_review_required: boolean
rate_limit_per_minute: integer | null
concurrency_limit: integer | null
retention_days: integer | null
attribution_required: boolean
legal_reviewed_at: datetime | null
privacy_reviewed_at: datetime | null
security_reviewed_at: datetime | null
authorization_expires_at: datetime | null
last_health_check_at: datetime | null
notes: string
```

## Adapter acceptance tests

An adapter is not complete until tests prove:

- policy denial occurs before network access;
- only approved hosts and paths are reachable;
- redirects cannot escape the allowlist;
- secrets are referenced and redacted;
- rate, concurrency, size, MIME, date-window, and pagination limits are enforced;
- retries and circuits do not duplicate observations;
- checkpoints advance only after transactional success;
- provider payloads cannot leak into canonical domain models;
- PII minimization and prohibited-field rejection work;
- timestamps and hashes are deterministic;
- replays are idempotent;
- removal or correction updates projections;
- authorization expiry disables collection;
- live network is absent from unit tests;
- integration fixtures are synthetic, minimized, licensed, or provider-published.

## Implementation priorities

### Priority A — authoritative structured sources

- organization registries;
- procurement and awards;
- official ATS APIs;
- vulnerability and advisory feeds;
- official corporate, regulatory, and CERT feeds.

### Priority B — passive organization and technology evidence

- search APIs and dork workflow;
- corporate sites, sitemaps, RSS, and documents;
- RDAP, DNS, CT, Censys, Shodan, SecurityTrails, urlscan, Wappalyzer, and BuiltWith;
- GitHub, GitLab, package registries, and official engineering publications.

### Priority C — people, providers, and market relationships

- licensed B2B professional data;
- organization charts and buying committees;
- partner directories, case studies, incumbent-provider and renewal analysis;
- LinkedIn official or explicitly authorized integration.

### Priority D — communities and unstructured intelligence

- Reddit official API;
- consented Discord connectors;
- public forums, blogs, podcasts, videos, transcripts, and conference material;
- aggregation and corroboration models that prevent individual surveillance.

### Priority E — quarantined and high-risk providers

- BrixHub assessment;
- browser-only sources;
- ransomware and dark-web metadata providers;
- any source containing breach, identity, or personal data.

These sources require the strongest legal, privacy, security, provenance, and human-review gates before implementation.

## Non-negotiable exclusions

The platform must not:

- create deceptive accounts or personas;
- covertly join private or restricted communities;
- scrape LinkedIn or Discord without express authorization;
- collect private messages or full personal message histories;
- de-anonymize pseudonyms or correlate aliases to expose real identities;
- profile individuals' beliefs, health, politics, religion, sexuality, private interests, or vulnerabilities;
- buy, download, search, or retain stolen credentials, infostealer logs, victim files, extorted data, or private datasets;
- bypass authentication, paywalls, CAPTCHA, MFA, rate limits, robots enforcement, or access controls;
- actively scan, exploit, authenticate to, or test prospect systems;
- autonomously contact, message, follow, connect with, or engage prospects;
- present a probabilistic lead as a confirmed fact.

The commercial value of a source never overrides source authorization, privacy, security, data minimization, evidence quality, or human accountability.
