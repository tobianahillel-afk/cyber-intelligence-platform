# Project Delivery Plan

## Purpose

This document is the authoritative production roadmap for Cyber Intelligence Platform. It divides delivery into continuous lots from foundation to controlled production scale. A lot is not complete because code exists; it is complete only when its exit gate passes on one final commit and the evidence is recorded in the pull request.

## Status vocabulary

- `IMPLEMENTED_VALIDATED`: merged implementation validated by the complete required CI.
- `IN_PROGRESS`: implementation exists on an active branch or pull request but has not passed its final gate.
- `PLANNED_LOCKED`: scope and exit criteria are defined; implementation has not started.
- `BLOCKED`: an external authorization, product, legal, or technical dependency prevents execution.
- `DEFERRED`: intentionally postponed because a simpler or safer mechanism has priority.

## Delivery rules

- Lot numbers are continuous and never reused.
- A lot has one primary business outcome.
- New source access requires a reviewed source-policy record before implementation.
- Public or licensed data is minimized; private, leaked, credential, or victim-file content is excluded.
- Each lot updates architecture, tests, operational documentation, and rollback behavior together.
- A later documentation commit invalidates an earlier validation run.
- The next lot may be designed while the current lot is validating, but code starts from the final merged `main` commit.

## Status overview

| Lot | Outcome | Status |
| ---: | --- | --- |
| 00 | Product, legal, and source-governance foundation | `IMPLEMENTED_VALIDATED` |
| 01 | Modular core, persistence, provenance, and retention | `IMPLEMENTED_VALIDATED` |
| 02 | Durable scheduler, worker, checkpoints, and recovery | `IMPLEMENTED_VALIDATED` |
| 03 | Evidence-backed opportunity engine and analyst Inbox | `IMPLEMENTED_VALIDATED` |
| 04 | TED European procurement signals | `IMPLEMENTED_VALIDATED` |
| 05 | BOAMP French procurement and executable architecture gates | `IMPLEMENTED_VALIDATED` |
| 06 | Greenhouse public cyber hiring signals | `IN_PROGRESS` |
| 07 | Multi-ATS hiring-source expansion | `PLANNED_LOCKED` |
| 08 | French and European organization identity foundation | `PLANNED_LOCKED` |
| 09 | Public-procurement expansion and buyer history | `PLANNED_LOCKED` |
| 10 | Vulnerability intelligence enrichment | `PLANNED_LOCKED` |
| 11 | Vendor advisories and product-to-organization matching | `PLANNED_LOCKED` |
| 12 | Incident and ransomware claim evidence | `PLANNED_LOCKED` |
| 13 | News, regulatory, and corporate-disclosure signals | `PLANNED_LOCKED` |
| 14 | Passive Internet-exposure observations | `PLANNED_LOCKED` |
| 15 | Technographics and technology-confidence model | `PLANNED_LOCKED` |
| 16 | Entity resolution and corporate graph | `PLANNED_LOCKED` |
| 17 | Professional-role enrichment and compliance controls | `PLANNED_LOCKED` |
| 18 | Analyst research and safe search-query workflows | `PLANNED_LOCKED` |
| 19 | Advanced scoring, calibration, and explainability | `PLANNED_LOCKED` |
| 20 | CRM synchronization and commercial workflow | `PLANNED_LOCKED` |
| 21 | Full analyst workspace and operational UX | `PLANNED_LOCKED` |
| 22 | Data quality, reconciliation, and lineage controls | `PLANNED_LOCKED` |
| 23 | Isolated browser and download-quarantine runtime | `DEFERRED` |
| 24 | Supply-chain, release provenance, and repository protection | `PLANNED_LOCKED` |
| 25 | Observability, performance, resilience, and recovery | `PLANNED_LOCKED` |
| 26 | Controlled pilot, production gate, and premium scale | `PLANNED_LOCKED` |

## Lot 00 — Product, legal, and source-governance foundation

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Define what the platform may collect, why it may collect it, how source access is authorized, and which uses remain prohibited.

**Dependencies:** None.

**Deliverables:**

- product charter and human-operated commercial-intelligence scope;
- explicit `enabled`, `conditional`, `quarantined`, and prohibited source states;
- approved purpose, host, path, automation, quota, and raw-storage controls;
- data-category allowlists and denylists;
- source registry with legal, licensing, attribution, retention, and economics metadata;
- explicit exclusion of credentials, leaked datasets, victim files, private communications, and intrusive access;
- LinkedIn and similar platforms disabled unless official scopes or written authorization exist;
- BrixHub represented only as a quarantined record with no executable access.

**Tests:** policy allow/deny matrix; expired authorization; unapproved host/path; raw-storage denial; automated-access denial; quota exhaustion; registry-schema validation.

**Exit gate:** No collector can reach a source without a positive policy decision and every executable source has a reviewed registry entry.

**Non-goals:** autonomous outreach, credential validation, access-control bypass, scraping every publicly visible page, or importing restricted datasets.

## Lot 01 — Modular core, persistence, provenance, and retention

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Establish the canonical model and persistence foundation required by every later source and workflow.

**Dependencies:** Lot 00.

**Deliverables:**

- modular-monolith package boundaries;
- organizations, evidence, events, observations, source accounts, suppression, retention, and metrics modules;
- PostgreSQL models and reversible Alembic migrations;
- timezone-aware UTC rules and distinct source/published/observed/collected times;
- deterministic identifiers and hashes where source identity is stable;
- immutable observation provenance envelope;
- executable retention policy and suppression hashes without raw contact identifiers;
- FastAPI application factory and local Docker Compose environment.

**Tests:** domain invariants; persistence constraints; deterministic identity; retention decisions; suppression behavior; API health; migration upgrade/downgrade/upgrade.

**Exit gate:** The application starts from a clean database, persists evidence with provenance, and can remove or suppress governed data without exposing raw identifiers.

**Non-goals:** external commercial connectors, browser automation, search indexing, or CRM synchronization.

## Lot 02 — Durable scheduler, worker, checkpoints, and recovery

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Convert one-shot collection into a durable, idempotent, recoverable execution pipeline.

**Dependencies:** Lots 00–01.

**Deliverables:**

- versioned collection schedules;
- deterministic schedule slots and job idempotency keys;
- PostgreSQL queue with transactional claim and bounded leases;
- `FOR UPDATE SKIP LOCKED` concurrency behavior;
- checkpoint ownership and atomic advancement;
- bounded exponential retry, circuit breaker, dead letters, and lease recovery;
- separate scheduler and worker commands;
- freshness, queue-lag, volume, error, and dead-letter metrics;
- first durable CISA KEV adapter path.

**Tests:** duplicate schedule prevention; concurrent claim; expired lease recovery; late-completion rejection; retry timing; circuit open/half-open/close; dead letter; rollback preserving checkpoint; worker interruption.

**Exit gate:** Replaying or interrupting a job cannot duplicate observations, lose a checkpoint, or record false success.

**Non-goals:** Redis without measured need, distributed microservices, or unbounded parallel collection.

## Lot 03 — Evidence-backed opportunity engine and analyst Inbox

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Turn normalized evidence into explainable, persistent, human-reviewed opportunities.

**Dependencies:** Lots 00–02.

**Deliverables:**

- normalized commercial signals and need hypotheses;
- versioned SIEM/SOC buying-intent rule;
- score components for intent, hiring, corroboration, confidence, freshness, and uncertainty;
- persistent opportunities with deterministic recalculation;
- analyst qualify, reject, snooze, reopen, enrichment, and override actions;
- immutable review history;
- list/detail APIs and Next.js Opportunity Inbox;
- loading, empty, unavailable, partial, and not-found states;
- preservation of analyst state and overrides during recalculation.

**Tests:** signal-to-opportunity workflow; score bounds and explanation; stale evidence; single-source penalty; corroboration; idempotent recalculation; analyst-state preservation; API contracts; persisted UI workflow.

**Exit gate:** Every visible opportunity is evidence-linked, explainable, reviewable, and impossible to create directly from the browser without backend evidence.

**Non-goals:** autonomous emails, automatic sales decisions, or hidden scoring without an explanation.

## Lot 04 — TED European procurement signals

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Produce the first real commercial signals from official European public-procurement notices.

**Dependencies:** Lots 00–03.

**Deliverables:**

- official anonymous TED Search API client;
- selected-field query for active notices;
- content-type and response-size validation;
- strict provider schemas;
- bounded search and local relevance filtering;
- deterministic buyer, evidence, observation, signal, and checkpoint identities;
- transactional projection into the Opportunity Inbox;
- typed HTTP, schema, policy, and checkpoint failures;
- no full procurement-document storage.

**Tests:** client, schema, query, mapper, irrelevant result, checkpoint, HTTP classification, policy-before-network, transactional rollback, idempotent Inbox integration.

**Exit gate:** A relevant TED notice creates one traceable opportunity and a replay cannot duplicate it or advance state after projection failure.

**Non-goals:** page scraping, document mirroring, or contact-block collection.

## Lot 05 — BOAMP French procurement and executable architecture gates

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Add official French public-procurement signals while converting maintainability rules into CI gates.

**Dependencies:** Lots 00–04.

**Deliverables:**

- official BOAMP/DILA Explore API connector;
- dated bounded window and safe pagination budget;
- checkpoint that refuses partial-window success;
- distinction between notice, rectification, cancellation, result, and expired deadline;
- projection only for actionable relevant notices;
- shared procurement-signal taxonomy instead of duplicated rules;
- refactor of the 532-line orchestration repository into focused modules and stable facade;
- AST duplicate-definition gate;
- hard 400-line application-file limit;
- separate architecture, unit/behavior, and persistent-integration suites.

**Tests:** schema variants; pagination; window overflow; mapping by notice type; deadline behavior; cancellation/result exclusion; checkpoint rollback; persistent Inbox integration; architecture rules.

**Exit gate:** BOAMP creates traceable opportunities without storing full documents, and CI prevents new duplicate definitions or oversized application modules.

**Non-goals:** DECP history, all French buyer portals, or lowering architecture standards to accommodate a connector.

## Lot 06 — Greenhouse public cyber hiring signals

**Status:** `IN_PROGRESS`

**Objective:** Add the first official ATS connector and make hiring evidence corroborate procurement opportunities without collecting candidate data.

**Dependencies:** Lots 00–05.

**Deliverables:**

- versioned registry of explicitly approved public Greenhouse boards;
- public GET-only Job Board API client with bounded response size and JSON validation;
- provider schemas for jobs, locations, departments, and offices;
- in-memory HTML-to-text normalization with script/style exclusion and length cap;
- shared cyber-role taxonomy for SOC, SIEM, MDR, XDR, detection, response, Sentinel, Splunk, QRadar, and Sekoia;
- deterministic job fingerprint, evidence, observation, signal, and organization identities;
- nested checkpoint by board and job;
- observation only for new or modified jobs;
- projection refresh for unchanged active jobs and natural expiry after removal;
- mutable idempotent signal upsert preserving immutable identity and creation time;
- transactional projection into the existing Inbox;
- stronger architecture, version, complexity, layering, and network-free unit-test gates.

**Tests:** board registry; invalid/duplicate tokens; HTML normalization; unsafe response; strict schema; mapping; false-positive rejection; new/changed/unchanged/removed jobs; nested checkpoints; HTTP 404/429/5xx; mutable upsert; rollback; persistent Inbox integration; architecture gates.

**Exit gate:** One final SHA passes backend and frontend CI; a modified job updates one existing signal; no candidate, application, email, resume, or raw HTML content is persisted; README and roadmap match the implementation.

**Non-goals:** submitting applications, reading candidate records, crawling arbitrary career pages, or inferring a named decision maker from a job listing.

## Lot 07 — Multi-ATS hiring-source expansion

**Status:** `PLANNED_LOCKED`

**Objective:** Expand hiring signals across additional official public ATS APIs while preserving one canonical job-signal contract.

**Dependencies:** Lot 06.

**Deliverables:**

- source-by-source review for Lever, SmartRecruiters, Teamtailor, Workable, and other documented public endpoints;
- approved board/company registry per provider;
- shared canonical job record and provider-specific schemas;
- common adapter contract suite;
- normalized location, department, employment type, seniority, and update time;
- provider-specific checkpoint strategy and removal detection;
- duplicate-job reconciliation across ATS migrations or mirrored postings;
- source-health and schema-drift metrics.

**Tests:** common adapter contract; provider fixtures; redirect/host control; pagination; deletion; duplicated posting; provider migration; policy denial; schema drift; cross-source deduplication.

**Exit gate:** At least two additional approved ATS providers produce the same canonical signal without provider schemas leaking into scoring or persistence.

**Non-goals:** browser scraping of unsupported ATS pages or candidate/profile collection.

## Lot 08 — French and European organization identity foundation

**Status:** `PLANNED_LOCKED`

**Objective:** Resolve collected buyers and employers to reliable legal organizations and group identities.

**Dependencies:** Lots 01, 04–07.

**Deliverables:**

- SIRENE/API Recherche Entreprises identity and establishment data;
- INPI RNE or other approved official registry integration where licensing permits;
- BODACC corporate-event metadata;
- GLEIF LEI identities and parent relationships;
- canonical SIREN/SIRET/LEI/company-number fields;
- legal name, trading name, jurisdiction, status, address precision, and registration timestamps;
- source-ranked organization aliases;
- explicit non-diffusion and restricted-record handling;
- deterministic organization merge candidates with evidence.

**Tests:** identifiers; legal-name normalization; establishment versus legal unit; non-diffusion; dissolved organization; conflicting registries; alias provenance; false-merge prevention.

**Exit gate:** Procurement and hiring organizations can be linked to official legal identities with explainable confidence and no automatic merge under ambiguity.

**Non-goals:** personal shareholder enrichment beyond lawful necessary public business information.

## Lot 09 — Public-procurement expansion and buyer history

**Status:** `PLANNED_LOCKED`

**Objective:** Build a broader buying-intent and contract-history view from official procurement sources.

**Dependencies:** Lots 04–05 and 08.

**Deliverables:**

- DECP open-contract data review and connector;
- BOAMP award/result enrichment;
- TED award and contract-modification linkage;
- buyer procurement history and recurring-category profile;
- contract start/end, amount range, lot, incumbent where lawfully published, and renewal estimate;
- PLACE, UK Find a Tender/Contracts Finder, SAM.gov, or regional portals only after separate review;
- duplicate notice/award/contract graph;
- tender lifecycle states and stale-actionability rules.

**Tests:** notice-to-award linkage; contract chronology; currency and amount range; duplicate publication; amendment; cancellation; renewal estimate; missing buyer ID; source conflict.

**Exit gate:** The platform distinguishes current intent from historical contract context and can explain an estimated renewal window without presenting it as a confirmed deadline.

**Non-goals:** bidding automatically or downloading restricted tender documents.

## Lot 10 — Vulnerability intelligence enrichment

**Status:** `PLANNED_LOCKED`

**Objective:** Add current vulnerability severity, exploitation, and ecosystem context to technology and incident evidence.

**Dependencies:** Lots 01–03.

**Deliverables:**

- NVD CVE metadata;
- CVE.org identity reconciliation;
- CISA KEV enrichment and change history;
- FIRST EPSS score and percentile history;
- OSV ecosystem/package mappings;
- GitHub Security Advisory aliases and affected ranges;
- canonical vulnerability identity, aliases, CVSS versions, CWE, affected products, references, exploitation status, and dates;
- update/retraction handling and source precedence;
- separate vulnerability facts from organization exposure inferences.

**Tests:** alias merge; conflicting CVSS; EPSS history; KEV add/remove/change; affected-range parsing; rejected malformed records; freshness; source precedence; retraction.

**Exit gate:** A CVE view reconciles official identities and exploitation context while never claiming an organization is vulnerable without separate exposure evidence.

**Non-goals:** exploit execution, credential testing, or intrusive validation.

## Lot 11 — Vendor advisories and product-to-organization matching

**Status:** `PLANNED_LOCKED`

**Objective:** Add vendor-specific advisory precision and connect observed products to relevant vulnerabilities with explicit uncertainty.

**Dependencies:** Lots 10 and 15.

**Deliverables:**

- prioritized PSIRT connectors for major infrastructure and security vendors;
- advisory-to-CVE and product-version mappings;
- fixed-version and workaround fields;
- superseded/retracted advisory handling;
- normalized product identifiers and CPE/package aliases;
- version-range evaluator with unknown/ambiguous states;
- technology observation plus advisory correlation evidence;
- confidence model separating product family, exact product, and exact vulnerable version.

**Tests:** version ranges; affected/not-affected/unknown; vendor alias; superseded advisory; multiple CVEs; malformed version; confidence downgrade; no exposure claim from family-only match.

**Exit gate:** Product and advisory evidence can produce a reviewable risk signal with explicit match level and no false certainty.

**Non-goals:** active scanning or proof-of-concept exploitation.

## Lot 12 — Incident and ransomware claim evidence

**Status:** `PLANNED_LOCKED`

**Objective:** Track cyber incidents and extortion claims with strict evidence levels and correction history.

**Dependencies:** Lots 00–03, 08, and 13.

**Deliverables:**

- approved aggregators such as ransomware.live or Ransomwhere where terms permit;
- official company statements, authority notices, and regulatory disclosures;
- claim states: actor claim, third-party report, official confirmation, regulatory disclosure, analyst inference, disputed, retracted, duplicate, false attribution;
- incident timeline and organization resolution;
- actor/group alias handling;
- minimal metadata and source URL without stolen files or victim data;
- correction, retraction, and conflicting-source workflow;
- analyst review before commercial use of unconfirmed claims.

**Tests:** claim-state transitions; source conflict; duplicate victim; organization ambiguity; retraction; official confirmation; stale claim; evidence ranking; forbidden-content rejection.

**Exit gate:** Every incident view distinguishes allegation from confirmation and preserves corrections without storing leaked content.

**Non-goals:** accessing criminal portals, downloading stolen data, negotiations, or credential material.

## Lot 13 — News, regulatory, and corporate-disclosure signals

**Status:** `PLANNED_LOCKED`

**Objective:** Detect material public events that alter cyber need, urgency, budget, or governance.

**Dependencies:** Lots 08 and 12.

**Deliverables:**

- official company pressrooms and RSS;
- SEC EDGAR cyber disclosures and other approved regulatory feeds;
- CNIL, ICO, HHS OCR, data-protection authorities, and sector regulators where relevant;
- selected licensed news metadata feeds;
- event taxonomy for breach, outage, leadership change, acquisition, expansion, compliance action, funding, and transformation;
- copyright-minimized storage of metadata, short summaries, hashes, and source links;
- event deduplication and article-cluster provenance;
- correction and publication-time handling.

**Tests:** filing extraction; duplicate articles; event classification; correction; publication versus event date; copyright storage limits; organization resolution; conflicting reports.

**Exit gate:** Material public events become traceable evidence without storing full copyrighted articles or converting a news report into an unqualified fact.

**Non-goals:** full-text news mirroring or paywall bypass.

## Lot 14 — Passive Internet-exposure observations

**Status:** `PLANNED_LOCKED`

**Objective:** Add lawful passive observations of public Internet assets and services without active probing of prospects.

**Dependencies:** Lots 00, 08, 10–11, and 16.

**Deliverables:**

- licensed/passive integrations selected from Shodan, Censys, SecurityTrails, Netlas, BinaryEdge, LeakIX, ONYPHE, FullHunt, urlscan, VirusTotal, crt.sh, RDAP, and RIPE sources;
- domain, certificate, IP, ASN, service, banner, and last-seen observations;
- strict provider terms, quotas, and retention;
- asset-to-organization evidence with confidence;
- stale-observation decay;
- separation between indexed observation and current reachable state;
- no automated direct scanning from the platform.

**Tests:** host/path policy; quota; pagination; stale data; certificate/domain linkage; shared hosting; CDN ambiguity; conflicting providers; unauthorized redirect; no direct target connection.

**Exit gate:** Passive evidence can support a technology or exposure hypothesis while the UI clearly states provider, observation date, confidence, and uncertainty.

**Non-goals:** port scans, vulnerability scans, authentication attempts, or exploit validation against prospects.

## Lot 15 — Technographics and technology-confidence model

**Status:** `PLANNED_LOCKED`

**Objective:** Build a time-aware, evidence-ranked view of technologies used by an organization.

**Dependencies:** Lots 08, 11, and 14.

**Deliverables:**

- approved BuiltWith, Wappalyzer, SimilarTech, PublicWWW, HTTP Archive, Common Crawl, job-posting, repository, and marketplace evidence;
- canonical technology/vendor/product taxonomy;
- observed version, version precision, first/last seen, and evidence source;
- confidence by evidence type and corroboration;
- contradictions and replacement history;
- technology lifecycle and end-of-support metadata;
- distinction between website technology, exposed service, internal job requirement, and confirmed deployed product.

**Tests:** alias normalization; conflicting observations; stale replacement; shared infrastructure; version precision; evidence weighting; false positive; no vulnerable-version conclusion without exact support.

**Exit gate:** An analyst can see why a technology is believed present, when it was observed, and how strong the conclusion is.

**Non-goals:** installing tracking code or actively fingerprinting private systems.

## Lot 16 — Entity resolution and corporate graph

**Status:** `PLANNED_LOCKED`

**Objective:** Reconcile organizations, domains, assets, subsidiaries, brands, and groups without unsafe automatic merges.

**Dependencies:** Lots 08–09 and 14–15.

**Deliverables:**

- canonical identifiers and source-ranked aliases;
- deterministic exact matches and scored candidate matches;
- parent/subsidiary, brand/legal entity, establishment, domain, certificate, ASN, and acquisition relationships;
- human review queue for ambiguous links;
- merge/split history and reversible decisions;
- false-merge protections and high-confidence identifier precedence;
- graph read model and lineage.

**Tests:** similar names; shared address; shared domain; subsidiary; renamed company; acquisition; conflicting registration IDs; merge reversal; precision/recall benchmark; false-merge threshold.

**Exit gate:** High-confidence exact links automate safely, ambiguous links remain reviewable, and every relationship exposes supporting evidence.

**Non-goals:** opaque probabilistic merges with no reversal or explanation.

## Lot 17 — Professional-role enrichment and compliance controls

**Status:** `PLANNED_LOCKED`

**Objective:** Identify relevant professional roles and permitted business contact channels with minimization, provenance, and objection handling.

**Dependencies:** Lots 00, 08, and 16.

**Deliverables:**

- role taxonomy for security, infrastructure, risk, procurement, finance, and executive sponsorship;
- official company/team pages, public reports, conference speakers, GitHub organizations, and licensed B2B providers after review;
- professional-only contact data model separated from organization intelligence;
- legal basis, source, collection date, purpose, retention, confidence, and opt-out state;
- suppression and do-not-contact propagation;
- generic mailbox preference where appropriate;
- source correction/deletion workflow;
- export controls and audit log.

**Tests:** professional/private distinction; purpose compatibility; suppression; deletion propagation; stale role; duplicate person; generic mailbox; export redaction; unauthorized provider block.

**Exit gate:** A contact or role cannot enter an export without source, lawful purpose, retention, and suppression checks, and objections propagate to every read model.

**Non-goals:** home addresses, family details, personal phone numbers, dating/social profiles, or scraped LinkedIn profiles.

## Lot 18 — Analyst research and safe search-query workflows

**Status:** `PLANNED_LOCKED`

**Objective:** Give analysts reproducible public-research workflows without automating access to restricted or sensitive content.

**Dependencies:** Lots 00, 08, 13–17.

**Deliverables:**

- saved research cases and hypotheses;
- query builder for official search APIs or analyst-assisted manual search;
- safe query templates for company pages, reports, jobs, tenders, advisories, `security.txt`, and public documents;
- result metadata, source snapshot hash, collection time, and analyst notes;
- manual-review queue for potentially sensitive results;
- OSINT Framework candidate catalog classified as approved, manual, restricted, or prohibited;
- no automatic download when a result appears secret, private, credential-related, or exposed by mistake;
- reproducible research audit trail.

**Tests:** query escaping; approved-host filtering; prohibited category; sensitive-result pause; duplicate result; source removal; analyst decision history; no automatic restricted download.

**Exit gate:** An analyst can reproduce how evidence was found while the system blocks unsafe automation and sensitive-content ingestion.

**Non-goals:** broad people-search enumeration, face search, account takeover research, or access-control circumvention.

## Lot 19 — Advanced scoring, calibration, and explainability

**Status:** `PLANNED_LOCKED`

**Objective:** Improve opportunity prioritization using multiple independent signal families without hiding uncertainty or human control.

**Dependencies:** Lots 07–18.

**Deliverables:**

- versioned scoring configuration and feature registry;
- service-fit, technical urgency, exploitation, recency, company importance, buying intent, contact relevance, and evidence-quality components;
- uncertainty, staleness, false-positive, legal-risk, and mono-source penalties;
- source-family independence and corroboration rules;
- score calibration dataset using analyst outcomes;
- drift, distribution, and fairness monitoring;
- full explanation and counterfactual reason codes;
- shadow evaluation before promotion of a new score version.

**Tests:** bounds; monotonic components; stale decay; contradictory evidence; corroboration; legal-risk veto; calibration replay; version migration; override preservation; regression dataset.

**Exit gate:** A new score version beats the approved benchmark, produces stable explanations, and can be rolled back without rewriting historical decisions.

**Non-goals:** opaque autonomous lead selection or model-only decisions with no rule/evidence trace.

## Lot 20 — CRM synchronization and commercial workflow

**Status:** `PLANNED_LOCKED`

**Objective:** Synchronize analyst-approved opportunities with HubSpot or Salesforce without duplicate records or autonomous outreach.

**Dependencies:** Lots 03, 17, and 19.

**Deliverables:**

- connector architecture with provider-specific clients and shared CRM commands;
- tenant/account authorization and secret isolation;
- organization/contact/opportunity mapping;
- external IDs and idempotent create/update behavior;
- field ownership and conflict policy;
- staged export requiring human approval;
- sync status, error queue, replay, and audit events;
- deletion/suppression propagation;
- dry-run and sandbox mode.

**Tests:** OAuth/secret boundary; mapping; idempotency; duplicate external record; conflict; rate limit; partial failure; replay; suppression; sandbox; rollback.

**Exit gate:** One approved CRM sandbox receives a reviewed opportunity exactly once, changes reconcile safely, and no message is sent automatically.

**Non-goals:** autonomous email sequences, covert tracking, or overriding CRM user edits without policy.

## Lot 21 — Full analyst workspace and operational UX

**Status:** `PLANNED_LOCKED`

**Objective:** Turn the Inbox into a complete evidence, organization, research, source-health, and workflow workspace.

**Dependencies:** Lots 08–20.

**Deliverables:**

- organization 360 page;
- evidence timeline and lineage graph;
- technology, vulnerability, incident, procurement, hiring, and contact sections;
- saved views, filters, sorting, bulk triage, and ownership;
- research-case workspace;
- source health, paused/quarantined state, and checkpoint visibility;
- score explanation and version comparison;
- compliance and suppression indicators;
- accessible keyboard, loading, partial, stale, error, and recovery states.

**Tests:** frontend components; API contracts; key workflows; accessibility; large timelines; stale/partial data; source outage; concurrent analyst edits; audit display.

**Exit gate:** Analysts can investigate and qualify an opportunity end to end without consulting database tables or hidden logs.

**Non-goals:** replacing the CRM or exposing raw restricted provider payloads.

## Lot 22 — Data quality, reconciliation, and lineage controls

**Status:** `PLANNED_LOCKED`

**Objective:** Detect silent source drift, missing data, duplicates, reconciliation gaps, and lineage breaks before they affect analysts.

**Dependencies:** Lots 08–21.

**Deliverables:**

- data-quality rules and thresholds by source and canonical entity;
- field-population, duplicate, freshness, schema, and volume baselines;
- observation-to-evidence-to-signal-to-opportunity lineage validation;
- source-to-canonical reconciliation reports;
- quarantine for malformed or contradictory records;
- backfill and replay controls;
- quality incidents and analyst resolution workflow;
- release-to-release regression datasets.

**Tests:** volume drift; missing field; duplicate spike; lineage break; replay; backfill; contradiction; quarantine release; regression comparison.

**Exit gate:** A silent parser or mapping regression causes a visible quality failure before deployment or opportunity publication.

**Non-goals:** masking quality problems by lowering thresholds automatically.

## Lot 23 — Isolated browser and download-quarantine runtime

**Status:** `DEFERRED`

**Objective:** Support approved JavaScript or authenticated sources only when structured API, feed, export, and static HTTP methods cannot meet the requirement.

**Dependencies:** Lots 00, 02, 22, and an explicit source authorization.

**Deliverables:**

- isolated browser worker with per-source context;
- narrow browser research port;
- host/path, page, time, and download budgets;
- MFA/CAPTCHA/terms-change safe pause;
- session isolation and secret handling;
- download quarantine, content validation, archive limits, scanning, and safe extraction;
- browser traces and redacted diagnostics;
- kill switch and source pause.

**Tests:** local emulated pages; cross-domain block; expired session; MFA/CAPTCHA; selector drift; crash/restart; context isolation; spoofed file; archive bomb; scanner unavailable; cleanup.

**Exit gate:** One explicitly approved source runs in isolation with no bypass behavior, no unrestricted download, and complete failure evidence.

**Non-goals:** generalized browser scraping, CAPTCHA solving, cookie reuse across accounts, or access-control bypass. This lot remains deferred until simpler sources and quarantine controls are mature.

## Lot 24 — Supply-chain, release provenance, and repository protection

**Status:** `PLANNED_LOCKED`

**Objective:** Make installations, builds, releases, and GitHub governance reproducible and tamper-evident.

**Dependencies:** All implemented code lots; tracked by repository hardening issue.

**Deliverables:**

- deterministic Python lockfile and verified frontend lockfile;
- `npm ci` and locked Python installation in CI;
- Python and npm SBOM generation;
- artifact checksums, signing, or GitHub attestations;
- actions pinned by full commit SHA;
- CODEOWNERS and protected `main` requiring PR, checks, resolved conversations, and no force push;
- secret scanning and available repository rules;
- release, rollback, dependency-update, and secret-rotation runbooks;
- lockfile-change validation.

**Tests:** two clean reproducible installs; lockfile drift; SBOM contents; artifact checksum; action pinning; release rollback rehearsal; secret fixture detection.

**Exit gate:** A release can be rebuilt from source with the same dependencies, has an SBOM and provenance, and cannot bypass required GitHub checks.

**Non-goals:** claiming repository protections are active when they require an unverified manual GitHub setting.

## Lot 25 — Observability, performance, resilience, and recovery

**Status:** `PLANNED_LOCKED`

**Objective:** Prove that the platform remains correct, diagnosable, and recoverable under production load and dependency failure.

**Dependencies:** Lots 02–24.

**Deliverables:**

- structured logs, metrics, traces, correlation IDs, and redaction;
- source freshness and SLA dashboards;
- queue, retry, circuit, dead-letter, and projection metrics;
- database and API latency budgets;
- connector throughput and quota monitoring;
- backup, restore, disaster-recovery, and retention verification;
- chaos scenarios for worker, database, provider, and frontend failures;
- capacity model and scaling thresholds;
- alert ownership and incident runbooks.

**Tests:** load; soak; worker kill; database interruption; provider 429/5xx; duplicate delivery; clock skew; backup restore; stale source; partial UI; resource limits.

**Exit gate:** Defined service objectives are met, a backup restore succeeds, injected failures preserve invariants, and every production alert has an owner and runbook.

**Non-goals:** adding Redis, OpenSearch, or microservices before measurements justify them.

## Lot 26 — Controlled pilot, production gate, and premium scale

**Status:** `PLANNED_LOCKED`

**Objective:** Move from engineering validation to a controlled analyst pilot, measurable commercial value, and governed expansion.

**Dependencies:** Lots 00–25, except deferred Lot 23 unless a pilot source requires it.

**Deliverables:**

- pilot tenant and least-privilege roles;
- approved source portfolio and source-by-source operating owner;
- data-protection and retention review;
- analyst training and operating procedures;
- quality, precision, review-time, conversion, and source-cost metrics;
- false-positive and false-merge review process;
- go/no-go checklist and rollback plan;
- production deployment, backup, monitoring, support, and incident ownership;
- premium-provider evaluation for threat intelligence, passive exposure, technographics, company data, and contacts;
- scale plan based on measured value, cost, legal fit, stability, and maintenance.

**Tests:** pilot replay; role authorization; data deletion/suppression; source outage; restore; load; end-to-end analyst workflow; CRM dry run; quality benchmark; operational tabletop.

**Exit gate:** A formal `GO`, `CONDITIONAL_GO`, or `NO_GO` decision is recorded with evidence. Production begins only after all blockers are closed and rollback is rehearsed.

**Non-goals:** uncontrolled source expansion, autonomous prospecting, or purchasing premium data without measured product value and legal review.

## Phase promotion record

For every lot promoted to `IMPLEMENTED_VALIDATED`, the closing pull request records:

- lot number and exact scope;
- final commit SHA;
- CI run identifier;
- backend test count;
- line and branch coverage;
- Mypy file count;
- migration result;
- dependency-audit result;
- frontend audit, typecheck, and build result;
- source/data limitations;
- next locked lot.
