# Social and Community Acquisition Requirements

## Status

This document is normative for future social, professional-community and community-platform acquisition work. It complements `OSINT_FULL_IMPLEMENTATION_MANDATE.md` and is authoritative for source-activation planning together with the Source Policy.

The target is not a documentation-only placeholder. LinkedIn, Reddit, Discord, BrixHub and other high-value professional/community sources must receive concrete provider-specific implementation paths, production adapters, runtime integration and controlled live validation when a legitimate access path exists.

## Commercial research purpose

The supported purpose is professional and organization-level cyber-commercial intelligence, including evidence about:

- technologies and security products used, evaluated or discussed;
- cloud, identity, endpoint, network, DevSecOps, SOC, SIEM, MDR, EDR/XDR, IAM/PAM and security tooling;
- hiring and team-growth signals;
- public or consented technical discussions;
- public professional roles and organization affiliations;
- vendor/provider relationships;
- migrations, integrations, incidents, operational problems and technology replacement discussions;
- public procurement, implementation and architecture context;
- professional communities relevant to a named organization or service family.

Political opinions, religion, health, private-life behavior, family relationships and unrelated sensitive traits are not target signal classes.

## Canonical social evidence model

Every provider must map into explicit source-aware records rather than directly creating an opportunity.

Minimum provenance for a social/community observation:

```text
provider
source_account_or_server_id
source_channel_or_container_id
source_record_id
source_url_or_provider_locator
observed_at
published_at
collected_at
public_or_consented_scope
organization_candidate
professional_role_candidate
pseudonymous_handle
content_excerpt_or_structured_signal
technology_mentions
vendor_mentions
service_family_mentions
confidence
retention_class
source_revision
```

A message, profile or username is evidence from that source. It is not automatically proof of a person's legal identity, employment, technology deployment or purchasing authority.

## LinkedIn implementation requirement

LinkedIn is a mandatory professional-context capability.

The implementation must support every legitimate access route that can be obtained for a deployment, including:

- official API scopes;
- approved partner or licensed products;
- written-authorized automated browser collection for exact hosts, fields and purpose;
- user-delegated authenticated browser sessions where the provider authorizes that automation;
- analyst-assisted verification when an automated scope is not available yet.

Where an authorized browser route exists, the production browser adapter must be capable of extracting provider-approved professional fields from rendered pages, including:

- company pages;
- public professional profiles;
- current role/title/organization;
- public business contact links where present and permitted;
- company posts and public professional posts relevant to organization or technology research;
- public job/recruiting context;
- public product, vendor, integration and technology references;
- rendered DOM fields;
- JSON-LD or public embedded JSON state used by the page;
- stable provider record identifiers and canonical URLs.

The adapter must not depend on brittle screenshot-only extraction when structured page state is available.

LinkedIn activation is not complete until at least one real deployment access route is production-wired and live-tested. A missing partner scope, account or written authorization remains an open prerequisite rather than a terminal exclusion.

## Reddit implementation requirement

Reddit is a mandatory community-intelligence source.

The preferred implementation is an official or licensed API path for public communities and provider-authorized data.

Required capabilities include:

- subreddit/community discovery relevant to cybersecurity technologies and named organizations;
- public post retrieval;
- public comment retrieval within provider quotas;
- thread chronology;
- username/handle preservation as a pseudonymous provider identifier;
- technology/vendor/product mention extraction;
- organization and professional-role candidate extraction when explicitly self-declared in the source;
- link/domain extraction;
- deletion/edit/revision handling;
- retention and suppression;
- source-level rate-limit and checkpoint handling;
- controlled live validation against public, non-sensitive test communities.

The system may aggregate public professional/technical signals at organization or product level. It must not secretly deanonymize pseudonymous users or infer private identity from unrelated cross-platform activity.

## Discord implementation requirement

Discord is a mandatory community-intelligence source through consented server access.

The production implementation must support an administrator-installed application/bot and authorized export ingestion.

### Bot capabilities

For a server where the bot has been explicitly installed and granted permissions, it must support:

- enumerating authorized guild/server metadata;
- enumerating authorized channels;
- reading message history only in channels the bot is permitted to read;
- incremental collection through message identifiers/timestamps;
- usernames, display names and server-scoped member identifiers when exposed through granted permissions;
- message edits/deletions where the API exposes them;
- thread messages;
- links, domains and attachment metadata where permitted;
- technology/product/vendor/tool mention extraction;
- organization/team/project references;
- role and channel context;
- provenance and retention controls;
- server/channel kill switch;
- rate-limit handling and replay-safe checkpoints.

The commercial output should focus on organization-level and professional technical signals such as:

- which tools are being discussed or used;
- implementation or migration problems;
- security-stack changes;
- SOC/SIEM/EDR/IAM/cloud/AppSec tooling;
- integration problems;
- hiring or capability gaps;
- vendor replacement or evaluation discussions;
- public/consented incident or operational context.

### Identity boundary

A Discord username or handle remains a provider-scoped identity unless one of these conditions exists:

- the user explicitly self-declares another professional identity/account;
- an administrator-provided directory maps the identity;
- the user has consented to account linking;
- another licensed/authorized source provides an explicit professional identifier match.

The product must not perform covert cross-platform deanonymization of a pseudonymous handle.

Private messages are not part of ordinary server-bot collection unless the exact participants and deployment have separately consented to that specific integration.

## BrixHub.cc implementation requirement

`https://brixhub.cc/` is a mandatory source-activation target and must not remain a generic review-only placeholder.

The implementation programme must establish and document:

- operator/owner identity;
- current access and registration flow;
- provider terms and privacy terms;
- datasets and field inventory;
- account, API, export and browser paths;
- authentication/session requirements;
- automation rights;
- storage/reuse rights;
- commercial-use rights;
- rate limits and quotas;
- retention/deletion requirements;
- provider-specific source identifiers;
- safe live-validation target and acceptance criteria.

If an API exists, implement the API adapter. If the provider's authorized product flow is browser-only, implement a provider-specific isolated browser adapter. If both exist, prefer the API for stable collection and retain the browser path for fields that are legitimately available only after rendering.

BrixHub is not complete until a real provider-specific access path has been implemented and live-tested, or the product owner explicitly removes it from the product target.

## Additional community sources

The same production standard applies to useful sources including:

- Stack Exchange;
- Mastodon;
- Bluesky;
- YouTube Data API and permitted transcript/metadata sources;
- public vendor forums;
- conference and association directories;
- professional community platforms;
- licensed B2B contact/professional datasets.

## User-delegated account model

The product must support user-delegated provider identities where an external service requires an account.

A user-delegated account is tied to the authenticated CIP tenant/user or deployment service identity and must have:

- provider account identifier;
- owning CIP tenant/user or service principal;
- purpose and source authorization;
- isolated secret/session reference;
- creation/authorization timestamp;
- scopes and permissions;
- renewal/expiry state;
- revocation and deletion workflow;
- audit trail.

Where the provider explicitly supports automated account creation, CIP may automate registration using a durable tenant-controlled email alias or provider-approved service-account mechanism.

Ephemeral aliases may be used for lifecycle isolation when they remain controlled by the real deploying organization and the provider permits them. Disposable third-party mailboxes or account rotation must not be used to evade trials, quotas, bans, identity checks, CAPTCHA, MFA or other provider controls.

## CAPTCHA and MFA in legitimate accounts

CAPTCHA and MFA are supported workflow states for legitimate accounts.

Required behavior:

```text
automation reaches challenge
-> persist resumable browser state securely
-> create human/provider-approved checkpoint
-> user completes CAPTCHA/MFA
-> verify successful session transition
-> resume the same governed acquisition job
```

The application should minimize manual effort and resume automatically after the legitimate challenge is completed. It must not solve or bypass security challenges to obtain access the user/provider has not granted.

## Live validation requirement

Each implemented social/community provider must have a controlled live test proving the production adapter can retrieve real non-empty provider data within an approved scope.

The live test must validate:

- authentication/connector installation if required;
- provider schema compatibility;
- pagination/checkpoints;
- edits/deletions where applicable;
- provenance;
- technology-signal extraction;
- zero secret leakage;
- tenant/source isolation;
- no direct promotion from raw message/profile data to a confirmed company fact without the evidence pipeline.

Fixtures and mocks do not satisfy this requirement.
