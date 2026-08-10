# Priority B completion audit

Status: final reconciliation gate for issue #77.

Reviewed on: 2026-08-10.

## Purpose

Priority B closes passive organization and technology evidence without turning catalogue breadth into ungoverned network authority. Completion means every exact Priority B capability/provider is either executable through the shared governed runtime or has an explicit owned terminal/future disposition. It does not mean checked-in example targets become authorized, that licensed providers are usable without contracts, or that passive observations become verified exposure.

## Earlier Source Activation regression check

The final Priority B gate also re-checks the Source Activation foundation that Priority B depends on.

### SA-00

- The Source Activation lifecycle, inventory loader and deterministic audit remain present.
- `osint-framework-import` remains a catalogue-candidate path only: catalogued/reviewed, non-executable, and owned by SA-00.
- OSINT Framework synchronization is candidate discovery and never grants crawling or provider authorization.

### SA-01

The following vulnerability/open-data providers remain active and executable:

- `cve-org-services`;
- `nvd-vulnerabilities`;
- `first-epss`;
- `osv-api`;
- `github-global-advisories`;
- `circl-vulnerability-lookup`.

They remain vulnerability knowledge, not company exposure proof.

### SA-02

- `brave-search-api` remains active/executable for governed search metadata.
- `internet-archive-cdx` remains active/executable for bounded archive discovery.
- the Lot 12 public-web capability remains adapter-present but the checked-in example target is disabled and unauthorized.

### SA-03

- `cloudflare-doh` remains active/executable for target-driven A/AAAA passive DNS metadata;
- `certspotter-ct` remains active/executable for target-driven certificate-transparency metadata;
- the checked-in passive-infrastructure target registry remains empty.

DNS/CT evidence remains review-required passive correlation and never proves ownership or exposure.

### SA-04

- `sec-cyber-disclosures` remains active/executable for targeted SEC Item 1.05 metadata;
- `phishtank-verified-online` remains active/executable for verified-online phishing telemetry;
- neither adapter directly creates a commercial signal, need, score, opportunity or outreach action.

## Priority B reconciliation

### B-1 — RDAP

`iana-rdap-public` is active/executable through the shared runtime. The checked-in `rdap_targets.yml` registry is empty, so repository defaults do not perform organization-bound RDAP collection. Registration/allocation metadata remains passive review-required evidence and excludes person/contact harvesting.

### B-2 — developer ecosystem/package metadata

The following exact capabilities are active/executable:

- `github-public-org-repositories`;
- `gitlab-public-group-projects`;
- `pypi-public-package-metadata`;
- `npm-public-package-metadata`;
- `maven-central-public-metadata`.

The checked-in `developer_ecosystem_targets.yml` registry is empty. Repository/package presence remains public engineering context, never production deployment, vulnerability applicability or verified exposure.

### B-3 — public web/feed/document completion

B-3 extends the existing Lot 12 bounded public-web collector with RSS/Atom, canonical `/.well-known/security.txt`, bounded plain text and bounded safe PDF text extraction. It does not create a second crawler.

The checked-in `public-web-example-fr-organization` target remains a documentation/example target with `enabled: false`, no authorization document reference and no review timestamp. This is intentionally not converted to `active` merely to close Priority B. B-3 completion is a capability statement; network execution still requires a real organization-bound authorized target.

### B-4 — provider-specific passive platforms

The six exact provider records are terminal fail-closed SA-07 dependencies:

- `censys-platform-passive`;
- `shodan-passive-data`;
- `securitytrails-passive-data`;
- `urlscan-passive-search`;
- `wappalyzer-technographics`;
- `builtwith-technographics`.

Each is `blocked`, mapped and owned by SA-07 with a provider-specific reason. None has adapter, authorization, executable, scheduled or live-tested stages. B-4 added no network client or scan/submission path.

### Future licensed passive families are owned, not unknown

The generic future families below intentionally remain `planned`, but each is explicitly owned by SA-07 and therefore is not an unknown/unowned Priority B row:

- `licensed-passive-dns`;
- `licensed-certificate-telemetry`;
- `licensed-passive-exposure`;
- `licensed-technographic-observations`;
- `licensed-cloud-asset-observations`.

SA-07 must decompose/select concrete providers and prove compatible entitlement before any of them can become executable.

## Final semantic boundary

Priority B completion does not change the evidence model:

- DNS, CT and RDAP do not prove current organization ownership or exposure;
- repository/package presence does not prove deployment;
- technography/provider observations do not prove vulnerability applicability;
- public-web/feed/security.txt/document presence does not prove a commercial need;
- no passive provider observation directly creates a signal, score, opportunity, contact target or outreach action;
- no active scan, probe, exploitation, authentication bypass, private-data collection or provider-control bypass is authorized.

## Machine-enforced completion gate

`tests/unit/source_activation/test_priority_b_completion.py` must enforce:

1. the SA-00 through SA-04 regression set above;
2. all B-1/B-2 executable source records and their mandatory stages;
3. B-1/B-2 empty checked-in target registries;
4. the B-3 checked-in target remaining disabled and unauthorized while the capability is represented in the Coverage Matrix;
5. all six B-4 provider records being terminal fail-closed SA-07 dispositions;
6. all generic future passive families having an explicit SA-07 owner rather than an unknown wave;
7. Source Activation truth and `SOURCE_COVERAGE_MATRIX.md` containing every exact Priority B source/provider ID;
8. the complete backend and frontend CI passing on one exact final SHA.

Only after this gate is green and issue #77 is closed may SA-05/Sherlock implementation begin.
