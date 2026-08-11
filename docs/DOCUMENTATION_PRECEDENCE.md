# Documentation Precedence for Source Activation

## Purpose

Cyber Intelligence Platform contains historical lot and Source Activation documents that accurately describe earlier implementation boundaries. Those historical records must remain truthful, but they must not be misread as the current future-state policy after the full-activation mandate.

## Normative order for future OSINT/source work

When documents conflict about whether a useful source or acquisition capability should be implemented in the future, use this order:

1. [`OSINT_FULL_IMPLEMENTATION_MANDATE.md`](OSINT_FULL_IMPLEMENTATION_MANDATE.md)
2. [`SOURCE_POLICY.md`](SOURCE_POLICY.md), [`ACQUISITION_ARCHITECTURE.md`](ACQUISITION_ARCHITECTURE.md), [`PRODUCT.md`](PRODUCT.md), and [`OSINT_COLLECTION_CATALOG.md`](OSINT_COLLECTION_CATALOG.md)
3. [`source_activation/SA_15_20_FULL_ACTIVATION_ROADMAP.md`](source_activation/SA_15_20_FULL_ACTIVATION_ROADMAP.md)
4. [`source_activation/SOURCE_ACTIVATION_MASTER_PLAN.md`](source_activation/SOURCE_ACTIVATION_MASTER_PLAN.md)
5. historical lot/SA closeout documents for the implementation state that existed when they were merged.

## Historical wording

Older documents may truthfully contain phrases such as:

- `blocked`;
- `manual`;
- `non-executable`;
- `disabled`;
- `deferred`;
- `no browser automation`;
- `no recursive crawler`;
- provider-specific candidates not yet authorized or live-tested.

Those phrases remain evidence of the historical release state. They do **not** create a permanent future prohibition when the current mandate assigns the useful capability to SA-15 through SA-20.

Examples:

- Lot 31 historically marked the browser runtime `DEFERRED`; SA-16 now makes generalized isolated browser acquisition mandatory future work.
- Earlier public-web documents excluded recursive crawling; SA-16 now requires recursive crawling inside explicit deployment scope and operational budgets.
- Earlier passive-provider records left Shodan/Censys/SecurityTrails/urlscan/technography candidates non-executable; SA-17 now requires obtaining legitimate entitlements and completing provider-specific activation/live proof.
- Earlier local-tool records declined blanket execution of Amass/theHarvester/SpiderFoot/Recon-ng; SA-17 now requires module/provider-level decomposition so legitimate useful modules can be implemented.
- Earlier LinkedIn/Discord/BrixHub records were fail-closed; SA-19/SA-20 now require legitimate provider-specific access paths or an explicit product-owner exclusion.
- Earlier vulnerability/incident/ATS/identity adapters without `live_tested` remain unfinished live-validation work under SA-18/SA-20.

## Authorization boundary

Future implementation is mandatory for useful legitimate acquisition paths, but this precedence document does not authorize defeating provider or security controls.

CAPTCHA/MFA/authentication bypass, stolen sessions, credential guessing, deceptive account farms, exploit-based data acquisition, private victim files, stolen credentials and private communications remain outside normal OSINT acquisition unless a separate explicit security-testing engagement authorizes the relevant testing technique.

Legitimate accounts may use human/provider-approved CAPTCHA/MFA checkpoints and resume afterward.

## Planning consequence

A useful capability may not be closed merely because it currently needs a key, account, contract, written permission, target registry, stable API or browser workflow. Those are explicit prerequisites owned by the new Source Activation roadmap.

Historical documentation is therefore preserved for auditability while the future implementation target remains unambiguous.