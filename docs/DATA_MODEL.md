# Canonical Data Model

## Design rules

- A source claim is not automatically a fact.
- Provider payloads, source records, observations, resolved entities, signals, hypotheses, opportunities, and analyst decisions are separate layers.
- All normalized records preserve provenance, source time, event time, retrieval time, schema version, and authorization context.
- Entity and relationship resolution is confidence-scored, temporal, reversible, and identifier-first.
- Duplicate reporting increases corroboration rather than creating duplicate entities or opportunities.
- Corrections, retractions, suppression, deletion, source disablement, and authorization expiry propagate to derived projections.
- Derived scores and relationships are reproducible and versioned.
- Professional contact data is isolated from general company intelligence.
- Anonymous product sessions are not users, professional identities, provider accounts, or source credentials.

## Source and collection control

### SourceCatalogEntry

Represents one candidate or executable source, including entries imported from OSINT Framework and named providers such as BrixHub.

```text
id
name
canonical_url
owner?
category
subcategory?
project_use_cases[]
collection_mode
authorization_status
onboarding_level
terms_url?
privacy_url?
licence?
api_documentation_url?
authentication_modes[]
approved_hosts[]
approved_path_prefixes[]
allowed_data_categories[]
prohibited_data_categories[]
automated_collection_allowed
raw_storage_allowed
human_review_required
rate_limit_per_minute?
concurrency_limit?
retention_days?
attribution_required
expected_freshness_class
expected_cost_class
expected_commercial_value
planned_lot?
legal_reviewed_at?
privacy_reviewed_at?
security_reviewed_at?
authorization_expires_at?
last_health_check_at?
```

A catalog entry is never sufficient to authorize network execution.

### ProviderOnboarding

```text
id
source_id
authentication_mode
state
secret_reference_ids[]
requested_scopes[]
granted_scopes[]
provider_account_reference?
last_verified_at?
credential_expires_at?
rotation_due_at?
revoked_at?
last_error_code?
created_at
updated_at
```

Raw passwords, tokens, API keys, session values, and MFA secrets remain outside the application database.

### AdapterCapability

```text
source_id
adapter_version
schema_version
output_types[]
supports_backfill
supports_incremental_cursor
supports_conditional_refresh
supports_webhook
supports_entity_lookup
supports_priority_refresh
maximum_page_size?
maximum_records_per_run?
maximum_bytes_per_response?
maximum_date_window?
maximum_concurrency
checkpoint_kind
correction_behavior
tombstone_behavior
retraction_behavior
commercial_use_cases[]
```

### CollectionRun

```text
id
source_id
adapter_version
mode
schedule_slot?
partition_key?
started_at
completed_at?
status
checkpoint_before?
checkpoint_after?
records_received
records_accepted
records_rejected
records_unchanged
bytes_received
retry_count
policy_decision_id
error_code?
```

### SourceRecord

Immutable provider-specific envelope.

```text
id
source_id
source_record_id
source_record_version?
schema_version
source_url?
source_published_at?
source_modified_at?
collected_at
content_hash
payload_storage_uri?
payload_storage_permitted
classification
retention_until?
collection_run_id
```

A `SourceRecord` does not write directly to canonical company, signal, score, or opportunity state.

## Canonical evidence and observation layer

### Evidence

```text
id
source_id
source_record_id?
source_url?
collected_at
published_at?
event_at?
evidence_type
content_hash?
summary
raw_storage_uri?
raw_storage_permitted
classification
confidence
retention_until?
```

Evidence types include:

- official_record
- licensed_feed_record
- public_web_page
- public_document
- search_result_metadata
- telemetry_observation
- source_snapshot
- analyst_note

### Observation

A typed statement extracted from one source record.

```text
id
observation_type
source_record_id
evidence_id
subject_reference_raw
predicate
value_normalized
value_raw?
valid_from?
valid_to?
observed_at
source_confidence
normalizer_version
superseded_by_id?
retracted_at?
```

Observation types include organization identity, procurement, contract, job, technology, provider, relationship, vulnerability, advisory, incident, indicator, exposure, public document, professional role, and contact-channel observations.

### Claim

Represents a source assertion that can be confirmed, contradicted, corrected, or retracted.

```text
id
claim_type
subject_type
subject_id?
subject_name_raw
claimant_type
claimant_name
statement_summary
claimed_at?
observed_at
verification_status
source_record_id
evidence_id
conflicts_with_claim_ids[]
supersedes_claim_ids[]
```

Claim types include actor claim, media report, official statement, authority notice, telemetry observation, analyst inference, correction, denial, dispute, and retraction.

## Organization and relationship layer

### Organization

```text
id
canonical_name
legal_name
country_code
sector_codes[]
size_band?
status
created_at
updated_at
```

### OrganizationIdentity

```text
id
organization_id
identity_type
identifier
registry
legal_name
status
valid_from?
valid_to?
confidence
source_claim_ids[]
```

Identity types include legal unit, establishment, brand, group, and foreign registry identity.

### Domain

```text
id
fqdn
created_at
updated_at
```

### Relationship

Temporal, evidence-backed edge.

```text
id
subject_type
subject_id
relationship_type
object_type
object_id
valid_from?
valid_to?
status
confidence
evidence_ids[]
accepted_by?
accepted_at?
reversed_at?
```

Relationship types include headquarters, establishment, parent, subsidiary, brand, domain ownership, asset ownership, customer, supplier, technology provider, integrator, MSSP, auditor, insurer, partner, incumbent, awardee, subcontractor, employment, and reporting relationship.

### ResolutionCandidate

```text
id
left_type
left_id
right_type
right_id
candidate_type
score
score_components
status
evidence_ids[]
created_at
reviewed_at?
reviewed_by?
review_reason?
```

Name similarity alone cannot confirm a candidate.

## Cyber and commercial evidence entities

### ProcurementRecord

```text
id
record_type
buyer_organization_id?
provider_organization_ids[]
notice_identifier
lot_identifier?
subject
service_categories[]
publication_at?
deadline_at?
award_at?
start_at?
end_at?
amount_min?
amount_max?
currency?
status
confidence
evidence_ids[]
```

Record types include notice, result, award, amendment, cancellation, contract, and renewal estimate.

### ProfessionalRole

Represents a professional role. A named person is optional.

```text
id
organization_id
role_type
business_unit?
seniority?
geography?
person_display_name?
professional_profile_url?
employment_started_at?
employment_ended_at?
source_evidence_ids[]
confidence
```

### ProfessionalContactChannel

```text
id
professional_role_id
channel_type
value_encrypted_or_referenced
is_role_based
source_evidence_ids[]
legal_basis?
permitted_purpose
notice_status
verified_at?
retention_until?
suppressed_at?
confidence
```

Channel types include public business email, role mailbox, switchboard, direct business number, and contact form. Private contact channels are excluded.

### Technology

```text
id
vendor
product
edition?
canonical_family
cpe?
purl?
lifecycle_status?
end_of_support_at?
```

### TechnologyObservation

```text
id
organization_id?
domain_id?
technology_id
version_expression?
version_precision
observation_method
observed_at
last_seen_at?
expires_at?
confidence
evidence_id
```

### Vulnerability

```text
id
cve_id
summary
published_at
modified_at
cvss_scores[]
epss_history[]
known_exploited_history[]
cwe_ids[]
status
```

### Advisory

```text
id
publisher
advisory_id
published_at
updated_at?
superseded_by_id?
fixed_versions[]
workarounds[]
vulnerability_ids[]
evidence_ids[]
```

### ExposureSignal

An inferred relevance between organization technology evidence and a vulnerability. It is not a confirmed organizational vulnerability.

```text
id
organization_id
technology_observation_id
vulnerability_id
advisory_id?
match_type
match_precision
confidence
reason
generated_at
expires_at?
evidence_ids[]
```

### CyberEvent

```text
id
event_type
canonical_title
primary_organization_id?
actor_or_group_id?
first_seen_at
occurred_at?
last_updated_at
status
confidence
```

Event types include ransomware, data extortion, data breach, DDoS, intrusion, phishing, malware, supply chain, outage, vulnerability exploitation, regulatory notice, and public security statement.

### EventClaim

```text
id
event_id
claim_id
claim_role
organization_match_confidence?
```

### IndicatorObservation

```text
id
indicator_type
indicator_value
malware_family?
campaign_id?
first_seen_at?
last_seen_at?
status
confidence
sensor_scope?
source_record_id
evidence_id
retention_until?
```

Indicators support contextual enrichment. They cannot independently prove a company-specific compromise.

## Research layer

### DorkTemplate

```text
id
name
purpose
provider
query_template
allowed_placeholders[]
risk_level
requires_manual_execution
source_id
created_by
created_at
```

### ResearchCase

```text
id
organization_id?
purpose
status
created_at
completed_at?
query_ids[]
result_ids[]
analyst_decisions[]
```

### SearchResult

```text
id
research_case_id
dork_template_id?
query_rendered
result_url
result_title?
result_snippet_redacted?
discovered_at
classification
review_status
evidence_id?
```

## Commercial intelligence layer

### CommercialSignal

A normalized, non-duplicated business-relevant change.

```text
id
organization_id
signal_type
signal_version
normalized_subject
active_from
active_until?
status
freshness_state
confidence
urgency
service_fits[]
source_independence_count
contradiction_state
evidence_ids[]
observation_ids[]
explanation
created_at
updated_at
```

Potential signal types include:

- open_cyber_procurement
- contract_award
- incumbent_provider
- renewal_window
- cyber_hiring
- security_transformation
- incident_actor_claim
- confirmed_incident
- regulatory_pressure
- technology_observed
- product_end_of_support
- applicable_known_exploited_vulnerability
- passive_exposure_hypothesis
- provider_replacement
- acquisition_or_expansion
- public_professional_interest

### NeedHypothesis

```text
id
organization_id
hypothesis_type
version
status
service_fits[]
urgency
confidence
valid_from
valid_until?
supporting_signal_ids[]
contradicting_signal_ids[]
explanation
created_at
updated_at
```

Hypotheses are explainable, rejectable, recalculable, and invalidated by corrections or stale evidence.

### Opportunity

```text
id
organization_id
commercial_motion
status
score
score_version
created_at
updated_at
reviewed_by?
reviewed_at?
```

### OpportunityHypothesis

```text
opportunity_id
need_hypothesis_id
relationship_type
```

### OpportunityComponent

```text
id
opportunity_id
component_type
value
weight
contribution
reason
evidence_ids[]
```

### AnalystDecision

```text
id
object_type
object_id
decision_type
reason
actor
created_at
previous_state?
new_state?
```

## Deduplication identities

- Source replay: source, record identifier, record version, and content hash.
- Mutable provider object: source and provider object identifier.
- Observation: normalized type, subject, predicate, value, validity interval, and source record.
- Event cluster: organization candidate, event type, bounded event window, and stable external identifiers.
- Commercial signal: organization, signal type, normalized subject, and active interval.
- Opportunity: organization, commercial motion, service family, and lifecycle policy.

Duplicate evidence can increase confidence only when sources are independently derived.

## Retention and propagation

Retention is evaluated by source, data category, purpose, and object type.

Deletion or suppression must:

- remove or irreversibly anonymize dependent professional contact data;
- remove prohibited source payloads and raw artifacts;
- preserve minimal non-personal audit evidence where justified;
- invalidate search, graph, signal, score, alert, and export projections;
- retain retraction and correction history without retaining prohibited content.
