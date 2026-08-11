# Acquisition Architecture

## Purpose

The acquisition layer retrieves useful public, licensed, customer-authorized and provider-authorized data through provider-specific execution paths while preserving source governance, provenance, replay safety and isolation.

The architecture must support APIs, feeds, bulk exports, recursive public-web crawling, JavaScript-rendered pages, legitimate authenticated sessions, controlled downloads, local OSINT modules, analyst-assisted checkpoints and manual imports.

The future target state is defined by [`OSINT_FULL_IMPLEMENTATION_MANDATE.md`](OSINT_FULL_IMPLEMENTATION_MANDATE.md).

## Acquisition principles

1. Prefer the most structured supported provider path when it gives equivalent evidence.
2. Do not leave a useful source permanently unimplemented merely because it requires a key, contract, account, target registry or browser workflow.
3. Preserve provider-specific authorization, quotas, retention and evidence semantics.
4. Use the same immutable observation/provenance pipeline regardless of transport.
5. Treat every external page, file, API payload and browser execution as untrusted.
6. Require controlled live validation through the production adapter before declaring a provider fully integrated.

## Acquisition methods

### 1. Official or licensed API

Preferred for structured provider data.

Required support includes:

- API keys;
- OAuth 2.0;
- service accounts;
- tenant/account identifiers;
- documented pagination/cursors;
- rate limits and quotas;
- incremental windows;
- provider webhooks/change streams when useful.

Useful paid or enterprise APIs remain implementation targets. Missing entitlement is tracked through Provider Onboarding.

### 2. Feed or bulk export

Supported formats include:

- RSS;
- Atom;
- JSON;
- CSV;
- XML;
- STIX/TAXII;
- ZIP archives;
- provider bulk snapshots;
- signed manifests.

Required controls:

- content-length limits;
- decompression-ratio limits;
- archive-member/path checks;
- checksum/signature validation when available;
- schema validation;
- replay-safe snapshot identity;
- bounded parser workers.

### 3. Static HTTP collection

Static HTTP is used for ordinary public pages/documents when JavaScript execution is unnecessary.

The collector may retrieve, inside the approved target scope:

- HTML;
- structured metadata;
- JSON-LD;
- embedded public JSON;
- public documents;
- response headers;
- ETag/Last-Modified validators;
- feeds/sitemaps/robots/security.txt;
- same-origin linked resources.

### 4. Recursive public-web crawling

Recursive crawling is a required production capability for approved organization domains.

The crawler must support:

- automatic governed target creation after canonical domain resolution;
- `robots.txt` evaluation;
- sitemap and sitemap-index recursion;
- RSS/Atom discovery;
- same-origin link extraction;
- configurable maximum depth;
- configurable page, byte, time and concurrency budgets;
- approved-origin/path constraints;
- duplicate/canonical URL suppression;
- MIME validation;
- incremental recrawling;
- change detection and tombstones;
- per-organization freshness schedules;
- source-specific overrides backed by explicit authorization.

The goal is broad automatic company-site coverage. Runtime budgets are engineering controls, not a reason to omit recursive crawling from the product.

### 5. Browser-rendered collection

A generalized isolated Playwright/Chromium runtime is mandatory.

Use it when:

- the site is JavaScript-rendered;
- required content is produced after client-side execution;
- first-party interaction is necessary;
- a provider/customer-authorized authenticated session is required;
- downloads require browser interaction;
- rendered screenshots are evidentially useful;
- browser-compatible cookies/client tokens are part of a legitimate provider flow.

Browser execution is a normal acquisition mode when technically necessary and authorized. It must not remain a permanently deferred fallback.

### 6. Authenticated web collection

The platform must support legitimate authenticated workflows for exact approved sources and accounts.

Supported patterns include:

- username/password for provider-approved service/test accounts;
- OAuth/OIDC;
- SSO when deployment authorization permits it;
- provider-issued session tokens;
- service accounts;
- administrator-installed integrations;
- account-specific API/browser sessions;
- analyst-assisted MFA for a legitimate account.

Authenticated collection must preserve account identity, authorization scope, source purpose, session lifetime and audit history.

### 7. Analyst-assisted checkpoint

A human checkpoint is supported for provider actions that legitimately require human presence, including:

- MFA;
- CAPTCHA presented to the authorized user;
- contract acceptance requiring human authority;
- provider approval prompts;
- export configuration;
- account-security verification;
- KYC/payment steps when applicable to a legitimate provider account.

The job pauses with a precise checkpoint and resumes after the authorized human/provider action completes.

### 8. Local OSINT execution

Local tools such as Sherlock, Amass, theHarvester, SpiderFoot and Recon-ng are executed through module/provider-specific manifests.

The runtime must know, per module:

- upstream provider;
- passive/active behavior;
- required credential;
- target type;
- exact network behavior;
- data categories;
- quota/rate boundaries;
- output mapping;
- authorization prerequisites.

Mixed frameworks are decomposed rather than rejected wholesale.

### 9. Manual import

Approved provider/customer exports may be imported through quarantine and the normal evidence pipeline.

Manual import is a fallback or complementary workflow, not a substitute for implementing a legitimate executable provider path when one exists.

## Automatic organization acquisition

After canonical domain resolution, the platform must be able to create an acquisition plan automatically for a deployment-approved organization.

```text
canonical organization
-> domain evidence
-> target-generation policy
-> source-governance authorization
-> crawl/browser/search/passive provider plan
-> scheduled jobs
-> immutable observations/resources
-> canonical evidence
-> refresh/change detection
```

Target generation must remain reversible when ownership, authorization or domain resolution changes.

## Selection policy

Each source declares supported and preferred modes, for example:

```yaml
acquisition:
  preferred: api
  fallbacks:
    - feed
    - static_http
    - recursive_web
    - browser
  authenticated_web_allowed: true
  analyst_assistance_allowed: true
  downloads_allowed: true
```

The orchestrator may use a fallback only if that mode is already authorized for the source/deployment.

## Browser runtime

### Isolation

Every browser job uses an isolated context and normally a disposable process/profile.

Required controls:

- Chromium sandbox;
- site isolation;
- per-source contexts;
- no cross-source cookie sharing;
- restricted filesystem;
- no cloud metadata access;
- restricted process capabilities;
- CPU/memory/wall-time budgets;
- process-tree cleanup;
- network request interception;
- download quarantine.

### Browser-context rule

```text
one source + one account + one authorization scope
= one isolated browser context
```

### Request interception

The browser worker enforces:

- source host/origin allowlists;
- redirect validation;
- blocked localhost/private ranges unless explicitly required for an owned environment;
- unsupported scheme rejection;
- download host checks;
- optional blocking of irrelevant trackers/media;
- maximum response/DOM/navigation budgets.

### Navigation budgets

Each browser job declares:

- maximum pages;
- maximum navigation depth;
- maximum elapsed time;
- maximum DOM size;
- maximum response size;
- screenshot limit;
- download limit;
- retry limit;
- allowed host transitions.

## Authentication and secret architecture

Credentials live in a secret manager. Persistent database records store references and lifecycle metadata, not raw secrets.

Required capabilities:

- API keys;
- OAuth refresh/access token lifecycle;
- service accounts;
- account/password secrets for legitimate automated accounts;
- short-lived browser session secrets;
- tenant-specific configuration;
- rotation and revocation;
- secret redaction from logs, screenshots and traces.

### Account provisioning

The platform should automate provider-approved account/service-account provisioning wherever the provider supports it.

If a legitimate provider requires manual signup, payment, KYC or human approval, Provider Onboarding creates a human checkpoint and resumes after completion.

The system must not use deceptive identities, stolen sessions or account multiplication to evade provider controls.

## CAPTCHA, MFA and access-control handling

CAPTCHA and MFA are supported as legitimate human/provider checkpoints for authorized accounts.

The platform does **not** implement mechanisms whose purpose is to defeat those controls. It must not:

- solve/bypass CAPTCHA through evasion services to obtain unauthorized automation;
- bypass MFA/passkeys/hardware tokens;
- steal/replay unrelated sessions;
- spoof identities to evade provider policy;
- rotate fake accounts after bans/limits;
- exploit provider systems for acquisition.

When a challenge appears in an authorized workflow:

1. preserve minimal diagnostic state;
2. pause the job;
3. create a human/provider-approved action;
4. resume the same governed job after successful legitimate completion;
5. audit the transition.

## Network isolation

Collectors/browser/local-tool workers run outside the API process.

Required controls:

- dedicated workers/sandboxes;
- no cloud metadata access;
- no unintended internal-network access;
- DNS-rebinding checks;
- SSRF protections;
- redirect validation;
- TLS validation;
- per-source outbound controls;
- no arbitrary end-user URL fetching without target validation.

## Download architecture

All downloads use quarantine:

```text
HTTP/browser/provider download
-> intake
-> quarantine object
-> hash/type/size validation
-> malware/archive screening
-> isolated parser
-> redacted/minimized extraction
-> evidence artifact or rejection
-> retention/deletion lifecycle
```

Supported parser families should expand to:

- HTML;
- PDF;
- Office Open XML;
- CSV/tabular;
- JSON/XML;
- email export where legitimately provided;
- archive containers;
- image/OCR;
- ExifTool/Tika-style metadata extraction;
- translation;
- plain text.

Files are never executed by the collection worker.

## Change detection and incremental refresh

Collectors should use the strongest available mechanism:

1. provider event/webhook;
2. provider cursor;
3. updated-since timestamp;
4. ETag/If-Modified-Since;
5. record/page checkpoint;
6. content hash/structural diff;
7. periodic reconciliation.

For websites/browser sources distinguish template changes from relevant evidence changes.

## Tombstones

Removal of a source record creates a source-aware tombstone rather than silently destroying historical truth, subject to deletion/suppression requirements.

## Live-validation architecture

Provider live proof is a first-class delivery step.

A live validation uses the **production adapter**, not a special fake client, and records only safe aggregate result metadata.

It proves:

- provider connectivity;
- current schema compatibility;
- authentication path when required;
- correct policy-before-network behavior;
- bounded acquisition;
- canonical mapping;
- checkpoint/idempotency behavior;
- secret hygiene;
- evidence-boundary compliance.

Skipped workflows and mock transports do not count.

## Observability

Record per source/mode:

- requests/navigation count;
- success/failure rate;
- latency;
- bytes;
- documents/downloads;
- records extracted;
- duplicates;
- schema drift;
- authentication failures;
- human-checkpoint frequency;
- rate-limit waits;
- freshness lag;
- retries/circuit state;
- worker crashes;
- parser quarantine rate;
- live-validation timestamp/result.

Logs contain identifiers and redacted metadata, not unrestricted payloads or credentials.