# SA-15 L06/L07 — Search diversity and governed dork library

## L06 — Marginalia Search API2

The independent-search capability remains **not live tested** and **not production-authorized**.

The production provider surface is the current API2 endpoint `https://api2.marginalia-search.com/search`; the shared `public` development key is rejected. Search-result payloads are discovery metadata only and remain quarantined; third-party page bodies are not fetched by the search adapter.

### Internal runtime readiness

The SA15 runtime-readiness pass closes the remaining internal implementation gap rather than promoting the provider:

- `MarginaliaSearchAdapter` now exists in `collection_orchestration` and maps bounded safe API2 results into immutable `RawObservation` records plus quarantined `SEARCH_RESULT` projections with zero claims;
- Source Governance is evaluated before commercial entitlement, secret resolution and network I/O;
- `MarginaliaSearchEntitlement` is loaded from a versioned checked-in policy and requires current API2 host, commercial-use rights, entitlement evidence and an API-key secret reference before live collection can proceed;
- the checked-in entitlement remains `commercial_use_rights: false`, `plan: unprovisioned`, with no evidence and no secret reference;
- the SA15 search-provider governance registry is now loaded by the collection runtime, and the Marginalia adapter is registered with the worker composition;
- the runtime secret supplier uses Provider Onboarding and returns no secret when Marginalia is not connected;
- a controlled `scripts/live_validate_sa15_marginalia.py` runner and manual workflow option are present for the future legitimate provider run;
- the controlled runner defers environment-secret resolution to the adapter, so the current `draft` / `authorization: missing` governance state denies execution before `MARGINALIA_API_KEY` is read;
- response bodies remain bounded while streaming at 2 MiB, and commercial entitlement is checked before any client network I/O.

Deterministic tests use a test-only in-memory authorization to exercise result mapping. They separately prove that the real checked-in governance state denies before secret/network. Test authorization is not production authorization.

### Current activation truth

The checked-in source remains:

`catalogued -> reviewed -> mapped -> adapter_present`

Source Governance remains `status: draft` with authorization `missing`, no approved hosts/paths/purposes and `automated_collection_allowed: false`. Source Activation remains `blocked`. No schedule or `live_tested` stage is added by this pass.

Remaining **external** prerequisites are a legitimate commercial API key, reviewed commercial-use/storage entitlement evidence, Provider Onboarding secret reference, explicit approved API2 host/path/purpose and deployment authorization. Only after those are present may the controlled production runner call the real provider; a non-empty provider result plus complete exact-SHA CI/live proof is still required before `live_tested` promotion.

## L07 — governed dork/query library

The version-2 library retains the required SA15 query families and operators. The internal-completion pass fixed the `site:` contract: domain-scoped templates use `{domain}` rather than interpolating the organization display name into `site:`.

`SearchQueryTemplate` supports exactly one of `{organization}` or `{domain}`. Domain templates require a bare canonical hostname; schemes, paths and whitespace are rejected. `SearchQueryPlan.from_template()` and the analyst Google URL renderer accept the explicit domain separately from the display name.

All checked-in templates remain disabled by default. The analyst Google URL renderer performs no network I/O and is not automated Google live proof.

## Completion truth

- **L07 internal implementation:** complete; the corrected implementation already passed the exact-final-head CI of the SA15 internal-completion merge.
- **L06 internal runtime implementation:** implemented and intentionally fail-closed; it must pass exact-final-head CI for this runtime-readiness PR before merge.
- **L06 provider activation/live proof:** still externally blocked and not `live_tested`.
