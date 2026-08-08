# Lot 20 — Validation report

## Decision

- Technical implementation: **FUNCTIONALLY VALIDATED; FINAL EXACT-SHA RELEASE CI REQUIRED**.
- Entity-resolution safety boundary: **VALIDATED ON FUNCTIONAL CANDIDATE**.
- Temporal graph and immutable history: **VALIDATED ON FUNCTIONAL CANDIDATE**.
- New external source activation: **NOT APPLICABLE / NOT INTRODUCED**.
- Production graph database: **NOT INTRODUCED**; PostgreSQL remains the source of truth.
- Target release: `0.21.0`.
- Authoritative pull request: #56.

The lot is not merge-authorized until the exact final pull-request head passes the full standard repository CI after every version, README, roadmap and validation-document update. Final exact-SHA evidence is recorded in the pull-request checks and PR body so documenting it never invalidates the SHA it describes.

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
- architecture gates forbidding network clients, source adapters, browser automation, `neo4j`, `networkx`, and framework/infrastructure/opportunity dependencies from the graph domain.

## Mandatory evidence boundary

```text
same or similar name
!= same organization

shared or reused domain
!= same organization

alias or reused identifier
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

The implementation includes deterministic regression cases for exact-name homonyms, reused domains, reused exact registration identifiers, similar-but-not-exact names, conflicting exact source bindings and rebrands with retained history. Ambiguous cases create review candidates or remain unresolved; they do not create an automatic binding.

## Reversible resolution and blast radius

Every merge-style decision is append-only. The current binding is stored separately from source snapshots. The blast-radius fingerprint includes the target organization, affected graph/downstream counts and current binding revision. A stale or target-mismatched fingerprint is rejected. Split restores the source-derived projection while retaining earlier decisions; restore can subsequently re-establish a reviewed binding without rewriting history.

## Source and runtime boundary

Lot 20 adds no external collector, source authorization, network client, browser runtime, graph database, autonomous opportunity creation, contact enrichment or outreach path. Explicit graph refresh only projects records already stored in PostgreSQL; normal analyst page views are persisted-data reads and never trigger source collection or graph refresh.

## Functional validation evidence

Functional candidate SHA: `993c2853b2475a336b21254e7067b5be34d0857e`.

GitHub Actions CI: run #1087, run ID `31284785175`.

- dependency consistency: passed;
- Python dependency audit: no known vulnerabilities;
- Ruff: passed;
- Mypy: 446 source files, zero issues;
- architecture/release contracts: 26 passed;
- PostgreSQL migration: `upgrade head -> downgrade base -> upgrade head` passed through `20260808_0020`;
- backend suite: 884 passed, 1 warning;
- aggregate branch-aware coverage: 90.22%;
- frontend dependency audit: passed;
- TypeScript typecheck: passed;
- Next.js production build: passed;
- review threads at functional-candidate audit: zero unresolved.

This functional evidence does not authorize merge after the release-document/version synchronization because those changes create a new SHA.

## Final release gate

The exact final release head must repeat the full standard CI. The PR body must record the final SHA, final CI run, backend/frontend success and final review-thread state before squash merge. Any code or documentation commit after that CI invalidates the evidence and requires another complete run.

## Lot 21 handoff boundary

Lot 21 may start only from the exact merged Lot 20 squash commit on `main`. Professional organization maps, contacts and public-community context must consume graph identities conservatively and preserve privacy, source authorization, temporal validity, analyst review and the distinction between a professional-role clue and lawful contact authorization.
