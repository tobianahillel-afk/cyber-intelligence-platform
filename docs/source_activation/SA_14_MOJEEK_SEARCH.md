# SA-14 — Mojeek Web Search metadata discovery

## Status

Source id: `mojeek-web-search-metadata`.

Adapter id: `mojeek-web-search`.

Activation wave: `SA-14`.

The adapter is production-wired but is intentionally not `live_tested` and not scheduled while provider access and durable-storage entitlement remain unprovisioned.

## Provider contract

The selected provider endpoint is `https://api.mojeek.com/search`. The Web Search API requires an API key and supports JSON responses containing result URL, title and query-dependent description/snippet metadata.

Mojeek advertises a limited free trial, but storage rights are plan-specific. CIP therefore treats technical authentication and durable-storage permission as two independent requirements. A working API key does not by itself authorize persistent ingestion.

Checked-in `policies/mojeek_search_entitlement.yml` is fail-closed:

- `durable_storage_authorized: false`;
- `plan: unprovisioned`;
- no evidence reference.

Enabling durable storage requires an explicit reviewed evidence reference. Provider Onboarding separately supplies the `api_key` secret through the existing `connected_secret_supplier` boundary.

## Runtime boundary

The adapter reuses the governed public-web targets and approved search-query templates. It executes one enabled target/template pair at a time and requests at most 20 results.

Order of gates before network access:

1. enabled target/template pair exists;
2. Source Governance authorizes the request;
3. durable-storage entitlement is explicitly authorized;
4. a connected Mojeek API key exists;
5. only then may the HTTP request be sent.

If the storage entitlement is absent, the API-key supplier is not even called.

The runtime composition groups search/archive credential callbacks under immutable `SearchArchiveSecretProviders`, avoiding parameter-count growth as SA-14 gains providers.

## Data minimization

CIP materializes only:

- result URL;
- result title;
- query-dependent snippet/description;
- result rank;
- organization/query-template provenance.

The adapter does not fetch third-party page bodies, images, scores or other provider fields. Unsafe non-HTTP(S) result URLs are discarded. The API key is never stored in observations or projection metadata.

Each retained item becomes an immutable `RawObservation` plus the existing quarantined Lot 12 `SearchResultLead` projection. Search hits create zero automatic claims, signals, needs, opportunities or outreach authority.

## Live-validation requirement

`live_tested` may be added only after all of the following are true on an exact candidate SHA:

1. a legitimate Mojeek API key has been provisioned;
2. the reviewed provider entitlement explicitly permits the bounded persistent metadata retained by CIP;
3. `policies/mojeek_search_entitlement.yml` records that reviewed entitlement evidence;
4. a controlled GitHub Actions job executes the real production `MojeekSearchAdapter` against the provider;
5. the job proves bounded observations/projections, zero automatic claims and zero third-party page-body retrieval;
6. complete deterministic CI passes on the same final SHA.

A skipped live job, a mocked HTTP response, an unreviewed trial key, or a key whose storage rights are insufficient must never be represented as `live_tested`.
