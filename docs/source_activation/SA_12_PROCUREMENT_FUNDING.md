# SA-12 — PLACE procurement awards and ADEME public funding

## Result

SA-12 adds two provider-specific, scheduled and controlled-live-tested public data integrations while reusing the existing collection scheduler, worker, source governance, immutable raw-observation path and canonical persistence modules.

`place-awards` and `ademe-financial-aid` are promoted to `live_tested` only after the production adapters completed real provider acquisition. Normal CI is not treated as provider live proof.

## PLACE — marchés publics conclus

Source id: `place-awards`.

Acquisition uses the official PLACE award-history dataset exposed by `data.economie.gouv.fr`. The adapter is GET-only, requests a selected set of procurement fields, uses bounded pages and response sizes, validates JSON strictly, applies Source Governance before network access, and maintains a latest-award checkpoint.

Every collected award is retained as procurement history. Collection is not restricted to cyber-classified titles. The canonical service taxonomy may therefore be empty for an award, while the underlying procurement publication and contract remain evidence.

The mapping emits:

- an immutable `RawObservation` with source record type `procurement_award`;
- a deterministic buyer organization scoped to the PLACE claim;
- a `ProcurementPublication` of kind `AWARD` and procedure status `AWARDED`;
- a `ProcurementContractProjection` with amount, notification date, optional awardee party and optional cyber service-family classification.

A historical award is not a current procurement need, renewal or incumbent relationship by itself. Later fusion/scoring logic must preserve that temporal distinction.

### PLACE live-provider drift handled

Controlled live acquisition exposed provider details that deterministic fixtures had not captured:

1. `annee_de_notification` is delivered as a year such as `"2017"`, not an ISO date;
2. `geocode_att` is an object with `lon` and `lat`, not an array;
3. some valid award rows have `nom_attributaire = null`.

The final schema models those forms explicitly. Longitude/latitude remain bounded. A missing awardee never causes the contract to be discarded and never creates a synthetic supplier; the canonical contract is retained with `parties=()`.

## ADEME — aides financières

Source id: `ademe-financial-aid`.

Acquisition uses the official ADEME Data Fair dataset through its public `/lines` API. The adapter is GET-only and selects only the fields required for public funding intelligence. It follows the provider `next` cursor with an exact HTTPS host/path check on every page, loop detection and a bounded page budget. The next cursor is persisted as the collection checkpoint.

The provider keys are normalized inside the adapter only:

- `_id` → canonical record id;
- `nomBeneficiaire` → beneficiary name;
- `objet` → funding object;
- `nature` → aid nature;
- `dateConvention` → event date;
- `montant` → amount.

Each row emits an immutable `RawObservation` plus a corporate-change `CONFIRMATION` claim with event type `FUNDING`. Beneficiary names remain unresolved (`organization_id=None`, `UNRESOLVED`) so a name-only match never becomes a canonical organization merge.

Funding older than the configured current-context horizon, or funding whose date cannot be parsed safely, remains historical-only. Funding metadata does not create a current cyber need by itself.

### ADEME live-provider drift handled

Controlled live acquisition exposed several provider details and the adapter was corrected against them rather than weakening validation:

1. the dataset uses `nomBeneficiaire` and `dateConvention`, not generic `nom` / `date` fields;
2. Data Fair injects `_score: null` into returned rows even when it is not requested, so `_score` is modeled explicitly as optional provider metadata;
3. cursor pages may omit `total`, so `total` is optional but remains non-negative whenever present.

The schema remains `extra="forbid"`; unrelated new provider fields still fail closed as schema drift.

## End-to-end persistence

SA-12 extends `AdapterCollectionBatch` with `corporate_change_claims` and reuses the existing collection worker to call the existing `persist_change_claims` reconciliation path. No second worker, scheduler, source-health subsystem or funding persistence silo is introduced.

PLACE continues through the existing procurement organization/publication/contract persistence path. ADEME continues through the existing corporate-change claim persistence path.

## Controlled live validation

The dedicated workflow `.github/workflows/sa12-live-validation.yml` executes `scripts/live_validate_sa12.py` against the real public endpoints using `PlaceAwardsAdapter` and `AdemeFundingAdapter` themselves.

The live harness retains no provider payload and prints aggregate counts only. It fails unless both providers return non-empty observations and unless canonical projections/claims are preserved one-for-one.

Successful controlled provider proof:

- workflow run: `31474048440`;
- source-code head for the proof: `1139c09857049b90cca176995148d4317a249949`;
- PLACE public award observations: `500`;
- PLACE procurement projections: `500`;
- ADEME public aid observations: `500`;
- ADEME funding claims: `500`.

This proof justified adding `live_tested` to both Source Activation records. Because the documentation and activation commits that follow change the PR head, the workflow must pass again on the exact final merge candidate.

## Completion gate

SA-12 may be squash-merged only when:

1. both provider-specific real adapters, governance policies, executable portfolio entries and enabled schedules are present;
2. PLACE retains all acquired award history without converting historical awards into current needs;
3. ADEME retains beneficiary names as unresolved funding claims rather than name-only entity merges;
4. provider schemas explicitly lock all live drift observed during implementation;
5. the existing worker persists PLACE procurement and ADEME corporate-change projections without a parallel subsystem;
6. deterministic provider, checkpoint, governance, runtime, error-contract and activation tests pass;
7. Ruff, strict Mypy, architecture/release checks, reversible migrations, branch-aware coverage and frontend checks pass;
8. the dedicated SA-12 live workflow passes on the exact final PR head;
9. reviews and review threads are clear before squash merge.
