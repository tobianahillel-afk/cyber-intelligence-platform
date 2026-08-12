# SA-15 L02-L04 — Credentialed search-provider live readiness

## Status

This tranche completes the production live-validation path for:

- SA15-L02 — Mojeek Web Search API metadata;
- SA15-L03 — PatentsView assignee patent metadata;
- SA15-L04 — Brave Search API metadata.

It does **not** claim `live_tested` for any of the three providers. The checked-in activation inventory must continue to omit that stage until a real provider call succeeds on an exact candidate SHA with the required legitimate credential/entitlement/target prerequisites.

Normal CI, mocks, deterministic adapter tests, a missing-secret skip, or a manually successful workflow that did not execute the production adapter are never provider proof.

## Common live-proof contract

`.github/workflows/sa15-provider-live-validation.yml` is a manually dispatched, credentialed validation workflow. It checks out the exact selected ref, installs the production package, and invokes one of the provider-specific runners under `scripts/`.

A successful provider proof must show all of the following:

1. the real production adapter performed the network request;
2. the real provider returned at least one normalized record;
3. no more than the adapter's 20-result bound was retained;
4. observation and projection counts match;
5. source provenance is preserved;
6. all projections remain quarantined discovery metadata;
7. zero automatic claims are created;
8. no third-party page body is fetched through the search adapter;
9. the single controlled target/checkpoint converges;
10. no provider secret is printed or stored in an observation/projection.

Only after the provider-specific live run and the complete repository CI pass on the same final candidate SHA may a separate activation change add `live_tested`.

## SA15-L02 — Mojeek

Production source id: `mojeek-web-search-metadata`.

Production adapter: `MojeekSearchAdapter`.

Provider endpoint: `https://api.mojeek.com/search`.

Current provider documentation requires an API key. Current commercial plan information distinguishes durable storage rights: the Business plan advertises storage rights, while other plan/storage combinations are plan-specific. CIP therefore retains the existing two independent gates:

- legitimate provider API key;
- reviewed durable-storage entitlement for the bounded URL/title/query-dependent snippet/rank metadata retained by CIP.

`scripts/live_validate_sa15_mojeek.py` loads `policies/mojeek_search_entitlement.yml` before reading `MOJEEK_API_KEY`. The checked-in policy remains deliberately fail-closed:

- `durable_storage_authorized: false`;
- `plan: unprovisioned`;
- `evidence_reference: null`.

Therefore the current exact repository state cannot truthfully perform or claim the Mojeek persistent-ingestion live proof. Once a legitimate plan with sufficient storage rights is acquired/reviewed, that entitlement must first be recorded with its evidence reference; only then may the controlled live runner consume `MOJEEK_API_KEY` and contact the provider.

## SA15-L03 — PatentsView

Production source id: `patentsview-patent-metadata`.

Production adapter: `PatentsViewPatentAdapter`.

Provider endpoint: `https://search.patentsview.org/api/v1/patent/`.

The current PatentSearch documentation requires `X-Api-Key`, documents a 45-request/minute key limit, and currently states that new API-key grants are temporarily suspended. The existing production adapter already sends the correct header, uses the explicit assignee equality query, bounds results to 20, minimizes fields, and revalidates returned assignee identity before materialization.

`scripts/live_validate_sa15_patentsview.py` additionally requires:

- `PATENTSVIEW_API_KEY`;
- `SA15_PATENTSVIEW_ASSIGNEE`, containing an exact provider `assignee_organization` known to return data;
- optional `SA15_PATENTSVIEW_CANONICAL_NAME` for analyst-readable context.

The checked-in production target registry remains empty. A live-validation assignee is intentionally provided only at controlled run time so this readiness tranche does not silently establish a production/prospect target. Until a legitimate provider key exists, PatentsView remains executable-but-not-live.

## SA15-L04 — Brave Search

Production source id: `brave-search-api`.

Production adapter: `BraveSearchAdapter`.

Provider endpoint: `https://api.search.brave.com/res/v1/web/search`.

Current Brave Search API documentation requires the `X-Subscription-Token` header and documents a maximum `count` of 20 results per page. The production adapter already uses that header and the same 20-result bound.

`scripts/live_validate_sa15_brave.py` requires `BRAVE_SEARCH_API_TOKEN` and uses a controlled organization name/URL supplied by the workflow. Defaults are the public Internet Archive organization and `https://archive.org/`; operators may replace those inputs with another approved neutral/first-party validation target.

A real subscription token is the remaining live-provider prerequisite. The repository never embeds or echoes it.

## Workflow inputs and secrets

Manual workflow inputs:

- provider: `brave`, `mojeek`, or `patentsview`;
- controlled organization name;
- controlled organization URL;
- exact PatentsView assignee when PatentsView is selected.

Repository/environment secrets consumed only at execution time:

- `BRAVE_SEARCH_API_TOKEN`;
- `MOJEEK_API_KEY`;
- `PATENTSVIEW_API_KEY`.

No secret value is accepted through a workflow input, command-line argument, checked-in YAML, query-template record, observation, projection, or documentation file.

## Activation truth after this tranche

Expected source truth remains:

| Source | Adapter | Authorized | Executable | Credential/entitlement ready | `live_tested` |
|---|---:|---:|---:|---:|---:|
| Brave Search | yes | yes | yes | no deployment token in repository | no |
| Mojeek | yes | yes | yes | no approved durable-storage entitlement/key | no |
| PatentsView | yes | yes | yes | no legitimate deployment key/production target | no |

The next change for any one of these rows is a provider-specific live-proof/promotion commit, not another mocked adapter implementation.
