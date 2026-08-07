# Lot 19 — Validation report

## Decision

- Technical implementation: **PASS**, subject to the final-head CI rule.
- Evidence and relationship-state boundary: **PASS**.
- Source-governance boundary: **PASS**.
- Production activation of new relationship sources: **NOT AUTHORIZED**.
- Automatic opportunity creation, contact enrichment, and outreach: **NOT IMPLEMENTED**.
- Target release: `0.20.0`.
- Authoritative pull request: #53.

## Delivered scope

Lot 19 delivers:

- a dedicated temporal relationship bounded context separate from Lot 08 identity relationships;
- directed provider/customer/partner/supplier/reseller/distributor/integrator/auditor/insurer/MSSP/cloud-provider/technology-vendor/subcontractor roles;
- claimed, observed, contracted, historical, and inferred evidence classes;
- assertion, dispute, correction, retraction, expiry, and supersession processing;
- exact, candidate, review-required, unresolved, and rejected identity links on both endpoints;
- current-state reconciliation that requires current observed or contracted evidence for `active`;
- historical and inferred relationships that cannot silently become current incumbents;
- immutable evidence snapshots, a current relationship projection, and separate contexts;
- contract-backed current/renewal context derived from adequate contract evidence;
- projection from already stored procurement history without new network activity;
- metadata-only provider schemas and mappings that deliberately cannot emit contracted evidence;
- four governed, unauthorized, unscheduled, non-executable source candidates;
- reversible migration `20260807_0019`;
- protected relationship list/detail APIs;
- `/relationships` and relationship-detail analyst views.

## Mandatory evidence boundary

```text
marketing claim
!= contract evidence
!= active incumbent

historical relationship
!= current relationship

inferred relationship
!= verified relationship

relationship evidence
!= service need
!= opportunity
!= authorization to contact
```

## Mandatory source and safety boundary

The release preserves all of the following:

- generic public/provider metadata cannot create `contracted` evidence;
- source and target direction is explicit and preserved;
- conflicting exact endpoint identities require review;
- private customer portals and personal networks are forbidden sources;
- new source candidates remain authorization `missing` and `executable: false`;
- no active probing, authentication, access-control bypass, or service connection;
- no automatic opportunity creation;
- no contact enrichment;
- no autonomous outreach;
- API and UI reads query persisted data only and never launch collection.

## Functional release-candidate evidence

Implementation head `6ed7a5f033147e6bb5e643c97ae33589e26cad62` passed GitHub Actions CI run `#972` (`31209260376`) before release/version/documentation synchronization:

- dependency consistency: pass;
- Python dependency audit: pass, no known vulnerabilities;
- Ruff: pass;
- Mypy strict: pass across **407 source files**;
- architecture, complexity, dependency, safety, release, and roadmap contracts: **24 passed**;
- PostgreSQL `upgrade -> downgrade -> upgrade`: pass through migration `20260807_0019`;
- backend suite: **846 passed**, 0 failed;
- aggregate branch-aware coverage: **91.09%**, above the 90% gate;
- line coverage: **94.06%**;
- branch coverage: **77.32%**;
- frontend dependency audit: pass;
- TypeScript typecheck: pass;
- Next.js production build: pass;
- backend diagnostics artifact: `backend-test-diagnostics`, artifact ID `9006079111`.

This functional run validates the Lot 19 vertical slice before final release synchronization. It is not merge authorization for any later head.

## Persistence and replay checks

The implementation verifies that:

- replaying identical evidence is idempotent;
- immutable evidence snapshots are retained across current-state changes;
- context changes do not mutate source evidence;
- cancellation/retraction adds a visible current source revision and removes current incumbency;
- completed contracts remain historical;
- stale evidence cannot remain current;
- conflicting roles or exact endpoint identities move the relationship to review rather than forcing a fact;
- migration `20260807_0019` is reversible.

## Provider activation decision

Production activation of the four new relationship source families is **not authorized by this software release**.

The checked-in entries remain `draft`/`candidate`, with missing authorization, empty approved hosts and paths, no schedule or executable adapter, and explicit prohibitions on private portals, personal networks, automatic opportunities, contact enrichment, and outreach.

Existing persisted procurement data may be projected into relationship evidence without authorizing any new source collection.

## Lot 20 handoff boundary

Lot 20 must start from the exact merged Lot 19 commit on `main`.

Entity-resolution and temporal graph work must preserve the evidence class, direction, time validity, source identity, confidence, review decisions, and reversible merge/split history created by earlier lots. Lot 20 must not upgrade claimed or inferred relationship evidence into verified current facts merely because those edges become part of a graph.

## Release synchronization

README and the authoritative delivery plan are synchronized by a temporary CI job only to avoid unsafe whole-file hand edits. That job is removed and the standard `main` CI workflow is restored before the final validation SHA is accepted.

## Final-head rule

The exact final pull-request head must rerun and pass every backend and frontend gate after version `0.20.0`, README, authoritative roadmap, and validation-document changes.

The final SHA, CI run, test count, coverage, review-thread count, and merge decision are recorded in pull request #53. Any commit added after that successful final run invalidates the decision and requires the complete validation chain again.
