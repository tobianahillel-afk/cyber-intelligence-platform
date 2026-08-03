# Normalization and Data Update Pipeline

## Purpose

The platform combines heterogeneous sources that use different identifiers, names, timestamps, confidence models, languages, and schemas. The normalization pipeline transforms source-specific records into canonical observations without losing provenance or pretending that uncertain matches are facts.

## Data layers

```text
L0 Source response or downloaded artifact
L1 Raw observation envelope
L2 Parsed source record
L3 Canonical observation
L4 Resolved entity links
L5 Evidence-backed signal
L6 Need hypothesis
L7 Commercial opportunity
L8 Read models and search indexes
```

Each layer is persisted or reproducible according to source policy. No adapter is allowed to skip directly from a source response to an opportunity.

## L0: Source response and artifact

Represents the provider response exactly as received when storage is permitted.

Examples:

- API response body;
- HTML page;
- rendered page snapshot;
- CSV export;
- PDF document;
- webhook body;
- response headers;
- screenshot.

L0 may be ephemeral when raw storage is prohibited.

## L1: Raw observation envelope

Every record enters the platform through one common envelope:

```text
observation_id
source_id
adapter_id
adapter_version
collection_job_id
source_record_key
source_record_type
source_url
collected_at
observed_at
published_at
updated_at
payload_reference_or_redacted_payload
payload_hash
schema_fingerprint
content_language
data_categories
classification
retention_until
```

The envelope is immutable. Corrections create a new observation linked to the previous one.

## L2: Parsed source record

A typed provider-specific model after validation.

Responsibilities:

- decode dates and identifiers;
- reject malformed records;
- distinguish missing from empty values;
- preserve source field names through metadata;
- normalize text encoding;
- produce parser warnings;
- preserve unknown fields only when policy permits.

L2 remains inside the source adapter and is not consumed by the opportunity engine.

## L3: Canonical observation

A canonical observation uses platform vocabulary.

Canonical families:

- organization identity;
- organization relationship;
- domain and infrastructure;
- professional role or contact;
- cyber event or claim;
- technology observation;
- vulnerability metadata;
- contract, tender, award, or renewal;
- job or transformation signal;
- publication or news item;
- source health and access state.

Each canonical observation contains:

```text
canonical_type
canonical_schema_version
subject_candidates[]
attributes
valid_time_start
valid_time_end
transaction_time
confidence_input
quality_flags[]
source_evidence_reference
```

## Canonical value normalization

### Organization names

Store separately:

- exact source name;
- normalized comparison name;
- legal name;
- commercial name;
- aliases;
- transliteration;
- registration identifiers.

Do not discard legal suffixes from evidence. A derived comparison key may remove punctuation and common suffixes for candidate generation only.

### Domains

- lowercase;
- Unicode converted through IDNA for comparison;
- trailing dot removed;
- public suffix evaluated;
- registrable domain separated from hostname;
- invalid or private hostnames flagged.

### Email addresses

- syntax validated;
- domain normalized;
- local part preserved as provided;
- generic versus named mailbox classified;
- source and verification date retained;
- suppression applied before search and export.

### Telephone numbers

- retain exact source value;
- parse to an international representation when country context is sufficient;
- mark ambiguous numbers rather than guessing;
- separate business switchboard from direct professional number.

### Dates and time

Store timestamps in UTC with original timezone and precision metadata.

Precision examples:

```text
exact_timestamp
day
month
year
estimated_range
```

Do not invent a midnight timestamp for a date-only source without marking the original precision.

### Money

Store:

- original amount;
- original currency;
- minimum and maximum if a range;
- converted amount only with exchange-rate source and date;
- tax inclusion state when known.

### Technology identifiers

Store vendor, product, edition, version expression, CPE, package URL, ecosystem, and source wording separately.

### Vulnerabilities

Use CVE as a canonical identifier when available. Preserve GHSA, OSV, vendor advisory, and other aliases.

## Quality flags

Examples:

```text
missing_identifier
ambiguous_date
machine_translated
source_conflict
stale_observation
incomplete_record
unverified_contact
version_inferred
organization_match_ambiguous
possible_duplicate
provider_schema_changed
```

Flags remain visible to downstream scoring and UI.

## Deduplication

Deduplication occurs at several levels.

### Exact source duplicate

Use source ID plus source record key plus content hash.

### Repeated observation

The same fact may be observed again. Update `last_seen_at` and evidence frequency without creating unnecessary duplicate read-model rows.

### Cross-source duplicate

Different sources may describe the same event, organization, contact, contract, or technology. Preserve each evidence record while linking them to a shared canonical entity or event.

### Near duplicate

Use candidate generation and scoring based on identifiers, normalized names, dates, domains, locations, and source relationships. Near duplicates require deterministic thresholds or analyst review.

## Entity resolution

Entity resolution is a separate module.

### Candidate generation

Generate possible matches using strong keys first:

- SIREN, SIRET, LEI, company registration number;
- official domain;
- VAT number;
- provider stable identifier;
- exact legal name plus jurisdiction.

Then use weaker keys:

- normalized name;
- address;
- group relationship;
- email domain;
- official social URL;
- phone number.

### Match scoring

A match stores component contributions:

```text
registration_identifier_match
official_domain_match
legal_name_similarity
address_similarity
parent_relationship_support
source_reliability
conflicting_identifier_penalty
```

### Decision

Possible outcomes:

- automatic link;
- analyst review;
- rejected link;
- explicit separate entities;
- merge proposal;
- split proposal.

All decisions are reversible and versioned.

## Evidence construction

Evidence links canonical observations to source material.

Evidence records include:

- exact source;
- source URL or record key;
- publication and collection timestamps;
- redacted excerpt or structured fields;
- artifact hash;
- classification;
- confidence;
- analyst review;
- retention.

One evidence item may support several observations, but each relationship explains what it supports.

## Claim, observation, and inference separation

### Observation

Something directly visible in a source, such as a job posting mentioning Splunk.

### Claim

A source asserts an event, such as a ransomware actor claiming an organization.

### Inference

The platform derives a conclusion, such as probable SIEM usage or an estimated contract-renewal window.

The UI and scoring must retain these distinctions.

## Signal generation

Signals are canonical, evidence-backed inputs to need detection.

Examples:

- `official_incident_confirmed`;
- `ransomware_claim_unconfirmed`;
- `technology_recently_observed`;
- `kev_relevance_high_confidence`;
- `security_tender_open`;
- `contract_renewal_window_open`;
- `soc_hiring_cluster_detected`;
- `ciso_role_identified`;
- `contact_data_stale`.

Signals have:

```text
signal_id
signal_type
organization_id
valid_from
valid_until
confidence
severity_or_strength
evidence_ids[]
generator_version
created_at
supersedes_signal_id
```

## Freshness model

Every canonical family has a freshness policy.

Example defaults:

| Data type | Fresh | Aging | Stale |
|---|---:|---:|---:|
| incident update | 0-24 h | 1-7 d | >7 d without confirmation |
| ransomware claim | 0-12 h | 12-72 h | >72 h without update |
| technology observation | 0-30 d | 30-180 d | >180 d |
| named contact role | 0-90 d | 90-180 d | >180 d |
| job posting | open | recently closed | >90 d after close |
| tender | open | awarded or recently closed | historical |
| contract renewal estimate | inside outreach window | approaching | passed without update |

Policies are configurable and versioned.

## Update processing

### New record

- store observation;
- normalize;
- resolve entities;
- generate or update evidence;
- recalculate affected signals and opportunities;
- update search indexes;
- emit user alerts if thresholds are met.

### Changed record

- compare stable fields;
- store new immutable observation;
- create a field-level change set;
- invalidate affected derived records;
- recalculate only impacted signals;
- notify only when the change is meaningful.

### Unchanged record

- update last-seen and collection health;
- avoid unnecessary downstream recomputation.

### Removed record

- create tombstone;
- expire or weaken affected signals;
- preserve historical non-personal evidence only when policy permits;
- propagate personal-data deletion when required.

## Field-level change sets

A change set records:

```text
entity_or_record_id
old_observation_id
new_observation_id
changed_fields[]
change_type
materiality
created_at
```

Materiality examples:

- cosmetic;
- informational;
- scoring_relevant;
- opportunity_relevant;
- compliance_relevant;
- deletion_relevant.

## Reprocessing and versioning

Parsers, mappers, entity-resolution models, and signal generators are versioned.

When logic changes, the platform can:

- reprocess from permitted L0 or L1 data;
- compare old and new outputs;
- run a shadow calculation;
- approve migration of derived records;
- retain score-version history.

A deployment must not silently rewrite all historical conclusions without recording the algorithm version.

## Backfills

Backfills are bounded jobs with:

- source;
- date range;
- record family;
- maximum expected volume;
- reason;
- requester;
- priority;
- cost budget;
- cancellation state;
- progress checkpoint.

Backfills use lower priority than fresh incremental data unless explicitly promoted.

## Search indexing

PostgreSQL remains the system of record. OpenSearch contains derived read models.

Index updates use an outbox or durable event mechanism. Rebuilding an index must be possible from canonical storage.

Indexes include:

- organizations;
- professional roles and permitted contacts;
- events and claims;
- technologies and vulnerabilities;
- contracts and tenders;
- opportunities;
- evidence metadata.

## Data lineage

For any UI value, the system must be able to trace:

```text
UI field
-> read model field
-> canonical entity or signal
-> canonical observation
-> raw observation envelope
-> source record or artifact
-> collection job and adapter version
```

## Data-quality monitoring

Metrics include:

- missing required identifiers;
- parse rejection rate;
- unresolved entity rate;
- duplicate rate;
- conflicting identifiers;
- stale data percentage;
- contact verification age;
- source-specific null-rate changes;
- volume anomalies;
- mapping coverage;
- opportunities supported by only one weak source.

Threshold breaches create Source Operations alerts and can pause downstream scoring for the affected record family.
