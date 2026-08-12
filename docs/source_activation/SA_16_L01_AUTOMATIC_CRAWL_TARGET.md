# SA-16 L01 — Automatic governed company crawl target

## Status

`REVALIDATION_IN_PROGRESS` on the current `main` content tree.

SA16-L01 is implemented and was originally live-tested before PR #128 merged, but the PR was squash-merged after `main` had advanced. The implementation-head proof remains genuine; this closeout deliberately re-runs both normal CI and the dedicated real-network SA-16 L01 workflow on the current repository content so the final status does not rely on an older branch tree.

Historical final implementation/documentation head:

`f99579909a10595acadc55d092e0aeee7ca42d6c`

That exact head passed:

- normal CI #1923 (`31588625902`): **PASS**;
- SA-16 L01 Live Validation run #2 (`31588625975`): **PASS**.

PR #128 was then squash-merged as `74542d9ade125f4a07afd0f77a6c61f0bb907e94`.

This document is now being revalidated from the current `main` baseline. L01 will be recorded `IMPLEMENTED_VALIDATED_MERGED` only after the final closeout head itself passes normal CI and the dedicated real production-path workflow.

## Objective

Remove the developer-edited-YAML dependency between a resolved organization website and the first governed public-web collection.

The production chain is:

```text
Organization.website_url
-> AutomaticPublicWebPolicy
-> deterministic PublicWebTarget
-> exact generated SourcePolicy / SourceAuthorization
-> PublicWebClient
-> collect_public_web_target
-> RawObservation + PublicResource provenance
```

L01 does not implement recursive link traversal, sitemap-index recursion, generalized browser rendering, or incremental recrawl. Those belong to subsequent SA-16 increments.

## Implemented behavior

`PublicWebTarget` remains the single target model. L01 adds explicit homepage `seed_urls` and a separate governed `source_id`, so an organization-specific target does not require a new source-policy YAML record for every company.

`provision_public_web_target()` generates an exact runtime source policy and authorization from a deployment-approved canonical organization domain. Authorization remains limited to the canonical host, approved path prefixes, `corporate-public-footprint`, bounded automated collection and no raw-content storage.

The generated target uses deterministic identity:

```text
public-web-<organization UUID hex>
```

and governed source identity:

```text
automatic-public-company-web
```

Initial discovery includes the canonical homepage and `/.well-known/security.txt`; it deliberately does not guess arbitrary sitemap/feed locations.

## Safety and provenance invariants

- source governance is evaluated before robots and resource requests;
- off-origin acquisition fails closed;
- raw-content storage remains disabled;
- observations/resources retain the governed source id while target/organization identity remains explicit;
- no page-view-triggered or unrestricted crawler is introduced by L01;
- no provider/live status is inferred from mocks, skipped workflows or adapter presence.

## Deterministic validation

Unit coverage proves the canonical website requirement, deterministic target identity, source/target separation, same-origin homepage/security.txt behavior, generated host/path authorization, off-host denial, raw-storage denial, expired-authorization denial and legacy target compatibility.

## Real live validation contract

The dedicated production-path runner uses the public Python Software Foundation website:

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

The workflow fails unless the generated homepage is checkpointed, real non-empty data is produced, source provenance is `automatic-public-company-web`, no resource escapes the approved origin, and the production client/collector perform the network requests.

## Completion rule

L01 is finally closed only when the same final content head passes:

1. dependency consistency and audits;
2. Ruff;
3. strict Mypy;
4. architecture/release contracts;
5. reversible migrations;
6. complete backend tests/coverage;
7. frontend audit/typecheck/build;
8. the SA-16 L01 real-network workflow;
9. zero unresolved review threads.

A skipped live job, mocked HTTP response, documentation-only claim, older SHA or synthetic merge-ref result does not satisfy this gate.
