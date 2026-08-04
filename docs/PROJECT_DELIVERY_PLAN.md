# Project Delivery Plan

## Purpose

This is the authoritative production roadmap for Cyber Intelligence Platform.

The product is a standalone cyber revenue-intelligence and commercial-operations system. Its purpose is not to accumulate the largest possible volume of OSINT records. Its purpose is to discover organizations with evidence-backed cybersecurity needs, explain why they may need a service or product, identify the correct professional context, and let analysts manage the opportunity inside the platform.

A lot is complete only when one final commit passes every applicable backend, frontend, architecture, migration, security, privacy, source-governance, data-quality, documentation, and rollback gate.

The source-to-opportunity design is defined in [`COMMERCIAL_INTELLIGENCE_INTEGRATION_ARCHITECTURE.md`](COMMERCIAL_INTELLIGENCE_INTEGRATION_ARCHITECTURE.md). The OSINT source families are defined in [`OSINT_COLLECTION_CATALOG.md`](OSINT_COLLECTION_CATALOG.md) and [`LIVE_CYBER_THREAT_SOURCE_CATALOG.md`](LIVE_CYBER_THREAT_SOURCE_CATALOG.md).

## Status vocabulary

- `IMPLEMENTED_VALIDATED`: implementation passed its complete exit gate.
- `IN_PROGRESS`: implementation is active but not finally validated.
- `PLANNED_LOCKED`: scope, dependencies, non-goals, and exit criteria are defined; code has not started.
- `BLOCKED`: an external authorization, legal, product, or technical dependency prevents execution.
- `DEFERRED`: intentionally postponed without blocking later lots that explicitly exclude it.

## Delivery rules

- Lot numbers are continuous and never reused.
- Completed lot numbers are immutable.
- Each lot has one primary business outcome.
- Code for a new lot starts from the merged `main` commit of the previous implemented lot.
- Source governance and provider onboarding are positive before network access.
- A source catalog entry is not an executable adapter.
- Every executable adapter declares backfill, incremental, lookup, webhook, and refresh capabilities explicitly.
- Provider payloads never write directly to company, score, alert, or opportunity tables.
- Evidence, claims, observations, resolved facts, signals, hypotheses, and analyst decisions remain distinct.
- Duplicate reporting increases corroboration; it does not duplicate entities, incidents, signals, alerts, or opportunities.
- Corrections, retractions, suppression, deletion, and authorization expiry propagate to all derived data.
- Every source lot includes commercial-usefulness tests, not only parser and coverage tests.
- Historical backfills must not flood the current analyst Inbox.
- Public or licensed data is minimized. Credentials, victim files, private communications, private-life data, and access-control bypasses are excluded.
- Any later commit invalidates an earlier validation result.

## Product delivery stages

### Stage A — validated foundations and explicit intent

Lots 00–11 establish governance, persistence, durable collection, company identity, provider onboarding, the source-portfolio runtime, and the highest-value explicit procurement signals.

### Stage B — broad company and cyber evidence

Lots 12–19 ingest public corporate evidence, vulnerabilities, incidents, telemetry, exposure, advisories, regulatory events, and provider relationships.

### Stage C — resolution, professional context, and conditional sources

Lots 20–23 build the temporal knowledge graph, professional organization context, approved premium/community sources, and reproducible research workflows.

### Stage D — commercial intelligence and analyst operations

Lots 24–27 fuse evidence into need hypotheses, calibrate scoring, deliver native commercial operations, and present the complete company workspace.

### Stage E — production assurance

Lots 28–32 enforce data quality, supply-chain security, resilience, optional browser isolation, and the controlled production gate.

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
| 08 | French and European organization identity foundation | `IMPLEMENTED_VALIDATED` |
| 09 | Official provider onboarding and secret lifecycle | `IN_PROGRESS` |
| 10 | Source portfolio runtime, backfill, freshness, and source health | `PLANNED_LOCKED` |
| 11 | Procurement history, providers, contracts, and renewal timing | `PLANNED_LOCKED` |
| 12 | Corporate public footprint, documents, search, and archives | `PLANNED_LOCKED` |
| 13 | Vulnerability knowledge and exploitation-state reconciliation | `PLANNED_LOCKED` |
| 14 | Live incidents, ransomware claims, and official confirmation | `PLANNED_LOCKED` |
| 15 | Malicious infrastructure, phishing, IOC, and attack telemetry | `PLANNED_LOCKED` |
| 16 | Passive exposure and technographic observations | `PLANNED_LOCKED` |
| 17 | Vendor advisories, product versions, and applicability | `PLANNED_LOCKED` |
| 18 | News, regulatory, corporate-disclosure, and change signals | `PLANNED_LOCKED` |
| 19 | Providers, customers, partners, and supply-chain relationships | `PLANNED_LOCKED` |
| 20 | Entity resolution and temporal corporate knowledge graph | `PLANNED_LOCKED` |
| 21 | Professional organization maps, contacts, and public community signals | `PLANNED_LOCKED` |
| 22 | Conditional, premium, LinkedIn, Discord, and BrixHub integrations | `PLANNED_LOCKED` |
| 23 | Analyst research and governed OSINT catalog orchestration | `PLANNED_LOCKED` |
| 24 | Signal fusion, need hypotheses, and commercial taxonomy | `PLANNED_LOCKED` |
| 25 | Advanced scoring, calibration, explainability, and feedback | `PLANNED_LOCKED` |
| 26 | Native commercial operations, alerts, tasks, and engagement | `PLANNED_LOCKED` |
| 27 | Complete company intelligence and analyst workspace | `PLANNED_LOCKED` |
| 28 | Data quality, reconciliation, lineage, and publication gates | `PLANNED_LOCKED` |
| 29 | Supply-chain, release provenance, and repository protection | `PLANNED_LOCKED` |
| 30 | Observability, performance, resilience, and recovery | `PLANNED_LOCKED` |
| 31 | Isolated browser and download-quarantine runtime | `DEFERRED` |
| 32 | Controlled pilot and production gate | `PLANNED_LOCKED` |

## Lots 00–08 — Validated foundation

### Lot 00 — Product, legal, and source-governance foundation

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** No collector can execute without a positive source-policy decision. Source owner, purpose, hosts, paths, data categories, automation, quota, retention, attribution, raw storage, review, and quarantine are executable controls.

### Lot 01 — Modular core, persistence, provenance, and retention

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Canonical organizations, evidence, observations, suppression, retention, PostgreSQL persistence, reversible migrations, deterministic identities, UTC time, and provenance envelopes exist behind modular boundaries.

### Lot 02 — Durable scheduler, worker, checkpoints, and recovery

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Versioned schedules, deterministic slots, durable queueing, leases, transactional checkpoints, retries, circuits, dead letters, interruption recovery, and source health prevent duplicate or false-success collection.

### Lot 03 — Evidence-backed opportunity engine and analyst Inbox

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Normalized evidence can produce explainable, versioned, persistent, human-reviewed opportunities without browser-created evidence or opaque scoring.

### Lot 04 — TED European procurement signals

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Relevant official European procurement notices create exactly one traceable commercial signal and opportunity with strict schemas, bounded collection, checkpoints, and no document mirroring.

### Lot 05 — BOAMP French procurement and executable architecture gates

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Actionable French procurement notices integrate with the same evidence and opportunity path, while CI enforces architecture, duplicate-definition, and maintainability constraints.

### Lot 06 — Greenhouse public cyber hiring signals

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Approved public job boards produce mutable, deterministic cyber hiring signals without candidate data, applications, private email, resumes, or raw HTML persistence.

### Lot 07 — Lever and SmartRecruiters multi-ATS expansion

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Three ATS providers use one canonical public-job contract, update changed jobs without duplication, expire withdrawn jobs, and keep ambiguous cross-provider matches separate.

### Lot 08 — French and European organization identity foundation

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** API Recherche d'entreprises, GLEIF, and BODACC resolve legal units, establishments, SIREN, SIRET, LEI, aliases, statuses, headquarters, parent relationships, claims, conflicts, and merge candidates. Exact identifiers can link automatically; ambiguous matches require review.

**Validation baseline:** Version `0.9.0`; reversible migrations; complete backend and frontend gates passed on the delivered lot.

## Lot 09 — Official provider onboarding and secret lifecycle

**Status:** `IN_PROGRESS`

**Primary business outcome:** Make approved source activation operable without exposing raw secrets to ordinary users.

**Dependencies:** Lots 00–08.

**Deliverables:** Provider catalog; onboarding state machine; public-source automatic connection; official account and authorization links; secret references; reference verification; provider-specific connectivity contracts; rotation, expiry, revocation, and audit; protected Sources control plane; anonymous public product access remains separate.

**Required tests:** State transitions; source quarantine; raw-secret rejection; reference redaction; public-source connection; provider approval states; revocation; migration reversal; API/UI contracts; anonymous visitor denial for administrative actions.

**Exit gate:** Every currently executable source has a consistent onboarding state, secrets never enter Git/database/API/frontend/logs, and one final SHA passes all repository gates.

**Non-goals:** Pretending every provider exposes automatic registration; bypassing CAPTCHA, MFA, KYC, payment, approval, or access controls.

## Lot 10 — Source portfolio runtime, backfill, freshness, and source health

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Turn the OSINT catalogs into an executable, measurable source portfolio without writing one-off orchestration for every provider.

**Dependencies:** Lots 00–09.

**Deliverables:** Machine-readable source catalog; adapter capability manifest; common adapter SDK; historical backfill partitions; incremental cursor, conditional request, webhook, lookup, and priority-refresh modes; source cost and value metadata; freshness classes; schema-version registry; source health; volume and drift baselines; authorization-expiry shutdown; catalog import from OSINT Framework as non-executable candidates.

**Required tests:** Common adapter contract; backfill/incremental convergence; replay idempotence; cursor rollback; schema drift; quota and cost budgets; stale-state transitions; source disablement; historical data not creating duplicate current alerts.

**Exit gate:** A new adapter can plug into one reviewed lifecycle from catalog candidate through health-monitored canonical records.

**Non-goals:** Implementing every catalog source in one lot.

## Lot 11 — Procurement history, providers, contracts, and renewal timing

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Identify explicit current demand, incumbents, provider displacement opportunities, and evidence-backed renewal windows.

**Dependencies:** Lots 04–05, 08, and 10.

**Deliverables:** DECP; TED and BOAMP awards, results, amendments, cancellations, and chronology; buyers, lots, amounts, currencies, awardees, subcontractors, incumbent hypotheses, contract start/end dates, renewal estimates, and cyber service classification.

**Required tests:** Notice-to-award linkage; amendment chronology; duplicate publication; provider identity; currency; cancellation; renewal uncertainty; current opportunity versus historical contract separation.

**Exit gate:** Analysts can distinguish open procurement, confirmed contract history, published provider relationship, and estimated renewal with provenance and confidence.

**Commercial value:** Highest-priority signals for organizations already buying or preparing to buy cybersecurity services.

## Lot 12 — Corporate public footprint, documents, search, and archives

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Build a reproducible public evidence map of each organization and discover projects, technologies, providers, changes, and contact paths not present in structured registries.

**Dependencies:** Lots 08 and 10.

**Deliverables:** Approved sitemaps, RSS, Atom, structured data, public corporate pages, career pages, engineering blogs, public documentation, GitHub/GitLab organizations, reports, presentations, public PDFs, Common Crawl, Wayback/CDX, approved search APIs, dork templates, bounded domain/path crawl, content hashes, copyright-minimized extraction, and historical page evidence.

**Required tests:** Crawl scope and depth; canonical URLs; robots/terms policy; MIME and size; duplicate pages; redirects; archive chronology; changed document; restricted result quarantine; no accidental-secret download; source-to-organization resolution.

**Exit gate:** An organization workspace can show its public footprint and extracted business/cyber claims without indiscriminate mirroring or page-view crawling.

**Commercial value:** Reveals transformations, named products, public architecture, support needs, projects, and professional contact routes.

## Lot 13 — Vulnerability knowledge and exploitation-state reconciliation

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Create a reliable vulnerability layer that can later determine product risk without equating publication with organizational exposure.

**Dependencies:** Lots 01–03 and 10.

**Deliverables:** CVE.org; NVD; CISA KEV history; EPSS history; OSV; GitHub advisories; CIRCL Vulnerability-Lookup; aliases; CVSS, CWE, products, ranges, references, proof-of-concept context, observed exploitation state, updates, supersession, and retractions.

**Required tests:** Alias reconciliation; conflicting CVSS; affected ranges; KEV/EPSS history; malformed versions; source precedence; proof-of-concept versus observed exploitation distinction; retraction.

**Exit gate:** Vulnerability facts reconcile across sources and cannot independently claim that a prospect is vulnerable.

## Lot 14 — Live incidents, ransomware claims, and official confirmation

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Detect organizations with current cyber urgency while separating attacker allegations from confirmations and corrections.

**Dependencies:** Lots 08 and 10.

**Initial sources:** Ransomware.live, RansomLook, Ransomwhere.org, CISA StopRansomware, CERT-FR, official company statements, regulator notices, approved licensed aggregators, and anonymized historical negotiation research.

**Deliverables:** Incident claim model; actor aliases; victim organization matching; timelines; duplicate clustering; allegation, public report, official confirmation, regulatory notice, dispute, denial, retraction, and false-attribution states; minimal public metadata; historical backfill and frequent incremental refresh.

**Required tests:** Duplicate victim; ambiguous organization; actor claim versus denial; confirmation; correction; retraction; stale claim; forbidden victim-content rejection; historical negotiation corpus isolation; source ranking.

**Exit gate:** Every incident displays claim type, source, confidence, corroboration, chronology, and current resolution without storing stolen files or private negotiations.

**Commercial value:** High-urgency incident response, recovery, hardening, resilience, monitoring, audit, and regulatory-support opportunities.

## Lot 15 — Malicious infrastructure, phishing, IOC, and attack telemetry

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Add campaign and sector context that improves urgency and relevance without turning global telemetry into unsupported company accusations.

**Dependencies:** Lots 10 and 13.

**Initial sources:** ThreatFox, URLhaus, Feodo Tracker, SSLBL, MalwareBazaar metadata, AlienVault OTX, DShield, Cloudflare Radar, PhishTank, OpenPhish, approved Spamhaus datasets, and later licensed CrowdSec, GreyNoise, VirusTotal, MISP, or OpenCTI feeds.

**Deliverables:** IOC, malicious URL/domain, C2, phishing, scanner, exploitation, BGP anomaly, outage, and campaign observations; STIX/TAXII mappings; indicator lifecycle; first/last seen; confidence; source and sensor scope; expiry; campaign and CVE relationships.

**Required tests:** Indicator normalization; active/inactive transition; duplicate feeds; sensor-scope labeling; false company linkage prevention; expiration; TAXII replay; oversized feed; provider outage; malicious binary exclusion.

**Exit gate:** Telemetry enriches threats, products, sectors, and incidents but cannot alone assert that a named organization was compromised.

## Lot 16 — Passive exposure and technographic observations

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Identify fresh, passive, evidence-backed external technology and asset hypotheses relevant to services and products.

**Dependencies:** Lots 08, 10, and 13.

**Candidate sources:** Censys, Shodan, BinaryEdge, Netlas, ZoomEye, FOFA, ONYPHE, LeakIX, Criminal IP, Hunter.how, SecurityTrails, DomainTools, WhoisXML, RDAP, Certificate Transparency, urlscan.io, BuiltWith, Wappalyzer, HTTP Archive, passive DNS, BGP, ASN, and licensed internet-measurement datasets.

**Deliverables:** Domains, certificates, IPs, ASNs, services, banners, technologies, versions, first/last seen, observation method, provider scope, shared-hosting/CDN uncertainty, asset-to-organization confidence, and last-seen decay.

**Required tests:** No direct prospect connection; host and provider policy; stale data; shared infrastructure; certificate/domain linkage; conflicting providers; version precision; quotas; asset false-link datasets.

**Exit gate:** Exposure and technology hypotheses show exactly who observed what, when, how precisely, and with what ownership confidence.

## Lot 17 — Vendor advisories, product versions, and applicability

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Convert vulnerability and technology evidence into precise, qualified product-risk hypotheses.

**Dependencies:** Lots 13 and 16.

**Deliverables:** Prioritized PSIRT connectors; advisory-to-CVE mapping; vendor/product/version taxonomy; fixed versions; workarounds; supersession; range evaluator; lifecycle/end-of-support; family, product, and exact-version match levels; exposure-signal generation.

**Required tests:** Affected/unaffected/unknown; version ranges; superseded advisory; malformed version; family-only downgrade; stale technology; contradictory evidence; applicable KEV; explanation completeness.

**Exit gate:** Every product-risk result exposes match precision and never presents family evidence as an exact vulnerable installation.

**Commercial value:** Patch governance, exposure review, compensating controls, architecture, managed detection, and remediation opportunities.

## Lot 18 — News, regulatory, corporate-disclosure, and change signals

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Detect events that create urgency, budget, governance, integration, or compliance needs.

**Dependencies:** Lots 08, 10, and 14.

**Deliverables:** Company pressrooms and RSS; SEC/market disclosures; CNIL, ICO, HHS, national regulators and authorities; CERT and law-enforcement announcements; licensed news metadata; acquisitions, expansions, funding, leadership, restructuring, cloud, data-center, and digital-transformation taxonomy; clustering; corrections; event time versus publication time.

**Required tests:** Primary versus secondary source; duplicate story; correction; date distinction; copyright storage limits; organization resolution; conflicting reports; event-to-need classification.

**Exit gate:** Material business and regulatory changes become traceable evidence and commercial signals without full-text news mirroring.

## Lot 19 — Providers, customers, partners, and supply-chain relationships

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Reveal incumbent providers, technology ecosystems, partnerships, dependencies, and relationship changes that shape commercial positioning.

**Dependencies:** Lots 08, 11–12, 16, and 18.

**Deliverables:** Vendor case studies; marketplace listings; partner directories; public customer stories; procurement-derived provider links; public supplier and integration references; relationship type; start/end evidence; confidence; historical and current state; replacement and consolidation hypotheses.

**Required tests:** Provider alias normalization; current versus historical; circular source citation; duplicate case studies; source incentive penalty; contradictory relationship; subsidiary scope; replacement chronology.

**Exit gate:** Analysts can see why a provider/customer/partner relationship is believed present, its timeframe, and whether it is confirmed, published, probable, or historical.

## Lot 20 — Entity resolution and temporal corporate knowledge graph

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Link legal entities, brands, groups, domains, assets, providers, contracts, incidents, technologies, and people without unsafe merges.

**Dependencies:** Lots 08 and 11–19.

**Deliverables:** Candidate generation; identifier-first and evidence-weighted matching; corporate hierarchy; acquisitions; aliases; temporal relationships; reversible merge/split; conflict queues; source-specific claims; graph projections; organization and incident clustering.

**Required tests:** Similar names; subsidiaries; acquisitions; shared domains and infrastructure; exact and fuzzy identifiers; false merges; missed links; merge reversal; temporal validity; contradiction preservation.

**Exit gate:** Every accepted node and edge is evidence-backed, temporal, reversible, and reviewable; ambiguous relations remain candidates.

## Lot 21 — Professional organization maps, contacts, and public community signals

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Identify the professional buying context and weak public professional signals needed to route opportunities correctly.

**Dependencies:** Lots 08, 10, 12, and 20.

**Deliverables:** Professional identities; roles; departments; seniority; employment dates; buying-committee roles; public/licensed business email, role mailbox, switchboard, direct business number, and contact form; source, purpose, freshness, retention, correction, objection, and suppression; approved public Reddit/forum/community signals; organization-level trends; explicit self-declared professional affiliation; pseudonym retained unless the person publicly links it to a professional identity.

**Required tests:** Person/employment deduplication; professional/private classification; stale role; contact suppression; public affiliation evidence; weak community signal penalty; employer-technology false inference; pseudonym non-deanonymization; export minimization.

**Exit gate:** Every visible professional contact and role has provenance, permitted purpose, freshness, and suppression state; community data remains weak evidence until corroborated.

## Lot 22 — Conditional, premium, LinkedIn, Discord, and BrixHub integrations

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Add high-value sources that require licences, explicit platform authorization, consented installation, or unresolved provider review, using the same canonical contracts as public sources.

**Dependencies:** Lots 09–10 and 20–21.

**Deliverables:** Licensed-provider contract template; cost and quota controls; LinkedIn official scopes or licensed products only; Discord administrator-installed connectors or authorized exports only; commercial CTI providers; premium B2B data; BrixHub provider assessment; BrixHub historical import and incremental-refresh adapter only after approval; source-specific retention, deletion, field allowlists, and value measurement.

**Required tests:** Licence and authorization expiry; scope mismatch; account/tenant isolation; premium cost budget; permitted channels and fields; deletion propagation; historical import/resume; incremental convergence; prohibited-field rejection; unique commercial-value benchmark against existing sources.

**Exit gate:** Conditional sources are either approved and fully governed, or remain non-executable with an explicit blocker. BrixHub is never activated merely because it appears in the roadmap.

## Lot 23 — Analyst research and governed OSINT catalog orchestration

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Make broad public research reproducible, prioritized, and connected to company and opportunity workflows.

**Dependencies:** Lots 10, 12, and 20–22.

**Deliverables:** Research cases; reusable queries; saved results; OSINT Framework candidate import; source classification queue; research plans by organization; approved search APIs; bounded document discovery; manual-review tasks; accidental-sensitive-result quarantine; catalog health; duplicate/replacement tools; source-value comparison.

**Required tests:** Query templates; candidate deduplication; dead/redirected tool; ownership change; restricted result quarantine; no secret or exposed-file download; authorization expiry; research history; source recommendation based on entity gaps.

**Exit gate:** An analyst can reproduce why a source or query was used, what it found, what remains uncertain, and how it affected a commercial hypothesis.

## Lot 24 — Signal fusion, need hypotheses, and commercial taxonomy

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Convert the complete evidence portfolio into non-duplicated, service-specific, explainable cybersecurity needs.

**Dependencies:** Lots 03 and 11–23.

**Deliverables:** Canonical signal taxonomy; event clustering; corroboration and contradiction engine; source independence; active intervals; service/product fit; need hypotheses for procurement, renewal, incident response, SOC/SIEM, IAM, cloud, GRC, exposure, vulnerability remediation, integration, provider replacement, and transformation; deterministic signal and hypothesis identities; recalculation and invalidation.

**Required tests:** Same event from many sources; contradictory claims; stale decay; retraction; one event with several service fits; no duplicate opportunities; weak community or actor claim cannot independently confirm urgent need; explanation and evidence completeness.

**Exit gate:** Every commercial hypothesis explains why it exists, which evidence supports or contradicts it, when it expires, and which service motion it enables.

## Lot 25 — Advanced scoring, calibration, explainability, and feedback

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Prioritize the most commercially useful and defensible opportunities while preserving human control.

**Dependencies:** Lot 24.

**Deliverables:** Buying intent; urgency; service fit; contract timing; company fit; product risk; incident confidence; role/contact availability; evidence quality; source independence; freshness; uncertainty; legal-risk, contradiction, weak-source, and single-source penalties; calibration datasets; source incremental-value metrics; analyst outcomes; rollbackable score versions.

**Required tests:** Bounds; monotonicity; stale decay; contradiction; source independence; benchmark precision/recall; false urgency; source ablation; calibration; override preservation; explanation completeness.

**Exit gate:** A scoring version beats the previous benchmark, can be explained and rolled back, and does not optimize ingestion volume over accepted opportunity quality.

## Lot 26 — Native commercial operations, alerts, tasks, and engagement

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Let a team operate the complete commercial workflow inside Cyber Intelligence Platform.

**Dependencies:** Lots 03, 08, 21, and 25.

**Deliverables:** Rules; alerts; saved searches; watchlists; opportunity stages; ownership; assignments; tasks; reminders; queues; service-level targets; notes; research requests; buying-committee views; approved interaction and engagement history; audit; reversible transitions; dashboards; controlled import/export.

**Required tests:** Alert deduplication/reopening; stage transitions; task recurrence; assignment; concurrent edits; immutable history; suppression before contact use; deletion; dashboard consistency; anonymous public access versus protected operations.

**Exit gate:** A team can discover, qualify, assign, research, track, and close an opportunity with complete history and no external CRM dependency.

## Lot 27 — Complete company intelligence and analyst workspace

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Present one coherent company workspace that connects evidence to action without exposing raw provider data.

**Dependencies:** Lots 20–26.

**Deliverables:** Company 360; public footprint; legal/corporate graph; domains/assets; technologies/providers; vulnerabilities; incidents; tenders/contracts; recruitment; events; professional org map; contacts; evidence timeline; conflicts; source freshness; alerts; hypotheses; score explanation; opportunity; tasks; notes; engagement; saved layouts and filters.

**Required tests:** Loading, empty, partial, stale, conflicting, suppressed, unavailable, unauthorized, and success states; graph/timeline navigation; deep links; keyboard/responsive access; end-to-end alert-to-opportunity investigation.

**Exit gate:** An analyst can understand what happened, why it matters commercially, who may be relevant, and what action is next without direct database or log access.

## Lot 28 — Data quality, reconciliation, lineage, and publication gates

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Stop silent source, parser, entity, signal, and derived-data regressions before they reach users.

**Dependencies:** Lots 10–27.

**Deliverables:** Expected volume and field baselines; freshness thresholds; duplicate rates; lineage validation; source reconciliation; golden datasets; schema-drift alerts; quarantine; replay/backfill; correction propagation; derived-data invalidation; source incremental-value and false-urgency dashboards; publication gates.

**Required tests:** Parser regression; volume anomaly; missing fields; stale source; duplicate entity/signal/opportunity; broken lineage; false merge; replay; correction; deletion; score drift; source-ablation benchmark.

**Exit gate:** A silent data regression blocks publication and can be replayed, diagnosed, corrected, and audited.

## Lot 29 — Supply-chain, release provenance, and repository protection

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Make builds and releases reproducible, verifiable, and protected.

**Dependencies:** Lots 00–28.

**Deliverables:** Python lock; deterministic frontend install; SBOMs; checksums; attestations; pinned actions; CODEOWNERS; strict `main` protection; secret scanning; release and rollback procedures; artifact retention.

**Required tests:** Clean rebuild; dependency integrity; SBOM; secret fixture detection; protected-branch checks; artifact verification; rollback rehearsal.

**Exit gate:** A release can be rebuilt from source and cannot bypass mandatory checks.

## Lot 30 — Observability, performance, resilience, and recovery

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Prove the database-first collection and analyst product remains reliable under source growth and failures.

**Dependencies:** Lots 02–29.

**Deliverables:** Structured logs; traces; metrics; source freshness, cost, quota, queue, backfill, schema, and opportunity-value dashboards; alerts; backups; restore runbooks; load/soak tests; fault injection; degraded modes; capacity thresholds; recovery objectives.

**Required tests:** Provider outage; quota exhaustion; worker/database crash; duplicate delivery; large backfill; index failure; backup restore; degraded UI; recovery time; no false-success state.

**Exit gate:** Restore succeeds, invariants survive injected failures, and capacity limits are measured.

## Lot 31 — Isolated browser and download-quarantine runtime

**Status:** `DEFERRED`

**Primary business outcome:** Support specifically approved browser-only and export workflows when structured APIs, feeds, and bounded static HTTP are insufficient.

**Dependencies:** Lots 00, 09–10, 23, and 28–30.

**Deliverables:** Isolated browser workers; exact host/path allowlists; session isolation; page/time budgets; safe pause for provider challenges; download quarantine; archive limits; file validation; malware-safe processing; redacted evidence; kill switch.

**Required tests:** Navigation escape; redirect; session mixing; challenge pause; timeout; unsafe download; archive bomb; parser failure; secret redaction; kill switch.

**Exit gate:** Approved browser collection cannot bypass access controls, silently download unsafe content, or mix provider sessions.

**Non-goals:** Bot evasion, copied cookies, account rotation to evade limits, private-area access, or unrestricted crawling.

## Lot 32 — Controlled pilot and production gate

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Prove that the complete product finds useful clients and can be operated safely and reliably.

**Dependencies:** Lots 00–30. Lot 31 must be completed only if a pilot source requires it; otherwise it is explicitly excluded.

**Deliverables:** Controlled deployment; approved source portfolio; accountless public data plane where intended; protected administrative and commercial operations; privacy and retention review; analyst training; source and opportunity quality metrics; end-to-end workflows; operational runbooks; rollback; premium-source evaluation; explicit GO/CONDITIONAL_GO/NO_GO decision.

**Required tests:** Source-to-opportunity flow; accepted/rejected opportunity benchmarks; duplicate and false-urgency review; suppression/correction; source outage; restore; permissions; contact-purpose review; rollback; analyst acceptance.

**Exit gate:** Governance, evidence quality, commercial usefulness, security, resilience, and operating metrics support an explicit production decision.

**Non-goals:** Broad rollout based on record volume, unsupported coverage claims, or unresolved source and data-quality blockers.
