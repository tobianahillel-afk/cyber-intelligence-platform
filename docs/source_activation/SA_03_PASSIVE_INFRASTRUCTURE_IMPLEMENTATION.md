# SA-03 — Passive Infrastructure Intelligence Implementation

## Scope

SA-03 activates bounded passive domain and infrastructure intelligence on top of the already validated Lot 16 canonical passive-exposure model. It does not add an active reconnaissance engine.

The collection path is:

```text
enabled target
  -> source-policy preflight
  -> approved provider request
  -> immutable RawObservation
  -> PassiveObservationSnapshot
  -> existing Lot 16 persistence/reconciliation
```

Provider output never writes a CommercialSignal, NeedHypothesis, Opportunity, contact target, or outreach action.

## Target registry

`policies/passive_infrastructure_targets.yml` is the only checked-in target registry for these adapters. The repository default is:

```yaml
version: 1
targets: []
```

Each future target requires an explicit internal organization UUID, a canonical public domain, and `enabled: true`. Domain validation reuses Lot 16 canonical public-domain normalization. Reserved/local/non-public suffixes are rejected. The registry is bounded to 500 targets.

An empty target registry causes both SA-03 adapters to return a deterministic no-op batch before provider traffic. Cert Spotter also returns before secret resolution when no target exists.

## Cloudflare DNS-over-HTTPS

Runtime identity:

- source: `cloudflare-doh`;
- adapter: `cloudflare-dns-json`;
- approved host/path: `cloudflare-dns.com/dns-query`;
- record families: A and AAAA only;
- authentication: none.

For each enabled target, the adapter performs only provider-side DNS-over-HTTPS requests. Returned addresses are not contacted.

A globally routable A/AAAA answer maps to a Lot 16 passive snapshot with:

- asset kind `ipv4` or `ipv6`;
- observation kind `passive_dns`;
- source-specific record identity;
- provider TTL represented as the observation expiry;
- organization link `review_required`;
- link method `passive_correlation`;
- explicit `shared_hosting` risk;
- no active-validation, credential, bypass, exploit, applicability or exposure flag.

Non-global/private/reserved addresses are rejected by the canonical Lot 16 asset normalizer and are not projected.

## Cert Spotter Certificate Transparency

Runtime identity:

- source: `certspotter-ct`;
- adapter: `certspotter-issuances-api`;
- approved host/path: `api.certspotter.com/v1/issuances`;
- production authentication: Provider Onboarding secret `api_token`.

The adapter fails closed when an enabled target exists but the connected provider secret cannot be resolved. No token value is written to RawObservation or canonical persistence.

The provider schema bounds issuance IDs, SHA-256 values and DNS-name arrays. Only issuances whose expanded DNS names match the enabled target domain or one of its subordinate names are retained.

Collection remains bounded and resumable:

- one target and one provider page are processed per adapter execution;
- enabled targets rotate through a deterministic `target_index` checkpoint;
- each target keeps its own provider `after` issuance cursor;
- at most 100 issuances are accepted from one provider page;
- cursor state is bounded to the same 500-target limit as the registry;
- a provider page may advance its cursor even when all returned names are out of target scope, preventing a permanently repeated page without promoting those records into observations.

Each retained issuance maps to:

- asset kind `certificate` using the provider-documented hexadecimal `tbs_sha256`;
- observation kind `certificate`;
- explicit current/expired state from certificate validity metadata;
- organization link `review_required` via `passive_correlation`;
- explicit shared/third-party infrastructure risk semantics;
- no endpoint deployment claim and no exposure conclusion.

## Shared persistence

`AdapterCollectionBatch` now includes `passive_exposure_projections`.

Both collection modes persist this field through `persist_passive_snapshots()`:

- normal incremental worker;
- historical backfill worker.

The projection write occurs in the same transaction as the collection completion/checkpoint path, so the runtime cannot report a successful collection while silently discarding the corresponding Lot 16 projection.

No new passive-exposure database table or migration is needed because SA-03 reuses migration `20260806_0016` and the existing Lot 16 persistence layer.

## Scheduling

Both checked-in SA-03 schedules are disabled. This is deliberate:

- the checked-in target registry contains no enabled organizations;
- Cert Spotter additionally requires deployment onboarding/API-key state;
- source activation therefore records both providers as executable target-driven capabilities, not as live-scheduled integrations.

A deployment may enable a schedule only after it supplies an authorized target and all provider-specific runtime dependencies.

## Deferred providers

The following candidates are not activated by SA-03:

- RIPEstat, pending an explicit product commercial-use decision;
- urlscan automated integration, pending approved commercial integration scope and with no scan submission in SA-03;
- `licensed-passive-dns`;
- `licensed-certificate-telemetry`;
- `licensed-passive-exposure`;
- `licensed-technographic-observations`;
- `licensed-cloud-asset-observations`.

The five licensed placeholders move to SA-07, whose Master Plan scope covers licensed/premium providers. Their `.example.invalid` catalog entries remain non-executable until a concrete contract is selected.

## Safety invariants

SA-03 preserves these distinctions:

```text
DNS lookup != organization ownership
DNS lookup != verified exposure
certificate issuance != deployed endpoint
certificate issuance != asset ownership
passive observation != vulnerability applicability
passive observation != compromise
source capability != live-tested integration
passive intelligence != commercial opportunity
```

No SA-03 unit test performs live network traffic. Provider behavior is tested with deterministic HTTP transports and bounded fixtures. Full SA completion still requires all repository gates on one exact final PR head.
