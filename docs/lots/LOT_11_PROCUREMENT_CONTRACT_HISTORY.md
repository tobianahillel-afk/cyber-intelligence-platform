# Lot 11 — Procurement History, Providers, Contracts, and Renewal Timing

## Status

`IN_PROGRESS`

## Business outcome

Identify explicit cyber demand, published awardees, incumbent-provider evidence, contract chronology, and evidence-backed renewal windows without confusing an open notice, an award publication, a confirmed contract, or an estimate.

## Dependencies

- Lot 04 — TED procurement signals;
- Lot 05 — BOAMP procurement signals;
- Lot 08 — organization identity foundation;
- Lot 10 — source portfolio runtime, backfill, freshness, quality, and health.

## Canonical distinctions

The lot preserves these distinct states:

```text
open procurement notice
  != published result or award
  != confirmed contract history
  != published provider relationship
  != estimated incumbent relationship
  != estimated renewal window
```

A source publication remains immutable. Procedures and contracts are mutable projections rebuilt from the publication chronology.

## Domain model

### Procedure

A procurement procedure groups publications that belong to one buyer process or lot. Its canonical identity must be deterministic and source-backed. It records the buyer, title, current status, first publication, latest publication, and source coverage.

### Publication

A publication is an immutable event with source identity, source record key, content hash, kind, timestamps, URL, buyer, and minimized structured details. Supported kinds are notice, rectification, result, award, amendment, cancellation, and unknown.

A changed provider payload creates another publication revision. It never overwrites the historical publication.

### Contract

A contract is a projection derived from one or more publications. It records:

- buyer and published supplier parties;
- award, active, completed, cancelled, or unknown state;
- published amount and ISO currency when available;
- award, start, and end dates;
- whether each date is published, derived, estimated, or unknown;
- renewal estimate and confidence separately from confirmed dates;
- service-family classifications with matched terms and confidence;
- the latest supporting publication and provenance.

### Parties and identity

A published party name is retained even when no canonical organization can be resolved. Exact official identifiers may confirm a party. Name-only matching remains a candidate and cannot silently create a confirmed provider relationship.

### Service classification

Procurement descriptions are classified against the complete canonical cyber-service family vocabulary. Multiple compatible families may apply to one contract. Classification does not duplicate the contract or create several copies of the same commercial opportunity.

## Source integration

### TED

The TED adapter must retrieve selected fields for results, awards, amendments, and cancellations in addition to active notices. Pagination and backfill remain bounded. Official identifiers and award fields are mapped when published.

### BOAMP

The BOAMP adapter already sees notice state, result markers, and published `titulaire` data. Lot 11 maps these fields into publication and contract projections while continuing to create current commercial signals only for actionable open notices.

### DECP

A reviewed official French essential-public-procurement-data source is added through the common source portfolio lifecycle. It must expose only approved published fields, bounded pagination, schema validation, checkpoints, and no document mirroring.

## Historical safety

Historical backfill writes raw observations and procurement history but creates no current commercial signal. Incremental collection may update chronology and current state. Replaying the same publication revision is idempotent.

## Data quality and corrections

- duplicate publications do not duplicate procedures or contracts;
- amendments update approved contract fields while retaining publication history;
- cancellations and retractions update the projected status;
- conflicting values remain visible with provenance rather than being silently overwritten;
- estimates are never displayed as confirmed dates;
- currency is mandatory whenever an amount is present;
- ambiguous supplier identity remains unresolved or candidate.

## Required tests

- notice-to-result and notice-to-award linkage;
- amendment chronology;
- duplicate publication and replay idempotence;
- published provider identity and ambiguous name-only identity;
- amount and currency validation;
- cancellation and retraction;
- confirmed versus estimated dates;
- current opportunity versus historical contract separation;
- multi-service contract without duplicated opportunity;
- backfill without false current signals;
- backfill/incremental convergence;
- policy before network, schema drift, bounded pagination, retry classification;
- reversible migration and full repository CI.

## Exit gate

Analysts can inspect a procedure and understand:

- what was published;
- who bought and who was awarded when published;
- which contract fields are confirmed or estimated;
- which cyber-service families are supported by the text;
- the current chronology and correction state;
- why a renewal window is estimated;
- which evidence and source revisions support every conclusion.

## Non-goals

- final global entity resolution;
- final signal fusion or calibrated scoring;
- Company 360 completion;
- private procurement portals or unauthorized authenticated areas;
- inferred contracts without sufficient published evidence;
- premium or conditional sources without approved authorization.