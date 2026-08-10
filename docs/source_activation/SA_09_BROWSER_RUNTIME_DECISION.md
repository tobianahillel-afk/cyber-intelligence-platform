# SA-09 — Isolated browser runtime trigger decision

## Decision

The SA-09 browser trigger is **false** for the current source inventory.

The Master Plan permits an isolated browser only for an approved source that cannot be served safely by an official API, feed/bulk export, bounded static HTTP/document path, governed local tool or analyst-assisted/manual workflow. No currently authorized/executable source meets that condition.

Therefore SA-09 deliberately adds **no browser runtime**.

## Current acquisition coverage

Current authorized/executable source paths are already served through bounded mechanisms such as:

- official/public APIs for vulnerability, procurement, hiring, search and passive metadata;
- bounded feeds, static HTTP, sitemaps, `security.txt` and public documents;
- passive DNS/CT/RDAP lookups with target and governance controls;
- bounded developer/package metadata APIs;
- governed local Sherlock execution only for analyst-approved professional targets;
- manual analyst review for generic corporate-change/relationship sources;
- blocked conditional/licensed sources where commercial/access authorization is absent.

A source being blocked by licence, authentication, private access, provenance or authorization requirements is **not** a reason to add a browser. Browser automation cannot be used to work around those gates.

## Runtime intentionally absent

SA-09 does not add:

- Playwright;
- Chromium/Chrome automation;
- Selenium;
- Puppeteer;
- persistent browser profiles;
- cookie/session pools;
- copied authenticated browser sessions;
- browser credentials;
- login automation;
- CAPTCHA or MFA handling/bypass;
- anti-bot, fingerprint or stealth/evasion logic;
- proxy/Tor rotation;
- browser-based paywall or access-control bypass;
- arbitrary user-supplied URL browsing;
- crawl-on-page-view behavior.

## Reopening trigger

A future source may reopen SA-09 only through a dedicated reviewed source-activation change that proves all of the following:

1. the source itself is concrete and approved by Source Governance;
2. legal/commercial authorization exists for the exact automated browser use;
3. official API, feed/export, static HTTP and analyst/manual routes are genuinely insufficient;
4. browser execution is the least-complex authorized acquisition mode;
5. exact hosts, paths, methods, redirects, page/byte/time budgets and retention are approved;
6. no login, CAPTCHA/MFA, paywall or access-control bypass is required;
7. credentials/cookies, if legitimately required, are deployment secrets governed by Provider Onboarding and never checked in or exposed to the frontend;
8. the browser runs in an isolated disposable environment with downloads, local-network access and arbitrary navigation disabled by default;
9. source-specific canonical mapping/evidence semantics are defined before runtime activation;
10. deterministic no-network tests and a separately authorized controlled live validation pass.

The browser runtime must remain source-specific infrastructure. It must not become a generic arbitrary browsing service or a shared bypass mechanism.

## Completion gate

SA-09 may close only when:

- the repository contains no browser automation dependency required by the product runtime;
- no activation record is made executable under `SA-09`;
- the decision document records the false trigger and strict reopening conditions;
- deterministic tests verify the Python and web manifests remain free of Playwright/Selenium/Puppeteer browser automation dependencies;
- no cookie/session/authentication/CAPTCHA/MFA/proxy/Tor workaround is introduced;
- one exact final SHA passes the complete backend and frontend CI;
- reviews and review threads are clear before squash merge.
