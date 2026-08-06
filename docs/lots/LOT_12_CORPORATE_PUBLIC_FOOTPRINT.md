# Lot 12 — Corporate Public Footprint, Documents, Search, and Archives

## Status

`IMPLEMENTED_VALIDATED`

The technical foundation, bounded public-web adapter, immutable history, protected read API, analyst workspace, tombstones, and quarantined search leads are implemented and validated.

This status means the **software capability is complete**. It does not authorize collection against a real organization. Production activation is a separate governance operation requiring a reviewed target, source policy, authorization reference, executable portfolio state, and schedule. The checked-in example remains disabled and non-executable.

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

A search result is a discovery lead. It cannot independently confirm a claim. A search result and its target page belong to the same corroboration group and never count as two independent sources.

## Implemented architecture

### Public resource identity

Every public resource has a deterministic identity based on the organization, canonical URL, and resource kind. The domain supports pages, documents, feeds, structured data, repositories, archives, and search results even where an executable provider is intentionally deferred.

### Immutable versions

Fetched content produces immutable versions containing bounded metadata:

- SHA-256 content hash;
- canonical and fetched URL;
- MIME type and byte size;
- fetch, publication, and source-update timestamps;
- language and bounded title;
- optional extracted-text hash;
- minimized excerpt;
- explicit predecessor relationship.

Changed content creates a new version. Unchanged content does not duplicate versions. Historical versions do not automatically create current commercial opportunities.

### Governed public-web adapter

The `public-web-sitemap` adapter implements:

- explicit organization-bound targets;
- source-policy and authorization evaluation before requests;
- `robots.txt` before sitemap and page retrieval;
- explicit sitemap URLs, host, and path allowlists;
- HTTPS/HTTP canonical URLs without embedded credentials;
- rejection of local names, internal suffixes, and IP-literal targets;
- bounded pages, total bytes, resource size, and redirects;
- redirect scope re-evaluation;
- bounded HTML, PDF, and text MIME handling;
- sitemap duplicate filtering and XML DTD/entity rejection;
- `noindex` and `noarchive` suppression;
- credential-marker quarantine;
- transactional persistence and replay-safe checkpoints;
- runtime-derived user-agent versioning.

### Tombstones and chronology

HTTP `404` and `410` responses create explicit tombstone versions instead of deleting history. Tombstones preserve resource identity, kind, last-known title, chronology, and predecessor links while retaining no response body and creating no claim.

### Search-result quarantine

Search-query templates are versioned and disabled by default. No external search provider is connected. Search metadata remains a quarantined lead, cannot confirm a claim, and is capped at candidate confidence. Target content must be retrieved through an independently approved path before it supports an observed or resolved fact.

### Protected read API

Implemented endpoints:

- `GET /v1/public-footprint/resources`;
- `GET /v1/public-footprint/resources/{resource_id}`.

The endpoints read persisted data only and support pagination, organization/source/kind/state filters, local persisted-data search, version chronology, claim provenance, hashes, and predecessor links. Analyst search never initiates collection.

### Research workspace

The `/research` workspace provides:

- resource list and detail views;
- collection, access, quarantine, and tombstone states;
- version and claim counts;
- immutable chronology;
- hashes and predecessor links;
- evidence basis, resolution status, and confidence;
- canonical source and corroboration provenance.

## Non-executable safeguards

The checked-in public-web example is independently blocked at every execution layer:

- source status: `draft`;
- authorization status: `missing`;
- automated collection: `false`;
- approved hosts, paths, and purposes: empty;
- target enabled: `false`;
- portfolio status: `candidate`;
- collection schedule: absent;
- search templates enabled: `false`.

A cross-registry test verifies identifier alignment while proving that the example cannot execute accidentally.

## Security and data boundaries

The implementation does not permit:

- paywall, authentication, CAPTCHA, MFA, or access-control bypass;
- private repositories or workspaces;
- credential or secret collection;
- indiscriminate document mirroring;
- LinkedIn, Discord, or BrixHub collection without explicit authorization;
- active scanning or exploitation;
- autonomous outreach;
- invented production authorization.

Only bounded metadata, hashes, minimized text, and provenance are persisted. Raw response bodies are not stored.

## Tests and validation coverage

The lot includes tests for:

- URL canonicalization and scope;
- redirect loops and budgets;
- robots and policy-before-network behavior;
- MIME and byte limits;
- sitemap parsing and XML hardening;
- duplicate pages and replay;
- immutable version history;
- tombstones;
- credential-marker quarantine;
- source-to-organization binding;
- search-result confidence and corroboration rules;
- API and persistence behavior;
- worker transactionality;
- migration upgrade, downgrade, and upgrade;
- frontend typecheck and production build.

The final release is version `0.13.0`. Exact final-head CI evidence is recorded on pull request `#35`; no documentation-only commit may be added after that successful final run without rerunning all gates.

## Accepted limitations

- No real organization target is authorized in the repository.
- No search API provider is connected.
- No archive provider such as CDX is connected.
- PDF handling records bounded document evidence; advanced extraction remains provider- and format-dependent.
- DNS-resolution pinning and isolated browser execution remain future hardening topics; the current adapter is restricted to explicitly reviewed public DNS targets and bounded static HTTP.

## Exit decision

Lot 12 is complete because the governed software path, persistence model, analyst read path, safety controls, and tests are delivered. Production activation is intentionally outside the merge decision and must be reviewed separately for each real source and organization.
