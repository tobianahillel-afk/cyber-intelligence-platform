# Source Policy

## Goal

Every collector must be reviewed individually. A source being visible on the Internet does not, by itself, establish permission to automate collection, republish its database, process personal data, or ignore contractual restrictions.

The platform therefore uses a source registry with explicit approval states.

The complete candidate-source taxonomy, OSINT Framework mapping, collection modes, adapter requirements, and implementation priorities are defined in [`OSINT_COLLECTION_CATALOG.md`](OSINT_COLLECTION_CATALOG.md). That catalog is a discovery and planning document. This policy and the executable source registry remain authoritative for network access.

## Source states

### `allowed`

A source may be ingested automatically when at least one of the following applies:

- an official API or downloadable feed expressly permits the intended use;
- an open-data or compatible content licence covers collection and reuse;
- the source owner has provided written permission;
- the source is an official public authority or vendor feed whose reuse terms are compatible;
- collection is limited to minimal factual metadata and has passed legal, contractual, privacy, and technical review.

### `conditional`

A source requires constraints such as:

- API key or paid licence;
- attribution;
- strict rate limits;
- limited fields;
- no republication of raw content;
- no personal-data enrichment;
- manual-only access;
- geographic restrictions;
- retention limits;
- human review before use.

### `blocked`

A source must not be collected when it requires or encourages:

- bypassing authentication, paywalls, CAPTCHAs, technical controls, or access restrictions;
- breaching contractual API or platform restrictions;
- acquiring stolen credentials, victim files, private communications, or extorted datasets;
- impersonation or deceptive interaction;
- intrusive probing of third-party systems;
- collection whose privacy impact cannot be justified or mitigated;
- de-anonymizing pseudonymous people or building behavioural dossiers from their message history;
- covertly joining private or restricted communities;
- scraping LinkedIn, Discord, or another platform contrary to its terms or without express authorization.

## Ransomware and live-incident sources

The system may ingest lawful public or licensed metadata such as:

- claimed victim organization;
- claiming actor or group;
- first-seen and publication dates;
- affected country and sector;
- public source URL;
- claim status;
- independent confirmation status;
- public incident summary;
- source reliability and confidence.

The system must distinguish:

- `actor_claim`: an allegation made by a threat actor;
- `public_report`: a third-party report;
- `official_confirmation`: a statement from the organization or authority;
- `analyst_inference`: a documented inference;
- `retracted_or_disputed`: a disputed or corrected claim.

Do not store leaked documents, personal records, credentials, encryption keys, private victim communications, or full negotiation transcripts. Do not interact with attackers or victim negotiation portals.

## Dorking and search providers

Allowed use:

- create search-query templates;
- use official search APIs where available;
- generate links for manual analyst review;
- collect ordinary result metadata where terms permit;
- find official publications, public tenders, job listings, security contacts, technology documentation, and public incident notices.

Restricted use:

- automated high-volume result scraping without provider permission;
- accessing results that require authentication or bypassing a restriction;
- downloading exposed confidential files;
- validating credentials or secrets found in search results;
- turning an accidental exposure into an intrusive test.

A suspicious result may be retained only as minimal metadata for review: URL, discovery timestamp, query, category, risk label, and redacted description.

## Professional contact data

Collect only data connected to a professional role and necessary for a documented B2B purpose. Record:

- source;
- collection date;
- role relevance;
- legal basis;
- privacy notice status;
- objection or suppression status;
- retention deadline.

Do not enrich with home addresses, private phone numbers, family information, sensitive traits, personal social activity, or unrelated personal history.

Public or pseudonymous social activity must not be used to infer a person's real identity, private interests, beliefs, vulnerabilities, or employer technology. An explicitly self-declared professional affiliation may create a low-confidence analyst lead only when independently corroborated and reviewed.

## Community and messaging sources

Reddit, Discord, forums, and similar community sources require provider-specific approval.

- Reddit automation must use an approved official or licensed API and should normally produce organization-level or aggregate signals.
- Discord data requires an administrator-installed application, an authorized export, or another consented connector.
- Self-bots, automated user accounts, covert joining, invite harvesting, member scraping, private-message access, and bulk personal-history collection are prohibited.
- A public server or public post is not blanket authorization for mass collection, commercial profiling, or identity correlation.

## LinkedIn

LinkedIn may be used only through official API scopes actually granted, a licensed authorized product, written crawling permission, or manual analyst review.

A normal user account, browser cookie, extension, proxy pool, CAPTCHA bypass, or ordinary browser automation is not an approved collection method. Profiles, posts, connections, groups, search results, and messages must not be scraped without express authorization covering the exact hosts, paths, fields, purpose, rate, storage, and retention.

## Mandatory registry fields

Each source configuration must include:

```yaml
id: string
name: string
base_url: string
status: allowed | conditional | blocked
source_type: api | feed | website | manual | licensed_dataset
owner: string
terms_url: string | null
licence: string | null
robots_reviewed_at: date | null
legal_reviewed_at: date | null
privacy_reviewed_at: date | null
allowed_data_categories: []
prohibited_data_categories: []
rate_limit_per_minute: integer | null
retention_days: integer | null
attribution_required: boolean
raw_content_storage: boolean
human_review_required: boolean
notes: string
```

## BrixHub

The exact candidate is `https://brixhub.cc/`.

It is registered as a mandatory source-assessment candidate because the product owner has identified it as potentially valuable. It must remain quarantined and non-executable until its owner, terms, privacy notice, data provenance, fields, licence, automation permission, authentication flow, rate limits, retention obligations, and security posture have been verified.

Before approval, no account creation, login automation, payment, crawl, scrape, download, import, or live connectivity test is permitted. If the provider passes review, an explicit registry authorization and a provider-specific adapter must be delivered before collection can start.

## Unknown or renamed sources

Any source whose exact identity, domain, owner, or access method is uncertain must remain unimplemented until resolved. A redirect, domain change, acquisition, ownership change, or major terms change returns an approved source to review or quarantine.
