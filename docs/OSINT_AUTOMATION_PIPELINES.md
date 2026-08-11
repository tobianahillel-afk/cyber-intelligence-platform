# OSINT Automation Pipelines

## Status

This document is normative for future automated discovery, crawling, browser, SERP, document, OCR and image-research implementation.

It complements `OSINT_FULL_IMPLEMENTATION_MANDATE.md` and `SOCIAL_COMMUNITY_ACQUISITION_REQUIREMENTS.md`.

## Objective

Cyber Intelligence Platform must be able to take a resolved organization, domain, company identifier, technology, professional role, incident, contract or other research seed and automatically execute the maximum useful approved discovery workflow through provider-specific adapters and governed browser/crawler workers.

The target is not a collection of analyst links. The target is a reproducible acquisition pipeline that can discover, retrieve, parse, normalize, version and prove real evidence through live provider tests.

## Canonical pipeline

```text
research seed
-> query/crawl plan
-> provider/source policy resolution
-> SERP/search providers
-> URL/record discovery
-> governed fetch or browser navigation
-> recursive crawl / provider pagination
-> document/media acquisition
-> HTML/DOM/JSON/JS/metadata extraction
-> OCR / media analysis where required
-> normalization and provenance
-> entity/technology/provider candidates
-> evidence store
-> signal/hypothesis pipeline
```

Every stage must be replay-safe and auditable.

## SERP pipeline

A normalized SERP pipeline is mandatory.

The system must support several independent providers so search coverage does not depend on one vendor.

Required provider families include:

- Brave Search;
- Mojeek;
- Google official programmable/search products where a deployment entitlement exists;
- Bing or a current equivalent approved web-search API;
- Common Crawl index;
- Internet Archive/Wayback discovery;
- GDELT current supported search/news stack;
- GitHub/GitLab search;
- publication/patent/standards search;
- other provider-specific search APIs selected by source activation.

### Normalized search result

Each result should capture at least:

```text
provider
query_id
query_text_or_template_id
rank
result_url
canonical_url
title
snippet_or_description
provider_record_id
published_at_if_known
observed_at
collected_at
result_type
source_scope
```

Search-result metadata is discovery lineage, not a confirmed company fact.

### Dork execution

The query library must support versioned Google-style dorks and equivalent provider syntax for:

- `site:` company-domain research;
- `filetype:` documents;
- `intitle:` and `inurl:` patterns;
- contracts, tenders and awards;
- technologies and vendors;
- architecture and migration documents;
- SOC/SIEM/MDR/EDR/XDR/SOAR;
- IAM/PAM/Zero Trust;
- cloud/Kubernetes;
- AppSec/DevSecOps/SAST/DAST/SCA/SBOM;
- pentest/red-team/purple-team;
- GRC/NIS2/DORA/ISO 27001/SOC 2/PCI DSS/HDS;
- incidents/ransomware/breach/regulator;
- hiring and security-team growth;
- partner/customer/case-study evidence;
- presentations, annual reports and technical PDFs;
- developer/code/package evidence.

Where an official API is available and authorized, execution should be automated. Where a provider allows browser automation for the deployment, a provider-specific browser adapter may execute the search through the isolated browser runtime. A provider challenge must use the legitimate checkpoint workflow rather than evasion.

## Automatic company crawl pipeline

After canonical domain resolution and deployment approval, CIP must be able to create a crawl target automatically and start a first crawl without a developer manually editing YAML.

Required stages:

1. resolve organization/domain evidence;
2. create governed target;
3. fetch/evaluate robots policy;
4. discover sitemap/sitemap indexes;
5. discover feeds/security.txt;
6. seed homepage and allowed entry pages;
7. extract same-origin links;
8. recursively traverse useful pages within configured scope;
9. route JavaScript-heavy pages to the browser worker;
10. route permitted documents/media to quarantine;
11. persist canonical resources/versions/provenance;
12. schedule incremental recrawl;
13. expire/tombstone removed content;
14. emit source-health and crawl metrics.

The crawler must support configurable depth, page, byte, time, concurrency, host and freshness budgets. These are engineering safety controls, not a reason to omit recursive crawling.

## Browser-rendered acquisition

A generalized Playwright/Chromium runtime is mandatory.

It must support:

- disposable browser workers;
- isolated context per provider/account;
- JavaScript execution required to render legitimate pages;
- navigation and form interaction;
- authorized login workflows;
- OAuth/SSO;
- human-assisted MFA/CAPTCHA checkpoints for legitimate accounts;
- screenshots;
- DOM snapshots where permitted;
- network/request metadata;
- controlled file downloads;
- host/path allowlists;
- download quarantine;
- resource and time budgets;
- crash cleanup and resumable jobs.

## HTML, CSS, JSON and JavaScript extraction

The web parser must extract useful structured evidence rather than treating every page as plain text.

Required inputs include:

- HTML DOM;
- semantic HTML metadata;
- JSON-LD;
- OpenGraph/Twitter-style public metadata;
- public embedded JSON application state;
- public API/JSON responses used by the rendered application when collection of those responses is authorized;
- script-exposed structured data that is part of the public/authorized page state;
- CSS/resource references when useful for product/vendor/technology attribution;
- response headers;
- canonical links;
- alternate-language links;
- forms and public endpoint references;
- document/media links.

Extraction must not execute arbitrary downloaded code outside the isolated browser/parser environment.

## Technology-identification pipeline

The system must combine multiple evidence classes for technology discovery:

- page content and metadata;
- public JavaScript/library fingerprints;
- HTTP headers;
- certificates/DNS/passive provider metadata;
- Wappalyzer/BuiltWith/HTTP Archive or equivalent providers;
- public source code/package metadata;
- public job descriptions;
- contracts and procurement documents;
- public/consented community messages;
- vendor case studies and partner directories;
- technical PDFs/presentations;
- public incident/advisory references.

Technology observations must retain source, confidence, first/last seen and evidence class. A mention remains distinct from verified deployment.

## Document and OCR pipeline

The document pipeline must support:

- PDF;
- DOCX/XLSX/PPTX and other approved Office formats;
- HTML-to-document exports;
- plain text;
- images;
- archive containers where allowed;
- scanned documents requiring OCR.

Required processing components include:

- MIME/type detection;
- file hashing;
- malware/reputation screening;
- parser sandbox;
- Apache Tika or equivalent extraction where useful;
- pypdf/type-specific parsers;
- ExifTool metadata extraction in isolation;
- OCR engine(s);
- language detection;
- translation pipeline;
- table/text extraction;
- bounded image extraction where needed;
- metadata normalization;
- provenance back to the source URL/provider record.

## OCR

OCR is mandatory for scanned PDFs, screenshots and images that contain potentially useful public/authorized professional or technical text.

The OCR path must record:

- engine/version;
- page/image identifier;
- detected language;
- confidence;
- bounding boxes when available;
- normalized extracted text;
- source artifact hash;
- collection/provenance timestamps.

OCR output remains derived evidence and must link back to the original artifact.

## Reverse-image and visual-research pipeline

An automated reverse-image/visual research pipeline is mandatory for organization and technical research where images materially contribute evidence.

The pipeline should support provider-authorized reverse-image/search APIs and local similarity methods, including:

- perceptual hashing;
- exact hash matching;
- image metadata;
- OCR-derived text queries;
- logo/product/vendor detection;
- screenshot similarity;
- provider-specific reverse-image APIs where licensing permits automation;
- analyst review of ambiguous matches.

Potential uses include:

- finding the original source of a public screenshot or diagram;
- identifying public vendor/product logos in presentations;
- locating duplicated public marketing/architecture images;
- correlating a public technical screenshot with vendor documentation.

Visual matching does not by itself prove organization identity or product deployment.

## Local OSINT-tool orchestration

The automation layer must expose provider/module-aware adapters for:

- Sherlock;
- OWASP Amass passive modules;
- theHarvester;
- SpiderFoot;
- Recon-ng;
- Maltego transforms;
- other useful OSINT Framework tools selected by activation review.

Each upstream provider/module must retain its own authorization, secret and quota state.

## Passive infrastructure pipeline

The pipeline must operationalize and live-test useful passive providers including:

- DNS/RDAP;
- certificate transparency;
- Shodan indexed/passive APIs;
- Censys;
- SecurityTrails;
- urlscan search/existing-scan metadata;
- VirusTotal metadata;
- GreyNoise;
- AbuseIPDB;
- Spamhaus;
- ASN/BGP data;
- Wappalyzer/BuiltWith/HTTP Archive;
- licensed passive DNS/exposure/cloud providers.

Active scan/exploitation capability remains a separate explicitly authorized security-testing workflow.

## Incident, CTI, ransomware and phishing pipeline

The platform must implement provider-specific acquisition for:

- company/regulator/CERT incident statements;
- SEC cyber disclosures;
- public authority/law-enforcement publications;
- CISA/NVD/EPSS/GHSA/CVE/OSV/CIRCL vulnerability intelligence;
- PhishTank or equivalent phishing metadata;
- STIX/TAXII providers;
- ransomware-claim metadata providers;
- malware/IOC metadata providers;
- malicious-infrastructure feeds;
- current GDELT/news sources.

The evidence model must preserve claim type, independence, chronology, corrections and retractions.

## Live company validation

Automatic crawling and research are not complete until they have been exercised end-to-end against real approved targets.

A live validation must demonstrate, as applicable:

- company/domain target generation;
- real robots/sitemap/feed handling;
- recursive page discovery;
- real browser-rendered page retrieval;
- structured HTML/JSON extraction;
- document download/quarantine;
- OCR on a real approved artifact;
- technology/vendor extraction;
- provenance and versioning;
- search/SERP discovery leading to evidence retrieval;
- non-empty provider data;
- checkpoint/replay behavior;
- no secret leakage.

## Planning note

This document defines required capability scope, not final implementation-lot sizing. The next roadmap review must decompose these pipelines into realistically sized, independently testable lots/SA increments with exact exit gates.
