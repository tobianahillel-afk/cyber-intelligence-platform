# SA-14 closeout — governed search and archive discovery

## Decision

SA-14 is complete as an implementation wave.

The wave expanded the existing Lot 12 research/public-footprint path without creating a duplicate search/archive subsystem and preserved the central evidence invariant: provider search/index/publication/patent/standards metadata is discovery context, not independent corroboration or an automatic commercial conclusion.

Residual work that depends on provider credentials, contractual entitlements, or a not-yet-stable provider API has been handed to GitHub issue `#115` (`SA-15: promote deferred search providers and activate GDELT 5`).

## Final implemented provider state

| Provider | Source id | Implementation state | Live state | Checked-in schedule |
| --- | --- | --- | --- | --- |
| Common Crawl URL Index | `common-crawl-index` | production adapter merged | `live_tested` | enabled per governed schedule |
| GitHub REST Code Search metadata | `github-code-search-metadata` | production adapter merged | `live_tested` | disabled |
| Crossref ROR publication metadata | `crossref-publication-metadata` | production adapter merged | `live_tested` | disabled |
| PatentsView assignee patent metadata | `patentsview-patent-metadata` | production adapter merged | not `live_tested`; provider key dependency | disabled |
| W3C affiliation/specification metadata | `w3c-affiliation-specification-metadata` | production adapter merged | `live_tested` | disabled |
| Mojeek Web Search metadata | `mojeek-web-search-metadata` | production adapter merged | not `live_tested`; key + durable-storage entitlement dependency | disabled |

Existing Brave Search and Internet Archive/CDX capabilities remain authoritative and were not duplicated by SA-14.

## Merge history

The SA-14 implementation tranches were merged through independently validated pull requests:

- Common Crawl — PR `#109`, squash merge `56216ec4b13bc8f5dcbfa375ef81e05f7301f4d8`;
- GitHub Code Search — PR `#110`, squash merge `2050cb19b4edf7ae7b9aaeaf8e58753d1cd7e5cf`;
- Crossref — PR `#111`, squash merge `986dca271a1dea021c6fb6861480181b6a9b9bc5`;
- PatentsView — PR `#112`, squash merge `3bcf142aaaa3e4cd41b0ec5b034472f313a70a0a`;
- W3C — PR `#113`, squash merge `a30a5884922903e3a11ce53b2c31aa265e99e764`;
- Mojeek — PR `#114`, squash merge `4b6ec85cdffd59e569fe81ad32811a5262526bef`.

Every `live_tested` state above was earned through a real production-adapter provider run. Credential-dependent workflows that were skipped were never counted as live proof.

## Mojeek handoff

Mojeek is no longer an unimplemented candidate. SA-14 delivered its real production adapter, Source Governance entry, Provider Onboarding `api_key`, runtime registration, bounded metadata mapping, deterministic tests, disabled schedule, and an independent durable-storage-entitlement gate.

Source Activation intentionally stops at `executable`. Promotion to `live_tested` is deferred to `#115` until both prerequisites exist:

1. a legitimate provider API key;
2. reviewed contractual rights that permit the durable result metadata retained by CIP.

A credential alone is not proof of storage permission. A trial or plan that permits only short-lived caching must not be used for persistent CIP collection.

## PatentsView handoff

PatentsView is also production-wired and deterministically validated. Its real API requires `X-Api-Key`; current provider documentation indicates that new key grants are unavailable. Therefore Source Activation remains at `executable` and the disabled schedule remains unchanged.

`#115` owns the future exact-SHA production-adapter live proof when a legitimate provider key can be provisioned. No mock, synthetic secret, or skipped workflow may promote this source to `live_tested`.

## GDELT 5 handoff

GDELT remains a high-value news/event-discovery candidate, but SA-14 deliberately did not create a new production adapter against the legacy DOC/GEO 2.0 stack.

The provider announced on 2026-04-18 that GDELT 5 would migrate the API stack to Spanner. On 2026-06-30 the official GDELT blog still described the search/API transition as underway, and on 2026-07-04 the Television News Explorer relaunch was still described as upcoming. As of the SA-14 closeout review on 2026-08-11, the official project material reviewed for this decision did not document a stable replacement public GDELT 5 search/news API execution contract suitable for a provider-specific production adapter.

Official provider references used for the closeout decision:

- `https://blog.gdeltproject.org/scaling-gdelt-for-a-new-era-migrating-to-spanner-with-agentic-interactive-gemini/`
- `https://blog.gdeltproject.org/2026/06/`
- `https://blog.gdeltproject.org/using-gemini-to-prototype-the-future-of-the-television-news-visual-explorer/`
- `https://blog.gdeltproject.org/2026/`

`#115` owns re-verification and implementation when the provider publishes a stable current contract. The implementation must use that supported GDELT 5 contract and must not relabel a legacy endpoint merely to satisfy a checklist.

## Preserved invariants

The closeout does not change these SA-14 rules:

- search/index/news metadata is a discovery lead, not independent corroboration;
- an indexed URL or returned result is not proof of deployment, exposure, vulnerability applicability, compromise, cyber need, opportunity, or outreach authorization;
- provider payloads do not write directly to organization, score, alert, need, or opportunity tables;
- policy and authorization checks happen before network access;
- collection remains bounded, replay-safe, provenance-backed, and auditable;
- credentials and contractual entitlements are separate concerns;
- CAPTCHA, MFA, access controls, provider restrictions, or terms are never bypassed;
- source schedules remain disabled unless a deployment intentionally provisions the required targets, credentials/entitlements, and execution approval;
- `live_tested` requires a real exact-SHA provider proof using the production adapter;
- any later promotion-changing commit invalidates prior validation and must pass the normal repository gates again.

## Handoff

GitHub issue `#108` may be closed after this closeout document passes the repository's exact-head validation. All unresolved external dependencies from SA-14 are explicitly tracked by `#115`; closing `#108` must not be interpreted as claiming that Mojeek or PatentsView has been live-tested or that a GDELT 5 adapter already exists.
