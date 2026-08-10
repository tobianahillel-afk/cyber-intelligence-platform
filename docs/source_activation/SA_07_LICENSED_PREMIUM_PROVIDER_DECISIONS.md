# SA-07 — Licensed, premium, LinkedIn and Discord provider decisions

## Decision

SA-07 closes the repository-level ambiguity around conditional/licensed acquisition without manufacturing a commercial entitlement that the deployment does not possess.

Every source owned by `SA-07` is therefore terminal `blocked` in the checked-in activation truth. A blocked record is not a failed product feature: it means the canonical model/control plane exists, but execution is forbidden until a provider-specific commercial and deployment dossier is approved.

Lot 22 remains the execution gate for any future reopening. A later activation must prove, at minimum, the concrete provider/product, customer-facing incorporation/redistribution rights, approved method and fields, lawful purpose, attribution and retention, onboarding/secret references, quotas/cost, Source Governance policy, Source Portfolio executable state, adapter capability, pause/kill-switch controls and controlled live validation.

## Terminal SA-07 inventory

### Licensed intelligence families

- `licensed-incident-reporting` — blocked until a concrete licensed incident provider and customer-facing rights are approved.
- `licensed-ransomware-metadata` — blocked; actor portals, victim files and private/leaked content remain prohibited.
- `licensed-stix-taxii` — blocked until a concrete provider, tenant/collection scope, sharing markings and commercial rights are approved.
- `licensed-phishing-metadata` — blocked; PhishTank remains the current governed public path.
- `licensed-passive-dns` — blocked pending a provider-specific contract, permitted fields, retention, quotas and runtime adapter.
- `licensed-certificate-telemetry` — blocked pending commercial entitlement beyond the governed public certificate path.
- `licensed-malware-metadata` — blocked; malware binaries/samples/download paths remain outside this source activation.
- `licensed-passive-exposure` — blocked pending a concrete provider and customer-facing data rights.
- `licensed-technographic-observations` — blocked pending explicit embedding/redistribution rights.
- `licensed-cloud-asset-observations` — blocked pending provider-specific commercial and deployment approval.
- `licensed-corporate-news-metadata` — blocked pending a concrete news provider, permitted fields, attribution/retention and customer-facing rights.

### Priority B-4 providers carried into SA-07

- `censys-platform-passive`
- `shodan-passive-data`
- `securitytrails-passive-data`
- `urlscan-passive-search`
- `wappalyzer-technographics`
- `builtwith-technographics`

Their B-4 provider-specific reasons remain authoritative. SA-07 does not add adapters, credentials, schedules, scans or product-data redistribution rights for them.

### Conditional professional/community/premium families

- `linkedin-official-api` — blocked until official/licensed access, provider authorization and a real adapter are approved. Scraping/crawling or copied browser sessions are not substitutes.
- `discord-authorized-integration` — blocked until an administrator-installed connector or authorized export and exact permitted scope exist. Self-bots, member scraping and private-message collection remain prohibited.
- `premium-cti-licensed` — blocked until a concrete provider and contract-bound capability are approved.
- `commercial-data-licensed` — blocked until a concrete dataset, permitted fields, lawful purpose and customer-facing rights are approved.

## Evidence and product boundaries

A paid account, trial, API key, free tier, research account, enterprise sales page or technical endpoint is not itself proof that this standalone customer-facing product may ingest, retain, transform, display or redistribute the provider data.

Likewise, provider data never upgrades the canonical evidence boundary by itself:

```text
provider result
!= organization ownership
!= production deployment
!= vulnerability applicability
!= verified exposure
!= compromise
!= commercial need
!= opportunity
!= outreach authorization
```

## Completion gate

SA-07 may close only when:

1. every activation record with `activation_wave: SA-07` has a terminal disposition and a non-empty reason;
2. no SA-07 record remains `planned`;
3. no blocked SA-07 record contains `adapter_present`, `authorized`, `executable`, `scheduled` or `live_tested` stages;
4. Source Activation truth and the Source Coverage Matrix enumerate the same SA-07 inventory;
5. no real provider adapter, secret, schedule, active scan/submission path or browser workaround is introduced by this wave;
6. deterministic reconciliation tests pass;
7. one exact final SHA passes the complete backend and frontend CI;
8. reviews and review threads are clear before squash merge.
