# SA-16 L08 — Automatic public-web runtime wiring

## Status

`FINAL_EXACT_HEAD_REVALIDATION_PENDING`.

SA16-L08 closes the production-runtime gap between SA16-L01 automatic company-site provisioning and the central collection scheduler/worker path.

Pre-documentation candidate:

`f3aa61cb2fb572e2a83e383f3318cb8621d1e251`

Exact-candidate evidence:

- CI #2102 / run `31734378706`: **PASS** backend and frontend;
- SA-16 L08 Live Validation #8 / run `31734378629`: **20/20 PASS**;
- tests: **1,578 passed, 0 failed, 0 errors, 0 skipped**;
- global line coverage: **93.23%**;
- `automatic_public_web_runtime.py`: **100% line / 100% branch**;
- `public_web_registration.py`: **100% line / 100% branch**;
- `public_web_browser_adapter.py`: **100% line / 100% branch**;
- Ruff, strict Mypy, architecture/release 36/36 and reversible migrations: **PASS**;
- frontend audit, typecheck and production build: **PASS**;
- reviews: **0**; unresolved review threads: **0**.

This documentation commit changes the pull-request tree. The resulting head must therefore repeat complete CI and the L08 live workflow before merge.

## Capability

L01 deliberately separates the organization-specific target identity from the governed source identity:

```text
target.id = public-web-<organization UUID hex>
target.source_id = automatic-public-company-web
```

L08 preserves that distinction end to end:

```text
persisted Organization.website_url
-> explicit deployment approval
-> AutomaticPublicWebRuntimeConfig
-> provision_public_web_target()
-> organization-specific PublicWebTarget
-> generated SourcePolicy / SourceAuthorization
-> PublicWebAdapter
-> organization-specific SourceSchedule
-> central collection runtime
-> central scheduler
-> CollectionJob keyed by target.id
-> existing public-web collector
-> canonical observation/resource provenance keyed by target.source_id
```

No per-organization target or schedule YAML is required for an explicitly approved automatic target.

## Runtime identity fix

Before L08, public-web registration and both static/browser adapter constructors still assumed `target.id` was also the source-policy identity. That prevented L01-generated targets with `target.id != target.source_id` from using the normal runtime path.

L08 resolves governance through the normalized source identity while retaining target identity for orchestration:

```text
entry.policy.id == target.source_id
adapter.source_id == target.id
```

Legacy targets remain compatible because an omitted `source_id` normalizes to the target id.

## Fail-closed activation

Automatic runtime collection is disabled by default.

Activation requires:

- explicit enablement;
- a non-empty exact organization UUID set;
- an authorization reference;
- a review timestamp;
- every approved organization to exist in the database;
- every approved organization to have a canonical website.

Optional authorization expiry is preserved. Refresh interval, link depth, page count, total bytes, resource bytes and redirects remain bounded settings.

Each approved organization receives its own deterministic adapter/schedule identity. Duplicate runtime adapter identities fail closed rather than overwriting existing registrations.

## Non-regression proof

Tests cover:

- disabled-by-default behavior;
- incomplete activation rejection;
- multiple approved organizations with distinct target/job identities;
- shared governed provenance without job/checkpoint collapse;
- missing organization rejection;
- missing website rejection;
- adapter collision rejection;
- legacy and split target/source registration;
- real central `build_collection_runtime()` integration;
- real central `run_scheduler_once()` creation of the expected `CollectionJobRecord`.

The repository's configured CI coverage gate passes. The diagnostic global branch coverage is 75.80%; it is recorded transparently and is not represented as a separate 90% branch result. The new L08 runtime module itself is 100% line and branch covered.

## Live validation

The dedicated workflow checks out the exact PR head, installs the normal project package, verifies dependency consistency and runs the production automatic-runtime builder plus real `PublicWebAdapter` HTTP acquisition.

Every configured target must produce a runtime binding, preserve `target.id != target.source_id`, keep `automatic-public-company-web` provenance, checkpoint its homepage, emit non-empty observations/projections and remain inside its approved canonical base origin.

The candidate passed all 20 configured public technical targets:

1. `https://example.com/`
2. `https://example.org/`
3. `https://example.net/`
4. `https://www.python.org/`
5. `https://docs.python.org/`
6. `https://pypi.org/`
7. `https://www.djangoproject.com/`
8. `https://www.freebsd.org/`
9. `https://go.dev/`
10. `https://nodejs.org/`
11. `https://kubernetes.io/`
12. `https://www.postgresql.org/`
13. `https://sqlite.org/`
14. `https://www.kernel.org/`
15. `https://www.w3.org/`
16. `https://www.ietf.org/`
17. `https://www.rfc-editor.org/`
18. `https://curl.se/`
19. `https://www.debian.org/`
20. `https://httpd.apache.org/`

During hardening, OpenSSL was removed because its robots policy denied the homepage, Rust because its robots path redirected under the strict client contract, and GNU because the GitHub runner could not reach it. None was converted into a pass, and no robots/network rule was weakened.

## Safeguards preserved

- source governance remains before acquisition;
- robots decisions remain authoritative;
- origin/path controls remain enforced;
- generated automatic policies keep raw storage disabled;
- page/byte/redirect limits remain enforced;
- unavailable or denied live targets are not counted as successful;
- browser dependencies remain isolated from the normal application manifest;
- existing YAML-configured sources and schedules keep their existing paths.

## Explicit exclusions

L08 is runtime registration and scheduling only. Automatic static-to-browser fallback, authenticated browser flows, form interaction, screenshots, downloads and broader browser-session capabilities remain outside this microlot.

The next SA16 microlot should implement governed static-first browser fallback with deterministic bounded selection criteria while reusing existing authorization, checkpoint and provenance semantics.

## Final completion rule

L08 may be squash-merged only when the **final documentation head itself** has:

1. complete backend and frontend CI green;
2. standard runtime import without browser bindings green;
3. dependency consistency/audits, Ruff, strict Mypy and architecture/release green;
4. reversible migrations green;
5. complete backend tests/coverage green and critical L08 coverage at target;
6. the dedicated live workflow at **20/20** on that exact head;
7. zero actionable reviews/unresolved threads;
8. mergeability against current `main`;
9. squash merge locked to the validated final head SHA;
10. a merged Git tree exactly identical to the validated final-head tree.

Previous-SHA results, skipped live jobs, mocked network paths, partial target passes or post-validation changes do not satisfy this closeout.
