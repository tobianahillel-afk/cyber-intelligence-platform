# SA-15 C2 — PatentsView provider-equivalent assessment

## Outcome

C2 is complete as an **assessment and blocker-resolution tranche**, not as a PatentsView live promotion.

The PatentsView capability remains **not `live_tested`**. No API, bulk-download, browser, mock, skipped workflow, readiness state, or historical archive is being relabeled as a successful production PatentsView run.

## What was tested in production

A candidate provider-equivalent implementation was built against the historical official PatentsView bulk artifact path:

- `https://s3.amazonaws.com/data.patentsview.org/download/g_assignee_disambiguated.tsv.zip`
- `https://s3.amazonaws.com/data.patentsview.org/download/g_patent.tsv.zip`

The production GitHub Actions run reached the provider and received **HTTP 403 Forbidden** on the first assignee artifact. This is treated as a real negative live result, not as live success and not as a condition that can be ignored or mocked away.

The experimental S3 runtime implementation was therefore removed from the final C2 candidate rather than merging a dead provider path.

## Current provider state

PatentsView data access has moved to the USPTO Open Data Portal (ODP). The current provider path requires legitimate USPTO.gov access, and API use requires provider-issued credentials/API-key authorization.

CIP must therefore fail closed until a legitimate current ODP account/key and the applicable provider terms are available for controlled validation. A missing account/key is a prerequisite, not a completed activation state.

## Historical archives are not an equivalent live replacement

Older public PatentsView releases and mirrors may remain useful for historical research, deterministic fixtures, or backfill after a separate governance review. They do **not** satisfy C2's current-provider live requirement because they are not the current production data-access path and may lag the provider's latest published corpus.

Accordingly, CIP must not use a stale historical release to mark the current PatentsView capability `live_tested`.

## Existing API adapter

The existing `patentsview-patent-metadata` adapter remains the authoritative current PatentsView query implementation in CIP. It continues to:

- require a real provider API key;
- fail closed with `provider_not_connected` when the key is absent;
- retain only bounded patent metadata;
- revalidate returned assignee identity before persistence;
- produce quarantined discovery metadata rather than direct commercial/evidence claims.

No change in C2 weakens that behavior.

## Exact external prerequisite

To resume PatentsView activation, all of the following must be true:

1. a legitimate USPTO.gov / ODP account is available to the deployment owner;
2. a current provider-issued API key or other officially documented ODP credential is available;
3. current ODP API/schema and storage/use terms are reviewed and recorded in Source Governance;
4. the production adapter is updated if the current ODP contract differs from the existing PatentSearch contract;
5. a controlled real provider run returns non-empty, organization-bound patent metadata;
6. observations/projections preserve provider provenance, remain bounded and quarantined, and produce zero unsupported claims;
7. normal repository CI passes on the exact same final candidate SHA;
8. only then may the activation matrix record `live_tested`.

## C2 exit decision

C2's decision is therefore:

- **historical PatentsView S3 bulk path:** rejected after controlled production HTTP 403;
- **historical/stale archives:** retained only as possible historical/backfill sources, not current live replacement;
- **current PatentsView capability:** remains externally blocked on legitimate current USPTO ODP access/credential;
- **existing API adapter:** retained fail-closed;
- **`live_tested`:** remains false;
- **next SA-15 work:** proceed to C3 while this external prerequisite remains tracked explicitly.

This satisfies the C2 assessment objective without fabricating provider readiness or weakening the project's live-validation standard.
