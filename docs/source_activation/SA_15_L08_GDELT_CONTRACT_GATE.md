# SA-15 L08 — GDELT current-contract gate

## Status

SA15-L08 still does **not** provide an executable GDELT 5 adapter and does not claim `adapter_present`, `executable` or `live_tested`.

As reviewed on 2026-08-12, the repository still lacks the stable official current GDELT 5 public API contract required for a provider-specific production implementation. Historical DOC/GEO APIs must not be relabeled as GDELT 5.

## Fail-closed contract

`policies/gdelt_api_contract.yml` remains `awaiting_official_contract`. The internal-completion pass hardens `cip.adapters.sources.gdelt.contract` so a future stable manifest can open the implementation gate only when:

- `product_generation` is exactly `GDELT 5` after normalization;
- a real API base URL exists;
- the contract/API version is nonblank after trimming;
- official schema documentation is recorded;
- official storage/retention terms are recorded;
- all provider references use HTTPS on `gdeltproject.org` or an exact subdomain;
- lookalike hosts are rejected;
- `/api/v1`, `/api/v2` and their descendants are rejected whether or not a trailing slash is present.

Deterministic tests cover the pending state, exact product generation, whitespace-only versions, storage-terms host validation, lookalike hosts and legacy API roots.

## External blocker and continuation

No further honest provider adapter can be implemented until GDELT publishes a sufficiently stable current GDELT 5 execution contract. When that happens, L08 must continue with a second implementation tranche: re-review official docs, record the real endpoint/version/schema/terms, add Source Governance, implement the provider schemas/adapter/runtime/checkpoint behavior, add network-free tests, obtain a non-empty controlled real-provider result, and pass exact-final-SHA CI before any `live_tested` promotion.

The current state is therefore **internally hardened but externally contract-blocked**.
