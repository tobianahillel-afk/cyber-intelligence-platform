# Project Delivery Plan

## Purpose

This is the authoritative production roadmap for Cyber Intelligence Platform. Delivery is divided into continuous lots with explicit dependencies, deliverables, test suites, non-goals, and exit gates. A lot is complete only when one final commit passes every applicable backend, frontend, architecture, migration, security, and documentation gate.

## Status vocabulary

- `IMPLEMENTED_VALIDATED`: implementation has passed its complete exit gate and is ready to merge or already merged.
- `IN_PROGRESS`: implementation is active but has not passed its final gate.
- `PLANNED_LOCKED`: scope and exit criteria are defined; implementation has not started.
- `BLOCKED`: an external legal, authorization, product, or technical dependency prevents execution.
- `DEFERRED`: intentionally postponed because a simpler or safer mechanism has priority.

## Delivery rules

- Lot numbers are continuous and never reused.
- Each lot has one primary business outcome.
- New source access requires an approved source-policy record before any network request.
- Public or licensed data is minimized; credentials, leaked data, victim files, and private communications are excluded.
- Code, tests, architecture, operations, compliance, and documentation move together.
- Any later commit invalidates earlier validation; the closing report always names the final SHA and CI run.
- Code for the next lot starts only from the merged `main` commit of the current lot.

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

**Objective:** Define the lawful, human-operated product boundary and make source authorization executable.

**Dependencies:** None.

**Deliverables:** Product charter; allowed/conditional/quarantined source states; purpose, host, path, automation, quota, raw-storage, attribution, retention, and economics fields; prohibited data categories; LinkedIn-like sources disabled without official permission; BrixHub quarantined with no executable access.

**Tests:** Policy allow/deny matrix; expired authorization; unapproved host/path; raw-storage denial; automated-access denial; quota exhaustion; registry-schema validation.

**Exit gate:** No collector can perform a request without a positive policy decision and every executable source has a reviewed registry entry.

**Non-goals:** Autonomous outreach, credential validation, access-control bypass, restricted datasets, or indiscriminate scraping.

## Lot 01 — Modular core, persistence, provenance, and retention

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Establish the canonical model and persistence foundation shared by all later workflows.

**Dependencies:** Lot 00.

**Deliverables:** Modular-monolith boundaries; organization, evidence, observation, suppression, retention, and metrics modules; PostgreSQL models; reversible Alembic migrations; UTC timestamp rules; deterministic IDs; provenance envelope; API factory; local Docker environment.

**Tests:** Domain invariants; persistence constraints; identity stability; retention and suppression; API health; migration `upgrade -> downgrade -> upgrade`.

**Exit gate:** A clean installation starts, persists evidence with lineage, and removes or suppresses governed data without exposing raw identifiers.

**Non-goals:** External commercial connectors, browser automation, search indexing, or CRM synchronization.

## Lot 02 — Durable scheduler, worker, checkpoints, and recovery

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Convert collection into a durable, idempotent, observable, and recoverable execution pipeline.

**Dependencies:** Lots 00–01.

**Deliverables:** Versioned schedules; deterministic slots; PostgreSQL queue; bounded leases; transactional claims; checkpoints; retry policy; circuit breaker; dead letters; lease recovery; scheduler/worker commands; operational metrics; durable CISA KEV path.

**Tests:** Duplicate scheduling; concurrent claim; expired lease; late completion; retry timing; circuit lifecycle; dead letter; rollback preserving checkpoint; worker interruption.

**Exit gate:** Replay or interruption cannot duplicate observations, lose checkpoints, or record false success.

**Non-goals:** Premature Redis, microservices, or unbounded parallel collection.

## Lot 03 — Evidence-backed opportunity engine and analyst Inbox

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Turn normalized evidence into explainable, persistent, human-reviewed commercial opportunities.

**Dependencies:** Lots 00–02.

**Deliverables:** Commercial signals; need hypotheses; versioned SIEM/SOC score; opportunity persistence; review actions; immutable review history; list/detail APIs; Next.js Inbox; partial/stale/error states; preservation of analyst overrides.

**Tests:** Signal-to-opportunity workflow; scoring bounds; explanations; freshness decay; corroboration; idempotent recalculation; state preservation; API contracts; persisted UI behavior.

**Exit gate:** Every visible opportunity is linked to evidence, explainable, reviewable, and impossible to create directly from the browser without backend evidence.

**Non-goals:** Autonomous emails, hidden scoring, or automatic sales decisions.

## Lot 04 — TED European procurement signals

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Produce real buying-intent signals from the official European procurement API.

**Dependencies:** Lots 00–03.

**Deliverables:** TED Search API client; selected fields; content-type and size limits; strict schemas; bounded queries; local cyber relevance; deterministic identities; checkpoint; transactional Inbox projection; typed errors; no full-document storage.

**Tests:** Client; schema; query; mapper; irrelevant notice; checkpoint; HTTP classification; policy-before-network; rollback; idempotent persistent projection.

**Exit gate:** A relevant TED notice creates exactly one traceable opportunity and projection failure cannot advance its checkpoint.

**Non-goals:** Page scraping, document mirroring, or contact-block collection.

## Lot 05 — BOAMP French procurement and executable architecture gates

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Add official French procurement signals and prevent maintainability regressions automatically.

**Dependencies:** Lots 00–04.

**Deliverables:** BOAMP/DILA Explore connector; bounded dated pagination; overflow refusal; notice/rectification/cancellation/result/deadline logic; actionable-only projection; shared procurement taxonomy; repository split; duplicate-definition gate; 400-line application-file gate; separated test suites.

**Tests:** Schema variants; pagination; overflow; notice types; deadlines; cancellation/result exclusion; checkpoint rollback; Inbox integration; architecture constraints.

**Exit gate:** BOAMP produces traceable actionable opportunities and CI blocks duplicate definitions or oversized application modules.

**Non-goals:** DECP history, every French buyer portal, or weakened architecture standards.

## Lot 06 — Greenhouse public cyber hiring signals

**Status:** `IMPLEMENTED_VALIDATED`

**Objective:** Add the first official ATS connector and use hiring evidence without collecting candidate data.

**Dependencies:** Lots 00–05.

**Deliverables:** Approved-board registry; public GET-only Greenhouse client; strict schemas; bounded JSON; in-memory HTML normalization; cyber-role taxonomy; deterministic job fingerprints and IDs; per-board/job checkpoint; new/changed observation logic; active-job refresh; removed-job expiry; mutable idempotent signal upsert; transaction-safe Inbox projection; dialect-safe UTC persistence; explicit architecture, complexity, layering, release, roadmap, and network-free unit-test gates.

**Tests:** Registry; invalid/duplicate tokens; HTML cleanup; unsafe response; strict timestamp schema; false-positive rejection; new/changed/unchanged/removed jobs; nested checkpoints; HTTP 404/429/5xx; mutable upsert; ORM refresh; UTC across SQLite/PostgreSQL; rollback; persistent Inbox projection; architecture contracts.

**Exit gate:** One final SHA passes all backend/frontend gates; a modified job updates one signal and one opportunity; no candidate, application, email, resume, or raw HTML is persisted.

**Non-goals:** Application submission, candidate records, arbitrary career-page crawling, or inferring a named decision maker from a listing.

## Lot 07 — Multi-ATS hiring-source expansion

**Status:** `PLANNED_LOCKED`

**Objective:** Add additional approved ATS providers behind one canonical job-signal contract.

**Dependencies:** Lot 06.

**Deliverables:** Provider reviews for Lever, SmartRecruiters, Teamtailor, Workable, and other documented APIs; provider registries; common canonical job model; shared contract suite; normalized location/department/type/seniority; checkpoint/removal logic; cross-provider deduplication; source-health metrics.

**Tests:** Common adapter contract; provider fixtures; redirects; pagination; removal; duplicate posting; provider migration; policy denial; schema drift; cross-source deduplication.

**Exit gate:** At least two additional approved ATS providers produce identical canonical behavior without provider schemas entering scoring or persistence.

**Non-goals:** Unsupported-page scraping or candidate/profile collection.

## Lot 08 — French and European organization identity foundation

**Status:** `PLANNED_LOCKED`

**Objective:** Resolve buyers and employers to reliable legal entities and group identifiers.

**Dependencies:** Lots 01, 04–07.

**Deliverables:** SIRENE/API Recherche Entreprises; approved INPI/RNE data; BODACC metadata; GLEIF; SIREN/SIRET/LEI/company-number fields; aliases; legal status; non-diffusion handling; evidence-backed merge candidates.

**Tests:** Identifier validation; legal-unit versus establishment; non-diffusion; dissolved entity; registry conflict; alias lineage; false-merge prevention.

**Exit gate:** Organizations link to official identities with explainable confidence and ambiguous candidates remain human-reviewed.

**Non-goals:** Unnecessary personal shareholder enrichment.

## Lot 09 — Public-procurement expansion and buyer history

**Status:** `PLANNED_LOCKED`

**Objective:** Distinguish current buying intent from historical contracts and likely renewal context.

**Dependencies:** Lots 04–05 and 08.

**Deliverables:** DECP review/connector; BOAMP results; TED awards/amendments; buyer history; amount/currency/lot/incumbent fields where published; renewal estimates; optional PLACE, UK, SAM.gov, and regional sources after separate approval; notice-award-contract graph.

**Tests:** Notice-to-award linkage; chronology; currency; duplicate publication; amendment; cancellation; renewal estimate; missing buyer ID; conflicting sources.

**Exit gate:** Current opportunities and historical context are clearly separated and estimates are labeled as estimates.

**Non-goals:** Automatic bidding or restricted-document downloads.

## Lot 10 — Vulnerability intelligence enrichment

**Status:** `PLANNED_LOCKED`

**Objective:** Build a reconciled vulnerability knowledge layer for later technology and incident correlation.

**Dependencies:** Lots 01–03.

**Deliverables:** NVD; CVE.org; CISA KEV history; FIRST EPSS history; OSV; GitHub advisories; canonical aliases; CVSS/CWE/products/references; affected ranges; updates/retractions; source precedence.

**Tests:** Alias merge; conflicting CVSS; EPSS history; KEV changes; range parsing; malformed records; freshness; precedence; retraction.

**Exit gate:** Vulnerability facts reconcile across primary sources without implying that any organization is exposed.

**Non-goals:** Exploit execution, credential testing, or intrusive validation.

## Lot 11 — Vendor advisories and product-to-organization matching

**Status:** `PLANNED_LOCKED`

**Objective:** Add vendor-specific affected-version precision and explicit match uncertainty.

**Dependencies:** Lots 10 and 15.

**Deliverables:** Prioritized PSIRT connectors; advisory/CVE/product mapping; fixed versions and workarounds; supersession/retraction; product identifiers; version-range evaluator; family/exact-product/exact-version confidence levels.

**Tests:** Version ranges; affected/not-affected/unknown; aliases; superseded advisory; malformed version; confidence downgrade; family-only false certainty prevention.

**Exit gate:** Risk signals expose exact match level and never present a family-level observation as a confirmed vulnerable version.

**Non-goals:** Active scanning or proof-of-concept exploitation.

## Lot 12 — Incident and ransomware claim evidence

**Status:** `PLANNED_LOCKED`

**Objective:** Track public incident and extortion claims with corrections and evidence levels.

**Dependencies:** Lots 00–03, 08, and 13.

**Deliverables:** Approved aggregators; official statements; authority/regulatory confirmation; claim states for allegation, report, confirmation, inference, dispute, retraction, duplicate, and false attribution; timelines; actor aliases; minimal metadata; analyst review.

**Tests:** Claim transitions; conflicts; duplicate victim; ambiguous organization; retraction; confirmation; stale claim; source ranking; forbidden-content rejection.

**Exit gate:** Every incident distinguishes allegation from confirmation and stores no stolen or victim content.

**Non-goals:** Criminal-portal access, leaked data, negotiations, or credential material.

## Lot 13 — News, regulatory, and corporate-disclosure signals

**Status:** `PLANNED_LOCKED`

**Objective:** Detect material public events that affect cyber need, urgency, budget, or governance.

**Dependencies:** Lots 08 and 12.

**Deliverables:** Company pressrooms/RSS; SEC cyber disclosures; CNIL/ICO/HHS and sector regulators; licensed news metadata; event taxonomy; copyright-minimized summaries; clustering; corrections; event versus publication time.

**Tests:** Filing extraction; duplicate stories; event classification; correction; date distinction; storage limits; organization resolution; conflicting reports.

**Exit gate:** Material events become evidence without full-text mirroring or unqualified factual claims.

**Non-goals:** Paywall bypass or copyrighted-article storage.

## Lot 14 — Passive Internet-exposure observations

**Status:** `PLANNED_LOCKED`

**Objective:** Add lawful indexed observations of public assets without probing prospects directly.

**Dependencies:** Lots 00, 08, 10–11, and 16.

**Deliverables:** Approved passive providers; domain/certificate/IP/ASN/service/banner observations; quotas and retention; asset-to-organization confidence; last-seen decay; indexed-observation versus current-state distinction; direct-scan prohibition.

**Tests:** Policy and quota; pagination; stale data; certificate/domain linkage; shared hosting/CDN ambiguity; provider conflict; redirect block; no direct target connection.

**Exit gate:** Exposure hypotheses show provider, observation time, confidence, and uncertainty.

**Non-goals:** Port scans, vulnerability scans, authentication, or exploit validation.

## Lot 15 — Technographics and technology-confidence model

**Status:** `PLANNED_LOCKED`

**Objective:** Build a time-aware and evidence-ranked view of organizational technologies.

**Dependencies:** Lots 08, 11, and 14.

**Deliverables:** Approved technographic sources; canonical technology taxonomy; version precision; first/last seen; confidence by evidence type; contradictions; replacement history; lifecycle/end-of-support; distinction between website, exposed service, job requirement, and confirmed deployment.

**Tests:** Alias normalization; conflicting observations; stale replacement; shared infrastructure; version precision; weighting; false positive; vulnerable-version evidence requirement.

**Exit gate:** Analysts can see why a technology is believed present, when it was seen, and how strong the conclusion is.

**Non-goals:** Tracking-code installation or private-system fingerprinting.

## Lot 16 — Entity resolution and corporate graph

**Status:** `PLANNED_LOCKED`

**Objective:** Reconcile legal entities, brands, subsidiaries, domains, assets, and groups reversibly.

**Dependencies:** Lots 08–09 and 14–15.

**Deliverables:** Canonical identifiers; exact and scored matches; parent/subsidiary/brand/domain/certificate/ASN/acquisition relationships; review queue; reversible merge/split history; graph read model; lineage.

**Tests:** Similar names; shared address/domain; subsidiary; rename; acquisition; identifier conflict; merge reversal; benchmark precision/recall; false-merge threshold.

**Exit gate:** Exact high-confidence links automate safely and ambiguous links remain evidence-backed and reversible.

**Non-goals:** Opaque automatic merges without explanation or rollback.

## Lot 17 — Professional-role enrichment and compliance controls

**Status:** `PLANNED_LOCKED`

**Objective:** Identify relevant professional roles and permitted business channels with minimization and objection handling.

**Dependencies:** Lots 00, 08, and 16.

**Deliverables:** Role taxonomy; approved official pages/reports/conferences/GitHub/licensed providers; isolated professional-contact model; source/legal basis/purpose/retention/confidence; suppression; generic mailbox preference; correction/deletion propagation; controlled exports.

**Tests:** Professional/private distinction; purpose compatibility; suppression; deletion; stale role; duplicate person; generic mailbox; export redaction; unauthorized provider block.

**Exit gate:** No contact enters an export without provenance, lawful purpose, retention, and suppression checks.

**Non-goals:** Home addresses, family details, personal phones, dating/social profiles, or scraped LinkedIn profiles.

## Lot 18 — Analyst research and safe search-query workflows

**Status:** `PLANNED_LOCKED`

**Objective:** Make public research reproducible while preventing unsafe automation or sensitive ingestion.

**Dependencies:** Lots 00, 08, and 13–17.

**Deliverables:** Research cases; hypotheses; approved search APIs/manual workflows; query templates; result metadata and hashes; sensitive-result review queue; OSINT Framework candidate classification; no automatic secret/private download; audit trail.

**Tests:** Query escaping; host filtering; prohibited category; sensitive-result pause; duplicate result; source removal; analyst history; restricted-download prevention.

**Exit gate:** Evidence discovery is reproducible and unsafe or sensitive paths stop for human review.

**Non-goals:** Broad people enumeration, face search, account takeover research, or access-control circumvention.

## Lot 19 — Advanced scoring, calibration, and explainability

**Status:** `PLANNED_LOCKED`

**Objective:** Prioritize opportunities using independent signal families with transparent uncertainty.

**Dependencies:** Lots 07–18.

**Deliverables:** Versioned feature registry; service fit, urgency, exploitation, recency, importance, intent, contact, and evidence components; uncertainty/staleness/legal penalties; source-family independence; calibration dataset; drift monitoring; explanations; shadow evaluation.

**Tests:** Bounds; monotonicity; stale decay; contradiction; corroboration; legal veto; replay; version migration; override preservation; regression benchmark.

**Exit gate:** A new score version improves the approved benchmark, remains explainable, and can be rolled back.

**Non-goals:** Opaque autonomous lead selection.

## Lot 20 — CRM synchronization and commercial workflow

**Status:** `PLANNED_LOCKED`

**Objective:** Synchronize analyst-approved opportunities with HubSpot or Salesforce safely and idempotently.

**Dependencies:** Lots 03, 17, and 19.

**Deliverables:** Provider clients and shared commands; secret isolation; organization/contact/opportunity mapping; external IDs; conflict policy; human-approved staged export; sync/replay/audit; suppression propagation; dry-run/sandbox.

**Tests:** Authorization; mapping; idempotency; duplicate record; conflict; rate limit; partial failure; replay; suppression; sandbox; rollback.

**Exit gate:** One reviewed opportunity reaches an approved CRM sandbox exactly once and no message is sent automatically.

**Non-goals:** Autonomous sequences, covert tracking, or overriding CRM edits without policy.

## Lot 21 — Full analyst workspace and operational UX

**Status:** `PLANNED_LOCKED`

**Objective:** Provide an end-to-end investigation, triage, source-health, and workflow interface.

**Dependencies:** Lots 08–20.

**Deliverables:** Organization 360; evidence timeline/graph; technology/vulnerability/incident/procurement/hiring/contact views; saved filters; bulk triage; research workspace; source/checkpoint health; score comparison; compliance indicators; accessible loading/partial/stale/error states.

**Tests:** Components; API contracts; end-to-end workflows; accessibility; large timelines; stale data; source outage; concurrent analyst edits; audit display.

**Exit gate:** Analysts can qualify an opportunity without hidden database or log access.

**Non-goals:** Replacing the CRM or exposing restricted raw payloads.

## Lot 22 — Data quality, reconciliation, and lineage controls

**Status:** `PLANNED_LOCKED`

**Objective:** Detect silent source drift, duplicates, missing data, and lineage breaks before publication.

**Dependencies:** Lots 08–21.

**Deliverables:** Quality rules; population/freshness/schema/volume baselines; observation-to-opportunity lineage validation; reconciliation reports; quarantine; backfill/replay controls; quality incidents; regression datasets.

**Tests:** Volume drift; missing field; duplicate spike; lineage break; replay; backfill; contradiction; quarantine release; release regression.

**Exit gate:** Parser or mapping regressions fail visibly before deployment or opportunity publication.

**Non-goals:** Automatically lowering thresholds to hide problems.

## Lot 23 — Isolated browser and download-quarantine runtime

**Status:** `DEFERRED`

**Objective:** Support an explicitly approved JavaScript/authenticated source only when API, feed, export, and static HTTP options are insufficient.

**Dependencies:** Lots 00, 02, 22, and explicit source authorization.

**Deliverables:** Isolated browser worker; narrow port; host/path/page/time/download budgets; MFA/CAPTCHA/terms safe pause; session isolation; quarantine; type validation; archive limits; scanning; redacted traces; kill switch.

**Tests:** Local emulated pages; cross-domain block; expired session; MFA/CAPTCHA; selector drift; crash/restart; context isolation; spoofed file; archive bomb; scanner outage; cleanup.

**Exit gate:** One approved source runs without bypass behavior, unrestricted download, or hidden failure.

**Non-goals:** Generalized browser scraping, CAPTCHA solving, cookie reuse, or access-control bypass.

## Lot 24 — Supply-chain, release provenance, and repository protection

**Status:** `PLANNED_LOCKED`

**Objective:** Make installs, builds, releases, and GitHub governance reproducible and tamper-evident.

**Dependencies:** All implemented code lots.

**Deliverables:** Deterministic Python lockfile; verified frontend lockfile; `npm ci`; Python/npm SBOMs; checksums/attestations; actions pinned by SHA; CODEOWNERS; protected `main`; secret scanning; release/rollback/dependency/secret runbooks.

**Tests:** Two clean installs; lock drift; SBOM contents; artifact checksum; action pinning; rollback rehearsal; secret fixture detection.

**Exit gate:** A release rebuilds from source with the same dependencies and required GitHub checks cannot be bypassed.

**Non-goals:** Claiming manual repository protections are active before verification.

## Lot 25 — Observability, performance, resilience, and recovery

**Status:** `PLANNED_LOCKED`

**Objective:** Prove correctness, diagnosability, and recoverability under production load and dependency failure.

**Dependencies:** Lots 02–24.

**Deliverables:** Structured logs/metrics/traces; redaction; freshness/SLA dashboards; queue/retry/circuit/dead-letter metrics; latency budgets; quota monitoring; backups/restores; disaster recovery; chaos scenarios; capacity thresholds; alert ownership/runbooks.

**Tests:** Load; soak; worker kill; database interruption; provider 429/5xx; duplicate delivery; clock skew; backup restore; stale source; partial UI; resource limits.

**Exit gate:** Service objectives are met, backup restoration succeeds, and injected failures preserve invariants.

**Non-goals:** Redis, OpenSearch, or microservices without measured need.

## Lot 26 — Controlled pilot, production gate, and premium scale

**Status:** `PLANNED_LOCKED`

**Objective:** Move from engineering validation to a governed analyst pilot and evidence-based production expansion.

**Dependencies:** Lots 00–25, excluding deferred Lot 23 unless a pilot source requires it.

**Deliverables:** Pilot tenant and roles; approved source portfolio; privacy/retention review; analyst training; quality/precision/review-time/conversion/cost metrics; false-positive and false-merge review; go/no-go checklist; rollback; production deployment/support; premium-provider evaluation and scale plan.

**Tests:** Pilot replay; authorization; deletion/suppression; source outage; restore; load; analyst workflow; CRM dry run; quality benchmark; operational tabletop.

**Exit gate:** A formal `GO`, `CONDITIONAL_GO`, or `NO_GO` decision is recorded with evidence and rollback has been rehearsed.

**Non-goals:** Uncontrolled source growth, autonomous prospecting, or premium purchases without measured value and legal review.

## Phase promotion record

For each lot promoted to `IMPLEMENTED_VALIDATED`, its closing pull request records the lot number, final SHA, CI run, test count, line/branch coverage, Mypy file count, migration result, dependency audits, frontend typecheck/build, data limitations, and next locked lot.
