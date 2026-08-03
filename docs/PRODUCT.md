# Product Definition

## Product statement

Cyber Intelligence Platform is an analyst-oriented system that transforms public or licensed cyber, company, technology, vulnerability, and professional-role data into evidence-backed commercial opportunities for cybersecurity services and products.

It does not decide that a company is vulnerable merely because it appears in one source. It gathers evidence, resolves entities, assigns confidence, and presents a reviewable timeline.

## Primary users

- Independent cybersecurity consultant
- Cybersecurity services sales engineer
- Threat-intelligence analyst
- SOC or incident-response business development team
- Security-product founder

## Core workflows

### 1. Investigate a company

Input: company name, legal identifier, domain, or public URL.

Output:

- resolved company identity and domains;
- public technology and infrastructure observations;
- relevant vulnerabilities and vendor advisories;
- public incident timeline;
- professional decision-maker roles;
- evidence list with timestamps and confidence;
- suitable service offers and factual outreach angles.

### 2. Monitor public cyber events

The platform ingests public or licensed incident-event feeds, official disclosures, ransomware trackers, CERT publications, regulatory notices, vendor advisories, and news sources.

It normalizes claims without treating attacker statements as verified facts. Each event records who made the claim, when it was observed, whether it was independently confirmed, and which organizations may be affected.

### 3. Run lawful dork research

Users may define reusable search-query templates to locate publicly indexed material. The system records the query, search provider, execution date, result URL, result type, and review state.

Discovery does not authorize access. Results that appear to expose secrets, personal files, credentials, restricted consoles, or non-public information are quarantined as metadata only and require manual review.

### 4. Build an organization map

The platform links public professional roles to organizations and business units. It prioritizes roles rather than unnecessary personal detail.

Relevant roles may include CISO, CIO, CTO, DPO, SOC manager, infrastructure manager, procurement, risk, compliance, and executive management for smaller organizations.

### 5. Score an opportunity

Opportunity scoring is explainable and evidence-driven. Initial dimensions:

- event recency;
- relevance to offered services;
- company fit;
- evidence confidence;
- public buying signals;
- role availability;
- data freshness;
- compliance risk;
- source reliability.

Scores must not rely on private vulnerabilities, personal distress, sensitive traits, or coercive pressure.

## MVP

The first usable release will provide:

1. source registry and policy engine;
2. company, domain, person-role, event, evidence, technology, and vulnerability entities;
3. ingestion from selected official/public feeds;
4. company search and event timeline;
5. passive technology-to-vulnerability correlation;
6. saved dork templates and manually reviewed results;
7. explainable opportunity score;
8. exportable evidence brief;
9. no autonomous outreach.

## Out of scope for the MVP

- active vulnerability scanning;
- exploitation or proof-of-concept execution against third parties;
- direct access to attacker infrastructure;
- automated interaction with ransomware actors or victims;
- storage of leaked files, credentials, or private negotiation transcripts;
- automated LinkedIn scraping that bypasses platform controls;
- autonomous bulk email or phone outreach.

## Success criteria

- Every displayed claim links to evidence and provenance.
- Duplicate companies and events are resolved reliably.
- The system distinguishes claim, observation, confirmation, and inference.
- Data retention and deletion rules are enforceable.
- A user can review why an opportunity was scored and reject any signal.
