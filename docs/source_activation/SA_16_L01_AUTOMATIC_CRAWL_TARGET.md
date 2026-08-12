# SA-16 L01 — Automatic governed company crawl target

## Status

`IN_PROGRESS` until both the repository CI and the dedicated real-network live workflow pass on the exact final candidate SHA.

This increment must not be called complete, `live_tested`, or fully integrated before that proof exists.

## Objective

Remove the developer-edited-YAML dependency between a resolved organization website and the first governed public-web collection.

The intended runtime chain is:

```text
Organization.website_url
-> AutomaticPublicWebPolicy
-> deterministic PublicWebTarget
-> exact generated SourcePolicy / SourceAuthorization
-> PublicWebClient
-> collect_public_web_target
-> RawObservation + PublicResource provenance
```

L01 does not implement recursive link traversal, sitemap-index recursion, generalized browser rendering, or incremental recrawl. Those remain subsequent SA-16 increments.

## Architecture decisions

### Reuse the canonical public-web target

`PublicWebTarget` remains the single target definition. L01 extends it with:

- `seed_urls` for explicit first-party entry pages such as the canonical homepage;
- `source_id` so a unique organization target identity is not confused with the governed acquisition-source identity.

Existing checked-in targets remain backward compatible: when `source_id` is omitted, it defaults to the existing target `id`.

### Generated governance, not per-company source YAML

The previous collector required `SourceRegistryEntry.policy.id == PublicWebTarget.id`. That made an automatic organization target effectively require a new source-policy record for every company.

L01 separates those identities. `provision_public_web_target()` generates an exact runtime `SourcePolicy` and `SourceAuthorization` from a deployment-approved organization/domain policy. The generated authorization is limited to:

- the canonical website host;
- approved path prefixes;
- the `corporate-public-footprint` purpose;
- bounded automated collection;
- no raw-content storage.

Policy evaluation still happens before the robots request and before every discovered resource request.

### Deterministic target identity

The target id is derived from the canonical organization UUID:

```text
public-web-<organization UUID hex>
```

The source identity for this capability is:

```text
automatic-public-company-web
```

Raw observations and public-resource projections retain the governed source identity while the organization id and target id preserve target lineage.

## Initial discovery behavior

L01 provisions:

- canonical homepage as an explicit `DIRECT` seed;
- `/.well-known/security.txt` discovery;
- exact crawl-scope budgets;
- first-crawl timestamp;
- refresh interval metadata.

It intentionally does not guess that `/sitemap.xml` exists. Automatic robots/sitemap/feed discovery and recursive traversal are owned by the following SA-16 crawler increments.

## Deterministic validation

Unit coverage must prove:

- a canonical website is mandatory;
- target identity is deterministic;
- source and target identities remain distinct;
- homepage and security.txt remain same-origin;
- generated governance permits the approved host and denies another host before collection;
- raw storage remains disabled;
- expired authorization fails closed;
- legacy target source-id behavior remains compatible.

Unit tests remain network-free.

## Controlled live validation

The dedicated production-path runner uses the public Python Software Foundation website as the neutral approved validation target:

```text
Organization(Python Software Foundation, https://www.python.org/)
-> automatic target provisioning
-> generated exact host/path authorization
-> real PublicWebClient
-> real robots.txt request
-> real homepage request
-> optional security.txt handling
-> non-empty RawObservation / PublicResource projection
```

The live gate fails unless:

1. the generated homepage is checkpointed;
2. at least one real observation and projection are produced;
3. every observation and projection uses `automatic-public-company-web` provenance;
4. no canonical resource escapes `https://www.python.org/`;
5. the production collector, not a mock transport, performs the network requests.

## Completion rule

L01 becomes `IMPLEMENTED_VALIDATED` / `live_tested` only after:

1. deterministic tests pass;
2. Ruff passes;
3. strict Mypy passes;
4. architecture/release contracts pass;
5. migration gates remain green;
6. complete backend coverage remains at or above repository thresholds;
7. frontend quality remains green;
8. the SA-16 L01 real-network workflow passes using the production client and collector;
9. the live proof is recorded in this document;
10. the documentation/live-state commit is itself revalidated by both normal CI and the live workflow on the exact final SHA.

A skipped live job, mocked HTTP response, documentation-only claim, or earlier SHA does not satisfy this gate.
