# SA-10 — Final source completeness classification and controlled live-validation gate

## Result

SA-10 deliberately separates two different notions of completion.

### Classification completeness: complete

Every checked-in Source Activation record now has an explicit non-`planned` disposition. The remaining target-dependent/generic/sample records have been resolved as follows:

- `recherche-entreprises` — `manual`: governed adapter present; a deployment-specific canonical organization target and authorization are still required.
- `gleif` — `manual`: governed adapter present; an analyst/deployment-selected LEI target is required.
- `bodacc-identity` — `manual`: governed adapter present; an explicit organization/SIREN target and reviewed deployment authorization are required.
- `osint-framework-import` — `manual`: analyst catalogue-discovery input only; imported listings never grant execution authority.
- `public-web-example-fr-organization` — `not_relevant`: checked-in disabled sample/configuration target, not a production source.
- `official-company-incident-disclosures` — `not_relevant`: generic family placeholder, not an executable provider; concrete sources must be provider-specific.
- `regulator-cert-incident-notices` — `not_relevant`: generic family placeholder, not an endpoint; concrete regulator/CERT sources require provider-specific records.
- `official-vendor-psirt` — `not_relevant`: generic family placeholder; concrete vendor feeds/APIs require separate source records.
- `official-linux-security-advisories` — `not_relevant`: generic family placeholder; distro-specific feeds/APIs require separate source records.
- `official-package-security-advisories` — `not_relevant`: generic family placeholder; ecosystem-specific feeds/APIs require separate source records.

No `planned` record remains in `policies/source_activation.yml`. Manual/blocked/not-relevant records retain a non-empty reason and never gain execution authority merely to improve a completeness percentage.

### Controlled live validation: still open

Repository CI, deterministic fixtures and no-network adapter tests are **not** controlled provider live validation. SA-10 therefore does not synthesize `live_tested` stages.

The synthetic reference adapter remains the only checked-in `active` record that is currently fully integrated according to the activation model because its required stages include `live_tested`.

Every real active source that lacks `live_tested` remains unresolved by `audit_inventory`, even though its adapter/runtime implementation may be validated by CI. The exact outstanding list is derived in tests from the activation inventory rather than duplicated as a manually maintained source of truth.

A source can receive `live_tested` only through a separately authorized provider-specific controlled validation that records the tested provider/method, deployment authorization, target/scope where applicable, timestamp, result, and any required onboarding/credential state without committing secrets.

## What SA-10 does not do

SA-10 does not:

- call external providers merely to manufacture a green status;
- enable checked-in target registries;
- create deployment credentials or secrets;
- invent provider contracts, licences or commercial rights;
- change a blocked/manual/not-relevant source into `active`;
- mark a source `live_tested` from unit/integration tests;
- weaken `audit_inventory`, coverage, lint, typing, architecture or migration gates;
- treat a successful HTTP response as proof of legal authorization, evidence quality or commercial usefulness.

## Controlled live-validation evidence requirements

For each active real provider that is still missing `live_tested`, a future validation record must establish at least:

1. the exact source/provider and acquisition method;
2. current Source Governance authorization for the tested host/path/method;
3. deployment Provider Onboarding state and secret references where required;
4. an approved target/scope when the source is target-bound;
5. bounded quota/cost/time behavior;
6. safe error, redirect and rate-limit behavior;
7. canonical mapping/provenance output without secret leakage;
8. evidence-boundary compliance (no unsupported exposure/compromise/need inference);
9. validation timestamp and reproducible result metadata;
10. an explicit review decision before adding `live_tested` to activation truth.

## SA-10 repository gate

The repository-side SA-10 classification increment may be merged only when:

- no activation record has disposition `planned`;
- every terminal non-executable disposition has a non-empty reason and is resolved by the activation model;
- the checked-in sample public-web target remains disabled and non-authorized;
- the Source Coverage Matrix matches all newly terminalized records;
- `audit_inventory` remains incomplete exactly because real active sources still lack controlled live validation, not because of unknown classifications;
- the synthetic reference remains the only fully integrated checked-in source unless real controlled live evidence is separately added;
- deterministic SA-10 reconciliation tests pass;
- one exact final SHA passes the complete backend and frontend CI;
- reviews and review threads are clear before squash merge.

After this repository gate is merged, issue SA-10 remains open until provider-specific controlled live validations close the outstanding active-source set. No product lot should claim the entire Source Activation axis is fully live-validated before that evidence exists.
