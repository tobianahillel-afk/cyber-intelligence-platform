# Lot 19 — Provider, customer, partner, and supply-chain relationship intelligence

**Status:** `IMPLEMENTED_VALIDATED` only after the exact final pull-request head passes every release gate.

**Target release:** `0.20.0`.

## Outcome

Lot 19 adds a temporal, evidence-backed relationship layer for professional organization-to-organization dependencies and commercial context.

The bounded context is intentionally separate from Lot 08 `organization_relationships`. Lot 08 relationships support organization identity and legal-structure resolution. Lot 19 `business_relationships` represent directed provider, customer, partner, supplier, reseller, distributor, integrator, auditor, insurer, MSSP/MDR, cloud/hosting, technology-vendor, subcontractor, and other reviewed business or technology relationships.

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

A relationship is never made current merely because a company published a case study or appeared in a directory. Generic public/provider metadata cannot create `contracted` evidence. Contract-backed state is reserved for adequate contract evidence already modeled by procurement history or another future provider explicitly reviewed to the same standard.

## Canonical model

### Directed roles

The source and target endpoints are semantically meaningful and must never be silently reversed. Supported roles include:

- provider;
- customer;
- partner;
- supplier;
- reseller;
- distributor;
- integrator;
- auditor;
- insurer;
- MSSP/MDR;
- cloud or hosting provider;
- technology vendor;
- subcontractor;
- other reviewed roles.

### Evidence classes

Lot 19 keeps evidence class separate from relationship state:

- `claimed`: a public statement, marketing claim, case study, or equivalent assertion;
- `observed`: independently observable public metadata that directly supports a relationship;
- `contracted`: adequate contract evidence;
- `historical`: evidence explicitly historical by nature;
- `inferred`: an explainable inference that still requires review.

Only current `observed` or `contracted` assertion evidence can make the current projection `active`. `claimed` stays `claimed`; `inferred` stays `inferred`; ended or historical evidence stays historical; expired evidence becomes stale.

### Claim lifecycle

Source revisions preserve:

- assertion;
- dispute;
- correction;
- retraction;
- supersession.

Current projections can therefore be under review, claimed, inferred, active, historical, disputed, corrected, retracted, or stale without deleting immutable source evidence.

## Identity handling

Both relationship endpoints preserve one of:

- exact;
- candidate;
- review required;
- unresolved;
- rejected.

Exact links require an organization UUID. Unresolved or rejected links cannot retain one. Conflicting exact organization identifiers force review instead of an unsafe merge. A relationship cannot resolve its source and target to the same organization.

## Chronology

The following timestamps remain distinct:

- source publication time;
- provider modification time;
- platform observation time;
- relationship validity start;
- relationship validity end;
- evidence expiry;
- contract renewal time;
- persistence time.

A historical contract therefore cannot silently become a current incumbent. A future start date does not become current evidence early. Expired evidence cannot remain current.

## Contract and incumbent context

The current projection exposes `has_contract_evidence` and `contract_backed_current` separately.

`contract_backed_current` is true only when:

1. the relationship is currently `active`;
2. current contracted evidence exists;
3. the directed role is capable of representing an incumbent/provider dependency.

Contract, product, and service context is persisted in `relationship_contexts`, separate from immutable evidence snapshots and separate from the current relationship fact. Updating a context row cannot mutate historical evidence.

## Persistence

Migration `20260807_0019` creates:

- `business_relationships`: the source-aware current canonical projection;
- `relationship_evidence_snapshots`: immutable source revisions;
- `relationship_contexts`: contract/product/service context kept outside raw relationship evidence.

Snapshot identity is deterministic and payload-derived. Replay is idempotent. Current relationship identity is deterministic by canonical relationship key. Corrections and retractions add immutable revisions and recompute current state.

The migration supports PostgreSQL `upgrade -> downgrade -> upgrade` and uses bounded explicit index names.

## Existing-evidence integration

Lot 19 does not require a new crawler to become useful.

The procurement adapter projects already persisted Lot 11 contract history into directed contracted evidence:

```text
published procurement contract
  + resolved awardee / subcontractor
  + buyer organization
  -> directed contracted relationship evidence
  -> contract and service contexts
  -> current or historical relationship projection
```

Completed contracts remain historical. Cancelled contracts generate visible retraction revisions. Candidate awardee identities remain candidates.

## Metadata-only provider mappings

The `relationship_catalogs` adapter package contains strict metadata schemas and deterministic mappings for approved future public or licensed sources such as:

- official organization disclosures;
- public partner directories;
- public case studies;
- public certificate relationship metadata;
- reviewed passive observations;
- regulatory filings;
- licensed metadata.

These generic schemas deliberately exclude the `contracted` evidence class. They can provide claimed, observed, historical, or inferred evidence only.

They accept bounded metadata and excerpts and contain no HTTP client, browser, collector, scheduler, opportunity, contact, or outreach path.

## Source governance

Four Lot 19 candidates are modeled in `policies/sources.relationships.yml` and `policies/source_portfolio.relationships.yml`:

- `official-relationship-disclosures`;
- `public-partner-directory-metadata`;
- `public-case-study-metadata`;
- `public-certificate-relationship-metadata`.

Every candidate remains:

- `draft` / `candidate`;
- authorization `missing`;
- without approved hosts or paths;
- automated collection disabled;
- raw-content storage disabled;
- `executable: false`;
- private portal access forbidden;
- personal network access forbidden;
- automatic opportunity creation forbidden;
- contact enrichment forbidden;
- autonomous outreach forbidden.

A checked-in catalog entry is not authorization to execute.

## Protected API

The deployment-protected API exposes persisted data only:

- `GET /v1/relationships`;
- `GET /v1/relationships/{relationship_key}`.

List filters include state, role, evidence class, source kind, endpoint identity state, organization, current contract-backed status, historical-only state, and free-text organization/key search.

The detail view returns the current relationship, immutable evidence chronology, endpoint names and identities, and separate product/service/contract contexts.

API reads never trigger source collection.

## Analyst workspace

The Next.js application exposes:

- `/relationships` for filtering and triage;
- `/relationships/[relationshipKey]` for chronology and evidence inspection.

The UI presents direction, relationship state, strongest evidence class, endpoint resolution, and time validity before the `contract-backed current` indicator. This prevents an inferred or marketing relationship from looking visually equivalent to a contract.

## Safety and architecture gates

The bounded context cannot import network clients, source collection adapters, or opportunity modules. It performs no:

- active scanning or service connection;
- authentication or access-control bypass;
- private customer portal collection;
- personal-network scraping;
- contact enrichment;
- automatic opportunity creation;
- outreach.

All evidence remains professional organization context and is minimized to the fields required for relationship reasoning and analyst review.

## Exit gate

Lot 19 is releasable only when one exact final SHA passes:

- dependency consistency and Python/npm audits;
- Ruff;
- Mypy strict;
- architecture, complexity, safety, release, and roadmap contracts;
- reversible PostgreSQL migrations through `20260807_0019`;
- full backend suite with configured branch-aware coverage threshold;
- frontend TypeScript and production build;
- zero unresolved review threads;
- synchronized `0.20.0` package, README, roadmap, and validation documentation.
