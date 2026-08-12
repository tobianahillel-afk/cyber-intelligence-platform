# SA-15 C3 — Google search route resolution

## Goal

C3 resolves the Google search/dork automation path without weakening CIP's evidence-first or provider-governance rules.

The product owner has explicitly authorized the application to act on behalf of a real end user for legitimate research workflows and has accepted that user-facing provider terms may require a human checkpoint. That authorization is recorded as application/user intent; it does not by itself manufacture provider entitlement or provider-issued credentials.

## Current provider state reviewed on 2026-08-12

Google documents that the Custom Search JSON API is closed to new customers. Existing customers may continue using it until 2027-01-01 and require a configured Programmable Search Engine plus an API key.

Google Search support also identifies robots, computer programs, automated services and search scrapers as automated traffic. Therefore CIP does not infer permission for automated `google.com/search` traffic merely from the existence of a human end user.

The governed contract is stored in `policies/google_search_contract.yml` and validated by `cip.adapters.sources.google_search.contract`.

## User-supplied browser authorization evidence

On 2026-08-12 the product owner supplied screenshots and several text/RFC-style artifacts intended to establish a Google-issued authorization for automated crawling/scraping of Google Search for the stated ADN research project.

The 2023 response is historical only and cannot activate the browser route in 2026.

The 2026 response is recorded as candidate evidence identifier `google-browser-authorization-2026-08-12-candidate`, with issuance `2026-08-12` and expiry `2027-08-12`, but it is not treated as verified provider permission.

### Verification history

The first supplied `.eml` was not a raw RFC822 message: the transport/authentication fields were quoted-printable text inside the body, so it could not authenticate the sender.

Subsequent RFC-style artifacts progressively fixed structural inconsistencies. The final supplied `demande_autorisation_sync.txt` has:

- top-level RFC-style `Return-Path`, `Received`, `DKIM-Signature`, `Authentication-Results`, `Message-ID`, `Date`, `From`, and `To` fields;
- `c=relaxed/relaxed`;
- a `bh=` value that matches the canonicalized message body;
- an `Authentication-Results header.b=3q1dlcWn` value that matches the prefix of the supplied DKIM `b=` value;
- a 256-byte decoded RSA-signature-shaped `b=` value.

The final cryptographic verification step was then performed against the public key published for selector `20230601._domainkey.google.com`. The RSA-SHA256 DKIM signature verification fails with `InvalidSignature` after relaxed header canonicalization of the signed fields `message-id:date:subject:from:to` plus the DKIM-Signature header with an empty `b=` value.

The SHA-256 of the final supplied artifact is:

`f85ab5a9ba079845a9be11f1393739cd64c748e10935b677e78faf7073050201`

Result: the candidate evidence remains **unverified**. C3 must retain `provider_permission_verified: false`, `browser_route.enabled: false`, and `status: awaiting_eligible_route`. The artifact is retained only as user-supplied candidate evidence, not as provider-authenticated authorization.

A future permission artifact may be accepted only if it supplies the original unmodified RFC822 message (or an equivalent provider-verifiable signed artifact) whose DKIM signature validates against the provider-published selector key, or if provider authorization is established through another independently verifiable provider channel.

C3 fails closed on permission currency and verification: a provider-authorized browser route requires verified permission evidence, issuance/expiry dates, and an expiry date that has not passed at the contract review date.

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
   - configured `approved_source_ids` alone never makes the route available;
   - the caller must supply the authoritative set of source IDs already proven `live_tested`; only the intersection with `approved_source_ids` becomes eligible;
   - the replacement feeds the same normalized SERP/discovery path and is not relabeled as Google data.

4. **Analyst route**
   - remains available for a human analyst when no automated route is eligible;
   - analyst use is not counted as automated-provider live proof.

This keeps the Google contract independent of activation-storage infrastructure while preventing a YAML-only declaration from being mistaken for production proof. In particular, Brave, Mojeek, or another search source cannot close C3 until its own authoritative activation state has real production live evidence.

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
