# Lot 12 — Corporate Public Footprint, Documents, Search, and Archives

## Status

`IN_PROGRESS`

## Primary business outcome

Build a reproducible public-evidence map for each organization so analysts can discover contracts, projects, technologies, providers, changes, security objectives, and professional contact paths that are absent from structured registries.

## Dependencies

- Lot 08 — organization identity foundation;
- Lot 10 — source portfolio runtime, backfill, freshness, cost, and health;
- Lot 11 — procurement history, contracts, published providers, and renewal timing.

## Canonical distinctions

```text
search result or analyst query
  != approved target retrieval
  != immutable resource version
  != extracted claim
  != resolved fact
  != current commercial opportunity
```

A search result is a discovery lead. It cannot independently confirm a claim. A search result and the target page it points to belong to the same corroboration group and never count as two independent sources.

## Initial architecture

### Public resource identity

Every public resource has a deterministic identity based on:

- canonical organization;
- canonical URL;
- resource kind;
- source and discovery method.

The first implementation supports sitemaps, feeds, structured data, public pages, documents, public repositories, archive snapshots, search-result metadata, and direct analyst-approved targets.

### Immutable versions

Fetched content creates immutable versions containing only bounded metadata:

- SHA-256 content hash;
- canonical and fetched URL;
- MIME type and byte size;
- fetch, publication, and source-update timestamps;
- language and bounded title;
- optional hash of extracted text;
- optional minimized summary or excerpt;
- explicit predecessor relationship.

A changed page creates a new version. An unchanged response does not duplicate a version. Historical versions never automatically create a current buying signal.

### Crawl scope

Before network access, every target is evaluated against an explicit scope:

- HTTP/HTTPS only;
- no embedded username or password;
- approved hosts and path prefixes;
- maximum depth, page count, bytes, resource size, and redirects;
- approved MIME types;
- source policy, authorization, quota, and retention from the existing runtime.

The scope returns a deterministic allow/deny reason suitable for tests and audit.

### Claims

Claims remain separate from resources and versions. Initial claim families are:

- public contract or project;
- named technology or architecture;
- provider, partner, or customer relationship;
- security, compliance, audit, resilience, or transformation objective;
- professional contact path;
- corporate change.

Claims carry confidence, source locator, bounded excerpt, evidence basis, and resolution status. Search-result metadata cannot be marked confirmed.

## Source families planned

1. approved sitemap and feed discovery;
2. bounded public-domain crawl;
3. public PDF and document metadata with minimized extraction;
4. GitHub/GitLab public organization and repository metadata;
5. approved search APIs and versioned analyst query templates;
6. Common Crawl and Wayback/CDX when source policy permits;
7. official corporate reports, presentations, documentation, engineering blogs, and career pages.

Each family requires its own source-policy decision and adapter contract. Catalog entries remain non-executable until approved.

## Mandatory invariants

1. No target outside an approved host or path is fetched.
2. Robots, terms, authorization, quota, and source governance are evaluated before network access.
3. No paywall, authentication, CAPTCHA, MFA, or access-control bypass is attempted.
4. No private repository, personal workspace, secret, credential, or non-public document is collected.
5. Search metadata remains a lead until the target is retrieved through an approved path.
6. Search metadata and target content do not count as independent corroboration.
7. Full documents are not indiscriminately mirrored; extraction is bounded and purpose-limited.
8. Redirects, canonical URLs, copies, and archive snapshots converge without duplicate facts.
9. Corrections, disappearance, tombstones, and retractions remain historical events.
10. Backfill reconstructs historical footprint without flooding the current Opportunity Inbox.

## Required tests

- URL canonicalization and invalid URL rejection;
- host/path/depth/page/byte/redirect budgets;
- MIME and resource-size rejection;
- deterministic resource identity and version keys;
- duplicate and changed resource behavior;
- archive chronology;
- search-result-only claim cannot be confirmed;
- search result and target share one corroboration group;
- restricted or credential-like content is quarantined;
- source-to-organization resolution;
- backfill/incremental convergence and replay idempotence;
- reversible migrations;
- protected API and analyst UI;
- complete CI and coverage gate.

## First implementation slice

The first slice intentionally contains no network adapter. It establishes:

- canonical URL identity;
- bounded crawl-scope decisions;
- immutable public-resource and version domain models;
- claim evidence and resolution constraints;
- unit tests for the safety and deduplication invariants.

Network collection begins only after this domain contract passes CI.

## Exit gate

An organization workspace can display its public footprint, document versions, archive chronology, and extracted business/cyber claims with provenance, date, confidence, resolution status, and explanation, without indiscriminate mirroring or access bypass.

## Non-goals

- personal-profile crawling;
- LinkedIn, Discord, BrixHub, or other conditional sources without explicit authorization;
- global entity resolution;
- final commercial scoring;
- authenticated browser automation;
- mass storage of copyrighted documents;
- autonomous outreach or engagement.