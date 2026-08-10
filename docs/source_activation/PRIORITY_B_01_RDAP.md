# Priority B-1 — Governed Public RDAP

## Objective

Complete the open RDAP portion of Priority B without introducing a second passive-asset model or a generic web client.

## Runtime path

```text
explicit RDAP target
  -> IANA RFC 9224 bootstrap
  -> exact HTTPS authoritative RDAP service
  -> minimal public RDAP schema
  -> sanitized RawObservation
  -> Lot 16 PassiveObservationSnapshot(registration)
  -> existing incremental/backfill persistence
```

The checked-in target registry is empty and the checked-in schedule is disabled, so a default deployment performs no RDAP network activity.

## Supported targets

- domain;
- globally routable IPv4;
- globally routable IPv6;
- 32-bit ASN.

Targets are normalized and bound to an internal organization UUID. Duplicate normalized resources are rejected.

## Bootstrap matching

- domains use the most specific matching DNS suffix;
- IPv4/IPv6 use the longest matching prefix;
- ASN uses the most specific containing numeric range.

Only HTTPS endpoints from the matching IANA bootstrap entry are eligible. Redirects are disabled. The response is revalidated against the requested domain, IP allocation range, or ASN range before a snapshot is emitted.

## Canonical evidence semantics

RDAP is represented as `PassiveObservationKind.REGISTRATION` in Lot 16.

The organization association is always `review_required` with `passive_correlation`. Registration or allocation does not prove current operational ownership. Attribution risks remain explicit:

- domain -> `abandoned_domain`;
- IP -> `reassigned_address`;
- ASN -> `reseller`.

All snapshots remain `metadata_only`, `passive_only`, with active probing, credential use, direct validation, applicability assessment, and exposure verification false through the Lot 16 model.

## Privacy boundary

The provider schema intentionally omits RDAP entities and vCard/contact structures. Unknown response fields are discarded by parsing. Raw HTTP response bytes are not stored; the persisted `RawObservation` hashes the sanitized structured provider model.

No registrant email, phone, postal address, entity/vCard, nonpublic registration data, RDRS access, authentication, or contact enrichment belongs in this capability.

## Activation state

The adapter, governance entry, portfolio entry, schedule definition, runtime registration, target registry, and deterministic tests are present. `scheduled` and `live_tested` remain false until deployment activation and separately authorized controlled validation.

## Completion tests

B-1 must prove:

- empty target registry -> no network;
- domain bootstrap + exact identity;
- IPv4 longest-prefix selection;
- ASN range selection;
- non-HTTPS authoritative endpoint fails closed;
- response identity mismatch fails closed;
- RDAP contacts/entities are not materialized;
- governance/portfolio/schedule/runtime reconciliation;
- full repository backend and frontend CI on one exact final SHA.
