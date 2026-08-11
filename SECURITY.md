# Security Policy

## Project status

Cyber Intelligence Platform is under active development. The source-acquisition roadmap intentionally expands toward broad public/licensed/authorized OSINT coverage, automatic company crawling, headless browser execution, legitimate authenticated workflows and provider-specific live validation.

The implementation mandate is documented in `docs/OSINT_FULL_IMPLEMENTATION_MANDATE.md`.

## Reporting a vulnerability

Do not open a public issue containing secrets, personal data, exploit details against a third party, or evidence taken from a compromised system. Use a private GitHub security advisory when repository settings permit it.

A useful report should include:

- affected component and version/commit;
- reproducible defensive description;
- impact;
- minimal proof using local fixtures or systems you are authorized to test;
- suggested remediation when available.

## Repository secret and data hygiene

Never commit:

- API keys, tokens, passwords, cookies, private keys or raw credentials;
- credential dumps or stolen databases;
- leaked victim files or private negotiation transcripts;
- unrelated private personal data;
- production exports containing unminimized personal data;
- unreviewed malware/exploit payloads outside an isolated defensive workflow;
- proprietary source content whose licence does not permit repository storage.

Provider credentials must be stored through the project secret-reference/onboarding model.

## Collector security requirements

Every external connector must:

- reference source governance for the exact execution path;
- preserve provider/deployment authorization scope;
- use outbound host/origin controls;
- apply timeouts, response-size and resource budgets;
- validate redirects;
- protect against SSRF and DNS rebinding;
- validate media types and parse untrusted content defensively;
- isolate browser sessions and downloaded files;
- redact secrets from logs/screenshots/traces;
- produce structured audit events;
- expose checkpoint/retry/circuit/source-health behavior;
- support controlled production-adapter live validation.

## Automatic crawling security

Recursive crawling of approved organization domains is a required product capability.

The crawler must use:

- canonical organization/domain evidence;
- deployment authorization;
- robots policy handling;
- approved origins and paths;
- configurable depth/page/byte/time/concurrency budgets;
- canonical URL and duplicate suppression;
- redirect/SSRF protections;
- MIME and document controls;
- incremental freshness/change detection;
- automatic shutdown/quarantine on ownership, scope or authorization changes.

The goal is broad automatic company research within approved scope, not unrestricted network behavior.

## Browser and authenticated workflow security

A generalized Playwright/Chromium runtime is a required acquisition capability.

Browser workers must use:

- disposable processes/contexts;
- Chromium sandbox and site isolation;
- restricted filesystem/process permissions;
- source-specific cookies/sessions;
- no cross-source credential reuse;
- request interception and host controls;
- download quarantine;
- CPU/memory/time/navigation budgets;
- secret redaction;
- complete navigation/authentication audit.

Legitimate authenticated workflows may use provider-approved service/test accounts, OAuth/SSO, administrator-installed connectors and analyst-assisted MFA.

## CAPTCHA, MFA and access-control boundary

The product must support human/provider checkpoints for CAPTCHA and MFA encountered by a legitimate authorized account.

Normal OSINT acquisition does not implement techniques whose purpose is to defeat access controls. Do not:

- bypass CAPTCHA/MFA/authentication to obtain unauthorized access;
- steal or replay another user's session;
- guess or validate credentials;
- create deceptive account farms to evade bans/quotas;
- exploit third-party systems to acquire data.

If a separately authorized security-testing engagement later includes active authentication or access-control testing, that capability must use a separate scope/authorization model, isolated runtime and complete audit trail.

## Passive intelligence and active testing

The product should maximize lawful passive intelligence coverage through DNS, CT, RDAP, Shodan passive/indexed APIs, Censys, SecurityTrails, urlscan, VirusTotal metadata, GreyNoise, reputation feeds and technography providers when legitimate access exists.

Passive-provider authorization does not automatically authorize active scanning or exploitation.

Active security testing may be implemented as a separate capability only for explicitly authorized targets and engagements with:

- exact target scope;
- allowed techniques;
- start/end times;
- tenant/user permissions;
- rate and safety controls;
- complete audit logs;
- rollback/stop controls;
- separate threat model.

## Local OSINT tools

Local frameworks with mixed behavior must be decomposed by module/provider.

Safe and authorized modules from Sherlock, Amass, theHarvester, SpiderFoot, Recon-ng, Maltego and similar tools may be implemented. A framework's active or unsupported modules must not silently inherit authorization from its passive modules.

## CTI, incident and ransomware data

The project may ingest lawful public/licensed incident, ransomware, phishing, malware and IOC metadata.

Threat-actor claims remain claims and must be corroborated separately.

Private victim files, stolen credentials, extorted datasets and private negotiations are not required normal inputs for the product.

## Professional/community data

Legitimate professional/community integrations may include official/authorized LinkedIn paths, Reddit APIs, Discord administrator-installed connectors, Stack Exchange, Mastodon, Bluesky, YouTube and licensed B2B datasets.

Private messages and unrelated private-life data remain outside ordinary B2B research scope.

## Download and parser security

All downloaded files enter quarantine before parsing.

Required controls include:

- generated internal filenames;
- independent content-type detection;
- compressed/uncompressed size limits;
- archive depth/member/path controls;
- malware/reputation checks where available;
- isolated PDF/Office/Tika/ExifTool/OCR/translation workers;
- no automatic execution;
- no analyst-workstation opening by the acquisition worker;
- bounded extraction output;
- retention/deletion policy.

## Personal-data controls

Professional-contact data must support provenance, purpose limitation, retention, objection, suppression, correction and deletion. Suppressed records must not re-enter the platform through later ingestion.

## Live-provider testing

Real provider connectivity is part of security assurance because it exposes schema drift, auth errors, redirect changes, quotas and source behavior that fixtures cannot prove.

Controlled live tests must:

- use production adapters;
- use legitimate provider access;
- avoid printing secrets/payloads unnecessarily;
- use neutral/first-party/approved targets;
- remain bounded;
- record only safe aggregate proof;
- rerun after any commit that changes the validated behavior/state.