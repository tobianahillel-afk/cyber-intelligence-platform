# Lot 20 — Validation report

## Decision

- Technical implementation: **PENDING FINAL CI**.
- Entity-resolution safety boundary: **IMPLEMENTED, validation pending**.
- Temporal graph and immutable history: **IMPLEMENTED, validation pending**.
- New external source activation: **NOT APPLICABLE / NOT INTRODUCED**.
- Production graph database: **NOT INTRODUCED**; PostgreSQL remains the source of truth.
- Target release: `0.21.0`.
- Authoritative pull request: #56.

The lot is not merge-authorized until the exact final pull-request head passes the full standard repository CI after every version, README, roadmap and validation-document update.

## Delivered scope

Lot 20 delivers:

- a dedicated `corporate_graph` bounded context;
- temporal nodes for organizations, establishments, groups, brands, aliases, exact identifiers, domains, assets, technologies, products, incidents, vulnerabilities, providers and material changes;
- source-aware directed edges for identity, alias, exact identifiers, structure, mergers/spin-offs, domains/assets, technology/product use, incidents, applicability, material changes and business relationships;
- immutable node and edge source snapshots with deterministic digests;
- current PostgreSQL projections plus historical `as_of` reconstruction;
- explicit correction/retraction/dispute/expiry/suppression semantics;
- conservative entity-resolution candidates with no probabilistic auto-merge;
- homonym, reused-domain and reused-identifier conflict handling;
- append-only merge/reject/split/override/restore decisions;
- analyst bindings layered over source history rather than mutating it;
- resolution-state-aware blast-radius fingerprints;
- downstream impact counts for identities, relationships, applicability, commercial signals and opportunities;
- deterministic local graph refresh from previously persisted evidence only;
- protected `/v1/graph` APIs;
- `/graph` analyst workspace, historical node detail and resolution-review workspace;
- server-side analyst decision actions that keep the control-plane token out of the browser;
- reversible migration `20260808_0020`;
- architecture gates forbidding network clients, source collectors, browser automation, graph databases and opportunity dependencies in the domain.

## Mandatory evidence boundary

```text
same or similar name
!= same organization

shared or reused domain
!= same organization

alias
!= verified identity

probabilistic candidate
!= merged entity

graph membership
!= stronger evidence

historical, claimed or inferred edge
!= verified current relationship

vulnerability applicability
!= verified exposure

incident claim
!= confirmed compromise

resolution decision
!= deletion or mutation of source history
```

## False-merge protections

The implementation includes deterministic regression cases for:

- exact-name homonyms;
- reused domains;
- reused exact registration identifiers;
- similar-but-not-exact names;
- conflicting exact source bindings;
- rebrands with retained history.

Ambiguous cases create review candidates or remain unresolved. They do not create an automatic binding.

## Reversible resolution and blast radius

Every merge-style decision is append-only. The current binding is stored separately from source snapshots.

Before a decision, the backend calculates a blast-radius preview containing the target organization, affected graph counts, relevant downstream record counts and the current resolution-binding revision. The SHA-256 fingerprint therefore changes when:

- the target organization changes;
- the graph/downstream impact changes;
- the current resolution binding changes.

A stale or target-mismatched fingerprint is rejected. Split restores the source-derived node projection while retaining earlier decisions; restore can subsequently re-establish a reviewed binding without rewriting history.

## Source and runtime boundary

Lot 20 adds no external collector, source authorization, network client, browser runtime, graph database, autonomous opportunity creation, contact enrichment or outreach path.

The explicit graph refresh operation only projects records already stored in PostgreSQL. Normal analyst page views are persisted-data reads and never trigger source collection or graph refresh.

## Required final validation

The exact final release head must pass:

- dependency consistency;
- Python dependency audit;
- Ruff;
- strict Mypy;
- all architecture, release, complexity and safety contracts;
- PostgreSQL `upgrade -> downgrade -> upgrade` through `20260808_0020`;
- complete pytest suite with branch-aware aggregate coverage at or above 90%;
- frontend dependency audit;
- TypeScript typecheck;
- Next.js production build;
- zero unresolved blocking review threads.

## Metrics

Final SHA: **PENDING**.

Final CI run: **PENDING**.

Mypy source-file count: **PENDING**.

Architecture contract count: **PENDING**.

Backend test count: **PENDING**.

Aggregate branch-aware coverage: **PENDING**.

Frontend validation: **PENDING**.

Review-thread count: **PENDING**.

Merge commit: **PENDING**.

## Lot 21 handoff boundary

Lot 21 may start only from the exact merged Lot 20 squash commit on `main`.

Professional organization maps, contacts and public-community context must consume graph identities conservatively and preserve privacy, source authorization, temporal validity, analyst review and the distinction between a professional-role clue and lawful contact authorization.
