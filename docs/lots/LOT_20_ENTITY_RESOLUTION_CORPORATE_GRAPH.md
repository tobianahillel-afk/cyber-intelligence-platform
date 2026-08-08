# Lot 20 — Entity resolution and temporal corporate knowledge graph

## Status

Implementation is complete on `agent/entity-resolution-knowledge-graph`. Functional candidate `993c2853b2475a336b21254e7067b5be34d0857e` passed the complete standard CI as run #1087.

Target release: `0.21.0`.

The release remains merge-authorized only when the exact post-version/documentation pull-request head also passes every standard backend and frontend gate and is merged into `main`.

## Outcome

Lot 20 builds a PostgreSQL-backed temporal corporate knowledge graph over evidence already collected by earlier lots. It gives analysts a reversible entity-resolution workflow without converting graph membership, fuzzy similarity, a shared name, a reused domain, or a weak relationship into a verified fact.

The graph remains a projection and review surface over existing source-aware records. PostgreSQL remains the authoritative source of truth. No graph database, crawler, browser runtime, active probe, new provider connection, autonomous opportunity creation, contact enrichment, or outreach path is introduced.

## Core safety boundary

```text
same name
!= same organization

shared or reused domain
!= same organization

alias
!= verified identity

probabilistic candidate
!= merged entity

graph membership
!= stronger evidence

historical edge
!= current edge

claimed or inferred relationship
!= verified relationship

vulnerability applicability
!= verified exposure

incident claim
!= confirmed compromise

resolution decision
!= deletion of source history
```

## Canonical graph model

Current projections model:

- organizations;
- establishments;
- groups;
- brands;
- aliases;
- exact registration identifiers;
- domains and passive assets;
- technologies and vendor products;
- public incident records;
- vulnerabilities and applicability edges;
- material corporate/regulatory changes;
- provider/customer/partner/supplier/reseller/integrator/auditor/insurer/MSSP/cloud/subcontractor relationships;
- parent/subsidiary/establishment/brand structure;
- predecessor, successor, merger and spin-off transitions.

Every graph edge retains:

- source module;
- source record key;
- evidence class;
- claim type;
- review state;
- source URL when available;
- observation time;
- validity window;
- expiry;
- confidence;
- suppression state;
- supersession lineage.

## Temporal model

Source snapshots are immutable. Current node and edge records are deterministic projections over those snapshots.

The graph supports `as_of` reconstruction from historical source snapshots. Corrections, retractions, expirations, historical-only records and suppression can remove an edge from the current graph without deleting its source history.

Rebrands preserve the stable node identity and prior display-name history. Structural transitions are directional and temporal rather than collapsed into a generic relation.

## Entity-resolution model

Resolution follows a conservative hierarchy:

1. source-backed exact organization bindings;
2. exact registration identifiers;
3. explicit reviewed aliases;
4. deterministic domain context where available;
5. normalized-name/context candidates only as human-review suggestions.

Probabilistic candidates never create a binding automatically.

Conflicting exact identifiers, homonyms, reused domains and other multi-owner conditions remain review candidates. The graph deliberately prefers unresolved state over a false merge.

## Reversible analyst decisions

Resolution decisions are append-only records supporting:

- merge;
- reject;
- split;
- override;
- restore.

The current binding is an overlay over immutable source snapshots. A later graph refresh cannot erase a valid analyst binding. Splitting the binding restores the projection derived from source evidence without deleting the original merge decision.

## Blast-radius guard

Before a decision, the API computes a blast-radius preview covering:

- affected graph nodes;
- graph edges;
- organization identities;
- business relationships;
- vulnerability applicability assessments;
- commercial signals;
- opportunities.

The preview has a SHA-256 fingerprint that includes the target organization, downstream counts and the current resolution-binding revision. A fingerprint obtained for another target or before a later resolution change is rejected.

This prevents a stale or mismatched preview from authorizing a different graph mutation.

## Internal projections only

The graph refresh reads existing PostgreSQL records from:

- organization identity;
- relationship intelligence;
- passive exposure;
- incident intelligence;
- corporate-change intelligence;
- vulnerability applicability and vulnerability knowledge.

It never contacts a network source. Page loads only query persisted graph projections. The analyst UI does not invoke the local refresh operation automatically.

## Persistence

Migration `20260808_0020` creates:

- `corporate_graph_nodes`;
- `corporate_graph_node_snapshots`;
- `corporate_graph_edges`;
- `corporate_graph_edge_snapshots`;
- `entity_resolution_candidates`;
- `entity_resolution_decisions`;
- `entity_resolution_bindings`.

The migration must pass PostgreSQL `upgrade -> downgrade -> upgrade` on the final release head.

## API surface

Protected control-plane routes under `/v1/graph` provide:

- node list/filtering;
- current or historical node detail;
- immutable source history;
- incoming/outgoing edges;
- blast-radius preview;
- resolution candidate list/detail;
- append-only analyst decisions;
- explicit local persisted-data refresh.

List reads are bounded to at most 200 records per request.

## Analyst workspace

The Next.js `/graph` workspace provides:

- graph-node search and filtering;
- current/historical/suppressed state;
- explicit resolved/unresolved identity state;
- source count and confidence;
- resolution-review queue;
- source-history and temporal edge detail;
- blast-radius visualization;
- server-side merge/reject/split actions;
- immutable decision history.

The control-plane token stays server-side.

## Regression coverage

The lot explicitly tests:

- homonyms never auto-merge;
- reused domains remain reviewable;
- reused exact identifiers remain reviewable;
- conflicting current source bindings resolve to no canonical organization;
- rebrands keep stable identity and historical names;
- merger/spin-off relationship direction is retained;
- replay is idempotent;
- edge direction/type cannot silently change;
- retractions preserve immutable history while removing current state;
- historical `as_of` reconstruction;
- analyst bindings survive local graph refresh;
- split restores source-derived projection;
- stale or target-mismatched blast-radius fingerprints are rejected;
- bounded query pagination has no overlap;
- the corporate-graph bounded context cannot import network clients, source collectors, browser automation, graph databases or opportunity logic into its domain.

## Release boundary

Lot 20 does not authorize new source collection and does not alter the authorization status of any provider.

Lot 21 must start only from the exact merged Lot 20 squash on `main` and may consume graph identities and organizational structure without weakening the evidence and privacy boundaries established here.
