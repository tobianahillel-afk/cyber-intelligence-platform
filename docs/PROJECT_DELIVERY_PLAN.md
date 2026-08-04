# Project Delivery Plan

## Purpose

This is the authoritative production roadmap for Cyber Intelligence Platform. The product is a standalone cyber revenue-intelligence and commercial-operations system. It owns alerts, company intelligence, professional organization maps, contacts, opportunities, tasks, notes, assignments, engagement history, and reporting instead of depending on Salesforce, HubSpot, or another external CRM.

A lot is complete only when one final commit passes every applicable backend, frontend, architecture, migration, security, compliance, and documentation gate.

## Status vocabulary

- `IMPLEMENTED_VALIDATED`: implementation passed its complete exit gate.
- `IN_PROGRESS`: implementation is active but not finally validated.
- `PLANNED_LOCKED`: scope and exit criteria are defined; code has not started.
- `BLOCKED`: an external authorization, legal, product, or technical dependency prevents execution.
- `DEFERRED`: intentionally postponed because a simpler or safer capability has priority.

## Delivery rules

- Lot numbers are continuous and never reused.
- Each lot has one primary business outcome.
- Source governance is approved before any network request.
- Public or licensed data is minimized; credentials, victim files, private communications, private-life data, and access-control bypasses are excluded.
- Professional contacts require provenance, permitted purpose, freshness, retention, correction, and suppression state.
- Code, tests, data policy, operations, documentation, and rollback behavior move together.
- Any later commit invalidates an earlier validation result.
- Code for a new lot starts from the merged `main` commit of the previous lot.

## Status overview

| Lot | Outcome | Status |
| ---: | --- | --- |
| 00 | Product, legal, and source-governance foundation | `IMPLEMENTED_VALIDATED` |
| 01 | Modular core, persistence, provenance, and retention | `IMPLEMENTED_VALIDATED` |
| 02 | Durable scheduler, worker, checkpoints, and recovery | `IMPLEMENTED_VALIDATED` |
| 03 | Evidence-backed opportunity engine and analyst Inbox | `IMPLEMENTED_VALIDATED` |
| 04 | TED European procurement signals | `IMPLEMENTED_VALIDATED` |
| 05 | BOAMP French procurement and executable architecture gates | `IMPLEMENTED_VALIDATED` |
| 06 | Greenhouse public cyber hiring signals | `IMPLEMENTED_VALIDATED` |
| 07 | Lever and SmartRecruiters multi-ATS expansion | `IMPLEMENTED_VALIDATED` |
| 08 | French and European organization identity foundation | `PLANNED_LOCKED` |
| 09 | Procurement history, providers, and contract timing | `PLANNED_LOCKED` |
| 10 | Vulnerability intelligence enrichment | `PLANNED_LOCKED` |
| 11 | Vendor advisories and product-version matching | `PLANNED_LOCKED` |
| 12 | Incident and ransomware claim evidence | `PLANNED_LOCKED` |
| 13 | News, regulatory, and corporate-disclosure signals | `PLANNED_LOCKED` |
| 14 | Passive Internet-exposure observations | `PLANNED_LOCKED` |
| 15 | Technographics and security-provider intelligence | `PLANNED_LOCKED` |
| 16 | Entity resolution and corporate relationship graph | `PLANNED_LOCKED` |
| 17 | Professional organization maps and contact governance | `PLANNED_LOCKED` |
| 18 | Analyst research and authorized public-search workflows | `PLANNED_LOCKED` |
| 19 | Advanced scoring, calibration, and explainability | `PLANNED_LOCKED` |
| 20 | Native commercial operations, alerts, tasks, and engagement | `PLANNED_LOCKED` |
| 21 | Complete company intelligence and analyst workspace | `PLANNED_LOCKED` |
| 22 | Data quality, reconciliation, and lineage controls | `PLANNED_LOCKED` |
| 23 | Isolated browser and download-quarantine runtime | `DEFERRED` |
| 24 | Supply-chain, release provenance, and repository protection | `PLANNED_LOCKED` |
| 25 | Observability, performance, resilience, and recovery | `PLANNED_LOCKED` |
| 26 | Controlled pilot and production gate | `PLANNED_LOCKED` |

## Lot 00 — Product, legal, and source-governance foundation

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Define the lawful human-operated product boundary and make source authorization executable.

**Dependencies:** None.

**Deliverables:** Product charter; source states; approved purpose, host, path, automation, quota, retention, attribution, and raw-storage fields; prohibited data categories; quarantine behavior; explicit controls for platform APIs and browser workflows.

**Tests:** Policy allow/deny matrix; expired authorization; wrong host/path/purpose; quota exhaustion; prohibited category; raw-storage denial; registry validation.

**Exit gate:** No collector can execute without a positive source-policy decision and every executable source has a reviewed registry record.

**Non-goals:** Credential validation, private-account access, leaked datasets, intrusive collection, autonomous outreach, or indiscriminate scraping.

## Lot 01 — Modular core, persistence, provenance, and retention

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Establish canonical entities and persistence shared by later workflows.

**Dependencies:** Lot 00.

**Deliverables:** Modular-monolith boundaries; organizations, evidence, observations, suppression, retention, and metrics modules; PostgreSQL models; reversible Alembic migrations; deterministic IDs; UTC timestamps; provenance envelopes; local development environment.

**Tests:** Domain invariants; persistence constraints; deterministic identity; retention and suppression; API health; migration upgrade/downgrade/upgrade.

**Exit gate:** A clean installation persists evidence with lineage and can remove or suppress governed data without exposing raw identifiers.

**Non-goals:** External source breadth, browser automation, or commercial workflow depth.

## Lot 02 — Durable scheduler, worker, checkpoints, and recovery

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Make collection durable, idempotent, observable, and recoverable.

**Dependencies:** Lots 00–01.

**Deliverables:** Versioned schedules; deterministic slots; PostgreSQL queue; leases; transactional claims; checkpoints; bounded retries; circuits; dead letters; interruption recovery; worker and scheduler entry points; source-health metrics.

**Tests:** Duplicate scheduling; concurrent claim; lease expiry; late completion; retry timing; circuit lifecycle; dead letter; checkpoint rollback; worker interruption.

**Exit gate:** Replay or interruption cannot duplicate observations, lose checkpoints, or record false success.

**Non-goals:** Premature microservices, Redis without measured need, or unbounded concurrency.

## Lot 03 — Evidence-backed opportunity engine and analyst Inbox

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Convert normalized evidence into explainable, persistent, human-reviewed opportunities.

**Dependencies:** Lots 00–02.

**Deliverables:** Commercial signals; need hypotheses; versioned SIEM/SOC rule; score components; persistent opportunities; analyst state transitions; immutable review history; APIs; Next.js Inbox; partial, stale, empty, and unavailable states.

**Tests:** Signal-to-opportunity flow; score bounds; freshness; corroboration; single-source penalty; idempotent recalculation; analyst-state preservation; API and UI contracts.

**Exit gate:** Every opportunity is evidence-linked, explainable, reviewable, and cannot be created directly by the browser without backend evidence.

**Non-goals:** Hidden scoring, automatic sales decisions, or autonomous contact.

## Lot 04 — TED European procurement signals

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Produce commercial intent signals from official European procurement notices.

**Dependencies:** Lots 00–03.

**Deliverables:** Official TED Search API client; selected metadata; strict schemas; bounded queries; local cyber relevance; deterministic identities; checkpoints; transactional opportunity projection; typed failures; no full-document storage.

**Tests:** Client; schema; mapper; irrelevant notice; HTTP failures; policy-before-network; checkpoint; rollback; replay; persistent projection.

**Exit gate:** A relevant TED notice creates exactly one traceable opportunity and projection failure cannot advance its checkpoint.

**Non-goals:** Page scraping, document mirroring, or contact-block collection.

## Lot 05 — BOAMP French procurement and executable architecture gates

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Add French procurement signals and enforce maintainability automatically.

**Dependencies:** Lots 00–04.

**Deliverables:** BOAMP/DILA connector; bounded dated pagination; overflow refusal; notice, rectification, cancellation, result, and deadline handling; actionable-only projection; repository refactor; AST duplicate-definition and file-size gates.

**Tests:** Schema variants; pagination; overflow; notice types; deadlines; cancellation/result exclusion; checkpoint rollback; persistent Inbox integration; architecture contracts.

**Exit gate:** BOAMP produces traceable opportunities and CI prevents duplicate definitions or oversized application modules.

**Non-goals:** Every French procurement portal, historical contract graph, or reduced architecture standards.

## Lot 06 — Greenhouse public cyber hiring signals

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Add the first official ATS connector without collecting candidate data.

**Dependencies:** Lots 00–05.

**Deliverables:** Approved-board registry; GET-only public client; strict schemas; bounded response; in-memory HTML cleanup; cyber-role taxonomy; job fingerprints; nested checkpoints; active-job refresh; removed-job expiry; mutable idempotent signal upsert; UTC-safe persistence; architecture, complexity, version, layering, and network-free unit-test gates.

**Tests:** Registry; transport; schema; HTML; mapping; false-positive rejection; new, changed, unchanged, and removed jobs; checkpoint; HTTP classification; mutable upsert; rollback; SQLite/PostgreSQL UTC; persistent Inbox integration.

**Exit gate:** One final SHA passes all backend and frontend gates; a modified job updates one signal and no candidate, application, email, resume, or raw HTML is retained.

**Non-goals:** Application submission, candidate records, arbitrary career-page crawling, or named-person inference from a listing.

## Lot 07 — Lever and SmartRecruiters multi-ATS expansion

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Add two official public ATS providers behind one canonical public-job contract.

**Dependencies:** Lot 06.

**Deliverables:** Canonical provider-independent job model; shared bounded HTML normalization; Lever registry, schemas, paginated GET client, mapper, collector, checkpoint, and orchestration adapter; SmartRecruiters company registry, public list/detail clients, schemas, mapper, collector, checkpoint, and adapter; common signal taxonomy; provider-safe identity; exact-only cross-provider match candidates; source-health and schema-drift failures; thirty-minute schedules.

**Tests:** Registry validation; client URLs and response bounds; provider schemas; location, department, employment, and seniority normalization; pagination; new, changed, unchanged, and removed jobs; duplicates; detail/list mismatch; policy denial; invalid checkpoints; HTTP and transport classification; canonical mapping; exact and ambiguous cross-provider matches; runtime registration; complete CI.

**Exit gate:** Lever and SmartRecruiters produce identical canonical behavior, replay is idempotent, changed postings update one signal, removed postings stop refreshing, ambiguous cross-provider records remain separate, and one final SHA passes all quality gates.

**Non-goals:** Candidate or application data, write endpoints, unsupported-page scraping, automatic ambiguous deduplication, or collection of private profiles.

## Lot 08 — French and European organization identity foundation

**Status:** `PLANNED_LOCKED`

**Objective:** Resolve buyers and employers to reliable legal entities, establishments, brands, and groups.

**Dependencies:** Lots 01 and 04–07.

**Deliverables:** SIRENE and API Recherche Entreprises; approved INPI/RNE data; BODACC metadata; GLEIF; SIREN, SIRET, LEI, and foreign identifiers; legal-unit versus establishment model; aliases; status; parent relationships; non-diffusion handling; evidence-backed merge candidates.

**Tests:** Identifier validation; establishment/legal-unit distinction; non-diffusion; dissolved entities; conflicting registries; aliases; false-merge prevention.

**Exit gate:** Organizations link to official identities with explainable confidence and ambiguous candidates require human review.

**Non-goals:** Unnecessary shareholder or private-person enrichment.

## Lot 09 — Procurement history, providers, and contract timing

**Status:** `PLANNED_LOCKED`

**Objective:** Distinguish current buying intent from historical contracts, incumbents, providers, and likely renewal context.

**Dependencies:** Lots 04–05 and 08.

**Deliverables:** DECP review and connector; TED and BOAMP award/result/amendment linkage; buyer history; lots, amounts, currencies, published incumbents and subcontractors; contract start/end dates; renewal estimates with confidence; provider/service classification for audit, SOC, SIEM, incident response, compliance, integration, insurance, and consulting.

**Tests:** Notice-to-award linkage; chronology; currency; amendments; cancellation; duplicate publication; provider identity; service classification; estimated renewal; missing identifiers; source conflict.

**Exit gate:** Current opportunity, confirmed contract history, published provider relationship, and estimated renewal are clearly separated and traceable.

**Non-goals:** Automatic bidding, restricted-document access, or presenting an estimate as a confirmed deadline.

## Lot 10 — Vulnerability intelligence enrichment

**Status:** `PLANNED_LOCKED`

**Objective:** Build a reconciled vulnerability knowledge layer.

**Dependencies:** Lots 01–03.

**Deliverables:** NVD; CVE.org; CISA KEV history; FIRST EPSS history; OSV; GitHub advisories; aliases; CVSS, CWE, products, ranges, references, exploitation state, updates, and retractions.

**Tests:** Alias merge; conflicting CVSS; EPSS history; KEV changes; affected ranges; malformed records; source precedence; retraction.

**Exit gate:** Vulnerability facts reconcile across primary sources without implying that an organization is exposed.

**Non-goals:** Exploit execution, credential testing, or intrusive validation.

## Lot 11 — Vendor advisories and product-version matching

**Status:** `PLANNED_LOCKED`

**Objective:** Add vendor-specific affected-version precision and explicit uncertainty.

**Dependencies:** Lots 10 and 15.

**Deliverables:** Prioritized PSIRT connectors; advisory-to-CVE and product mapping; fixed versions; workarounds; supersession; product identifiers; range evaluator; family, product, and exact-version confidence levels.

**Tests:** Version ranges; affected, unaffected, and unknown states; aliases; superseded advisory; malformed versions; confidence downgrade; family-only false certainty prevention.

**Exit gate:** Every risk result exposes its match precision and never presents family evidence as an exact vulnerable version.

**Non-goals:** Active scanning or proof-of-concept exploitation.

## Lot 12 — Incident and ransomware claim evidence

**Status:** `PLANNED_LOCKED`

**Objective:** Track public incident and extortion claims with evidence levels and corrections.

**Dependencies:** Lots 00–03, 08, and 13.

**Deliverables:** Approved public or licensed aggregators; official statements; regulatory confirmations; allegation, report, confirmation, inference, dispute, retraction, duplicate, and false-attribution states; timelines; actor aliases; minimal metadata; analyst review.

**Tests:** Claim transitions; conflicts; duplicate victim; ambiguous organization; correction; retraction; confirmation; staleness; source ranking; forbidden-content rejection.

**Exit gate:** Every incident distinguishes allegation from confirmation and stores no stolen or victim content.

**Non-goals:** Criminal-portal access, leaked files, negotiations, private messages, or credentials.

## Lot 13 — News, regulatory, and corporate-disclosure signals

**Status:** `PLANNED_LOCKED`

**Objective:** Detect public events affecting cyber need, urgency, budget, governance, or organizational change.

**Dependencies:** Lots 08 and 12.

**Deliverables:** Company pressrooms and RSS; SEC cyber disclosures; CNIL, ICO, HHS, and sector regulators; licensed news metadata; event taxonomy; short copyright-minimized summaries; clustering; corrections; event-time versus publication-time distinction.

**Tests:** Filing extraction; duplicate stories; classification; correction; date distinction; storage limits; organization resolution; conflicting reports.

**Exit gate:** Material events become evidence without full-text mirroring or unqualified factual claims.

**Non-goals:** Paywall bypass or copyrighted-article storage.

## Lot 14 — Passive Internet-exposure observations

**Status:** `PLANNED_LOCKED`

**Objective:** Add authorized passive observations of public assets without probing prospects directly.

**Dependencies:** Lots 00, 08, 10–11, and 16.

**Deliverables:** Approved passive providers; domains, certificates, IPs, ASNs, services, and banner observations; quotas; retention; asset-to-organization confidence; last-seen decay; indexed-observation versus current-state distinction; direct-scan prohibition.

**Tests:** Policy and quota; pagination; stale data; certificate and domain linkage; shared hosting/CDN ambiguity; provider conflicts; redirect block; no direct target connection.

**Exit gate:** Exposure hypotheses show provider, observation time, confidence, and uncertainty.

**Non-goals:** Port scans, vulnerability scans, authentication, or exploit validation.

## Lot 15 — Technographics and security-provider intelligence

**Status:** `PLANNED_LOCKED`

**Objective:** Build a time-aware view of technologies, vendors, service providers, and cybersecurity relationships.

**Dependencies:** Lots 08, 09, 11, and 14.

**Deliverables:** Approved technographic sources; canonical technology and provider taxonomies; versions; first/last seen; confidence by evidence type; replacement history; lifecycle and end-of-support; public references to SOC, MSSP, integrator, auditor, consultant, cloud, insurer, and incident-response providers; relationship start/end evidence where published.

**Tests:** Alias normalization; conflicting observations; stale replacement; shared infrastructure; version precision; provider classification; relationship chronology; false positives; vulnerable-version evidence requirement.

**Exit gate:** Analysts can see why a technology or provider relationship is believed present, when it was observed, and how strong the evidence is.

**Non-goals:** Tracking-code installation, private-system fingerprinting, or unsupported relationship inference.

## Lot 16 — Entity resolution and corporate relationship graph

**Status:** `PLANNED_LOCKED`

**Objective:** Link legal entities, brands, groups, domains, assets, providers, contracts, and people without unsafe merges.

**Dependencies:** Lots 08–09 and 14–15.

**Deliverables:** Candidate generation; evidence-weighted matching; corporate hierarchy; acquisitions; aliases; domain and asset ownership; relationship validity intervals; reversible merge and split operations; conflict queues.

**Tests:** Exact and fuzzy identifiers; brand/legal conflicts; subsidiaries; acquisitions; shared domains; shared infrastructure; false-merge datasets; merge reversal; history preservation.

**Exit gate:** Ambiguous relations remain reviewable candidates and every accepted edge is evidence-backed and reversible.

**Non-goals:** Silent automatic merging based on name similarity alone.

## Lot 17 — Professional organization maps and contact governance

**Status:** `PLANNED_LOCKED`

**Objective:** Build current and historical professional organization maps and lawful business contact records.

**Dependencies:** Lots 00, 08, and 16.

**Deliverables:** Person and professional-identity records; roles, departments, seniority, geography, and employment dates; reporting-line candidates; buying-committee roles; public or licensed professional emails, direct business numbers, switchboards, contact forms, and role mailboxes; source, verification, confidence, purpose, retention, correction, objection, and suppression fields; preference for company and role channels over personal details.

**Tests:** Person and employment deduplication; role history; ambiguous names; reporting-line conflicts; professional/private classification; stale contacts; correction; suppression propagation; export denial; lawful-purpose checks.

**Exit gate:** Every visible contact channel has provenance, permitted purpose, freshness, and suppression state, and ambiguous identities are not merged automatically.

**Non-goals:** Home addresses, family data, private phone numbers, private emails, personal accounts, sensitive traits, leaked data, or unauthorized platform scraping.

## Lot 18 — Analyst research and authorized public-search workflows

**Status:** `PLANNED_LOCKED`

**Objective:** Make public research reproducible, scoped, and safe.

**Dependencies:** Lots 00, 08, 16, and 17.

**Deliverables:** Research cases; reusable queries; saved results; public document discovery; approved search APIs; source classification; analyst review tasks; quarantined metadata for accidental sensitive exposure; query and result provenance; OSINT catalog classification.

**Tests:** Query templates; provider controls; duplicates; restricted-result quarantine; no secret download; case history; retention; authorization expiry; analyst decisions.

**Exit gate:** Research is reproducible and any result suggesting private, secret, or restricted content stops before collection.

**Non-goals:** Search-engine abuse, credential discovery, private-account access, or automated collection of accidental exposures.

## Lot 19 — Advanced scoring, calibration, and explainability

**Status:** `PLANNED_LOCKED`

**Objective:** Improve prioritization while preserving transparent human control.

**Dependencies:** Lots 03 and 08–18.

**Deliverables:** Service fit; urgency; buying intent; contract timing; technology and vulnerability relevance; company priority; role/contact availability; evidence quality; freshness; uncertainty; legal-risk and single-source penalties; calibration datasets; rule versions; analyst feedback loops.

**Tests:** Score bounds; monotonicity; stale decay; uncertainty; source independence; override preservation; benchmark precision/recall; regression comparison; explanation completeness.

**Exit gate:** A new scoring version beats its benchmark, remains explainable, and can be rolled back without losing analyst decisions.

**Non-goals:** Opaque autonomous ranking or sensitive-trait profiling.

## Lot 20 — Native commercial operations, alerts, tasks, and engagement

**Status:** `PLANNED_LOCKED`

**Objective:** Provide the complete commercial operating layer inside Cyber Intelligence Platform.

**Dependencies:** Lots 03, 08, 17, and 19.

**Deliverables:** Native accounts and ownership; rule-generated alerts; saved searches and watchlists; opportunity stages; assignments; tasks; reminders; queues; due dates and service-level targets; notes; research requests; contact and buying-committee views; engagement records; interaction history; attachments limited to approved business content; audit trail; reversible transitions; dashboards and reports; product-controlled import/export for portability only.

**Tests:** Alert deduplication and reopening; assignment; task recurrence; overdue state; stage transitions; immutable history; note revisions; suppression before contact use; concurrent edits; permissions; export minimization; deletion propagation; dashboard consistency.

**Exit gate:** A team can discover, qualify, assign, research, track, and close an opportunity entirely inside the platform with complete audit history and no external CRM dependency.

**Non-goals:** Salesforce or HubSpot synchronization, hidden outreach automation, autonomous messaging, or third-party CRM as source of truth.

## Lot 21 — Complete company intelligence and analyst workspace

**Status:** `PLANNED_LOCKED`

**Objective:** Deliver one coherent workspace for full company investigation and commercial action.

**Dependencies:** Lots 08–20.

**Deliverables:** Company 360; corporate graph; professional org chart; people and role history; contacts; technologies; providers; vulnerabilities; incidents; tenders; contracts; recruitment; regulatory and business events; evidence timeline; alert center; opportunity workspace; tasks; notes; engagement history; source health; score explanation; saved layouts and filters.

**Tests:** Loading, empty, partial, stale, conflicting, suppressed, unavailable, unauthorized, and success states; graph navigation; timelines; filtering; keyboard access; responsive layout; deep links; audit visibility; end-to-end investigation.

**Exit gate:** An analyst can move from alert to evidence, organization map, contact, task, opportunity, and history without direct database or log access.

**Non-goals:** Displaying raw restricted data, hiding uncertainty, or requiring another system to complete the workflow.

## Lot 22 — Data quality, reconciliation, and lineage controls

**Status:** `PLANNED_LOCKED`

**Objective:** Detect silent source, parser, mapping, identity, and derived-data regressions.

**Dependencies:** Lots 08–21.

**Deliverables:** Quality rules; expected volumes; freshness thresholds; duplicate detection; lineage validation; source reconciliation; quarantine queues; replay; backfill; golden datasets; schema-drift alerts; correction propagation; derived-data invalidation.

**Tests:** Parser regression; volume anomaly; missing fields; stale source; duplicate entity; broken lineage; replay idempotence; backfill; correction and deletion propagation.

**Exit gate:** A silent parser or mapping regression blocks publication before corrupting analyst-visible intelligence.

**Non-goals:** Accepting low-quality data because it increases record volume.

## Lot 23 — Isolated browser and download-quarantine runtime

**Status:** `DEFERRED`

**Objective:** Support approved browser-only sources after structured APIs and static HTTP are insufficient.

**Dependencies:** Lots 00, 18, 22, and 24–25.

**Deliverables:** Isolated browser workers; allowlisted navigation; session separation; page and time budgets; MFA/CAPTCHA safe pause; download quarantine; archive limits; file validation; redacted evidence; kill switch; browser-specific source authorization.

**Tests:** Host/path escape; redirects; CAPTCHA and MFA pause; timeout; download type and size; archive bomb; malware quarantine; session isolation; secret redaction; kill switch.

**Exit gate:** Approved browser collection cannot bypass access controls, silently download unsafe content, or mix sessions.

**Non-goals:** Bot evasion, copied cookies, fake-account rotation, CAPTCHA bypass, private-area access, or unrestricted crawling.

## Lot 24 — Supply-chain, release provenance, and repository protection

**Status:** `PLANNED_LOCKED`

**Objective:** Make builds reproducible and releases verifiable.

**Dependencies:** Lots 01–07.

**Deliverables:** Reproducible Python lock; deterministic frontend install; SBOMs; checksums; attestations; pinned actions; CODEOWNERS; strict `main` protection; secret scanning; release procedure; rollback procedure; artifact retention.

**Tests:** Clean rebuild; dependency integrity; SBOM generation; secret fixture detection; protected-branch rules; signed or attested artifact verification; rollback rehearsal.

**Exit gate:** A release can be rebuilt from source with the same dependencies and cannot bypass required checks.

**Non-goals:** Manual undocumented production releases.

## Lot 25 — Observability, performance, resilience, and recovery

**Status:** `PLANNED_LOCKED`

**Objective:** Prove operational reliability under expected load and failure.

**Dependencies:** Lots 02–24.

**Deliverables:** Structured logs; traces; metrics; freshness and queue dashboards; latency and quota views; alerts; backups; restore runbooks; capacity thresholds; load tests; fault injection; degraded modes; recovery objectives.

**Tests:** Load and soak; quota exhaustion; provider outage; database restart; worker crash; duplicate delivery; backup restore; degraded UI; alert delivery; recovery-time measurement.

**Exit gate:** Restore succeeds, invariants survive injected failures, and capacity limits are measured rather than assumed.

**Non-goals:** Production scale claims without repeatable evidence.

## Lot 26 — Controlled pilot and production gate

**Status:** `PLANNED_LOCKED`

**Objective:** Validate the complete standalone product with controlled users and approved data.

**Dependencies:** Lots 00–25, with deferred capabilities either completed or explicitly excluded from the pilot.

**Deliverables:** Pilot tenant; least-privilege roles; approved source portfolio; privacy and retention review; analyst training; native alert, investigation, org-map, contact, task, opportunity, and engagement workflows; quality and conversion metrics; operational runbooks; rollback plan; premium-source evaluation.

**Tests:** End-to-end alert-to-opportunity workflow; suppression and correction exercise; source outage; backup restore; permissions; contact-purpose review; native commercial workflow; analyst acceptance; rollback rehearsal; go/no-go review.

**Exit gate:** Governance, product, data-quality, security, resilience, and business-value evidence supports an explicit `GO`, `CONDITIONAL_GO`, or `NO_GO` decision.

**Non-goals:** Broad production rollout before blockers close or unsupported claims of complete coverage.
