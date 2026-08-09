# SA-03 Provider Authorization — Passive Infrastructure Intelligence

## Decision boundary

This document authorizes only the bounded provider requests described below for the Cyber Intelligence Platform SA-03 implementation. It does not authorize active scanning, direct connection to returned assets, authenticated enumeration of prospect infrastructure, vulnerability validation, exploitation, compromise inference, autonomous opportunity creation, or outreach.

A provider appearing in this document is not evidence that a discovered asset belongs to an organization. Provider output must pass through the Lot 16 passive-exposure model and organization-link review rules.

## Cloudflare DNS-over-HTTPS

- Source ID: `cloudflare-doh`
- Owner: Cloudflare
- Approved host: `cloudflare-dns.com`
- Approved path: `/dns-query`
- Approved method: `GET`
- Approved purpose: `passive-infrastructure-intelligence`
- Approved record types in SA-03: `A`, `AAAA`
- Authentication: none
- Raw response storage: forbidden
- Canonical retention category: `technology_observation`
- Targeting: only domains explicitly enabled in `policies/passive_infrastructure_targets.yml`

Cloudflare documents the public 1.1.1.1 DNS-over-HTTPS resolver, including JSON GET requests with `Accept: application/dns-json`, and states that the API does not require authentication. The public resolver remains subject to Cloudflare's published terms of use.

The JSON representation is provider-defined rather than an IETF-standard schema. SA-03 therefore treats schema changes as a source-contract concern, bounds response size, and supports only the A/AAAA fields required for the passive DNS projection.

A DNS answer is a passive resolution observation. It is not proof of asset ownership, dedicated hosting, exposure, vulnerability applicability, or compromise.

## Cert Spotter / SSLMate CT Search API

- Source ID: `certspotter-ct`
- Owner: Opsmate, Inc. / SSLMate
- Approved host: `api.certspotter.com`
- Approved path: `/v1/issuances`
- Approved method: `GET`
- Approved purpose: `passive-infrastructure-intelligence`
- Authentication for production: API key through Provider Onboarding secret reference `api_token`
- Raw response storage: forbidden
- Canonical retention category: `technology_observation`
- Targeting: only domains explicitly enabled in `policies/passive_infrastructure_targets.yml`

SSLMate documents `tbs_sha256` as the hexadecimal SHA-256 digest identifying an issuance. The domain issuance endpoint can be used on a limited unauthenticated basis for personal/evaluation purposes, but SSLMate requests account registration and API-key authentication for production use. CIP therefore does not rely on anonymous production access: the runtime adapter fails closed when an enabled target exists but the connected `api_token` cannot be resolved.

A CT issuance can include a domain because a certificate was issued for it. It does not prove that the certificate is currently installed, that the underlying endpoint is operated directly by the organization, that an asset is exposed, or that any vulnerability applies.

## Providers deliberately not executable in SA-03

### RIPEstat

RIPEstat remains a candidate/non-executable path until the project has an explicit decision covering commercial use for this product and the exact API fields, hosts, paths, cadence, and retention.

### urlscan.io

SA-03 does not submit URLs for scanning and does not automate urlscan search. Any future commercial integration requires a separately approved provider plan/authorization and a new source-policy review.

### Licensed passive providers from Lot 16

The existing `licensed-passive-exposure`, `licensed-technographic-observations`, `licensed-cloud-asset-observations`, `licensed-passive-dns`, and `licensed-certificate-telemetry` placeholders remain non-executable. Their `.example.invalid` entries are governance placeholders, not runnable adapters. They may only be activated after a concrete provider contract identifies the exact allowed fields, licence, credentials, hosts, paths, quotas, cost, retention, and automation scope.

## Mandatory evidence semantics

```text
DNS lookup != ownership
certificate issuance != deployed endpoint
passive asset != verified exposure
technology/version observation != vulnerability applicability
provider candidate != execution authorization
passive observation != commercial opportunity
```

No SA-03 adapter may bypass these distinctions.
