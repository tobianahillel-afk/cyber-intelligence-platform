# Source Policy

## Goal

Cyber Intelligence Platform must implement every useful public, licensed, customer-authorized or provider-authorized source through a concrete provider-specific acquisition path.

Source policy is therefore both an authorization control and an activation contract: a useful source that currently lacks an API key, paid plan, account, target registry, written permission, stable API or deployment connector remains unfinished work with an explicit prerequisite owner and target SA.

The complete target is defined in [`OSINT_FULL_IMPLEMENTATION_MANDATE.md`](OSINT_FULL_IMPLEMENTATION_MANDATE.md).

## Core rule

Internet visibility alone is not authority to ignore provider access controls or contractual scope. At the same time, a missing entitlement or account is not a reason to permanently discard a useful provider.

For every useful provider the project must answer:

1. what legitimate access mode is available;
2. what account/licence/permission is required;
3. what exact hosts/paths/methods/fields are in scope;
4. what data may be stored and for how long;
5. what production adapter is required;
6. what live validation will prove the integration;
7. which SA owns completion.

## Source states

The existing registry vocabulary may contain `allowed`, `conditional`, and `blocked` for compatibility.

### `allowed`

The deployment may execute the approved acquisition path now.

Examples:

- official public API;
- compatible open-data feed;
- approved ordinary public-web crawl;
- licensed API whose current deployment entitlement is connected;
- administrator-installed connector;
- written-authorized browser workflow.

### `conditional`

The source is useful and executable after explicit constraints or prerequisites are satisfied, for example:

- API key;
- paid/enterprise licence;
- customer authorization;
- provider account;
- attribution;
- retention limits;
- bounded fields;
- target registry;
- service account;
- browser session;
- analyst-assisted MFA;
- contract approval.

`conditional` is active implementation work, not a terminal state.

### `blocked` compatibility state

A useful source may temporarily be represented as `blocked` when no current deployment authorization or legitimate access path is ready.

For future work, every useful `blocked` source must also have:

- an exact missing prerequisite;
- implementation owner;
- target SA;
- planned adapter/access path;
- acceptance/live-test condition.

A useful provider must not be closed merely because it is currently `blocked`. It remains in the activation backlog until the prerequisite is resolved, it is replaced by an equivalent fully integrated provider, or the product owner explicitly excludes it as no longer useful.

## Supported acquisition modes

Source Governance should be able to authorize all of these legitimate modes:

- `official_api`;
- `open_data`;
- `licensed_api`;
- `feed_or_bulk`;
- `static_http`;
- `recursive_web`;
- `authorized_browser`;
- `authorized_authenticated_web`;
- `consented_connector`;
- `local_tool_module`;
- `manual_import`.

A source may use several modes with an explicit preference/fallback order.

## Web and crawling policy

For approved organization domains, recursive crawling is an intended production capability.

The policy may authorize:

- robots retrieval/evaluation;
- sitemap and sitemap-index traversal;
- RSS/Atom;
- security.txt;
- same-origin recursive link discovery;
- configurable crawl depth;
- configurable page/byte/time/concurrency budgets;
- JavaScript-rendered browser collection;
- permitted document downloads through quarantine;
- automatic refresh schedules;
- legitimate authenticated access for exact approved accounts and paths.

Automatic company crawling should be generated from canonical organization/domain evidence when deployment policy approves that research scope.

## Browser and login policy

A useful source must not be excluded simply because it requires JavaScript or a legitimate account.

The platform should implement:

- Playwright/Chromium adapters;
- provider-approved service/test accounts;
- OAuth/SSO;
- account-specific cookies/session state;
- administrator-installed integrations;
- analyst-assisted MFA checkpoints;
- screenshots and controlled downloads;
- resume-after-human-action workflows.

Browser credentials and sessions remain isolated per source/account/authorization scope.

## CAPTCHA, MFA and access-control boundary

The platform supports CAPTCHA/MFA as human/provider checkpoints for legitimate authorized accounts.

Normal acquisition does not implement techniques whose purpose is to defeat access controls. It must not:

- bypass CAPTCHA or MFA to obtain unauthorized automation;
- steal/replay another user's session;
- guess/validate credentials;
- create deceptive identities or disposable account farms to evade restrictions;
- exploit a provider or third-party system to obtain data;
- evade bans/quotas through fake-account rotation.

If a legitimate workflow requires human CAPTCHA/MFA completion, the job pauses, creates a precise checkpoint and resumes afterward.

## Search and dorking

Search is a mandatory multi-provider capability.

The project must pursue executable paths for:

- Brave;
- Mojeek;
- Bing or equivalent approved web-search API;
- Google official API products where an entitlement permits automation;
- Google analyst dork links;
- Common Crawl;
- Internet Archive;
- GDELT current supported stack;
- GitHub/GitLab search and repository APIs;
- publication/patent/standards/documentation search APIs.

Search-result metadata remains discovery context until the referenced resource is retrieved through an approved evidence path.

## Passive infrastructure and technography

Useful provider-specific integrations are mandatory implementation targets, including:

- Cloudflare DNS-over-HTTPS;
- RDAP;
- Certificate Transparency;
- Cert Spotter;
- Shodan passive/indexed APIs;
- Censys;
- SecurityTrails;
- urlscan search/existing-scan metadata;
- VirusTotal metadata within licensed scope;
- GreyNoise;
- AbuseIPDB;
- Spamhaus;
- Wappalyzer;
- BuiltWith;
- HTTP Archive or equivalent technography;
- licensed passive DNS/certificate/exposure/cloud-asset providers.

A missing commercial entitlement is a Provider Onboarding prerequisite, not a permanent exclusion.

Active scanning or exploitation requires a separate explicit security-testing authorization and is not implied by passive-source approval.

## Local OSINT frameworks

Frameworks with mixed capabilities must be decomposed into governed modules.

The project must pursue useful modules for:

- Sherlock;
- OWASP Amass passive modules;
- theHarvester approved upstreams;
- SpiderFoot approved modules;
- Recon-ng approved modules;
- Maltego approved transforms;
- additional OSINT Framework tools selected as useful.

One unavailable/active module must not cause legitimate passive modules to be permanently discarded.

## Ransomware, incident and CTI sources

The system should ingest all useful lawful public/licensed metadata paths, including:

- claimed victim organization;
- claiming actor/group;
- public source URL;
- first-seen/publication dates;
- public incident summary;
- official confirmation/correction state;
- regulator/CERT/company disclosures;
- licensed STIX/TAXII;
- licensed ransomware/phishing/malware/IOC metadata.

Claim states remain explicit:

- `actor_claim`;
- `public_report`;
- `official_confirmation`;
- `analyst_inference`;
- `retracted_or_disputed`.

Private victim files, stolen credentials, private negotiation content and extorted datasets are not required product inputs and are not normal source-activation targets.

## Professional and community sources

The product must pursue legitimate provider-specific activation rather than leaving these categories as permanent placeholders.

### LinkedIn

Implement one or more legitimate paths:

- official API scopes actually granted;
- authorized LinkedIn partner/product access;
- written-authorized automated collection for exact scope;
- analyst links/manual verification while machine access is being provisioned.

### Reddit

Implement official/licensed API collection for approved public communities and organization-level signals.

### Discord

Implement administrator-installed bot/connector and authorized-export ingestion paths.

### Additional community/professional sources

Implement useful paths for:

- Stack Exchange;
- Mastodon;
- Bluesky;
- YouTube Data API;
- conference/association directories;
- licensed B2B professional-contact providers.

Private messages and unrelated private-life data remain outside ordinary B2B research scope.

## Professional contact data

Permitted professional data may include:

- professional name;
- organization;
- current public professional role;
- department/seniority;
- buying-committee role;
- public/licensed business email;
- role mailbox;
- company switchboard/direct business number;
- permitted contact form.

Store provenance, purpose, collection/verification dates, retention, correction, objection and suppression state.

## Managed provider onboarding

Provider Onboarding is expected to eliminate as many manual prerequisites as the provider legitimately permits.

It should support:

- official account/service-account provisioning APIs;
- OAuth authorization;
- secret generation/storage;
- key rotation/revocation;
- contract/entitlement evidence;
- tenant/account identifiers;
- administrator connector installation state;
- approved mailbox verification workflows;
- human checkpoints for payment/KYC/contract acceptance/MFA;
- live-test readiness.

A useful provider requiring onboarding remains owned work until the real deployment prerequisite is completed.

### Email verification

An approved organization-controlled mailbox/alias may be used for provider onboarding. Verification processing must be scoped to the active transaction and expected provider.

Disposable mailboxes, fake identities and account multiplication to evade provider controls are not acceptable onboarding methods.

## Mandatory registry fields

Each source configuration should record at least:

```yaml
id: string
name: string
base_url: string
status: allowed | conditional | blocked
source_type: api | feed | website | browser | connector | local_tool | manual | licensed_dataset
owner: string
terms_url: string | null
licence: string | null
allowed_data_categories: []
prohibited_data_categories: []
rate_limit_per_minute: integer | null
retention_days: integer | null
attribution_required: boolean
raw_content_storage: boolean
human_review_required: boolean
activation_owner: string | null
target_sa: string | null
missing_prerequisite: string | null
live_test_required: boolean
notes: string
```

## BrixHub

`https://brixhub.cc/` remains a mandatory provider assessment and implementation candidate.

The project must determine:

- owner/operator;
- terms/privacy;
- data provenance;
- available datasets/fields;
- account/payment/API/browser/export paths;
- automation and commercial-reuse rights;
- quotas;
- retention/deletion obligations;
- legitimate sample access path.

If a legitimate useful path exists, the project must implement Provider Onboarding, source governance, schemas, adapter, runtime registration and controlled live validation. Uncertainty remains a prerequisite to resolve rather than a declaration that the capability is complete.

## Unknown or renamed sources

A materially changed provider returns to review, but useful capability ownership remains. The project must resolve the new owner/access contract and either re-activate the provider, migrate to a replacement, or explicitly exclude the capability by product decision.

## Live validation

A provider may be presented as fully integrated only after the production adapter completes a legitimate controlled live run where provider exercise is possible.

Mocks, fixtures, skipped workflows and successful compilation never count as live proof.