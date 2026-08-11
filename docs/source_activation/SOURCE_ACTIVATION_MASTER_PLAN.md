# Source Activation Master Plan

## Purpose

The Source Activation programme closes the gap between a source being named or modelled and a source being genuinely usable by Cyber Intelligence Platform.

A source is **not integrated** merely because it appears in documentation, a Source Portfolio bundle, a provider schema, a mapper, an approval dossier, or a deterministic test. A useful provider reaches completion only through a real runtime path and controlled production-adapter validation where legitimate provider access exists.

This programme is a delivery axis alongside product Lots 00–32. Historical SA-00 through SA-14 closeout documents remain truthful records of what was implemented at their merge time. Future work is governed by [`../OSINT_FULL_IMPLEMENTATION_MANDATE.md`](../OSINT_FULL_IMPLEMENTATION_MANDATE.md) and [`SA_15_20_FULL_ACTIVATION_ROADMAP.md`](SA_15_20_FULL_ACTIVATION_ROADMAP.md).

## Canonical activation lifecycle

```text
catalogued
  -> reviewed
  -> mapped
  -> adapter_present
  -> deployment authorization / entitlement ready
  -> executable
  -> scheduled or explicitly invokable
  -> controlled live tested
  -> observable/supportable
  -> fully integrated
```

The lifecycle is intentionally stricter than Source Portfolio `status`.

## Mandatory completion principle

Every useful source or capability discovered through the product roadmap, OSINT Framework, a provider catalogue, analyst research, or a new business requirement must receive an implementation owner and an activation path.

For a useful source, the following are **temporary prerequisite conditions**, not acceptable permanent completion states:

- API key unavailable;
- paid/enterprise plan not yet purchased;
- written provider permission not yet obtained;
- deployment target registry empty;
- provider account not yet provisioned;
- customer/admin connector not yet installed;
- browser account or service account not yet configured;
- stable current API contract not yet published;
- legal/commercial review not yet complete.

Each such condition must record the exact dependency, owner, target SA and acceptance/live test. The source remains unfinished until the prerequisite is resolved, the capability is replaced by an equivalent canonical source, or the product owner explicitly decides the source is no longer useful.

## Dispositions

The machine-readable model may still contain historical or transitional disposition values such as `active`, `planned`, `manual`, `blocked`, `replaced`, `duplicate`, and `not_relevant`.

For future planning, interpret them as follows:

- `active`: implementation is intended and must progress to full integration;
- `planned`: implementation work remains and must have a target SA;
- `manual`: temporary fallback while an executable legitimate path is pursued, unless the product owner explicitly chooses manual-only operation;
- `blocked`: temporary prerequisite state for a useful source, never a convenient terminal closeout;
- `replaced`: equivalent canonical capability exists and must itself be fully integrated;
- `duplicate`: redundant with a canonical fully owned capability;
- `not_relevant`: reserved for an explicit product-owner exclusion, not for lack of credentials, licence work or implementation effort.

## Authorization boundary

Source Activation planning is aggressive about implementation but does not silently grant access authority.

Network execution still requires the applicable Source Governance, Provider Onboarding, Source Portfolio, tenant/deployment authorization, quota/cost controls and runtime registration.

The programme must implement legitimate authenticated and browser workflows when needed, including provider-approved service/test accounts and analyst-assisted MFA. It must not require defeating security controls.

Out of scope for ordinary OSINT acquisition unless a separate explicit security-testing engagement authorizes them:

- CAPTCHA or MFA bypass;
- authentication/access-control bypass;
- stolen or replayed third-party sessions;
- credential guessing/validation;
- exploit-based data acquisition;
- deceptive account farms;
- private victim files, stolen credentials or private communications.

## Truth invariants

```text
catalogued != reviewed
reviewed != deployment-authorized
mapped != adapter present
adapter present != executable
executable != scheduled/invokable
scheduled != live-tested
unit-test success != provider live proof
OSINT Framework entry != executable adapter
search result != factual evidence
missing credential != completed source
```

The `source_activation` bounded context remains separate from HTTP clients, browser runtimes, provider adapters, collection orchestration, opportunities and outreach.

## Historical programme — SA-00 through SA-14

SA-00 through SA-14 established the activation truth model and progressively delivered vulnerability, web/search/archive, infrastructure, CTI, local-tool governance, corporate context, conditional providers, browser design, completeness classification, company identity, procurement/funding, ATS and search/archive provider expansions.

These units remain immutable historical records. Their old `blocked`, `manual`, or non-live statuses describe the state at that point in time; they are not a declaration that the corresponding useful source should remain unfinished forever.

### SA-00 — activation truth and OSINT Framework catalogue

Delivered:

- machine-readable activation lifecycle;
- reconciliation invariants;
- OSINT Framework catalogue normalization;
- coverage matrix;
- architecture and deterministic tests.

Future requirement: every useful imported candidate must be assigned to an executable provider-specific activation path or explicitly excluded by product decision.

### SA-01 — vulnerability providers

Scope:

- NVD;
- FIRST EPSS;
- GitHub Global Security Advisories;
- CVE Services;
- OSV;
- CIRCL Vulnerability-Lookup.

Future requirement: all remaining non-live executable providers receive controlled production-adapter live proof under SA-18.

### SA-02 — web, search and archives

Delivered foundational public-web, Brave Search and Internet Archive paths.

Future requirement: SA-15 and SA-16 complete real search-provider live coverage, automatic company crawl, recursive crawling, generalized browser rendering and legitimate authenticated workflows.

### SA-03 — domain/infrastructure

Future requirement: SA-17 promotes open and commercial passive infrastructure providers through real entitlements, adapters and live validation.

### SA-04 — CTI/incidents

Future requirement: SA-18 activates concrete provider-specific incident, ransomware, phishing, CERT and threat feeds.

### SA-05 — local OSINT tools

Future requirement: SA-17 implements useful framework modules rather than treating mixed frameworks as permanently unavailable wholesale.

### SA-06 — corporate/public business context

Future requirement: automatic company crawling and provider-specific corporate/news sources feed the canonical evidence pipeline.

### SA-07 — licensed/premium/social providers

Future requirement: commercial/provider prerequisites are owned implementation work. SA-17 through SA-19 cover passive providers, CTI and professional/community integrations.

### SA-08 — BrixHub

BrixHub remains a mandatory access-path/provider review candidate. If it is useful and a legitimate access path is available, provider onboarding, exact schemas, adapter, runtime and live validation must be implemented. Lack of current information is a prerequisite to resolve, not a green completion state.

### SA-09 — isolated browser

The browser capability is no longer intended to remain indefinitely deferred. SA-16 owns generalized headless-browser and authenticated-web implementation.

### SA-10 — classification audit

SA-10 completed historical classification truth. It did **not** establish full live integration. SA-20 supersedes it as the future broad source-completeness gate.

### SA-11 — company identity expansion

BRREG earned controlled live proof. Remaining useful identity providers and target-dependent adapters must be operationalized before SA-20 completion.

### SA-12 — procurement and public funding

PLACE, ADEME and CORDIS earned controlled live proof. Existing procurement adapters without live evidence must be live-validated under SA-20.

### SA-13 — ATS expansion

Ashby and Recruitee earned live proof. Teamtailor and other useful ATS providers remain future activation work.

### SA-14 — search/archive expansion

Common Crawl, GitHub Code Search, Crossref and W3C earned controlled live proof. Mojeek, PatentsView and GDELT dependencies were handed forward to SA-15.

## New mandatory waves

### SA-15 — Search, news and deferred-provider live completion

Owns:

- Mojeek live promotion;
- PatentsView live promotion;
- current supported GDELT integration;
- Brave live proof;
- Internet Archive live proof;
- one additional independent search provider such as Bing;
- official Google API path where entitlement permits, with analyst dork links retained.

### SA-16 — Automatic company web crawling and browser runtime

Owns:

- deployment-governed automatic crawl-target generation from resolved company domains;
- recursive crawling inside configured scope;
- sitemap/feed/link discovery;
- document acquisition;
- JavaScript rendering;
- generalized Playwright/Chromium workers;
- legitimate authenticated login workflows;
- OAuth/SSO where approved;
- analyst-assisted MFA checkpoints;
- real end-to-end live crawl proofs.

Recursive crawling is a required capability, with budgets and authorization scope as engineering controls.

### SA-17 — Passive infrastructure, technography and local OSINT tools

Owns activation and live validation for:

- DNS/CT/RDAP providers;
- Shodan passive/indexed APIs;
- Censys;
- SecurityTrails;
- urlscan search;
- VirusTotal metadata;
- GreyNoise;
- AbuseIPDB;
- Spamhaus;
- Wappalyzer/BuiltWith/HTTP Archive or equivalents;
- licensed passive providers;
- Sherlock, Amass passive modules, theHarvester, SpiderFoot, Recon-ng and Maltego through module/provider-specific controls.

### SA-18 — Vulnerability, incident, CTI, ransomware and phishing activation

Owns:

- live proof for existing vulnerability adapters;
- concrete CERT/vendor advisory providers;
- SEC/regulator/company incident paths;
- PhishTank;
- licensed STIX/TAXII;
- ransomware/phishing/malware/IOC metadata providers.

### SA-19 — Professional and community activation

Owns legitimate executable paths for:

- LinkedIn official/partner/written-authorized access;
- Reddit official/licensed API;
- Discord administrator-installed connector/authorized export;
- Stack Exchange;
- Mastodon;
- Bluesky;
- YouTube;
- conference/professional directories;
- licensed B2B contact providers.

### SA-20 — Documents, developer ecosystems and final live-completeness gate

Owns:

- document/media extraction expansion;
- ExifTool/Tika/OCR/translation where justified;
- GitHub/GitLab/package-provider live proof;
- NuGet/crates.io/RubyGems/container/SBOM/release ecosystems;
- residual identity/procurement/ATS live proof;
- final machine-derived unresolved-prerequisite inventory.

## OSINT Framework synchronization contract

OSINT Framework remains a discovery taxonomy, but useful candidates may no longer disappear into a generic catalogue-only state.

For each useful candidate, synchronization must eventually produce:

- canonical provider identity;
- capability decomposition;
- implementation owner;
- access/onboarding prerequisites;
- target SA;
- adapter/runtime design;
- controlled live-test plan.

Mixed active/passive tools are decomposed at module/provider level so legitimate useful modules can proceed independently.

## Testing and validation

Each SA must satisfy repository development standards:

1. Ruff;
2. strict Mypy;
3. architecture/release tests;
4. reversible migrations when persistence changes;
5. complete backend regression suite with branch instrumentation and >=90% aggregate coverage;
6. frontend audit/typecheck/build when applicable;
7. provider adapter contract tests and deterministic fixtures;
8. no live-network unit tests;
9. controlled live validation through production adapters after legitimate authorization/onboarding;
10. exact final SHA CI after all live-state/documentation changes;
11. no unresolved review blocker before merge.

## New definition of source completeness

Broad source completeness is no longer satisfied by classification alone.

At SA-20, each useful source must be either:

```text
fully integrated
replaced by a fully integrated canonical source
duplicate of a fully integrated canonical source
explicitly excluded by product-owner decision
```

A source that still needs a key, contract, account, deployment target, provider permission, stable API, browser workflow or live test is **unfinished work** and must remain visible in the prerequisite backlog.

The project must never label deterministic CI, a mock transport or a skipped workflow as real provider validation.