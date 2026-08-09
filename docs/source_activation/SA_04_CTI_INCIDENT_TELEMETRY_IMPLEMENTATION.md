# SA-04 — CTI, Incident and Threat Telemetry Implementation

## Scope

SA-04 activates two provider-specific public paths on top of the already validated Lot 14 and Lot 15 canonical models:

```text
SEC target -> submissions metadata -> RawObservation -> IncidentClaimSnapshot
PhishTank feed -> verified online URL metadata -> RawObservation -> IndicatorSnapshot
```

Both canonical projection channels are persisted by the shared incremental worker and historical-backfill worker in the same transaction as collection progress.

## SEC EDGAR path

The checked-in `policies/sec_incident_targets.yml` is empty by default. Each future target requires:

- an internal organization UUID;
- an exact 10-digit SEC CIK;
- explicit `enabled: true`;
- a deployment `CIP_SEC_EDGAR_USER_AGENT` value before provider traffic.

The adapter processes one enabled target per execution. It retrieves only `data.sec.gov/submissions/CIK##########.json`, validates that the response CIK equals the target CIK, and scans the bounded `filings.recent` arrays.

Only non-amended Form 8-K variants whose `items` metadata contains Item 1.05 are projected. At most 100 new Item 1.05 records are emitted in one execution. Per-target accession checkpoints prevent already-seen recent metadata from being projected repeatedly.

An Item 1.05 filing maps to a Lot 14 official company confirmation with an exact organization link backed by the deployment's explicit CIK-to-organization target. SA-04 intentionally does not infer:

- occurrence date from `reportDate`;
- incident subtype from filing metadata;
- victim count or affected systems;
- severity beyond the fact that the issuer filed Item 1.05;
- commercial urgency or opportunity state.

The filing narrative is not downloaded by this adapter.

## PhishTank path

The PhishTank adapter is global defensive telemetry, not organization intelligence.

Production collection requires:

- connected Provider Onboarding secret `api_token`;
- deployment `CIP_PHISHTANK_USER_AGENT`;
- the exact authorized `data.phishtank.com/data/` path.

The provider key is used only to construct the outbound feed request. RawObservation uses a key-free provider URL and stores no raw feed body.

One refresh may parse at most 100,000 provider records and projects at most the 1,000 highest PhishTank IDs. Only provider records already marked `verified=yes` and `online=yes` are accepted by the strict schema.

Each accepted record maps to a Lot 15 URL indicator with:

- state `malicious`;
- source kind `phishing_feed`;
- provider-aggregate sensor scope;
- two-hour freshness expiry from collection time;
- no binary payload;
- no direct validation;
- no organization ID or compromise relation.

The provider `target` field is deliberately ignored in the canonical projection because an impersonated brand is not evidence that that organization is compromised or affected.

SA-04 never visits the phishing URL or any infrastructure named by an indicator.

## Shared persistence

`AdapterCollectionBatch` adds:

- `incident_claims`;
- `threat_indicator_snapshots`.

The incremental worker and backfill worker both call the existing validated persistence functions:

- `persist_incident_claims()`;
- `persist_indicator_snapshots()`.

No new database migration is needed. SA-04 reuses the Lot 14/15 persistence schema.

## Scheduling and deployment state

SEC and PhishTank schedules are checked in but disabled. This is deliberate:

- SEC has no checked-in target and no default User-Agent;
- PhishTank has no checked-in application secret and no default User-Agent.

Their activation records therefore prove adapter/governance executability but do not claim `scheduled` or `live_tested`.

## Deferred source families

Licensed incident reporting, ransomware metadata, STIX/TAXII, commercial phishing, malware metadata and other commercial CTI are assigned to SA-07.

Generic provider-family placeholders such as `official-company-incident-disclosures`, `regulator-cert-incident-notices`, and generic advisory families are assigned to SA-10 provider decomposition/reconciliation rather than being falsely counted as provider integrations.

## Safety invariants

```text
attacker claim != official confirmation
SEC filing != complete incident narrative
ingestion time != incident time
global IOC != organization compromise
phishing brand target != affected organization
malicious URL != permission to visit it
provider data != opportunity
```

No SA-04 unit test performs live network traffic. Complete delivery still requires all repository gates on one exact final PR head.
