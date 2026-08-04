# Product Definition

## Product statement

Cyber Intelligence Platform is a complete, standalone cyber revenue-intelligence and commercial-operations system. It discovers organizations with current or emerging cybersecurity needs, explains the evidence behind those needs, maps the relevant professional buying committee, and lets users manage the entire investigation and opportunity lifecycle inside the product.

The platform is not a data plug-in for Salesforce, HubSpot, or another CRM. It owns its native company records, people and role records, alerts, saved searches, opportunities, tasks, notes, assignments, review history, engagement history, and reporting.

It remains evidence-first. A company is never presented as vulnerable, compromised, using a technology, nearing a contract renewal, or working with a provider merely because one source suggested it. Claims, observations, confirmations, and analyst inferences are stored separately with provenance, time, confidence, and corrections.

## Primary users

- cybersecurity service providers and integrators;
- penetration-testing and audit firms;
- SOC, SIEM, MDR, incident-response, governance, risk, and compliance teams;
- cybersecurity product vendors;
- cyber revenue-intelligence and business-development analysts;
- independent cybersecurity consultants.

## Native product capabilities

### Opportunity discovery and alerts

Users define versioned rules and saved searches such as:

- organizations publishing SIEM or SOC tenders;
- companies recruiting detection, response, or security-operations roles;
- contracts approaching an estimated renewal period;
- newly observed technologies affected by material advisories;
- public incidents, regulatory notices, acquisitions, expansions, or leadership changes;
- passive public-exposure observations requiring analyst review.

A rule produces a native alert linked to the matching evidence, affected organization, confidence, urgency, service fit, and next review date. Alerts can be filtered, assigned, snoozed, grouped, dismissed, corrected, or converted into an opportunity.

### Company intelligence workspace

Each company record is intended to consolidate:

- legal entities, establishments, brands, subsidiaries, parent groups, domains, IP ranges, certificates, and public identifiers;
- business units, locations, markets, customers and partners only where publicly and lawfully documented;
- open tenders, historical awards, contracts, published incumbents, amendments, end dates, and estimated renewal windows;
- technologies, security products, cloud providers, public services, first/last-seen dates, version precision, and confidence;
- relevant vulnerabilities and vendor advisories without claiming exposure beyond the supporting observation;
- incidents, ransomware claims, official confirmations, corrections, regulatory actions, and news events;
- recruitment activity and capability gaps;
- current and historical cybersecurity providers, auditors, integrators, insurers, consultants, and other business relationships where supported by public or licensed evidence;
- every source, timestamp, confidence score, conflict, and analyst decision.

### Professional organization map

The platform builds an evidence-backed professional organization map containing:

- business units and reporting relationships when publicly documented;
- current and former professional roles;
- role category, seniority, department, geography, and employment dates;
- likely buying-committee position such as sponsor, technical evaluator, procurement, legal, privacy, finance, executive approver, or operational user;
- public or licensed professional email addresses, company switchboards, direct business numbers, contact forms, and role-based mailboxes;
- source, collection date, last verification date, confidence, permitted purpose, retention rule, correction state, and objection/suppression state for every contact channel.

The product prioritizes professional relevance and business channels. It does not collect home addresses, family details, private phone numbers, private email addresses, personal accounts, sensitive traits, credentials, private messages, or data taken from leaked victim files. A public page does not automatically make every personal detail necessary or appropriate to retain.

### Native commercial operations

The system provides its own commercial workspace:

- company and account ownership;
- opportunity stages and qualification state;
- tasks, reminders, due dates, queues, service-level targets, and assignments;
- research requests and enrichment tasks;
- analyst notes with immutable history;
- contact and buying-committee records;
- interaction and outreach history entered or imported through approved product workflows;
- alerts generated from changed evidence;
- saved views, filters, segments, watchlists, and priority lists;
- dashboards for freshness, coverage, opportunity quality, analyst throughput, and conversion;
- complete audit trail and reversible state transitions.

Salesforce, HubSpot, or third-party CRM synchronization is not a product dependency or roadmap goal. Controlled exports may exist for reporting or portability, but the authoritative operational state remains inside Cyber Intelligence Platform.

## Core workflows

### Investigate a company

Input: company name, legal identifier, domain, public URL, technology, tender, incident, or professional role.

Output:

- resolved legal and corporate identity;
- company graph and professional organization map;
- technologies, providers, vulnerabilities, tenders, contracts, recruitment, incidents, and business changes;
- professional contact channels with provenance and permitted use;
- evidence timeline with conflicts and confidence;
- relevant cybersecurity needs and suitable offers;
- native tasks, alert rules, watchlists, and opportunity state.

### Monitor markets and needs

The platform continuously evaluates approved public or licensed sources against saved rules. New evidence can create or update alerts, company facts, needs, and opportunities without duplicating the underlying entity.

A change is not silently overwritten. Material changes retain previous values, observed dates, supporting evidence, and the rule version that produced the alert.

### Research public information safely

Users may create reusable search-query templates and analyst research cases for public company documents, tenders, hiring pages, vendor references, conference material, support forums, public code, professional pages, and other authorized sources.

Discovery does not authorize access. Authentication bypass, CAPTCHA evasion, copied sessions, secret validation, intrusive scanning, private-account access, restricted downloads, and collection of leaked credentials or victim files are prohibited. Potentially sensitive accidental exposures are quarantined as minimal metadata for human review rather than collected as prospect intelligence.

### Build and verify an organization map

The platform links people to organizations through public or licensed professional evidence, preserves role history, and supports competing or uncertain reporting relationships. Ambiguous identity or employment matches remain candidates until reviewed.

### Score and manage an opportunity

Opportunity scoring is explainable and versioned. Dimensions may include:

- evidence confidence and independence;
- event and observation recency;
- explicit buying intent;
- service and product fit;
- company fit and strategic priority;
- contract timing and procurement state;
- technology relevance;
- incident or vulnerability urgency;
- availability of relevant professional roles and business contact channels;
- uncertainty, legal risk, staleness, and single-source penalties.

The user can qualify, reject, snooze, reassign, request research, add tasks, override components with a reason, and retain the generated baseline for audit.

## Product data model direction

The complete product is expected to own canonical records for:

- organizations, establishments, brands, groups, domains, assets, and relationships;
- people, professional identities, roles, reporting relationships, and business contact channels;
- sources, authorizations, observations, claims, evidence, corrections, and lineage;
- technologies, products, versions, vendors, providers, contracts, tenders, awards, and renewal estimates;
- vulnerabilities, advisories, incidents, regulatory events, recruitment, and business events;
- rules, saved searches, alerts, watchlists, needs, opportunities, stages, tasks, notes, assignments, and engagement history;
- suppression, objection, correction, retention, access, and audit records.

## Product boundaries

The platform may use approved official APIs, public feeds, licensed datasets, public professional pages, and isolated analyst-assisted research where terms and authorization permit it.

It does not:

- actively scan or exploit third-party systems without a separate explicit authorization;
- validate passwords, tokens, cookies, or leaked credentials;
- store stolen files, private communications, or ransomware-victim data;
- access private LinkedIn data or automate LinkedIn collection without official scopes or reviewed written permission;
- bypass authentication, paywalls, access controls, rate limits, CAPTCHA, or bot protections;
- use personal distress, sensitive traits, or private-life information to pressure a prospect;
- autonomously send bulk email, place calls, or make a sales decision.

## Success criteria

- Every material fact and alert links to provenance and observed time.
- The product distinguishes observation, source claim, confirmation, inference, correction, and retraction.
- Company, person, role, technology, contract, and provider identities are deduplicated without unsafe automatic merges.
- A user can complete discovery, investigation, qualification, prioritization, task management, and history review without another CRM.
- Professional contact data has a permitted purpose, provenance, freshness, retention, correction, and suppression state.
- Every score and rule match is explainable and rejectable.
- Data retention, deletion, correction, and objection rules are enforceable across alerts, opportunities, exports, and derived data.
