# SA-15 L08 — GDELT current-contract gate

## Status

SA15-L08 is **not** an executable GDELT adapter and does not claim `adapter_present`, `executable`, or `live_tested`.

As reviewed on 2026-08-12, GDELT's own 2026 publications still describe GDELT 5 as an upcoming launch and describe the migration of the search/API infrastructure to Spanner as still underway. The repository therefore must not relabel the historical DOC/GEO 1.x/2.x APIs as a GDELT 5 implementation.

The checked-in truth is machine-readable in `policies/gdelt_api_contract.yml` and enforced by `cip.adapters.sources.gdelt.contract`.

## Official references reviewed

- `https://blog.gdeltproject.org/scaling-gdelt-for-a-new-era-migrating-to-spanner-with-agentic-interactive-gemini/`
- `https://blog.gdeltproject.org/2026/06/`
- `https://blog.gdeltproject.org/using-the-new-web-ngrams-dataset-to-find-relevant-coverage/`

Those references describe the GDELT 5 / Spanner migration state but do not provide the stable current API base URL, contract version, and schema reference required for a production provider adapter.

## Fail-closed contract

Current manifest state:

- product generation: `GDELT 5`;
- status: `awaiting_official_contract`;
- API base URL: unset;
- API version: unset;
- schema reference: unset;
- storage/retention terms reference: unset.

`GdeltApiContract.require_adapter_contract()` fails while that status remains pending.

A future `stable_public_contract` manifest is valid only when:

1. an actual API base URL is recorded;
2. an actual contract/version identifier is recorded;
3. an official schema/documentation reference is recorded;
4. all contract references use official HTTPS GDELT hosts;
5. the API base URL is not a legacy `/api/v1/` or `/api/v2/` endpoint.

The test values named `future-api`, `future-schema`, and `future-storage-terms` are deliberately synthetic unit-test values on the official hostname. They are not assertions that those paths exist.

## Why legacy DOC 2.0 is not used

The historical DOC 2.0 API is a real legacy GDELT interface, but implementing it now and calling it "GDELT 5" would make the activation inventory misleading and would bind CIP to an interface GDELT is actively replacing.

If product requirements later call for a temporary legacy-GDELT adapter as a distinct source, that adapter must have its own source ID, governance, lifecycle, and live proof. It must never satisfy the GDELT 5 completion gate.

## Exact exit criteria

When GDELT publishes the current stable API contract, L08 continues with a second implementation tranche:

1. re-review the official provider documentation;
2. update `policies/gdelt_api_contract.yml` with the real stable contract values;
3. document storage/retention rights;
4. add the governed source policy and authorization;
5. define provider-specific response schemas;
6. implement the isolated GDELT adapter;
7. register runtime/checkpoint/retry/quota behavior;
8. map provider results to discovery metadata / `RawObservation` without converting search results directly into facts;
9. add deterministic network-free tests;
10. add a controlled real-provider live-validation workflow;
11. obtain a non-empty real payload on the production adapter;
12. run complete exact-head CI on the same final SHA;
13. only then promote the source to `live_tested`.

Until those conditions are met, the correct state is a mandatory implementation prerequisite rather than a fabricated adapter or terminal abandonment.
