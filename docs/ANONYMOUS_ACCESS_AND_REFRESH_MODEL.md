# Anonymous access and refresh model

## Product access model

Cyber Intelligence Platform is intended to be usable without end-user registration, login, password, or email collection.

A visitor receives an anonymous, short-lived platform session identifier used only for ordinary product behaviour such as navigation state, rate limiting, abuse prevention, saved filters for the current session, and request correlation. The identifier is not a person profile and must not be reused as an identity on external providers.

The platform must not create an external provider account for every visitor. External collection is performed by approved shared service identities, official APIs, open-data feeds, or provider-authorized machine integrations owned by the platform deployment.

## Separation of identities

The architecture separates three concepts:

1. `anonymous_session`: temporary identifier for a visitor using the product;
2. `platform_service_identity`: stable machine identity used by the deployment for an approved provider;
3. `source_credential`: secret reference, token, API key, or delegated authorization attached to that service identity.

An anonymous visitor must never receive, control, or be represented by a provider credential. Provider accounts and credentials belong to the deployment, are centrally governed, and are reused only within the provider licence, quota, purpose, and authorization boundaries.

## Collection model

The product is database-first, not crawl-on-every-page-view.

```text
approved provider or public source
  -> scheduled collector
  -> normalized observation
  -> PostgreSQL canonical storage
  -> projections, evidence, scores, and indexes
  -> anonymous read-only product experience
```

A page request reads current materialized data from the platform database and indexes. It does not normally trigger a live crawl of every source.

## Refresh scheduling

Each source and entity type must define a freshness policy with:

- target refresh interval;
- maximum acceptable staleness;
- provider quota and rate limit;
- cost and expected value;
- change frequency;
- retry and backoff policy;
- checkpoint and last-success timestamp;
- priority for user-requested entities;
- authorization-expiry handling.

Typical scheduling classes:

| Class | Intended cadence | Examples |
|---|---|---|
| `near_realtime` | minutes | urgent incident feeds, critical advisories, source health |
| `frequent` | tens of minutes to hours | active tenders, public job postings, rapidly changing news |
| `daily` | once or several times per day | organization pages, contracts, technography, public assets |
| `weekly` | several days | legal identity reconciliation, partner directories, slower sources |
| `event_driven` | provider webhook or approved notification | supported provider updates |
| `manual_priority` | queued refresh, not direct page-view crawling | analyst-requested company or source refresh |

The exact cadence is provider-specific and must stay inside the approved quota and collection policy.

## Cache and stale-data behaviour

Every displayed fact must expose its source timestamp, retrieval timestamp, freshness state, and confidence.

Suggested states:

- `fresh`;
- `aging`;
- `stale_refresh_queued`;
- `source_unavailable`;
- `authorization_expired`;
- `historical_only`.

When data is stale, the interface may enqueue a bounded priority refresh. It should still display the latest stored evidence with a clear stale label rather than blocking the user while crawling.

## Anonymous-user safeguards

Because no account is required on the product itself, the platform must still implement:

- privacy-preserving session identifiers;
- short retention for session telemetry;
- no cross-site identity correlation;
- no collection of visitor email or password;
- rate limiting and abuse controls;
- CSRF, origin, and request-integrity controls where relevant;
- read-only anonymous access by default;
- administrative operations isolated behind deployment-level administration controls;
- no exposure of provider secrets, raw source credentials, or onboarding consoles to anonymous visitors.

## Administrative bootstrap

Although ordinary visitors require no setup, a deployment still needs a one-time controlled bootstrap for infrastructure and governance, including:

- database and worker deployment;
- secret backend;
- source authorization registry;
- provider service identities where required;
- approved billing or licence configuration where applicable;
- collection schedules;
- retention and privacy policies.

This bootstrap belongs to the deployment operator, not to every visitor. After bootstrap, ordinary browsing and data retrieval remain accountless and database-backed.

## Non-goals

The platform must not:

- create a new external account for each anonymous visitor;
- use random visitor identities to evade provider account limits or attribution;
- crawl all providers on every page request;
- expose live provider sessions to visitors;
- couple product availability to the immediate availability of every external source;
- treat cached data as current without showing freshness and provenance.
