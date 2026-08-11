# SA-12 — Procurement awards and public funding expansion

## Result

SA-12 adds three provider-specific, scheduled and controlled-live-tested public-data integrations while reusing the existing collection scheduler, worker, Source Governance, immutable raw-observation path and canonical persistence modules:

- `place-awards` — French PLACE award history;
- `ademe-financial-aid` — French ADEME public financial-aid results;
- `cordis-eu-funded-projects` — CORDIS Horizon Europe project-participation funding evidence.

Normal CI is not provider live proof. A source receives `live_tested` only after its production adapter completes controlled acquisition against the approved real provider path and preserves canonical output.

## PLACE — marchés publics conclus

Source id: `place-awards`.

Acquisition uses the official PLACE award-history dataset exposed by `data.economie.gouv.fr`. The adapter is GET-only, requests a selected set of procurement fields, uses bounded pages and response sizes, validates JSON strictly, applies Source Governance before network access, and maintains a latest-award checkpoint.

Every collected award is retained as procurement history. Collection is not restricted to cyber-classified titles. The canonical service taxonomy may therefore be empty for an award while the underlying procurement publication and contract remain evidence.

The mapping emits:

- an immutable `RawObservation` with source record type `procurement_award`;
- a deterministic buyer organization scoped to the PLACE claim;
- a `ProcurementPublication` of kind `AWARD` and procedure status `AWARDED`;
- a `ProcurementContractProjection` with amount, notification date, optional awardee party and optional cyber service-family classification.

A historical award is not a current procurement need, renewal or incumbent relationship by itself.

### PLACE live-provider drift handled

Controlled live acquisition exposed provider details that deterministic fixtures had not captured:

1. `annee_de_notification` is delivered as a year such as `"2017"`, not an ISO date;
2. `geocode_att` is an object with `lon` and `lat`, not an array;
3. some valid award rows have `nom_attributaire = null`.

The final schema models those forms explicitly. A missing awardee never causes the contract to be discarded and never creates a synthetic supplier; the contract is retained with `parties=()`.

## ADEME — aides financières

Source id: `ademe-financial-aid`.

Acquisition uses the official ADEME Data Fair dataset through its public `/lines` API. The adapter selects only fields required for public-funding intelligence. It follows the provider `next` cursor with an exact HTTPS host/path check on every page, loop detection and a bounded page budget. The next cursor is persisted as the collection checkpoint.

Each row emits an immutable `RawObservation` plus a corporate-change `CONFIRMATION` claim with event type `FUNDING`. Beneficiary names remain unresolved (`organization_id=None`, `UNRESOLVED`) so a name-only match never becomes a canonical organization merge.

Funding older than the configured current-context horizon, or funding whose date cannot be parsed safely, remains historical-only. Funding metadata does not create a current cyber need by itself.

### ADEME live-provider drift handled

Controlled live acquisition exposed several provider details and the adapter was corrected against them rather than weakening validation:

1. the dataset uses `nomBeneficiaire` and `dateConvention`, not generic `nom` / `date` fields;
2. Data Fair injects `_score: null` into returned rows even when it is not requested;
3. cursor pages may omit `total`.

The schema remains strict; unrelated new provider fields still fail closed as schema drift.

## CORDIS — Horizon Europe projects and organisations

Source id: `cordis-eu-funded-projects`.

The first implementation attempt used the documented CORDIS/EURIO SPARQL capability. Controlled live validation proved that the selected `/datalab/sparql-endpoint` route was not a directly executable HTTP query endpoint and returned `404` for the production request. SA-12 did not reinterpret that failure as success and did not add `live_tested`.

The final adapter instead uses CORDIS's official public Horizon Europe bulk distribution:

`https://cordis.europa.eu/data/cordis-HORIZONprojects-csv.zip`

A controlled provider probe observed:

- HTTP `200`;
- content type `application/zip`;
- archive size `36,672,015` bytes at the validation time;
- 9 archive members, including 8 CSV files;
- `organization.csv` as the organization-participation dataset.

The observed `organization.csv` header includes `projectID`, `projectAcronym`, `organisationID`, `name`, `role`, `ecContribution`, `netEcContribution`, `totalCost`, `contentUpdateDate`, `endOfParticipation` and `active`, together with other published organization fields.

### CORDIS bounded bulk parsing

The production adapter downloads only the exact approved archive URL and parses only `organization.csv`. It enforces:

- HTTPS host/path equality before network access;
- maximum HTTP response size of 100 MB;
- a maximum archive-member count;
- path-traversal rejection for archive members;
- encrypted-member rejection;
- maximum uncompressed size for `organization.csv`;
- compression-ratio protection;
- UTF-8 CSV decoding and strict provider-column validation;
- batches capped at 500 participation rows.

No nested archive is opened and no unrelated CORDIS member is parsed by this adapter.

Each row is identified by `projectID + organisationID`, not by a fuzzy name. It emits an immutable `RawObservation` and a corporate-change `FUNDING` confirmation claim. The organization name remains unresolved until the platform's entity-resolution layer links it using independent identity evidence.

The row-level `ecContribution` field is preserved as CORDIS organization-participation evidence. The adapter does not invent a currency, does not reinterpret it as a vulnerability or cyber need, and does not turn project participation into an opportunity or outreach authorization.

`contentUpdateDate` is retained as source time when it is valid and not in the future relative to collection. `endOfParticipation` is retained as participation context and may contribute to historical classification; it is not invented as the funding-event occurrence timestamp.

### CORDIS snapshot checkpoints

The collection checkpoint contains:

- the SHA-256 of the fetched archive;
- the next row offset;
- whether the snapshot was completely traversed.

A changed archive hash starts the new snapshot from row zero. Replaying the same completed archive produces no duplicate batch. This keeps a monthly bulk source replay-safe while retaining the existing worker and source-health runtime.

## End-to-end persistence

SA-12 reuses existing canonical paths rather than adding provider-specific silos:

- PLACE uses the existing procurement organization/publication/contract persistence path;
- ADEME and CORDIS use the existing corporate-change claim reconciliation path;
- all providers use the common collection scheduler, worker, retry/circuit model, source governance and raw-observation infrastructure.

A source payload never writes directly to an opportunity or bypasses entity resolution.

## Controlled live validation

The dedicated workflow `.github/workflows/sa12-live-validation.yml` executes `scripts/live_validate_sa12.py` with the production provider adapters themselves. The harness retains no provider payload and prints aggregate counts only.

The successful three-provider proof was run on source head `31e3afe954f5f3660fd83c9a88c1530dce618555` in workflow run `31482097009` and observed:

- PLACE public award observations: `500`;
- PLACE procurement projections: `500`;
- ADEME public aid observations: `500`;
- ADEME funding claims: `500`;
- CORDIS organization-project participations: `500`;
- CORDIS funding claims: `500`.

The one-for-one counts prove that the real acquired records survive the provider adapter boundary into their intended canonical projection types. They do not prove that every record is commercially relevant.

This proof justified adding `live_tested` to CORDIS Source Activation. Because this documentation and activation update change the branch head, the dedicated live workflow and the complete repository CI must pass again on the exact final merge candidate before SA-12 is merged.

## Completion gate

SA-12 may be squash-merged only when:

1. all three provider-specific adapters, governance policies, executable portfolio entries and enabled schedules are present;
2. PLACE retains all acquired award history without converting historical awards into current needs;
3. ADEME retains beneficiary names as unresolved funding claims rather than name-only entity merges;
4. CORDIS uses the verified official bulk path, preserves project/organisation identifiers and keeps names unresolved;
5. provider schemas explicitly lock all live drift observed during implementation;
6. bulk/HTTP safety, checkpoints, replay behavior and policy-before-network are deterministic and tested;
7. the existing worker persists procurement and corporate-change projections without a parallel subsystem;
8. Ruff, strict Mypy, architecture/release checks, reversible migrations, complete branch-aware coverage and frontend checks pass;
9. the dedicated SA-12 live workflow passes on the exact final PR head;
10. reviews and review threads are clear before squash merge.
