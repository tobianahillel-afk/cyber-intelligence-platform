# Lot 11 — Procurement History, Providers, Contracts, and Renewal Timing

## Status

`IMPLEMENTED_VALIDATED`

Validated implementation SHA: `df1db1364fec4b7a52f597f658c9958e665acc35`  
Validation CI: run `#517` (`31025684920`)  
Release version: `0.12.0`  
Detailed evidence: `docs/lots/LOT_11_VALIDATION_REPORT.md`

## Business outcome

Identify explicit cyber demand, published awardees, incumbent-provider evidence, contract chronology, and evidence-backed renewal windows without confusing an open notice, an award publication, a confirmed contract, or an estimate.

## Dependencies

- Lot 04 — TED procurement signals;
- Lot 05 — BOAMP procurement signals;
- Lot 08 — organization identity foundation;
- Lot 10 — source portfolio runtime, backfill, freshness, quality, and health.

## Canonical distinctions

The implementation preserves these distinct states:

```text
open procurement notice
  != published result or award
  != confirmed contract history
  != published provider relationship
  != resolved canonical provider identity
  != estimated renewal window
```

A source publication remains immutable. Procedures and contracts are mutable projections rebuilt from the publication chronology.

## Delivered architecture

### Procedure

A procurement procedure groups publications that belong to one buyer process or lot. Its canonical identity is deterministic and source-backed. It records the buyer, title, current status, first publication, latest publication, and source coverage.

### Publication

A publication is an immutable event with source identity, source record key, revision hash, kind, timestamps, URL, buyer, and minimized structured details. Supported kinds are notice, rectification, result, award, amendment, cancellation, and unknown.

A changed provider payload creates another publication revision. It never overwrites the historical publication.

### Contract

A contract is a projection derived from one or more publications. It records:

- buyer and published supplier parties;
- award, active, completed, cancelled, or unknown state;
- published amount and ISO currency when available;
- award, conclusion, notification, start, end, and renewal dates;
- whether each date is published, derived, estimated, or unknown;
- service-family classifications with matched terms and confidence;
- the latest supporting publication and provenance.

Conclusion and notification are separate canonical fields. Neither is silently treated as an execution start date.

### Parties and identity

A published party name is retained even when no canonical organization can be resolved. Exact identifiers are preserved, but a source identifier or name does not silently create a confirmed canonical provider relationship. Name-only parties remain `unresolved` or `candidate` until the organization identity workflow resolves them.

### Service classification

Procurement descriptions are classified against the complete canonical cyber-service family vocabulary. Multiple compatible families may apply to one contract. The classifier covers strategy, audit and risk, GRC, pentest, red/purple teaming, vulnerability management, SOC/SIEM/MDR/XDR/SOAR, DFIR, resilience, IAM/PAM/Zero Trust, cloud, AppSec/DevSecOps, network/SASE, data protection, supply chain, OT/ICS/IoT, awareness, managed services, implementation, training and maintenance.

## Official source integration

### TED Search API

- selected bounded fields only;
- anonymous official Search API;
- active notices create current commercial signals and procedure history;
- awards/results create contract history without a current commercial signal;
- procedure and contract identifiers, winner names/identifiers, values, currency, award date, and conclusion date are mapped when published;
- full notice documents are not mirrored.

### BOAMP Explore API

- bounded official DILA Explore API;
- active notices continue to create actionable current signals;
- result/award/cancellation markers create chronology and contract projections;
- published `titulaire` names are retained as unresolved provider parties;
- embedded contact blocks and full documents are not stored.

### DECP official dataset

- official `decp-2022-marches-valides` dataset through Explore API v2.1;
- selected published fields only, maximum 100 records per page;
- no bulk-export mirroring;
- buyer SIRET/SIREN, published titular identifiers, amount in EUR, notification date, duration, and modifications are mapped;
- duration may derive an end date;
- a renewal date derived from duration is explicitly marked `estimated`;
- modifications create immutable publication revisions while updating the same contract projection.

DECP is registered through separate machine-readable source policy, source portfolio, and schedule files. Bundle loaders reject duplicate source IDs and duplicate schedules across registries.

## Persistence and migrations

- migration `20260805_0010` creates procedures, publications, contracts, parties, and service classifications;
- migration `20260805_0011` adds notification date and its proof basis;
- both migrations are additive and reversible;
- observations, checkpoints, buyer organizations, publications, contracts, and current opportunity projections share one worker transaction;
- replaying the same publication revision remains idempotent;
- an older publication cannot roll back a newer contract projection.

## Historical safety

Historical backfill writes raw observations, buyer organizations, procurement publications, and contract projections. It intentionally ignores current commercial and identity projections, including when an adapter mistakenly supplies them.

This permits historical reconstruction without fabricating a current buying opportunity.

## Protected analyst access

The backend exposes read-only endpoints under `/v1/procurement-history`:

- paginated contract list;
- filters by status, cyber-service family, buyer, and renewal window;
- contract detail with parties, service classifications, and immutable publication timeline.

The routes use the existing control-plane authentication. No mutation endpoint can edit imported procurement facts.

The frontend adds a protected **Contracts** workspace with:

- status and renewal filters;
- value, buyer, provider, source, and service-family columns;
- visible `published`, `derived`, `estimated`, and `unknown` date badges;
- contract detail and official-source timeline;
- unresolved-provider identity status and identifiers;
- direct links to official publications.

The control-plane token remains server-side and is not exposed to the browser.

## Data quality and corrections

- duplicate publications do not duplicate procedures or contracts;
- amendments update approved contract fields while retaining publication history;
- cancellations update the projected status when published;
- estimates are never displayed as confirmed dates;
- currency is mandatory whenever an amount is present;
- ambiguous supplier identity remains unresolved or candidate;
- SQLite and PostgreSQL timestamp differences are normalized to UTC before comparison;
- publication ordering uses source time, collection time, and revision key deterministically.

## Vertical proofs

The repository contains end-to-end worker tests for:

1. BOAMP award → raw observation → buyer → publication → contract → unresolved awardee, with zero current signals and opportunities;
2. TED award → raw observation → buyer → publication → contract → unresolved awardee with official identifier, with zero current signals and opportunities;
3. DECP award/modification → raw observation → buyer → immutable publication → contract → derived end and estimated renewal timing;
4. historical backfill that persists procurement history while rejecting deliberately injected current projections;
5. protected API list/detail with chronology, source coverage, filters, authentication, and invalid-window handling.

## Validation result

The exit gate passed on the validated implementation SHA:

- dependency consistency and Python security audit: PASS;
- Ruff: PASS;
- strict Mypy across 241 source files: PASS;
- 13 architecture and release tests: PASS;
- reversible PostgreSQL migration cycle: PASS;
- 568 backend tests: PASS;
- branch coverage 91.65% against a 90% requirement: PASS;
- frontend dependency audit, typecheck, and production build: PASS.

## Non-goals

- final global entity resolution;
- final signal fusion or calibrated scoring;
- Company 360 completion;
- private procurement portals or unauthorized authenticated areas;
- inferred contracts without sufficient published evidence;
- premium or conditional sources without approved authorization.
