# SA-15 L06/L07 — Search diversity and governed dork library

## L06 — Marginalia Search API2

The current independent-search implementation remains **not live tested** and not production-authorized. The production client targets `https://api2.marginalia-search.com/search`; the shared `public` development key is rejected.

The SA15 internal-completion pass closes two post-merge defects:

- `MarginaliaSearchEntitlement.assert_live_collection_ready()` is now evaluated before query/key processing and before any network I/O, so a non-public development/test key cannot bypass commercial-use authorization;
- response bodies are read through a bounded streaming path and collection stops once the 2 MiB response limit would be exceeded, instead of downloading an oversized response first.

Deterministic tests prove that missing commercial entitlement prevents the HTTP transport from being reached.

Current proven state remains:

`catalogued -> reviewed -> mapped -> adapter_present`

Remaining external prerequisites are a legitimate commercial API key, commercial-use entitlement evidence, Provider Onboarding secret reference, exact deployment authorization, controlled real-endpoint validation, and exact-SHA CI/live proof. No `live_tested` promotion is made by this pass.

## L07 — governed dork/query library

The version-2 library retains the required SA15 query families and operators. The internal-completion pass fixes the `site:` contract: domain-scoped templates now use `{domain}` rather than interpolating the organization display name into `site:`.

`SearchQueryTemplate` supports exactly one of `{organization}` or `{domain}`. Domain templates require a bare canonical hostname; schemes, paths and whitespace are rejected. `SearchQueryPlan.from_template()` and the analyst Google URL renderer accept the explicit domain separately from the display name.

All checked-in templates remain disabled by default. The analyst Google URL renderer performs no network I/O and is not automated Google live proof.

## Completion truth

- **L07 internal implementation:** complete subject to exact-final-head CI for this pass.
- **L06 internal fail-closed implementation:** complete subject to exact-final-head CI, but provider activation remains externally blocked and not `live_tested`.
