# SA-15 L08 — GDELT 5 contract re-verification

## Status

`CONTRACT_PREREQUISITE_OPEN`

This increment re-verifies the provider contract required before a GDELT 5 production adapter may be implemented. It deliberately does not create or relabel an adapter against the legacy GDELT DOC/GEO 2.0 endpoints.

The evidence boundary from Lot 12 / SA-14 remains unchanged: GDELT search/news metadata is discovery context until the referenced original resource is acquired through a separately governed evidence path.

## Re-verification date

2026-08-12

## Official provider material reviewed

- `https://blog.gdeltproject.org/scaling-gdelt-for-a-new-era-migrating-to-spanner-with-agentic-interactive-gemini/`
- `https://blog.gdeltproject.org/scaling-gdelt-for-a-new-era-moving-to-daemon-proxies-for-bigtable-gcs-using-agentic-gemini/`
- `https://blog.gdeltproject.org/2026/05/`
- legacy DOC 2.0 documentation at `https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/`
- legacy GEO 2.0 documentation at `https://blog.gdeltproject.org/gdelt-geo-2-0-api-debuts/`

## Current contract finding

The official 2026 GDELT material still describes GDELT 5 as an upcoming/new-era platform transition and describes migration of the API/search infrastructure to Spanner as ongoing work.

The provider material reviewed for this increment does not yet publish a stable replacement GDELT 5 public search/news production contract with all of the information required by Cyber Intelligence Platform:

- canonical supported GDELT 5 search/news endpoint;
- stable request/query semantics;
- stable response schema and versioning contract;
- pagination/checkpoint behavior;
- provider rate/quota behavior;
- redistribution and durable-storage terms for the metadata CIP would persist;
- documented failure/error semantics;
- migration/compatibility policy suitable for a provider-specific production adapter.

The public DOC/GEO 2.0 material remains available, but those endpoints are historical/legacy contracts relative to the GDELT 5 target explicitly owned by issue #115 and SA-15.

## Decision

Do not implement a new `gdelt5` adapter yet.

In particular, do not:

- call DOC 2.0 or GEO 2.0 and label the result `GDELT 5`;
- add `adapter_present`, `executable`, `scheduled`, or `live_tested` stages for a non-existent GDELT 5 adapter;
- infer a production contract from blog implementation details;
- enable a schedule against a legacy endpoint merely to close SA15-L08.

This is a provider-contract prerequisite, not a completed source activation.

## Required implementation once the provider contract is published

When official GDELT material publishes a stable current GDELT 5 search/news execution contract, SA15-L08 must continue with a provider-specific vertical containing:

1. exact host/path/version contract freeze;
2. source-governance entry before any network request;
3. bounded organization/research-purpose query model;
4. provider response schemas;
5. minimum news/event discovery metadata mapping;
6. deterministic provider record identity;
7. result URL canonicalization and safe-host validation;
8. normalized SERP/news discovery projection;
9. zero direct promotion to Evidence, CommercialSignal, NeedHypothesis or Opportunity;
10. pagination/checkpoint/idempotency behavior;
11. retry/rate-limit/schema-drift classification;
12. runtime registration and explicit invocation/schedule policy;
13. deterministic network-free tests;
14. controlled real-endpoint production-adapter validation;
15. exact-head normal CI after any activation-stage promotion.

## Acceptance gate for resuming implementation

Implementation may begin only when official provider documentation is sufficient to answer all of the following without guessing:

- What exact endpoint is the supported current GDELT 5 search/news API?
- What query parameters/operators are stable and supported?
- What fields identify an article/event/result deterministically?
- What are the provider pagination and time-window semantics?
- What are the request/response size limits and rate/quota constraints?
- What may CIP retain durably and redistribute internally for commercial research?
- What error/status behavior is contractual enough to classify safely?

Until then, the exact missing prerequisite remains:

`provider publication of a stable GDELT 5 public search/news execution contract`.

## Relationship to issue #115

Issue #115 remains open and authoritative for this dependency. This document records a fresh 2026-08-12 re-verification and prevents accidental implementation against a legacy contract while the provider migration remains incomplete.
