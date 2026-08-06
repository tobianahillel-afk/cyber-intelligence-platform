# Lot 14 — Live Incidents, Ransomware Claims, and Official Confirmation

## Status

`IMPLEMENTED_VALIDATED`

## Primary business outcome

Provide analysts with a canonical, temporal view of public cyber incidents while preserving the difference between an allegation, a secondary report, an official confirmation, a denial, a correction, and a retraction.

The capability is evidence infrastructure. It does not by itself authorize collection from a provider, prove that a named organization was compromised, create an urgent opportunity, or authorize outreach.

## Dependencies

- Lot 08 — organization identity and reviewable links;
- Lot 10 — source portfolio, governance, freshness, and backfill controls;
- Lot 12 — bounded public evidence and immutable chronology;
- Lot 13 — canonical vulnerability and exploitation-state knowledge.

## Canonical distinctions

```text
public allegation
  != independent secondary report
  != official company confirmation
  != regulator or CERT notice
  != resolved organization identity
  != current commercial urgency
  != authorization to contact
```

A syndicated report uses one independence key and therefore counts once for corroboration. An attacker allegation remains an allegation even when repeated by multiple sites. A historical backfill remains historical and cannot create urgency merely because it was collected recently.

## Domain model

### Incident claim snapshot

Each source revision becomes an immutable `IncidentClaimSnapshot` containing bounded metadata:

- explicit source and source kind;
- source record key and published URL;
- explicit canonical incident key supplied by a governed mapping;
- claim type and incident type;
- bounded title and summary;
- claimed organization name and optional resolved organization identifier;
- organization-link status;
- occurrence, discovery, publication, modification, and confirmation timestamps;
- independence key for syndication control;
- confidence, active state, historical-only state, and supersession reference;
- a mandatory metadata-only flag.

The domain rejects any snapshot that is not metadata-only. Exact organization links require a canonical organization UUID. A confirmation timestamp is permitted only for company confirmation, regulator notice, or CERT notice claims.

### Claim types

Implemented claim types are:

- attacker allegation;
- media report;
- researcher report;
- company confirmation;
- regulator notice;
- CERT notice;
- provider statement;
- denial;
- correction;
- retraction.

### Reconciled incident

The current incident projection is rebuilt from the latest revision of each source record. It exposes:

- current incident type, title, summary, and resolution status;
- optional exact organization link or an explicit review state;
- separate occurrence, discovery, first-publication, confirmation, and last-update timestamps;
- total active current claims;
- count of independent positive source groups;
- official-confirmation, denial, and retraction flags;
- historical-only state.

Claims are grouped only by their explicit incident key. Name similarity, matching titles, actor names, or timing do not merge incident records automatically.

## Resolution rules

- attacker-only evidence resolves to `alleged`;
- non-official positive reporting resolves to `reported`;
- an active company confirmation, regulator notice, or CERT notice resolves to `confirmed`;
- denial remains visible and can resolve an otherwise unsupported incident to `denied`;
- a latest-source retraction remains visible and can resolve an incident to `retracted`;
- conflicting exact organization identifiers remove the exact link and require human review;
- syndicated reports share an independence key and do not increase independent-source count;
- corrections and retractions supersede the current revision from the same source while preserving all immutable historical snapshots.

## Persistence and migration

Migration `20260806_0014` creates:

- `incidents` — current reconciled projections;
- `incident_claim_snapshots` — immutable source revisions.

Snapshot digests provide replay idempotence. Persistence recalculates only touched incident records. Empty batches are a no-op. The migration supports PostgreSQL `upgrade -> downgrade -> upgrade` without leaving residual objects.

## Protected API

Implemented endpoints:

- `GET /v1/incidents`;
- `GET /v1/incidents/{incident_key}`.

The list endpoint supports persisted-data filters for status, incident type, claim type, source kind, organization-link state, official confirmation, historical-only state, and local text search. Neither endpoint initiates source collection.

## Analyst workspace

The `/incidents` workspace provides:

- filtered incident inventory;
- separate current status and official-confirmation indicators;
- claim count and independent-source count;
- organization-link review state;
- denial, retraction, and historical flags;
- a detail page with separated timestamps;
- immutable source-claim chronology;
- confidence, syndication group, supersession, and source links;
- a persistent safety warning.

## Source mappings

Selected deterministic schemas and mappings cover:

- official company disclosures;
- regulator and CERT notices;
- bounded public or licensed reporting metadata;
- licensed ransomware/extortion metadata.

Ransomware metadata maps to a low-confidence attacker allegation. It never maps to official confirmation. A name-only victim reference is a candidate or review-required link, never an exact organization match.

## Governance boundary

Five source contracts are installed as non-executable candidates:

- SEC cyber disclosures;
- official company incident disclosures;
- regulator and CERT incident notices;
- licensed incident reporting;
- licensed ransomware metadata.

For every candidate:

- source status is `draft`;
- authorization is missing;
- automated collection is disabled;
- approved hosts and paths are empty;
- source portfolio status is `candidate`;
- `executable` is `false`;
- no collection schedule exists;
- raw-content storage is disabled.

Merging the software does not approve any provider, target, licence interpretation, quota, credential, or schedule.

## Prohibited data and actions

The implementation excludes:

- threat-actor interaction;
- negotiation portals;
- `.onion` source URLs;
- victim files or stolen datasets;
- credentials or credential validation;
- private communications or private personal data;
- restricted content;
- active scanning or exploitation;
- autonomous outreach.

Source policies explicitly prohibit credentials, victim files, private communications, private personal data, and restricted content. Ransomware schemas reject threat-actor `.onion` URLs.

## Historical backfill

Historical source metadata can be persisted with `historical_only=true`. The current projection preserves this state. No code path in this lot creates an opportunity, alert, contact action, or urgency signal from an incident record.

## Exit decision

Lot 14 is complete when the final pull-request head passes dependency audits, Ruff, Mypy strict, architecture contracts, reversible PostgreSQL migrations, the complete backend suite with the configured coverage gate, frontend audit, TypeScript typecheck, and production build.

Exact final-head evidence is recorded on pull request `#39`. Any later code or documentation commit invalidates an earlier run and requires every gate to be rerun.
