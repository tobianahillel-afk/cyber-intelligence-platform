# Commercial Intelligence Integration Architecture

## Purpose

Cyber Intelligence Platform exists to find and qualify organizations that may need cybersecurity services or products. Source breadth is useful only when collected data becomes traceable commercial intelligence rather than an undifferentiated data lake.

Every source integration must therefore answer five questions before implementation:

1. What approved evidence does the source provide?
2. Which canonical entity or event does that evidence describe?
3. Which business-relevant change or need can be inferred from it?
4. How will the inference be corroborated, aged, corrected, and explained?
5. Which analyst workflow, alert, task, or opportunity will use it?

A source that cannot answer those questions remains a catalog candidate and does not receive an executable adapter.

## Product value chain

```text
source candidate
  -> governance and onboarding decision
  -> adapter capability and schedule
  -> historical backfill or incremental collection
  -> immutable source record and provenance
  -> canonical observation or claim
  -> organization, asset, product, person-role, contract, or event resolution
  -> contradiction and corroboration processing
  -> commercial signal
  -> need hypothesis
  -> explainable score and priority
  -> alert, company workspace, research task, or opportunity
  -> analyst decision and outcome feedback
```

The platform is database-first. Visitors and analysts query current stored projections. Page views do not crawl every provider again. Schedulers use source-specific freshness policies and may enqueue a bounded priority refresh for stale entities.

## Business-value map

| Evidence family | Primary commercial value | Typical need hypotheses | Typical urgency |
|---|---|---|---|
| Open tender or procurement notice | Explicit buying intent and budget | Audit, SOC, SIEM, IAM, pentest, compliance, integration, incident response | High while open |
| Contract award, incumbent, amendment, or end date | Provider displacement and renewal timing | Renewal, competitive replacement, extension, managed service transition | Medium to high near renewal |
| Cyber hiring and team growth | Capability investment or staffing gap | SOC buildout, tool deployment, training, managed service, architecture support | Medium |
| Official incident or regulatory disclosure | Confirmed urgency and governance pressure | Incident response, recovery, hardening, audit, compliance, monitoring | Very high |
| Ransomware or actor claim | Early warning requiring corroboration | Incident support or resilience review | High but heavily confidence-penalized |
| Public attack telemetry and malicious infrastructure | Sector, technology, and campaign context | Proactive hardening, threat monitoring, exposure review | Contextual until linked precisely |
| Technology or provider observation | Installed-base and replacement context | Migration, integration, optimization, managed operations, licence rationalization | Medium |
| Vulnerability and vendor advisory | Product risk and remediation need | Patch governance, exposure review, compensating controls, managed detection | High only with applicable evidence |
| Passive public exposure | External attack-surface hypothesis | Asset inventory, configuration review, attack-surface management | High when fresh and precise |
| Corporate website, engineering publication, repository, or document | Architecture and transformation evidence | Cloud/security transformation, product deployment, consulting | Medium |
| News, acquisition, expansion, leadership, or regulation | Change, budget, integration, and compliance trigger | Post-merger integration, governance, security program change | Medium |
| Professional role and buying committee | Reachability and decision context | Correct service positioning and task assignment | Enabler, not a need by itself |
| Public professional community signal | Weak early indicator and terminology discovery | Product interest, operational pain, migration exploration | Low until corroborated |

## Canonical layers

### 1. Source catalog

The catalog records every candidate from OSINT Framework, live cyber trackers, official registries, commercial providers, public communities, corporate sites, and named sources such as BrixHub.

A catalog entry is not executable. It records owner, access mode, terms, licence, allowed fields, prohibited fields, expected value, expected volume, freshness, cost, quota, retention, risk, and planned lot.

### 2. Provider onboarding and authorization

The onboarding module records whether a source is anonymous, officially provisioned, licensed, manually approved, browser-only, quarantined, or blocked. Credentials remain secret references. Authorization expiry disables execution automatically.

### 3. Adapter capability manifest

Every executable adapter declares:

- `source_id` and adapter version;
- supported modes: `backfill`, `incremental`, `lookup`, `webhook`, or `priority_refresh`;
- canonical output types;
- cursor and checkpoint semantics;
- maximum page, record, byte, date-window, and concurrency limits;
- expected update cadence and maximum acceptable staleness;
- raw-content policy;
- tombstone, correction, and retraction behavior;
- provider schema version and drift strategy;
- commercial use cases enabled by the adapter.

### 4. Immutable source record

The transport layer produces a source-specific immutable record envelope. It preserves source identifiers, retrieval time, source time, content hash, schema version, and authorization decision. It does not write directly to company, opportunity, or scoring tables.

### 5. Canonical observation and claim

Provider-specific payloads map to typed records such as:

- organization identity observation;
- procurement notice, award, amendment, or contract claim;
- job and hiring observation;
- technology or provider observation;
- vulnerability or advisory fact;
- incident claim, official confirmation, dispute, or retraction;
- malicious infrastructure or telemetry observation;
- public document or professional-role observation.

Observations remain distinct from resolved facts. Multiple observations can disagree.

### 6. Entity resolution

Resolution is identifier-first, evidence-weighted, temporal, reversible, and confidence-scored. The system must never merge organizations, domains, technologies, people, incidents, or providers solely because their names look similar.

Resolution creates accepted links, rejected links, and review candidates. Every accepted relationship has evidence and a validity interval.

### 7. Commercial signal

A commercial signal is a normalized business-relevant change derived from evidence. It contains:

- signal type and version;
- affected organization;
- evidence and observation references;
- event and observation dates;
- freshness and expiry;
- confidence and source independence;
- service or product fit;
- urgency;
- contradiction state;
- deduplication identity;
- explanation.

One underlying event may produce several service-fit components but must not create duplicate signals for each source that reported it.

### 8. Need hypothesis

A need hypothesis explains why the organization may need a cybersecurity capability. Examples include:

- active procurement need;
- contract renewal or incumbent replacement window;
- SOC or SIEM program buildout;
- incident-response urgency;
- applicable product-risk remediation;
- cloud, IAM, GRC, or security transformation;
- provider integration or consolidation;
- capability gap suggested by hiring and public project evidence.

A hypothesis is versioned, explainable, rejectable, and recalculated when evidence changes.

### 9. Opportunity and analyst workflow

An opportunity groups compatible need hypotheses for one organization and commercial motion. It must preserve analyst state when evidence is refreshed. Evidence changes may raise, lower, reopen, dispute, or close an alert without duplicating the opportunity.

## Deduplication design

Deduplication occurs at several levels:

1. **Transport replay:** same source, source record ID, version, and content hash.
2. **Provider record:** mutable provider object keyed by source and provider identity.
3. **Cross-source observation:** exact authoritative identifiers or reviewed match candidates.
4. **Event cluster:** same organization, event class, bounded time window, and corroborating identifiers.
5. **Commercial signal:** deterministic signal type, organization, normalized subject, and active interval.
6. **Opportunity:** organization, commercial motion, service family, and lifecycle policy.

Duplicate reporting increases corroboration; it does not create duplicate companies, incidents, signals, alerts, or opportunities.

## Contradiction handling

Conflicts are retained rather than overwritten. Examples include:

- actor claim versus company denial;
- conflicting legal status or parent relationship;
- technology observed by one provider but absent or historical in another;
- contract end date changed by amendment;
- vulnerability applicability with uncertain version precision;
- professional role shown as current by one source and ended by another.

Every projection exposes the competing claims, source rank, dates, confidence, and current resolution decision. Retractions and corrections invalidate derived outputs and trigger recalculation.

## Historical backfill and incremental refresh

Every adapter must explicitly support one or more collection modes:

- `historical_backfill`: bounded import of past records with date partitions and resumable checkpoints;
- `incremental_cursor`: provider cursor, sequence, or timestamp;
- `conditional_refresh`: ETag, Last-Modified, or content hash;
- `webhook`: provider-authorized event delivery;
- `entity_lookup`: bounded lookup for a known organization or identifier;
- `priority_refresh`: queued refresh for stale high-value entities.

Backfill and live collection use the same normalization and projection contracts. Replaying historical data must not create duplicate current alerts. Historical evidence can improve chronology, contract timing, provider history, and model calibration without pretending to be current.

## Source-family integration order

### Foundation first

- provider onboarding and secret lifecycle;
- machine-readable source catalog;
- adapter capability contracts;
- source health, schema drift, backfill, freshness, and cost controls.

### Explicit commercial intent next

- procurement history, awards, contracts, incumbents, amendments, and renewal timing;
- corporate sites, documents, public project material, and approved search discovery.

### Cyber urgency and relevance

- vulnerability knowledge;
- ransomware and incident claims;
- official confirmations and regulatory disclosures;
- malicious infrastructure, phishing, exploitation telemetry, and threat context;
- passive exposure and technographics;
- vendor advisory and product-version applicability.

### Relationships and reachability

- providers, partners, customers, suppliers, and corporate relationships;
- professional organization maps, buying committees, and governed business contacts;
- approved public-community and professional signals;
- licensed and conditional providers, including BrixHub only after approval.

### Product intelligence and operations

- signal fusion and need hypotheses;
- calibrated scoring;
- native alerts, tasks, opportunities, notes, and engagement;
- complete company workspace;
- data-quality, resilience, security, and production gates.

## Testing model

Every source lot must prove all of the following:

### Adapter correctness

- policy decision occurs before network access;
- only approved hosts, paths, fields, and methods are used;
- pagination, date windows, quotas, sizes, and concurrency are bounded;
- payload schemas are strict and drift is classified;
- secrets are redacted;
- retries and checkpoints are idempotent;
- backfill and incremental modes converge to the same canonical state.

### Data correctness

- canonical mapping is deterministic;
- corrections, tombstones, and retractions propagate;
- duplicate inputs do not duplicate entities or opportunities;
- conflicting sources remain visible;
- timestamps preserve source time, event time, and retrieval time;
- prohibited fields are rejected before persistence.

### Commercial usefulness

- every produced signal maps to at least one documented need hypothesis;
- explanations identify the evidence and uncertainty;
- stale and weak evidence receives the correct penalty;
- low-confidence community or actor claims cannot independently create a confirmed high-priority opportunity;
- benchmark fixtures measure precision, recall, duplicate rate, false merge rate, and opportunity usefulness.

### Operational reliability

- provider outage, quota exhaustion, malformed payload, worker interruption, and partial projection cannot record false success;
- source health and freshness are visible;
- circuit breaking and backoff prevent uncontrolled retries;
- historical replay does not flood the analyst Inbox;
- authorization expiry and source disablement stop future jobs.

## Commercial quality metrics

The platform measures value, not only ingestion volume:

- percentage of signals with resolved organizations;
- corroboration and contradiction rates;
- duplicate suppression rate;
- stale-data rate;
- opportunity acceptance, rejection, and snooze rates;
- analyst time from alert to qualification;
- precision of service-fit classification;
- conversion by source family and signal type;
- incremental value of each source over existing evidence;
- cost per accepted opportunity;
- false-urgency rate for ransomware and vulnerability signals;
- false-merge and incorrect-provider-attribution rates.

A source that adds records but no unique, reliable commercial value should be deprioritized or removed.

## BrixHub placement

BrixHub remains a named candidate, not an implicit authorization. Its planned integration belongs to the conditional and premium-source phase after the common catalog, onboarding, backfill, schema, entity-resolution, provenance, deletion, and quality controls exist.

If approved, its adapter must support:

1. a controlled historical import;
2. resumable partitions and content hashes;
3. strict field allowlists and prohibited-field rejection;
4. canonical organization and event mapping;
5. incremental API, export-delta, cursor, or bounded-web refresh;
6. correction, deletion, and retraction handling;
7. source-specific freshness and health;
8. comparison against existing sources to quantify unique commercial value.

It must not bypass the same acceptance gates required of every other source.

## Definition of integrated

A source is integrated only when:

- its governance and onboarding state is executable;
- its adapter passes the common contract suite;
- backfill and refresh are durable and idempotent;
- its records map to canonical observations;
- entities, conflicts, and corrections are handled;
- its signals map to documented commercial needs;
- the company workspace and opportunity engine display its value and uncertainty;
- quality, privacy, retention, cost, and source-health metrics exist;
- one final commit passes all repository gates.
