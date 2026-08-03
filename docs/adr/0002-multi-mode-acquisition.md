# ADR 0002: Multi-Mode Acquisition

- Status: Accepted
- Date: 2026-08-03
- Decision owners: project maintainers

## Context

The platform must retrieve structured APIs, feeds, ordinary HTML, JavaScript-rendered applications, authenticated exports, and permitted documents. Using only direct HTTP would not support every authorized source. Using a full browser for every source would increase cost, fragility, attack surface, and operational risk.

Downloaded files and rendered pages are untrusted inputs and must not enter the API process or ordinary application filesystem directly.

## Decision

Support separate acquisition modes selected explicitly by each source manifest:

1. official API;
2. feed or bulk export;
3. static HTTP;
4. isolated Chromium browser through Playwright;
5. analyst-assisted browser session;
6. manual file import;
7. webhook.

The preferred order is the least complex authorized method that produces equivalent evidence.

Browser automation runs in dedicated isolated workers with fresh contexts, source-specific network allowlists, budgets, download restrictions, audit logs, and kill switches.

Downloads enter a quarantine pipeline with hashing, type and size validation, archive controls, malware screening, sandboxed parsing, retention enforcement, and no automatic execution.

CAPTCHA, bot challenges, MFA, changed terms, or account-security prompts cause a safe pause and human task. The system does not implement bypass, stealth, disposable-account rotation, or challenge-solving services.

## Consequences

### Positive

- APIs and static pages remain efficient and deterministic;
- JavaScript and approved authenticated workflows remain possible;
- browser compromise is isolated from the main application;
- file parsing risk is isolated;
- every source has an explicit technical and policy scope;
- automated tests can emulate each acquisition mode locally.

### Negative

- more runtime components and operational monitoring;
- browser flows require maintenance when interfaces change;
- authenticated sessions require secure secret and account lifecycle management;
- download quarantine adds latency and storage cost;
- manual intervention is required for some legitimate challenges.

## Rejected alternatives

### Browser for every source

Rejected because it is unnecessarily expensive, difficult to replay, vulnerable to interface changes, and exposes a larger attack surface.

### HTTP for every source

Rejected because it cannot reliably support authorized JavaScript-rendered pages, user-driven exports, and some authenticated workflows.

### Parsing downloads in the API process

Rejected because hostile or malformed files can exploit parsers, consume resources, and expose the application filesystem.

### Automatic anti-bot circumvention

Rejected because challenges are access-control and policy signals. The correct response is safe pause, authorized manual action, or a provider-approved API or workflow.
