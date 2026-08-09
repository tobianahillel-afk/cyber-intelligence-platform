# SA-01 Provider Access and Governance Review

## Scope

This document is the internal Source Governance reference for the public vulnerability-metadata access paths activated by SA-01. It is a technical/product authorization record, not a legal opinion and not permission to collect unrelated data.

Approved purpose for every source in this document:

`vulnerability-intelligence`

Approved data category:

`vulnerability_metadata`

Raw provider payload storage remains disabled. Credentials, victim data, private communications, private personal data and restricted content remain prohibited.

## NVD CVE API 2.0

- provider: NIST National Vulnerability Database;
- route: `https://services.nvd.nist.gov/rest/json/cves/2.0`;
- approved host: `services.nvd.nist.gov`;
- approved path prefix: `/rest/json/cves/2.0`;
- access: public API; an API key may improve rate limits but is not required by the default adapter;
- adapter: `nvd-cve-api`;
- collection: bounded pagination with deterministic checkpoints;
- provider record -> RawObservation + VulnerabilitySnapshot;
- no organization exposure inference.

Reference: `https://nvd.nist.gov/developers/vulnerabilities`.

## FIRST EPSS

- provider: FIRST EPSS;
- API route: `https://api.first.org/data/v1/epss`;
- approved host: `api.first.org`;
- approved path prefix: `/data/v1/epss`;
- adapter: `first-epss-api`;
- use: targeted CVE lookup in bounded batches from the explicit query-target registry;
- full daily bulk synchronization is not forced through the materialized CollectionAdapter batch because FIRST recommends the daily CSV for bulk access;
- EPSS remains an exploitation-probability signal, not organization risk or exposure proof.

References: `https://api.first.org/epss/` and `https://www.first.org/epss/data.html`.

## GitHub Global Security Advisories

- provider: GitHub;
- route: `https://api.github.com/advisories`;
- approved host: `api.github.com`;
- approved path prefix: `/advisories`;
- adapter: `github-global-advisories`;
- access: public global-advisory metadata path;
- collection: bounded pagination, deterministic mapping and replay-safe observations;
- no repository scraping or unrelated GitHub account/profile collection.

Reference: `https://docs.github.com/en/rest/security-advisories/global-advisories`.

## CVE Services

- provider: CVE Program;
- route prefix: `https://cveawg.mitre.org/api/cve/`;
- approved host: `cveawg.mitre.org`;
- approved path prefix: `/api/cve/`;
- adapter: `cve-org-records`;
- execution: only explicit CVE identifiers from the query-target registry;
- no free-form crawling.

Reference: `https://www.cve.org/AllResources/CveServices`.

## OSV

- provider: OSV;
- base route: `https://api.osv.dev/v1`;
- approved host: `api.osv.dev`;
- approved path prefix: `/v1/vulns/`;
- adapter: `osv-api`;
- execution: only explicit OSV identifiers from the query-target registry;
- no arbitrary package enumeration.

Reference: `https://google.github.io/osv.dev/api/`.

## CIRCL Vulnerability-Lookup

- provider: CIRCL;
- route prefix: `https://vulnerability.circl.lu/api/cve/`;
- approved host: `vulnerability.circl.lu`;
- approved path prefix: `/api/cve/`;
- adapter: `circl-cve-v5`;
- execution: only explicit CVE identifiers from the query-target registry;
- CVE-compatible payloads preserve CIRCL as a distinct source lineage.

Reference: `https://vulnerability.circl.lu/`.

## Runtime constraints

All six paths remain subject to:

1. Source Governance policy evaluation before HTTP;
2. Source Portfolio executable state and runtime adapter reconciliation;
3. quota/cost/circuit controls;
4. bounded response-size and JSON-schema validation;
5. immutable RawObservation hashes;
6. deterministic canonical mappings;
7. retry only for transport, `429`, or server failures;
8. fail-closed behavior for schema drift, policy denial and invalid checkpoints;
9. no direct company, signal, need, score or opportunity writes;
10. exact-SHA regression validation before merge.

## Review date

Internal technical/source-governance review recorded: 2026-08-09.

Any provider terms, access method, hostname, API path, authentication requirement or material schema change invalidates this review and requires a new authorization revision before continued automated collection.
