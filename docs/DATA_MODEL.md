# Canonical Data Model

## Design rules

- A source claim is not automatically a fact.
- All normalized records preserve provenance.
- Entities and observations are separated.
- Derived scores and relationships are reproducible.
- Personal professional-contact data is isolated from general company intelligence.

## Core entities

### Organization

```text
id
canonical_name
legal_name
registration_ids[]
country_code
sector_codes[]
size_band
website_url
status
created_at
updated_at
```

### Domain

```text
id
fqdn
organization_id?
relationship_type
first_seen_at
last_seen_at
confidence
```

### ProfessionalRole

Represents the business-relevant role. A named person is optional.

```text
id
organization_id
role_type
business_unit?
person_display_name?
professional_profile_url?
professional_email?
professional_phone?
source_evidence_ids[]
legal_basis?
notice_status
suppressed_at?
retention_until?
confidence
```

### CyberEvent

```text
id
event_type
canonical_title
first_seen_at
occurred_at?
last_updated_at
severity?
status
confidence
primary_organization_id?
```

Suggested event types:

- ransomware_claim
- confirmed_ransomware_incident
- data_breach
- service_disruption
- vulnerability_exposure_signal
- regulatory_notice
- vendor_advisory
- public_security_statement

### EventClaim

Stores one source's statement about an event.

```text
id
event_id
claim_type
claimant_type
claimant_name
claimed_at?
observed_at
statement_summary
verification_status
source_record_id
evidence_id
```

Claim types:

- actor_claim
- media_report
- official_statement
- authority_notice
- analyst_inference
- correction
- denial

### Technology

```text
id
vendor
product
edition?
version?
cpe?
purl?
```

### TechnologyObservation

```text
id
organization_id?
domain_id?
technology_id
observation_method
observed_at
expires_at?
confidence
evidence_id
```

Observation methods remain passive in the MVP, for example public headers, official documentation, certificate metadata, DNS, public job descriptions, and licensed technographic data.

### Vulnerability

```text
id
cve_id
summary
published_at
modified_at
cvss_score?
epss_score?
known_exploited
vendor_severity?
```

### ExposureSignal

An inferred relevance between an organization observation and a vulnerability. It is not a confirmed vulnerability unless authorized validation has occurred outside the passive MVP.

```text
id
organization_id
technology_observation_id
vulnerability_id
match_type
confidence
reason
generated_at
expires_at?
evidence_ids[]
```

### Evidence

```text
id
source_id
source_record_key?
source_url
collected_at
published_at?
evidence_type
content_hash?
summary
raw_storage_uri?
raw_storage_permitted
classification
confidence
retention_until?
```

Evidence types:

- official_record
- licensed_feed_record
- public_web_page
- search_result_metadata
- source_snapshot
- analyst_note

### Source

```text
id
name
base_url
status
source_type
owner
terms_url?
licence?
allowed_data_categories[]
prohibited_data_categories[]
rate_limit_per_minute?
retention_days?
attribution_required
raw_content_storage
human_review_required
review_dates
```

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

### SearchResult

```text
id
dork_template_id
query_rendered
result_url
result_title?
result_snippet_redacted?
discovered_at
classification
review_status
evidence_id
```

### Opportunity

```text
id
organization_id
status
score
score_version
created_at
updated_at
reviewed_by?
reviewed_at?
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

Potential component types:

- recent_confirmed_incident
- unconfirmed_actor_claim
- relevant_known_exploited_vulnerability
- technology_match
- public_security_hiring
- public_tender
- transformation_event
- decision_role_available
- stale_data_penalty
- weak_source_penalty
- compliance_risk_penalty

## Relationship principles

- An organization can have many domains, but a domain relationship is confidence-scored and time-bounded.
- One cyber event can contain contradictory claims.
- A ransomware-site claim does not become a confirmed incident without independent evidence.
- A vulnerability match is an exposure signal, not proof of exploitability.
- A professional role may exist without identifying a person.
- Suppression of a professional contact must propagate to search and exports.

## Data retention

Retention is evaluated per source, category, and purpose. Deletion must remove or irreversibly anonymize dependent professional-contact records while preserving non-personal audit evidence where legally justified.
