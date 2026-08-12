# SA-15 C3 — Google search route resolution

## Goal

C3 resolves the Google search/dork automation path without weakening CIP's evidence-first or provider-governance rules.

The product owner has explicitly authorized the application to act on behalf of a real end user for legitimate research workflows and has accepted that user-facing provider terms may require a human checkpoint. That authorization is recorded as application/user intent; it does not by itself manufacture provider entitlement or provider-issued credentials.

## Current provider state reviewed on 2026-08-12

Google documents that the Custom Search JSON API is closed to new customers. Existing customers may continue using it until 2027-01-01 and require a configured Programmable Search Engine plus an API key.

Google Search support also identifies robots, computer programs, automated services and search scrapers as automated traffic. Therefore CIP does not infer permission for automated `google.com/search` traffic merely from the existence of a human end user.

The governed contract is stored in `policies/google_search_contract.yml` and validated by `cip.adapters.sources.google_search.contract`.

## User-supplied historical browser authorization evidence

On 2026-08-12 the product owner supplied screenshots showing:

- a request dated 2023-10-24 asking Google for authorization to crawl and scrape Google Search for the stated ADN research project; and
- a response presented as sent by `research-policy@google.com` on 2023-11-07 granting an exceptional authorization subject to technical limits, exclusive use, non-interference and a stated duration of 12 months.

The response image therefore describes a permission period ending on 2024-11-07. It is historical evidence only for the current 2026 review and cannot activate the browser route.

The screenshots alone are not cryptographic/provider-side verification of the sender. The contract records the historical evidence identifier and dates while keeping `provider_permission_verified: false`, `browser_route.enabled: false`, and `status: awaiting_eligible_route`.

C3 now fails closed on permission currency as well as presence: a provider-authorized browser route requires verified permission evidence, issuance/expiry dates, and an expiry date that has not passed at the contract review date. This prevents stale historical approvals from silently reactivating automation.

## Automated route precedence

CIP resolves Google search automation in this order:

1. **Existing-customer Custom Search JSON API**
   - requires explicit existing-customer entitlement evidence;
   - requires provider-issued API-key and search-engine-id secret references;
   - uses only `https://customsearch.googleapis.com/customsearch/v1`;
   - must still pass controlled real live proof on the exact candidate SHA.

2. **Provider-authorized browser route**
   - may be consumed by the generalized browser runtime delivered under SA-16;
   - requires explicit, verified and current provider-permission evidence recorded in governance;
   - may use a real browser, JavaScript execution, DOM extraction and normalized SERP mapping;
   - requires a human checkpoint for any provider-requested login, MFA, CAPTCHA or terms acknowledgement;
   - never bypasses CAPTCHA, anti-bot controls, authentication, rate limits or provider blocks;
   - if the provider presents a block/challenge that cannot be completed legitimately, the job stops or pauses rather than evading it.

3. **Canonical replacement**
   - requires at least one approved independent search source whose equivalent capability has a production adapter and real live proof;
   - the replacement feeds the same normalized SERP/discovery path and is not relabeled as Google data.

4. **Analyst route**
   - remains available for a human analyst when no automated route is eligible;
   - analyst use is not counted as automated-provider live proof.

## Account creation and terms checkpoint

CIP may model account onboarding as a resumable human checkpoint:

`open official signup -> human identity/account step -> email/MFA if required -> terms acceptance -> provider approval if required -> retrieve credential -> register secret reference -> resume exact job`.

The platform must not invent identity details, accept a provider contract without the deployment owner's actual account interaction, bypass MFA/CAPTCHA, or store raw credentials in logs/configuration.

The current ChatGPT/GitHub integration used to implement this repository cannot itself submit the external Google/USPTO signup forms or receive MFA/email on the user's behalf. The code must therefore make that transition explicit rather than pretending the account exists.

## Browser implementation boundary

C3 defines the authorization/selection contract. It intentionally does not add a one-off Google Playwright dependency because the normative roadmap assigns the isolated generalized Playwright/Chromium runtime to SA-16.

When SA-16 browser workers are available, the Google browser adapter must consume this C3 contract before navigation. That preserves the architecture rule that provider authorization and policy are checked before network/browser execution.

## Exit gate

C3 can only be considered fully complete when one automated route has reached an allowed terminal state:

- existing-customer Google API route with real non-empty production results and exact-SHA CI/live proof; or
- provider-authorized browser route with explicit, verified, non-expired permission evidence and real non-empty production results plus exact-SHA CI/live proof; or
- an approved canonical replacement whose equivalent search capability is itself production-live and whose results feed the normalized SERP/discovery pipeline.

Until one of those outcomes is true, `status: awaiting_eligible_route` remains correct and C3 must not claim Google `live_tested`.
