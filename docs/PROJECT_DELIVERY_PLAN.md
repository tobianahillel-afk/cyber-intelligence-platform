# Project Delivery Plan

## Purpose

This document is the authoritative production roadmap for Cyber Intelligence Platform.

The product is a standalone cyber revenue-intelligence and commercial-operations system. Its purpose is not to accumulate the largest possible volume of OSINT records. Its purpose is to discover organizations with evidence-backed cybersecurity needs, explain why they may need a service or product, identify the correct professional context, and let analysts manage the opportunity inside the platform.

A lot is complete only when one final commit passes every applicable backend, frontend, architecture, migration, security, privacy, source-governance, data-quality, documentation, and rollback gate.

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
- Source governance and provider onboarding must be positive before network access.
- A source catalog entry is not an executable adapter.
- Provider payloads never write directly to company, score, alert, or opportunity tables.
- Evidence, claims, observations, resolved facts, service mappings, signals, hypotheses, and analyst decisions remain distinct.
- Duplicate reporting increases corroboration; it does not duplicate entities, incidents, signals, alerts, or opportunities.
- Corrections, retractions, suppression, deletion, and authorization expiry propagate to derived data.
- Historical backfills must not flood the current analyst Inbox.
- Public or licensed data is minimized. Credentials, victim files, private communications, private-life data, active prospect scanning, and access-control bypasses are excluded.
- Every commercial lot covers the canonical service taxonomy rather than treating SIEM or SOC as the default need.
- Any later commit invalidates an earlier validation result; the final pull-request head must pass all gates.

## Product delivery stages

- **Stage A — foundations and explicit intent:** lots `00–11`.
- **Stage B — broad company and cyber evidence:** lots `12–19`.
- **Stage C — resolution, professional context, and conditional sources:** lots `20–23`.
- **Stage D — commercial intelligence and analyst operations:** lots `24–27`.
- **Stage E — production assurance:** lots `28–32`.

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
| 09 | Official provider onboarding and secret lifecycle | `IMPLEMENTED_VALIDATED` |
| 10 | Source portfolio runtime, backfill, freshness, and source health | `IMPLEMENTED_VALIDATED` |
| 11 | Procurement history, providers, contracts, and renewal timing | `IMPLEMENTED_VALIDATED` |
| 12 | Corporate public footprint, documents, search, and archives | `IMPLEMENTED_VALIDATED` |
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

## Lot 00 — Product, legal, and source-governance foundation

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Executable source policies control owner, purpose, hosts, paths, data categories, automation, quota, retention, attribution, raw storage, review, authorization, and quarantine before any collector can use the network.

## Lot 01 — Modular core, persistence, provenance, and retention

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Modular domain boundaries, PostgreSQL persistence, reversible migrations, canonical organizations, evidence, observations, suppression, retention, UTC timestamps, and provenance envelopes are implemented.

## Lot 02 — Durable scheduler, worker, checkpoints, and recovery

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Versioned schedules, durable jobs, leases, transactional checkpoints, retries, circuits, dead letters, interruption recovery, and source-health metrics prevent duplicate collection and false success.

## Lot 03 — Evidence-backed opportunity engine and analyst Inbox

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Normalized evidence can create persistent, explainable, versioned, human-reviewed opportunities with filters, detail views, score components, qualification, rejection, snooze, and analyst overrides.

## Lot 04 — TED European procurement signals

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Relevant official TED notices create deterministic procurement evidence, commercial signals, and opportunities through a bounded, checkpointed, replay-safe adapter without mirroring full notices.

## Lot 05 — BOAMP French procurement and executable architecture gates

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Relevant BOAMP notices use the same evidence-to-opportunity path while CI enforces dependency boundaries, module size, complexity, duplicate-definition, migration, and maintainability contracts.

## Lot 06 — Greenhouse public cyber hiring signals

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Approved Greenhouse boards produce mutable and deterministic public hiring signals without collecting applications, candidates, CVs, private emails, screening answers, or raw HTML.

## Lot 07 — Lever and SmartRecruiters multi-ATS expansion

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Greenhouse, Lever, and SmartRecruiters share one canonical public-job contract, update and expire postings idempotently, and keep ambiguous cross-provider matches reviewable.

## Lot 08 — French and European organization identity foundation

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Recherche d'entreprises, GLEIF, and BODACC resolve legal units, establishments, SIREN, SIRET, LEI, aliases, statuses, headquarters, parent relationships, registry claims, conflicts, and merge candidates; exact identifiers may link automatically while ambiguous cases require review.

## Lot 09 — Official provider onboarding and secret lifecycle

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** Provider onboarding supports public automatic connection, official human checkpoints, references to secrets rather than raw secret values, verification, rotation state, expiry, revocation, audit, protected APIs, and a Sources workspace. CAPTCHA, MFA, KYC, approval, payment, and access controls are never bypassed.

## Lot 10 — Source portfolio runtime, backfill, freshness, and source health

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** A common machine-readable source portfolio governs adapter capabilities, historical backfill, incremental refresh, conditional requests, priority refresh, immutable source records, transactional checkpoints, corrections, tombstones, retractions, freshness, health, drift, volume, quotas, costs, circuits, authorization expiry, pause, resume, and disablement.

## Lot 11 — Procurement history, providers, contracts, and renewal timing

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** DECP, TED, and BOAMP publications are reconciled into procurement procedures, awards, contracts, provider relationships, amendments, cancellations, amounts, currencies, confirmed dates, and explicitly uncertain renewal estimates across the complete cyber-service taxonomy. Historical backfill does not create false current opportunities.

## Lot 12 — Corporate public footprint, documents, search, and archives

**Status:** `IMPLEMENTED_VALIDATED`

**Outcome:** The software foundation for organization-bound public-web evidence is implemented: governed targets, policy-before-network, robots checks, bounded sitemap/page retrieval, immutable resources and versions, hashes, chronology, tombstones, minimized claims, search-result quarantine, protected APIs, and a Research workspace. Production activation remains a separate governance operation: the checked-in example target is disabled and unauthorized, no search or archive provider is connected, and merging the lot authorizes no real-world collection.

## Lot 13 — Vulnerability knowledge and exploitation-state reconciliation

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Build a reliable vulnerability layer without equating publication with organizational exposure.

**Dependencies:** Lots 01–03, 10, and 12.

**Deliverables:** CVE.org, NVD, CISA KEV history, EPSS history, OSV, GitHub advisories, CIRCL Vulnerability-Lookup, aliases, CVSS, CWE, products, affected ranges, references, exploitation state, updates, supersession, and retractions.

**Required tests:** Alias reconciliation, conflicting scores, affected ranges, malformed versions, KEV/EPSS history, source precedence, proof-of-concept versus observed exploitation, corrections, and retractions.

**Exit gate:** Vulnerability facts reconcile across sources and cannot independently claim that a prospect is vulnerable.

## Lot 14 — Live incidents, ransomware claims, and official confirmation

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Detect organizations with current cyber urgency while separating allegations, secondary reports, confirmations, denials, and corrections.

**Dependencies:** Lots 08, 10, 12, and 13.

**Deliverables:** Incident claims, actor aliases, victim matching, timelines, duplicate clustering, source ranking, allegation/report/confirmation/regulatory/denial/retraction states, bounded public metadata, historical backfill, and frequent refresh.

**Required tests:** Duplicate victims, ambiguous organizations, actor claim versus denial, official confirmation, stale claims, correction, retraction, forbidden victim-content rejection, and source ranking.

**Exit gate:** Every incident exposes claim type, source, confidence, corroboration, chronology, and resolution without storing stolen files or private negotiations.

## Lot 15 — Malicious infrastructure, phishing, IOC, and attack telemetry

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Add campaign and sector context without turning global telemetry into unsupported accusations against named organizations.

**Dependencies:** Lots 10 and 13–14.

**Deliverables:** IOC, malicious URL/domain, C2, phishing, scanning, exploitation, outage, and campaign observations; STIX/TAXII mappings; first/last seen; confidence; sensor scope; expiry; and campaign/CVE relations.

**Required tests:** Indicator normalization, active/inactive transitions, duplicate feeds, sensor scope, expiration, TAXII replay, oversized feeds, provider outages, false organization linkage, and malicious-binary exclusion.

**Exit gate:** Telemetry enriches threats and incidents but cannot alone assert that a named organization was compromised.

## Lot 16 — Passive exposure and technographic observations

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Identify fresh, passive, evidence-backed asset and technology hypotheses relevant to services and products.

**Dependencies:** Lots 08, 10, and 13.

**Deliverables:** Governed passive providers, domains, certificates, IPs, ASNs, services, banners, technologies, versions, first/last seen, observation method, provider scope, shared-hosting uncertainty, ownership confidence, and decay.

**Required tests:** No direct scanning, host and provider policy, stale data, shared infrastructure, certificate/domain linkage, provider conflict, version precision, quotas, and false-link datasets.

**Exit gate:** Every exposure hypothesis shows who observed what, when, through which passive method, and with what ownership and version confidence.

## Lot 17 — Vendor advisories, product versions, and applicability

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Convert vulnerability and technology evidence into precise, qualified product-risk hypotheses.

**Dependencies:** Lots 13 and 16.

**Deliverables:** Prioritized PSIRT connectors, advisory-to-CVE mappings, vendor/product/version taxonomy, fixed versions, workarounds, supersession, range evaluation, lifecycle state, and match precision.

**Required tests:** Affected/unaffected/unknown, version ranges, superseded advisories, malformed versions, family-only downgrade, stale technology, contradiction, applicable KEV, and explanation completeness.

**Exit gate:** Product-risk results expose match precision and never present family evidence as an exact vulnerable installation.

## Lot 18 — News, regulatory, corporate-disclosure, and change signals

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Detect events that create urgency, budget, governance, integration, or compliance needs.

**Dependencies:** Lots 08, 10, 12, and 14.

**Deliverables:** Company pressrooms, RSS, market disclosures, regulators, authorities, licensed news metadata, acquisitions, funding, leadership, restructuring, cloud, data-center, transformation events, clustering, corrections, and event/publication time separation.

**Required tests:** Primary versus secondary source, duplicate stories, corrections, date distinctions, copyright limits, organization resolution, conflicting reports, and event-to-need classification.

**Exit gate:** Material changes become traceable evidence and commercial signals without full-text news mirroring.

## Lot 19 — Providers, customers, partners, and supply-chain relationships

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Reveal incumbent providers, ecosystems, partnerships, dependencies, and relationship changes that shape commercial positioning.

**Dependencies:** Lots 08 and 11–18.

**Deliverables:** Public case studies, marketplace listings, partner directories, customer stories, procurement-derived links, relationship types, temporal state, confidence, replacement, consolidation, and source-incentive metadata.

**Required tests:** Alias normalization, current versus historical state, circular citation, duplicate case studies, source incentive penalties, contradictions, subsidiary scope, and replacement chronology.

**Exit gate:** Every relationship exposes why it is believed, its timeframe, and whether it is confirmed, published, probable, contradicted, or historical.

## Lot 20 — Entity resolution and temporal corporate knowledge graph

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Link legal entities, brands, groups, domains, assets, providers, contracts, incidents, technologies, and people without unsafe merges.

**Dependencies:** Lots 08 and 11–19.

**Deliverables:** Candidate generation, identifier-first matching, evidence-weighted matching, corporate hierarchy, acquisitions, aliases, temporal relationships, reversible merge/split, conflict queues, source-specific claims, and graph projections.

**Required tests:** Similar names, subsidiaries, acquisitions, shared infrastructure, exact and fuzzy identifiers, false merges, missed links, merge reversal, temporal validity, and contradiction preservation.

**Exit gate:** Every accepted node and edge is evidence-backed, temporal, reversible, and reviewable; ambiguous relations remain candidates.

## Lot 21 — Professional organization maps, contacts, and public community signals

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Identify the professional buying context and weak public professional signals needed to route opportunities correctly.

**Dependencies:** Lots 08, 10, 12, and 20.

**Deliverables:** Professional identities, roles, departments, seniority, employment dates, buying-committee roles, public/licensed business contacts, provenance, purpose, freshness, retention, correction, objection, suppression, and governed public community signals.

**Required tests:** Person and employment deduplication, professional/private classification, stale roles, contact suppression, public affiliation evidence, weak-signal penalties, pseudonym non-deanonymization, and export minimization.

**Exit gate:** Every visible contact and role has provenance, permitted purpose, freshness, and suppression state; community data remains weak evidence until corroborated.

## Lot 22 — Conditional, premium, LinkedIn, Discord, and BrixHub integrations

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Add high-value sources that require licences, platform authorization, consented installation, or provider review through the same canonical contracts as public sources.

**Dependencies:** Lots 09–10 and 20–21.

**Deliverables:** Licensed-provider contracts, cost and quota controls, official LinkedIn scopes or licensed products, consented Discord connectors or exports, commercial CTI, premium B2B data, and a BrixHub assessment and adapter only after explicit approval.

**Required tests:** Licence expiry, authorization expiry, scope mismatch, tenant isolation, cost budgets, permitted channels and fields, deletion, historical import/resume, incremental convergence, prohibited-field rejection, and unique-value benchmarks.

**Exit gate:** Conditional sources are either approved and governed or remain non-executable with explicit blockers. BrixHub is never activated merely because it appears in the roadmap.

## Lot 23 — Analyst research and governed OSINT catalog orchestration

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Make broad public research reproducible, prioritized, and connected to company and opportunity workflows.

**Dependencies:** Lots 10, 12, and 20–22.

**Deliverables:** Research cases, reusable queries, saved results, OSINT catalog candidates, source classification queues, organization research plans, approved search APIs, bounded document discovery, review tasks, sensitive-result quarantine, catalog health, and source-value comparison.

**Required tests:** Query templates, candidate deduplication, dead or redirected tools, ownership changes, restricted-result quarantine, no secret download, authorization expiry, research history, and source recommendations based on evidence gaps.

**Exit gate:** Analysts can reproduce why a source or query was used, what it found, what remains uncertain, and how it affected a commercial hypothesis.

## Lot 24 — Signal fusion, need hypotheses, and commercial taxonomy

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Convert the evidence portfolio into non-duplicated, service-specific, explainable cybersecurity needs across the canonical taxonomy.

**Dependencies:** Lots 03 and 11–23.

**Deliverables:** Executable service taxonomy, event clustering, corroboration, contradiction, source independence, active intervals, service/product fit, deterministic signals, need hypotheses, commercial motions, recalculation, and invalidation.

**Required tests:** Positive, negative, and ambiguous cases for every service family; multilingual aliases; duplicate sources; contradiction; stale decay; retraction; compatible grouping; unrelated needs; cross-service bias; search metadata limits; and explanation completeness.

**Exit gate:** Every hypothesis explains why it exists, supporting and contradicting evidence, expiry, service family, and the distinct or grouped commercial motion it enables.

## Lot 25 — Advanced scoring, calibration, explainability, and feedback

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Prioritize commercially useful and defensible opportunities while preserving human control.

**Dependencies:** Lot 24.

**Deliverables:** Intent, urgency, fit, timing, company fit, product risk, incident confidence, contact availability, evidence quality, source independence, freshness, uncertainty, penalties, calibration datasets, thresholds by service family, source value, outcomes, and rollbackable score versions.

**Required tests:** Bounds, monotonicity, stale decay, contradiction, source independence, precision/recall, false urgency, source ablation, cross-service bias, calibration, override preservation, and explanation completeness.

**Exit gate:** A scoring version improves service-specific and global benchmarks, is explainable and rollbackable, and optimizes accepted opportunity quality rather than ingestion volume.

## Lot 26 — Native commercial operations, alerts, tasks, and engagement

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Let a team operate the complete commercial workflow inside Cyber Intelligence Platform.

**Dependencies:** Lots 03, 08, 21, and 25.

**Deliverables:** Rules, alerts, saved searches, watchlists, opportunity stages, ownership, assignments, tasks, reminders, queues, service levels, notes, research requests, buying committees, engagement history, audit, dashboards, and controlled import/export.

**Required tests:** Alert deduplication and reopening, stage transitions, task recurrence, assignment, concurrent edits, immutable history, suppression before contact use, distinct service motions, deletion, and dashboard consistency.

**Exit gate:** A team can discover, qualify, assign, research, track, and close opportunities with complete history and no external CRM dependency.

## Lot 27 — Complete company intelligence and analyst workspace

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Present one coherent company workspace that connects evidence to action without exposing raw provider data.

**Dependencies:** Lots 20–26.

**Deliverables:** Company 360, public footprint, corporate graph, assets, technologies, providers, vulnerabilities, incidents, contracts, recruitment, events, professional map, contacts, evidence timeline, conflicts, freshness, service coverage, alerts, hypotheses, scores, opportunities, tasks, notes, engagement, and saved layouts.

**Required tests:** Loading, empty, partial, stale, conflicting, suppressed, unavailable, unauthorized, and success states; graph and timeline navigation; service filters; deep links; accessibility; responsiveness; and end-to-end investigations.

**Exit gate:** Analysts can understand what happened, why it matters commercially, which services fit, who may be relevant, and what action is next without direct database or log access.

## Lot 28 — Data quality, reconciliation, lineage, and publication gates

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Stop silent source, parser, entity, signal, and derived-data regressions before they reach users.

**Dependencies:** Lots 10–27.

**Deliverables:** Volume and field baselines, freshness thresholds, duplicate rates, lineage validation, source reconciliation, golden datasets, drift alerts, quarantine, replay, correction propagation, invalidation, source value, service coverage, false-urgency dashboards, and publication gates.

**Required tests:** Parser regression, volume anomaly, missing fields, stale sources, duplicate entities/signals/opportunities, broken lineage, false merge, replay, correction, deletion, score drift, service coverage, and source ablation.

**Exit gate:** Silent data or commercial-classification regressions block publication and can be replayed, diagnosed, corrected, and audited.

## Lot 29 — Supply-chain, release provenance, and repository protection

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Make builds and releases reproducible, verifiable, and protected.

**Dependencies:** Lots 00–28.

**Deliverables:** Python lock, deterministic frontend install, SBOMs, checksums, attestations, pinned actions, CODEOWNERS, strict `main` protection, secret scanning, release and rollback procedures, and artifact retention.

**Required tests:** Clean rebuild, dependency integrity, SBOM generation, secret fixture detection, protected-branch checks, artifact verification, and rollback rehearsal.

**Exit gate:** A release can be rebuilt from source and cannot bypass mandatory checks.

## Lot 30 — Observability, performance, resilience, and recovery

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Prove the database-first collection and analyst product remains reliable under source growth and failures.

**Dependencies:** Lots 02–29.

**Deliverables:** Structured logs, traces, metrics, source freshness/cost/quota/queue/backfill/schema/value dashboards, alerts, backups, restore runbooks, load tests, soak tests, fault injection, degraded modes, capacity thresholds, and recovery objectives.

**Required tests:** Provider outage, quota exhaustion, worker crash, database crash, duplicate delivery, large backfill, index failure, backup restore, degraded UI, recovery time, and no false-success state.

**Exit gate:** Restore succeeds, invariants survive injected failures, and capacity and recovery limits are measured.

## Lot 31 — Isolated browser and download-quarantine runtime

**Status:** `DEFERRED`

**Primary business outcome:** Provide a tightly isolated browser path only when approved APIs and bounded static HTTP are insufficient.

**Dependencies:** Lots 09–10, 22–23, and 29–30.

**Deliverables:** Ephemeral Playwright workers, host/path allowlists, network interception, page/time/CPU/memory/download budgets, login/MFA/CAPTCHA/challenge detection, manual-action state, MIME verification, hashes, archive limits, parser isolation, kill switch, and cleanup.

**Required tests:** Local simulated sites, worker isolation, challenge pause, redirect limits, forbidden host access, download quarantine, archive bombs, browser crash, interruption recovery, and process cleanup.

**Exit gate:** Browser execution cannot bypass access controls, cannot expose downloads directly, and remains optional. No current lot depends on its activation.

## Lot 32 — Controlled pilot and production gate

**Status:** `PLANNED_LOCKED`

**Primary business outcome:** Validate commercial usefulness, safety, operations, and recovery with a bounded production pilot before broader rollout.

**Dependencies:** Lots 24–30 and any explicitly approved subset of Lot 31.

**Deliverables:** Approved source and organization cohort, operator roles, runbooks, service-level objectives, truth datasets, source and service benchmarks, false-positive review, privacy and security review, restore exercise, incident exercise, cost review, and GO/CONDITIONAL-GO/NO-GO decision record.

**Required tests:** End-to-end source-to-opportunity workflows, multi-service detection, false urgency, source ablation, suppression and deletion, authorization expiry, outage, restore, operator error, and audit completeness.

**Exit gate:** The project records an evidence-based production decision with explicit accepted risks, blockers, ownership, rollback, and follow-up actions.

## Current release boundary

Version `0.13.0` includes lots `00–12`.

Lot 12's software is complete, but real public-web collection remains disabled until a separately reviewed organization target, source policy, authorization reference, portfolio state, and schedule are all approved. Search providers and archive providers are also separate governance activations. No merge, release, or documentation status may be interpreted as permission to collect an unapproved source.
