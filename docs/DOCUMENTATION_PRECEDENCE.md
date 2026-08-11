# Documentation Precedence for Source Activation

## Purpose

Cyber Intelligence Platform contains historical lot and Source Activation documents that accurately describe earlier implementation boundaries. Those historical records must remain truthful, but they must not be misread as the current future-state policy after the full-activation mandate.

## Normative order for future OSINT/source work

When documents conflict about whether a useful source or acquisition capability should be implemented in the future, use this order:

1. [`OSINT_FULL_IMPLEMENTATION_MANDATE.md`](OSINT_FULL_IMPLEMENTATION_MANDATE.md)
2. [`SOCIAL_COMMUNITY_ACQUISITION_REQUIREMENTS.md`](SOCIAL_COMMUNITY_ACQUISITION_REQUIREMENTS.md) and [`OSINT_AUTOMATION_PIPELINES.md`](OSINT_AUTOMATION_PIPELINES.md)
3. [`SOURCE_POLICY.md`](SOURCE_POLICY.md), [`ACQUISITION_ARCHITECTURE.md`](ACQUISITION_ARCHITECTURE.md), [`PRODUCT.md`](PRODUCT.md), and [`OSINT_COLLECTION_CATALOG.md`](OSINT_COLLECTION_CATALOG.md)
4. [`source_activation/SA_15_20_FULL_ACTIVATION_ROADMAP.md`](source_activation/SA_15_20_FULL_ACTIVATION_ROADMAP.md)
5. [`source_activation/SOURCE_ACTIVATION_MASTER_PLAN.md`](source_activation/SOURCE_ACTIVATION_MASTER_PLAN.md)
6. historical lot/SA closeout documents for the implementation state that existed when they were merged.

## Mandatory current target

The future-state target now explicitly includes:

- automatic governed company-domain target generation;
- recursive company-site crawling with operational budgets;
- generalized isolated Playwright/Chromium acquisition;
- authorized login, OAuth and SSO workflows;
- human/provider-approved CAPTCHA/MFA checkpoints with resumable jobs;
- normalized SERP/search pipelines and automated dork execution through authorized provider paths;
- HTML DOM, JSON-LD, public embedded JSON/JS state and structured metadata extraction;
- document quarantine, Tika/type-specific parsing, ExifTool, OCR and translation;
- automated reverse-image/visual research through authorized APIs and local similarity methods;
- Shodan, Censys, SecurityTrails, urlscan, VirusTotal, GreyNoise, Wappalyzer, BuiltWith and other passive/technography providers;
- Sherlock, Amass passive modules, theHarvester, SpiderFoot, Recon-ng and Maltego provider/module-aware execution;
- CTI, ransomware, phishing, incident, CERT and vulnerability provider activation/live proof;
- LinkedIn through a real legitimate executable provider/partner/written-authorized path;
- Reddit official/licensed public-community acquisition;
- Discord administrator-installed bot/connector and authorized-export acquisition;
- BrixHub.cc provider-specific activation and live validation;
- controlled live tests against real approved sources/targets before a provider is called fully integrated.

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

Those phrases remain evidence of the historical release state. They do **not** create a permanent future prohibition when the current mandate assigns the useful capability to SA-15 through SA-20 or to a later decomposition produced by the next roadmap review.

Examples:

- Lot 31 historically marked the browser runtime `DEFERRED`; SA-16 now makes generalized isolated browser acquisition mandatory future work.
- Earlier public-web documents excluded recursive crawling; SA-16 now requires recursive crawling inside explicit deployment scope and operational budgets.
- Earlier passive-provider records left Shodan/Censys/SecurityTrails/urlscan/technography candidates non-executable; SA-17 now requires obtaining legitimate entitlements and completing provider-specific activation/live proof.
- Earlier local-tool records declined blanket execution of Amass/theHarvester/SpiderFoot/Recon-ng; SA-17 now requires module/provider-level decomposition so legitimate useful modules can be implemented.
- Earlier LinkedIn/Discord/BrixHub records were fail-closed; the current social/community specification now requires real provider-specific executable paths and controlled live proof.
- Earlier vulnerability/incident/ATS/identity adapters without `live_tested` remain unfinished live-validation work under SA-18/SA-20.

## User-delegated provider identities

The current target includes user-delegated provider accounts when an external service requires an account and the provider permits the registration/automation model.

Such accounts must be tied to a real CIP tenant/user or deployment service principal, use isolated secret/session storage, support revocation/deletion and retain an audit trail. Tenant-controlled aliases may be automated where provider rules permit them.

Disposable third-party mailboxes or account multiplication may not be used to evade trials, quotas, bans, identity checks, CAPTCHA, MFA or other provider controls.

## Authorization boundary

Future implementation is mandatory for useful legitimate acquisition paths, but this precedence document does not authorize defeating provider or security controls.

CAPTCHA/MFA/authentication bypass, stolen sessions, credential guessing, deceptive account farms, exploit-based data acquisition, private victim files, stolen credentials and private communications remain outside normal OSINT acquisition unless a separate explicit security-testing engagement authorizes the relevant testing technique.

Legitimate accounts may use human/provider-approved CAPTCHA/MFA checkpoints and resume afterward.

For consented Discord servers and other administrator-installed community integrations, message history in explicitly permitted channels is valid source material for professional/technical signals. Provider-scoped pseudonymous handles remain pseudonymous unless the user self-declares, consents, or an authorized professional source provides an explicit identity link.

## Planning consequence

A useful capability may not be closed merely because it currently needs a key, account, contract, written permission, target registry, stable API or browser workflow. Those are explicit prerequisites owned by the Source Activation roadmap.

The next roadmap review must decompose the new social/browser/SERP/document/media requirements into realistically sized, independently implementable lots or SA increments with exact live-test exit gates.

Historical documentation is therefore preserved for auditability while the future implementation target remains unambiguous.
