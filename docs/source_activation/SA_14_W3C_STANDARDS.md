# SA-14 — W3C affiliation standards discovery

## Status

Source id: `w3c-affiliation-specification-metadata`.

Adapter id: `w3c-affiliation-specifications`.

Activation wave: `SA-14`.

This capability is a governed, target-bound discovery adapter for public W3C affiliation, group-participation and specification metadata. It does not collect people and it does not retrieve specification bodies.

The W3C API used by this adapter is public, read-only and requires no provider credential. Consequently there is no W3C API key to create or store in Provider Onboarding for this source.

## Purpose and evidence boundary

The capability answers a narrow discovery question: for an explicitly configured W3C affiliation, which W3C groups publicly list that affiliation as participating, and which specifications are publicly listed for those groups?

A returned relationship remains discovery metadata. It does not establish that the target organization authored, owns, endorses, deploys or is currently implementing a specification. It also does not establish vulnerability applicability, compromise, security maturity, commercial need, an opportunity or outreach authorization.

Every accepted result therefore becomes:

- one immutable `RawObservation` containing only the normalized metadata fingerprint;
- one quarantined Lot 12 `SEARCH_RESULT` public-footprint projection;
- zero candidate `PublicClaim` objects;
- zero automatic signals, needs, opportunities or outreach actions.

## Target governance

Targets are defined in `policies/w3c_affiliation_targets.yml` as an explicit tuple of:

- CIP canonical `organization_id`;
- human-reviewed `canonical_name`;
- numeric W3C `affiliation_id`;
- local `target_id`;
- `enabled` flag.

The checked-in registry is empty. Registering the adapter cannot therefore trigger organization discovery by itself.

Before secondary traversal, the production client fetches `GET /affiliations/{id}` and compares the provider-returned affiliation name with the configured canonical name using whitespace-normalized, case-insensitive equality. A mismatch fails closed with `target_identity_mismatch`. No participation or group request is made after that mismatch.

This prevents a stale or incorrectly provisioned numeric affiliation id from silently collecting metadata for another organization.

## Provider traversal

The production path is limited to the following public read-only relationship chain:

1. `GET https://api.w3.org/affiliations/{affiliation_id}`;
2. `GET /affiliations/{affiliation_id}/participations?items=20&page=1&embed=1`;
3. follow only an HTTPS `api.w3.org/groups/<type>/<shortname>` `group` link;
4. `GET /groups/<type>/<shortname>/specifications?items=20&page=1&embed=1`.

W3C HAL collection resources require `embed=1` for the objects used by this adapter. That behavior was confirmed against the real provider before the production schema was finalized.

The adapter never follows participation links such as participants or other person-bearing relationships. It never calls endpoints for users, chairs, team contacts or editors.

## Bounded execution

The provider client is bounded by all of the following controls:

- HTTPS `api.w3.org` only;
- exact `/affiliations` root validation;
- redirects disabled;
- JSON responses only;
- maximum response body of 2 MiB per request;
- at most 20 participation records requested for the target;
- at most 5 valid W3C groups traversed per collection;
- at most 20 unique specification records emitted across all traversed groups;
- group links must match exactly `/groups/<type>/<shortname>` with no query or fragment;
- off-host group links are discarded;
- duplicate group/specification identities are removed before persistence.

HTTP 429 and server failures are typed as retryable. Transport failures are retryable. Unsafe response types/sizes, schema drift, invalid checkpoints and identity mismatches fail closed.

## Data minimization

The materialized provider schema is intentionally narrower than the W3C API response.

CIP retains only the fields needed to establish the public metadata relationship:

- target affiliation id and configured canonical name;
- W3C group type and group shortname;
- specification shortname;
- specification title;
- a safe W3C specification/document URL;
- provider request URL as observation provenance.

The adapter does not materialize or persist:

- participants;
- W3C users;
- chairs;
- team contacts;
- editors;
- specification versions;
- specification bodies;
- unrelated affiliation profile fields.

The preferred public-resource URL is a specification `shortlink` only when it is HTTPS on `w3.org` or `www.w3.org`. The fallback is the specification HAL `self` link only when it is HTTPS `api.w3.org/specifications/...` without query or fragment. Unsafe/off-host result URLs are discarded.

Each projection excerpt explicitly states that participants, editors, versions and specification body were not retrieved.

## Controlled provider discovery used to establish the schema

Before the adapter was written, a temporary schema probe was used only to understand the current public HAL representation. The probe was removed before the production live-validation stage.

The real provider exposed the following controlled relationship:

- affiliation: Lawrence Berkeley National Laboratory, W3C affiliation id `1015`;
- group: Devices and Sensors Working Group, id `43696`, shortname `das`, type `wg`;
- group specification collection: `/groups/wg/das/specifications`;
- observed specification example: `dap-api-reqs` — `Device APIs Requirements`.

No person endpoint was required to discover or validate this relationship.

## Production-adapter live validation

The dedicated `.github/workflows/sa14-live-validation.yml` job `live-w3c-standards` runs `scripts/live_validate_sa14_w3c.py`. The script instantiates the production `W3cStandardAdapter`; it does not use a provider mock or the removed schema probe.

The controlled live target is Lawrence Berkeley National Laboratory (`affiliation_id=1015`). It is used only to exercise the public provider contract and metadata boundary.

On source head `d50392bedad80a7d8ddbb7908a091b4f0eaee77c`, the real production adapter completed successfully and produced:

- provider-backed observations: `20`;
- quarantined public-footprint projections: `20`;
- claims: `0`;
- person endpoint fetches: `0`;
- specification-body fetches: `0`.

The live validator additionally asserts that every result remains quarantined and every public-resource URL stays inside the approved W3C URL boundary.

This real provider proof, together with the complete deterministic repository CI on the same source head, justifies recording `live_tested` for W3C. It does not justify the `scheduled` stage because the checked-in schedule remains disabled by default.

## Deterministic validation

The W3C tests cover the critical fail-closed boundaries:

- checked-in target registry is empty;
- disabled/no target performs zero network requests;
- exact affiliation identity is required before participation traversal;
- participation requests use bounded `items=20` and `embed=1`;
- only approved W3C group links are followed;
- person-bearing `participants` links are not followed;
- off-host groups are ignored;
- unsafe specification URLs are discarded;
- results are quarantined and carry zero claims;
- invalid checkpoints fail closed;
- malformed provider JSON is classified as schema drift;
- HTTP 429 is retryable.

On `d50392bedad80a7d8ddbb7908a091b4f0eaee77c`, repository CI also passed with:

- `1378` tests;
- `90.03%` branch-aware coverage;
- strict Mypy over `667` source files;
- `36` architecture/release contract tests;
- reversible Alembic migrations;
- dependency consistency and `pip-audit`;
- frontend audit, typecheck and build.

## Runtime and scheduling

W3C targets are loaded through the normal `Settings -> AdapterCompositionInputs -> SearchArchiveRegistrationInputs -> register_search_archive_adapters()` composition path. No parallel worker, database silo or source-specific scheduler is introduced.

The PatentsView tranche previously introduced immutable `SearchArchiveRegistrationInputs`; W3C extends that structure rather than enlarging the registration function signature.

The checked-in W3C collection schedule exists but remains `enabled: false`. A deployment must explicitly provision an enabled canonical-organization target and deliberately enable execution before scheduled collection can occur.

## Activation truth

The legitimate W3C activation stages are:

- `catalogued`;
- `reviewed`;
- `mapped`;
- `adapter_present`;
- `authorized`;
- `executable`;
- `live_tested`.

`scheduled` is intentionally absent while the checked-in schedule remains disabled.

The final documentation/activation promotion changes the candidate SHA. Therefore the complete deterministic CI and the real W3C production-adapter live workflow must pass again on the exact final PR head before squash merge.
