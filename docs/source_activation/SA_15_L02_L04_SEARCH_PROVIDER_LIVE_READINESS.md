# SA-15 L02-L04 — Credentialed search-provider live readiness

## Current truth after the SA15 internal-completion and L06 runtime-readiness passes

Normal CI, mocks, deterministic adapter tests, missing-secret skips, entitlement gates, runtime registration and runner presence are not provider live proof.

### L02 — Mojeek

`MojeekSearchAdapter` and its production live runner are implemented. The runner constructs a valid governed `PublicWebTarget` with an explicit seed, so the target model no longer blocks execution before the provider call.

The source remains **not `live_tested`**. Real execution still requires both:

- a legitimate `MOJEEK_API_KEY`;
- reviewed durable-storage rights recorded in `policies/mojeek_search_entitlement.yml` with evidence.

The checked-in entitlement remains fail-closed. The controlled runner checks the storage entitlement before reading `MOJEEK_API_KEY`; no provider call may be used as persistent-ingestion proof until those rights are actually available.

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

`BraveSearchAdapter` and its live runner are implemented. The runner supplies an explicit governed seed and can reach the provider stage when a legitimate token exists.

Brave remains **not `live_tested`** because no real `BRAVE_SEARCH_API_TOKEN` has been provisioned/run through the workflow. A real non-empty provider response and complete exact-SHA CI/live validation are still required before activation promotion.

### L06 — Marginalia workflow presence after PR #136

Marginalia is now exposed by the same manual credentialed-provider workflow because its internal runtime adapter and controlled runner are present. This does **not** make it equivalent to the L02/L04 currently authorized/executable candidates.

Its checked-in Source Governance remains `draft` with authorization `missing`, its Source Portfolio entry remains `candidate` / `executable: false`, Source Activation remains `blocked`, and its commercial entitlement remains unprovisioned. The Marginalia runner therefore exists only as the controlled future execution path to use after legitimate commercial-use evidence, exact approved API2 scope and Provider Onboarding credentials are configured.

## Credentialed workflow

`.github/workflows/sa15-provider-live-validation.yml` exposes three manually selectable controlled runners:

- `brave` — implementation ready; legitimate subscription token still required;
- `mojeek` — implementation ready; legitimate key plus durable-storage entitlement still required;
- `marginalia` — runtime ready but deliberately fail-closed; commercial-use authorization/evidence, Provider Onboarding credential and approved API2 scope still required.

PatentsView is intentionally absent until the current USPTO ODP contract is implemented.

Merely appearing as a workflow option is not an activation stage and is not provider live proof. A skipped or blocked run does not satisfy `live_tested`.

## Activation matrix

| Source | Production implementation | Current route authorized/executable | External prerequisite | `live_tested` |
|---|---:|---:|---|---:|
| Brave Search | yes | yes | legitimate subscription token + controlled real run | no |
| Mojeek | yes | yes, entitlement-gated | legitimate key + durable-storage rights/evidence + controlled real run | no |
| Marginalia | yes, runtime-ready | **no; candidate/blocked** | commercial key + commercial-use evidence + approved API2 scope/onboarding + controlled real run | no |
| PatentsView legacy PatentSearch | historical adapter retained | **no; paused/revoked** | replace with current USPTO ODP contract | no |

No row may be promoted by association with another provider's successful workflow, by adapter presence, by CI alone or by a skipped provider workflow.
