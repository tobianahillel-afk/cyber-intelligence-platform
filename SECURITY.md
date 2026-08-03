# Security Policy

## Project status

This project is in an early bootstrap phase and is not yet intended for production deployment.

## Reporting a vulnerability

Do not open a public issue containing secrets, personal data, exploit details against a third party, or evidence taken from a compromised system. Use a private GitHub security advisory when repository settings permit it.

A useful report should include:

- affected component and version or commit;
- reproducible defensive description;
- impact;
- minimal proof using local fixtures or systems you are authorized to test;
- suggested remediation, when available.

## Prohibited repository content

Never commit:

- API keys, tokens, passwords, cookies, private keys, or credentials;
- credential dumps or stolen databases;
- leaked victim files or private negotiation transcripts;
- private phone numbers, home addresses, or unrelated personal profiles;
- production exports containing personal data;
- malware samples or exploit payloads without an approved isolated workflow;
- proprietary source content whose licence does not allow storage.

## Collector security requirements

Every external connector must:

- reference an approved source policy;
- use an outbound allowlist;
- apply timeouts, response-size limits, and rate limits;
- reject redirects to unapproved hosts;
- protect against SSRF and DNS rebinding;
- validate media types and parse untrusted content defensively;
- avoid browser automation intended to defeat access controls;
- avoid arbitrary URL fetching supplied by untrusted users;
- produce structured audit events.

## Passive-analysis boundary

The default product scope is public or licensed intelligence collection and passive analysis. Discovery of a potentially exposed asset does not authorize authentication, exploitation, file access, credential validation, or active security testing.

Any future active-testing capability must be isolated behind explicit authorization records, scope controls, tenant permissions, complete audit logs, and a separate threat model.

## Personal-data controls

Professional-contact data must support provenance, purpose limitation, retention, objection, suppression, correction, and deletion. Suppressed records must not re-enter the platform through later ingestion.
