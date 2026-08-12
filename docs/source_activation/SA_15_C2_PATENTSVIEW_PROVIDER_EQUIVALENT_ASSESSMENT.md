# SA-15 C2 — PatentsView provider-equivalent assessment

## Outcome

C2 is complete as an **assessment and fail-closed transition**, not as a PatentsView live promotion.

The capability remains **not `live_tested`**. A real historical provider-equivalent attempt reached the PatentsView bulk S3 path and returned HTTP 403. Current PatentsView access has moved to the USPTO Open Data Portal (ODP), which requires legitimate current provider access/credentials and a fresh contract/schema review.

## Internal-completion hardening

A post-merge review identified that the historical `https://search.patentsview.org/api/v1/patent/` route was still enabled/authorized. That could have caused a future current-provider credential to be sent to a legacy endpoint.

The SA15 internal-completion pass fixes this by making the legacy route fail closed at every checked-in execution layer:

- Source Governance: source `paused`, authorization `revoked`, no approved hosts/paths/purposes, automation disabled;
- Source Activation: `blocked`, with only `catalogued -> reviewed -> mapped -> adapter_present` retained;
- Source Portfolio: `paused`, `executable: false`, `authorization_status: revoked`, current contract explicitly `USPTO_ODP`;
- credentialed SA15 workflow: PatentsView removed;
- legacy live runner: stops before reading `PATENTSVIEW_API_KEY` or constructing the historical adapter.

The old adapter remains in the repository only as reviewed implementation history. It is not an authorized production route.

## Exact external prerequisite

PatentsView activation can resume only when all of the following are available:

1. legitimate deployment-owner USPTO.gov / ODP access;
2. current provider-issued API credential or officially documented equivalent;
3. reviewed current ODP API endpoint, schema and storage/use terms;
4. a provider-specific implementation updated to that current contract;
5. controlled non-empty organization-bound real-provider validation;
6. bounded/quarantined projections with provenance and zero unsupported claims;
7. complete repository CI on the same final SHA;
8. only then, a truthful `live_tested` promotion.

Historical archives, mocks, skipped workflows and the HTTP 403 attempt do not satisfy the current-provider live gate.
