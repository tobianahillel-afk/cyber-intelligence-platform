# SA-15 L02-L04 — Credentialed search-provider live readiness

## Current truth after the SA15 internal-completion pass

Normal CI, mocks, deterministic adapter tests, missing-secret skips and runner presence are not provider live proof.

### L02 — Mojeek

`MojeekSearchAdapter` and its production live runner remain implemented. The runner now constructs a valid governed `PublicWebTarget` with an explicit seed, so the target model no longer blocks execution before the provider call.

The source remains **not `live_tested`**. Real execution still requires both:

- a legitimate `MOJEEK_API_KEY`;
- reviewed durable-storage rights recorded in `policies/mojeek_search_entitlement.yml` with evidence.

The checked-in entitlement remains fail-closed. No provider call may be used as persistent-ingestion proof until those rights are actually available.

### L03 — PatentsView

The old PatentSearch route is no longer considered a current executable production route. C2 established that PatentsView access has moved to the USPTO Open Data Portal and a controlled attempt against the historical bulk path returned HTTP 403.

The internal-completion pass therefore:

- pauses the legacy source policy;
- revokes its network authorization;
- removes `authorized` and `executable` from Source Activation;
- marks the Source Portfolio entry paused/non-executable;
- removes PatentsView from the credentialed SA15 workflow;
- makes `scripts/live_validate_sa15_patentsview.py` fail before reading any credential or performing network I/O.

The historical adapter code is retained as implementation history only. It must not receive a future ODP credential. PatentsView remains **not `live_tested`** until the current ODP endpoint/schema/terms/credential model is reviewed, implemented and successfully exercised on an exact candidate SHA.

### L04 — Brave Search

`BraveSearchAdapter` and its live runner remain implemented. The runner now supplies an explicit governed seed and can reach the provider stage when a legitimate token exists.

Brave remains **not `live_tested`** because no real `BRAVE_SEARCH_API_TOKEN` has been provisioned/run through the workflow. A real provider response and complete exact-SHA CI are still required before activation promotion.

## Credentialed workflow

`.github/workflows/sa15-provider-live-validation.yml` now exposes only the currently legitimate runnable credentialed candidates:

- `brave`;
- `mojeek`.

PatentsView is intentionally absent until the current ODP contract is implemented.

## Activation matrix

| Source | Production implementation | Current route authorized/executable | External prerequisite | `live_tested` |
|---|---:|---:|---|---:|
| Brave Search | yes | yes | legitimate subscription token + real run | no |
| Mojeek | yes | yes, entitlement-gated | legitimate key + durable-storage rights + real run | no |
| PatentsView legacy PatentSearch | historical adapter retained | **no; paused/revoked** | replace with current USPTO ODP contract | no |

No row may be promoted by association with another provider's successful workflow.
