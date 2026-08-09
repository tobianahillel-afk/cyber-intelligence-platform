# SA-02 — Search and archive provider authorization

## Purpose

This document is the reviewed authorization reference for the two external provider paths activated by SA-02:

- Brave Search API (`brave-search-api`);
- Internet Archive CDX (`internet-archive-cdx`).

It authorizes only the exact methods, hosts, paths, purposes and data categories described below. It does not authorize arbitrary web search, unrestricted crawling, browser automation, login/session reuse, collection from page views, or promotion of provider metadata directly into evidence or commercial conclusions.

## Common boundary

```text
provider candidate
!= execution authorization

search-result metadata
!= evidence

archive index metadata
!= current fact

historical capture
!= current urgency

provider authorization
!= enabled organization target
```

Every request still passes Source Governance and the shared collection runtime. Runtime execution additionally depends on exact adapter registration, Source Portfolio executable state, schedule state, quota/cost controls, and where required Provider Onboarding/secret availability.

No provider path in SA-02 may create a CommercialSignal, NeedHypothesis, score, Opportunity, contact target or outreach authorization.

## Brave Search API

### Approved method

- Official Brave Search API over HTTPS.
- Endpoint: `https://api.search.brave.com/res/v1/web/search`.
- Authentication: provider API token supplied through the existing Provider Onboarding secret-reference lifecycle.
- Secret name: `api_token`.
- The checked-in onboarding profile is `NOT_CONFIGURED`; no credential is stored in the repository.

### Approved scope

- Host: `api.search.brave.com`.
- Path: `/res/v1/web/search`.
- Purpose: `corporate-public-footprint`.
- Data category: `public_result_metadata`.
- Automation: permitted only after all runtime gates are positive.
- Raw provider payload storage: prohibited.
- Result count: bounded by the adapter.
- Redirect following: disabled.
- Search queries: only enabled `SearchQueryTemplate` values rendered against enabled, explicitly reviewed `PublicWebTarget` organizations.

The adapter cannot accept an arbitrary analyst-supplied query through its collection interface. If no enabled target/template pair exists, collection is a no-op. If the provider token cannot be resolved from a connected onboarding state, collection fails closed before network I/O with `provider_not_connected`.

### Secret handling

Only secret **references** are persisted. Supported local resolution mechanisms remain those already governed by Lot 09 (`env://`, `vault://`, `file-secret://` where a resolver is available). The Brave adapter receives a callable token supplier and resolves the value at collection time. The value is not written into source policy, source portfolio, observations, logs, checkpoints, evidence or provider metadata.

### Evidence semantics

Brave results are discovery leads only. Each result may create:

- a minimized RawObservation containing provider-published result metadata and a content hash;
- a Lot 12 `SearchResultLead` / `SEARCH_RESULT` resource in `QUARANTINED` retrieval state.

The mapping creates zero `PublicClaim` objects and does not independently corroborate the target page. A later approved retrieval path must fetch and evaluate the actual target content before it can become evidence.

### Schedule

The checked-in Brave schedule is disabled by default. A deployment must positively configure onboarding/secret state and explicitly enable the schedule after confirming plan, quota, licence/terms and target authorization.

## Internet Archive CDX

### Approved method

- Public Internet Archive CDX index over HTTPS.
- Endpoint: `https://web.archive.org/cdx/search/cdx`.
- Authentication: none.

### Approved scope

- Host: `web.archive.org`.
- Path: `/cdx/search/cdx`.
- Purpose: `archive-discovery`.
- Data category: `official_document_discovery`.
- Raw archived page storage: prohibited by this adapter.
- Result rows: bounded to a maximum of 50 deduplicated captures per target request.
- Target URL: only the base URL of an enabled, explicitly reviewed `PublicWebTarget`.
- Redirect following: disabled.

The CDX adapter queries metadata only. It does not fetch archived page bodies, replay pages in a browser, follow archived links recursively, or infer current state from a historical capture.

### Evidence semantics

A CDX row creates:

- a minimized RawObservation of the capture metadata;
- a Lot 12 `ARCHIVE_SNAPSHOT` resource in `QUARANTINED` state with explicit `capture_at` chronology.

The mapper creates zero claims. The capture timestamp is historical evidence context, not a current observation time. A historical snapshot is not current urgency, current deployment proof, current exposure, or current commercial intent.

### Schedule

The checked-in CDX schedule is weekly. With no enabled public-web target, the adapter is a no-op and performs no network request.

## Transport and schema controls

Both adapters enforce:

- HTTPS-only policy scope;
- bounded response sizes;
- no redirect following;
- explicit request timeouts;
- strict provider schema validation;
- deterministic checkpoint validation;
- retry only for transport failures, HTTP 429 and server-side 5xx failures;
- fail-closed behavior for schema drift, policy denial, invalid checkpoints or missing provider connection.

Unit tests use `httpx.MockTransport`; they never make live provider requests.

## Explicitly not authorized

SA-02 does not authorize:

- Google/Bing/other search automation that lacks a separately approved provider contract;
- arbitrary dork generation or arbitrary analyst query execution by the worker;
- unrestricted recursive crawling;
- browser automation;
- login automation;
- copied cookies or authenticated sessions;
- CAPTCHA, MFA, paywall or access-control bypass;
- proxy rotation or ban evasion;
- archive page-body collection through CDX;
- current-fact inference from archive metadata;
- direct result-to-evidence, result-to-signal or result-to-opportunity promotion;
- autonomous outreach.

## Review and revocation

Authorization is implemented through versioned Source Governance and Provider Onboarding/Portfolio state. Removing approved hosts/paths/purposes, revoking provider authorization, disabling a schedule, pausing the source, exhausting quota/cost controls, or disconnecting the Brave secret path prevents subsequent automated execution without deleting historical provenance.
