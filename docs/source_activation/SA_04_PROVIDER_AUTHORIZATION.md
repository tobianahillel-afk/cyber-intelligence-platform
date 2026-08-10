# SA-04 Provider Authorization — Incidents and Threat Telemetry

## Decision boundary

This document authorizes only the bounded provider requests described below. It does not authorize threat-actor interaction, `.onion` access, victim files, stolen datasets, credentials, phishing-page visits, malicious-infrastructure connections, scanning, exploitation, organization-compromise inference, commercial opportunity creation, or outreach.

## SEC EDGAR cybersecurity disclosures

- Source ID: `sec-cyber-disclosures`
- Provider: U.S. Securities and Exchange Commission
- Approved host: `data.sec.gov`
- Approved path prefix: `/submissions/`
- Approved method: `GET`
- Approved purpose: `incident-intelligence`
- Authentication: none
- Required deployment configuration: descriptive SEC-compliant `User-Agent`
- Targeting: CIKs explicitly enabled in `policies/sec_incident_targets.yml`
- Raw filing content storage: forbidden

SEC documents its public JSON submissions APIs under `data.sec.gov` and requires automated clients to identify themselves and respect its fair-access limits. SA-04 uses only the issuer submissions metadata endpoint and does not enumerate the global issuer corpus.

SA-04 treats a non-amended Form 8-K family filing containing Item 1.05 as an official company cybersecurity-incident disclosure. The adapter does not download or parse the filing narrative, does not infer the incident occurrence date from `reportDate`, and keeps incident type `unknown` unless another separately authorized official source provides that detail.

## PhishTank verified online phishing data

- Source ID: `phishtank-verified-online`
- Provider: PhishTank / OpenDNS
- Approved host: `data.phishtank.com`
- Approved path prefix: `/data/`
- Approved method: `GET`
- Approved purpose: `threat-telemetry`
- Production authentication: application key through Provider Onboarding secret reference `api_token`
- Required deployment configuration: descriptive `User-Agent`
- Raw feed storage: forbidden

PhishTank's published data terms permit use of its data for commercial and non-commercial purposes subject to those terms. Its developer guidance provides database files for automated high-volume consumption and recommends an application key for automated downloads.

SA-04 consumes only verified-online phishing URL metadata. It never connects to the phishing URL. The provider `target`/brand field is not projected as an organization relationship, victim claim, exposure claim, or compromise claim.

The application key may appear only in the outbound provider request path required by the provider. It is resolved transiently from Provider Onboarding and is excluded from RawObservation source URLs, payloads, logs and canonical telemetry.

## Deferred providers

### ThreatFox and URLhaus Community APIs

The community APIs are not activated for this commercial product. Current abuse.ch guidance distinguishes community access from commercial/enhanced access. Any future integration requires a reviewed commercial entitlement and source-specific authorization, handled in SA-07.

### Ransomware.live

A provider API exists, but the project has not established a sufficiently explicit commercial-use/licence decision for this deployment. It remains non-executable pending provider review. No threat-actor portal, victim file, stolen data, screenshot, negotiation message or credential may be collected.

### Existing licensed placeholders

`licensed-incident-reporting`, `licensed-ransomware-metadata`, `licensed-stix-taxii`, `licensed-phishing-metadata`, `licensed-malware-metadata`, and the other licensed passive providers remain non-executable and are assigned to SA-07 unless a concrete contract is selected.

## Mandatory semantics

```text
SEC filing != complete incident narrative
official disclosure != automatic commercial urgency
phishing URL != organization compromise
impersonated brand != affected organization
global IOC != prospect exposure
ransomware claim != official confirmation
source candidate != execution authorization
```
