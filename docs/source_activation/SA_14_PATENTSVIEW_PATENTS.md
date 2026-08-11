# SA-14 — PatentsView patent discovery

## Objective

This tranche adds a real PatentsView PatentSearch adapter for bounded organization-targeted patent metadata. It extends the existing SA-14 search/archive runtime and does not create a patent-specific persistence subsystem.

Source id: `patentsview-patent-metadata`.

Adapter id: `patentsview-assignee-patents`.

## Targeting

`policies/patentsview_patent_targets.yml` is checked in empty. A target contains:

- a canonical CIP organization UUID;
- a stable internal target id;
- a canonical organization name for analyst context;
- one exact PatentsView `assignee_organization` label;
- an explicit enabled flag.

The adapter never performs global organization discovery. No enabled target means no provider secret read and no network request.

## Current provider contract

The adapter targets the current PatentsView PatentSearch endpoint:

`GET https://search.patentsview.org/api/v1/patent/`

Provider access requires `X-Api-Key`. Production runtime obtains that key through Provider Onboarding and the existing secret-supplier boundary:

`patentsview-patent-metadata / api_key -> connected_secret_supplier -> PatentsViewPatentAdapter`.

The organization query uses the PatentsView Query Language explicit equality operator:

`{"_eq":{"assignees.assignee_organization":"<configured assignee>"}}`

CIP additionally bounds the request to 20 results and asks only for:

- `patent_id`;
- `patent_title`;
- `patent_date`;
- `patent_type`;
- `assignees.assignee_organization`.

The client disables redirects and rejects non-JSON, responses larger than 2 MiB, schema drift and inconsistent provider envelopes. HTTP 429 and server failures are classified as retryable; malformed or unsafe responses fail closed.

## Data-minimization and evidence boundary

PatentsView can expose substantially richer patent data. This capability deliberately does not materialize:

- abstracts;
- patent claims;
- inventors or other person records;
- classifications;
- full text;
- patent documents or binary files.

A provider response is retained only if:

- the patent id contains no whitespace;
- the patent date is a valid ISO date;
- at least one returned assignee organization exactly matches the configured target, case-insensitively.

Each retained item emits one immutable `RawObservation` and one existing Lot 12 quarantined `SEARCH_RESULT` projection. The projection contains no candidate claim. Patent metadata therefore does not automatically prove current technology deployment, security exposure, vulnerability applicability, compromise, cyber need, commercial opportunity or outreach authority.

## Runtime and scheduling

The adapter is registered in the shared collection runtime through `search_archive_registration`. The SA-14 registration surface now uses immutable `SearchArchiveRegistrationInputs` so adding provider-specific registries does not grow the registration function beyond project architecture limits.

The checked-in PatentsView schedule is present but `enabled: false`. Source Activation therefore records the source through `executable`, but intentionally does not record `scheduled` or `live_tested`.

## Live-validation status

No live-provider proof is claimed in this tranche.

The current PatentsView service requires an API key, while provider documentation currently states that new API-key grants are temporarily suspended. CIP does not have a legitimate deployment key available in the checked-in repository or CI. Synthetic tests, mocks and successful normal CI are not substitutes for provider validation.

The terminal state for this PR is therefore:

- real provider-specific adapter: yes;
- Source Governance authorization: yes;
- Provider Onboarding path: yes;
- runtime executable when provisioned: yes;
- deterministic CI validated: required before merge;
- checked-in schedule enabled: no;
- controlled provider `live_tested`: no, outstanding until a legitimate key exists.

When a legitimate PatentsView key becomes available, the source must be live-tested on the exact release-candidate SHA using a controlled non-prospect target. Only a successful production-adapter run with real returned patent metadata can add the `live_tested` stage.

## Deterministic validation

Tests cover:

- empty checked-in target registry;
- no target -> no secret read and no network;
- missing API key -> `provider_not_connected` and no network;
- exact `_eq` assignee query shape and `X-Api-Key` header;
- 20-result bound and selected-field minimization;
- exact returned-assignee revalidation;
- invalid patent ids and dates;
- invalid checkpoints;
- schema drift;
- provider error envelopes;
- HTTP 429 retry classification;
- exclusion of abstract, claim and inventor structures from normalized material.

The PR may be squash-merged without a false live badge only if the complete deterministic repository CI is green on the exact final SHA and Source Activation continues to truthfully omit `live_tested`.
