# Priority B-4 — Passive provider-specific dispositions

Status: implementation decision record for issue #82 / parent #77.

Reviewed on: 2026-08-10.

## Purpose

Priority B-4 closes the six named passive technology/exposure providers at provider/product level. A named provider is not considered integrated merely because an API exists or a free/community plan can return data. For this standalone customer-facing commercial product, execution is allowed only when the repository can prove a compatible commercial entitlement, onboarding/secrets, collection boundaries, canonical mapping and a governed runtime path.

All six providers below add potentially useful passive evidence, but the repository currently has no contract or written entitlement proving that their data may be incorporated into this product for customer-facing use. They therefore remain fail-closed and are handed to SA-07 as licensed dependencies. B-4 intentionally does not create fake adapters, schedules, secrets or `live_tested` state.

## Common non-negotiable boundary

- Provider datasets may be consumed only through an authorized documented API/export under a compatible contract.
- No provider scanning, probe submission, active host discovery or prospect-directed measurement is authorized by this lot.
- No scraping of provider web interfaces, quota evasion, account rotation or bypass of product controls.
- Provider observations remain passive evidence. They do not by themselves prove organization ownership, deployment, vulnerability applicability, exposure, compromise or a commercial need.
- Person/contact fields are outside the B-4 mapping even if a provider can return them.
- A future activation must use Provider Onboarding, Source Governance, portfolio/quota controls, the shared collection runtime and the existing canonical passive-exposure/public-footprint projections.

## Provider decisions

### Censys

**Provider record:** `censys-platform-passive`

**Relevant product/API path:** Censys Platform/Search data through authorized Censys APIs. Only passive provider-returned host/certificate/service observations are in scope.

**Commercial entitlement finding:** Censys' published Terms of Service state that Free and Researcher access is non-commercial. Paying plans permit their own commercial purposes subject to restrictions, while incorporation of Censys Data into software/products/services made available to third parties requires an Enterprise account. Current Censys customer terms also restrict ordinary service use to internal business operations unless separately agreed.

**Authentication/onboarding:** provider account/API credentials and a contract entitlement explicitly covering incorporation in this customer-facing product. Secrets must be held through Provider Onboarding, never policy files.

**Prohibited methods:** provider UI crawling/scraping, bypass, active scanning/probing, using a free/research plan for this product, or exposing raw Censys data as a standalone dataset.

**Canonical mapping if activated:** Lot 16 passive asset/observation records with provider provenance, observation time, bounded service/technology/certificate metadata and `REVIEW_REQUIRED` organization links. Existing Cloudflare DNS, Cert Spotter CT and RDAP remain independent source families; Censys would add provider-observed internet service context, not replace them.

**Disposition:** `blocked`, owned by `SA-07`, pending an Enterprise or written product-integration entitlement and deployment onboarding.

### Shodan

**Provider record:** `shodan-passive-data`

**Relevant product/API path:** Shodan Search/Host passive indexed-data APIs only. Scan/submission endpoints are out of scope.

**Commercial entitlement finding:** Shodan's published terms prohibit reproducing, selling, trading or reselling the Services unless separately agreed in writing. Academic/Research access is expressly non-commercial. The repository contains no separate Shodan agreement covering incorporation into this product.

**Authentication/onboarding:** paid/commercial account plus written entitlement appropriate to customer-facing product use; API key through Provider Onboarding.

**Prohibited methods:** Shodan scan APIs, prospect-directed scanning, provider UI scraping, account/quota evasion, research/academic entitlements for commercial execution, resale of provider data.

**Canonical mapping if activated:** Lot 16 passive service/banner-derived observation metadata after strict field allowlisting and provenance preservation. A Shodan observation remains provider-observed context and cannot become verified exposure or vulnerability applicability without independent applicability logic/evidence.

**Disposition:** `blocked`, owned by `SA-07`, pending a separate compatible commercial agreement and deployment onboarding.

### SecurityTrails

**Provider record:** `securitytrails-passive-data`

**Relevant product/API path:** read-only SecurityTrails REST API under `api.securitytrails.com/v1`, using exact organization-bound domain/IP targets. DNS/WHOIS/company/passive metadata can be technically queried through the documented API.

**Commercial entitlement finding:** current public API documentation proves authentication, subscription quotas and technical API behavior, but the repository review did not establish public licence text granting redistribution/incorporation rights for this standalone customer-facing product. Technical availability is not treated as commercial authorization.

**Authentication/onboarding:** SecurityTrails subscription, `APIKEY`, quota configuration and a contract/order form or provider confirmation explicitly covering the intended product use.

**Prohibited methods:** execution before entitlement review, UI scraping, quota circumvention, person/contact harvesting, and any active measurement not supplied as an existing passive provider dataset.

**Canonical mapping if activated:** existing Lot 16 DNS/domain/IP passive observations and organization-link review candidates. Unique value would be provider historical/passive DNS and enrichment beyond the active public DoH/RDAP/CT paths; it must not overwrite those independent sources.

**Disposition:** `blocked`, owned by `SA-07`, pending contract/licence evidence and deployment onboarding.

### urlscan

**Provider record:** `urlscan-passive-search`

**Relevant product/API path:** urlscan Search/Result API over already-existing scans only. Submission/automatic scan APIs are explicitly excluded for prospect collection.

**Commercial entitlement finding:** urlscan's public terms say commercial use requires approval/permission, and its FAQ specifically asks customers integrating urlscan data into a commercial offering to contact the provider to determine acceptable use or a commercial agreement.

**Authentication/onboarding:** commercial agreement or written permission covering product integration, API key, quotas and attribution/data-use requirements.

**Prohibited methods:** submitting prospect URLs for scans, automatic submissions, scraping/mirroring the service outside authorized API use, bypassing quotas, or redistributing provider content beyond the agreed rights.

**Canonical mapping if activated:** Lot 16 passive web/service observations from historical existing scans, plus bounded source/provenance metadata. The linked site remains the underlying third-party subject; urlscan search metadata is not independent proof of compromise or a commercial need.

**Disposition:** `blocked`, owned by `SA-07`, pending written commercial product-integration permission and deployment onboarding.

### Wappalyzer

**Provider record:** `wappalyzer-technographics`

**Relevant product/API path:** Wappalyzer technology lookup/API with only website/technology fields required for passive technographic context. Contact/person enrichment is excluded.

**Commercial entitlement finding:** Wappalyzer's current terms state that commercial-service data is licensed and may not be sublicensed, resold, published, embedded in a customer-facing product or otherwise shared without explicit written permission. Its FAQ points Enterprise users needing broader licensing to the provider.

**Authentication/onboarding:** Enterprise/custom written terms permitting customer-facing embedding, API key/credits, quotas and approved field set.

**Prohibited methods:** customer-facing embedding under self-serve/free rights, resale/sharing, contact harvesting, provider crawling, or treating technology detection as production deployment/vulnerability applicability.

**Canonical mapping if activated:** Lot 16 technology observations attached to an organization-bound public web asset with source timestamp and confidence/provenance. This is potentially richer technography than the existing bounded public-web parser but remains an independent provider observation.

**Disposition:** `blocked`, owned by `SA-07`, pending explicit written Enterprise/custom embedding rights and deployment onboarding.

### BuiltWith

**Provider record:** `builtwith-technographics`

**Relevant product/API path:** BuiltWith Domain API/technology detection for exact organization-bound domains only.

**Commercial entitlement finding:** BuiltWith's Terms of Use (updated 2026-03-06) describe the standard licence as internal business use and prohibit resale, redistribution, sublicensing, commercial exploitation and building/enhancing a competing product. BuiltWith API documentation also says APIs may enhance a product provided data is not resold as-is and the product does not duplicate BuiltWith functionality. Because those public statements leave material ambiguity for this platform's customer-facing technographic use, the repository must not infer permission.

**Authentication/onboarding:** paid API entitlement plus written provider/contract confirmation that the exact customer-facing use, retained fields and derived analytics are permitted; API key through Provider Onboarding.

**Prohibited methods:** database reconstruction, bulk extraction beyond licensed endpoints, provider UI scraping, resale/redistribution, competing BuiltWith-like functionality, and technology-to-vulnerability inference without separate applicability evidence.

**Canonical mapping if activated:** Lot 16 technology observations for explicit canonical organization/domain targets, preserving source timestamp and confidence/provenance. BuiltWith adds provider technography but does not replace the bounded first-party public-web evidence path.

**Disposition:** `blocked`, owned by `SA-07`, pending written entitlement resolving customer-facing/product-use ambiguity and deployment onboarding.

## B-4 terminal-state contract

B-4 is complete only when all six provider records:

1. exist in `policies/source_activation.yml`;
2. are `blocked` with `activation_wave: SA-07`, a non-empty provider-specific reason and no `adapter_present`, `authorized`, `executable`, `scheduled` or `live_tested` stage;
3. are represented consistently in `SOURCE_COVERAGE_MATRIX.md`;
4. have deterministic reconciliation tests preventing a future generic/unknown state;
5. remain network-inert: B-4 adds no adapters, credentials, schedules or outbound provider calls;
6. pass the complete backend and frontend CI on one exact final SHA.

A later SA-07 change may reopen one provider only after contract/entitlement evidence is reviewed and the complete adapter/governance/onboarding/runtime/test chain is implemented.

## Official references reviewed

- Censys Terms of Service: https://censys.com/terms-of-service
- Censys Terms and Conditions: https://censys.com/terms-and-conditions/
- Shodan Terms: https://static.shodan.io/legal/terms.html
- SecurityTrails API overview: https://docs.securitytrails.com/docs/overview
- SecurityTrails quotas and rate limits: https://docs.securitytrails.com/docs/quotas-rate-limits
- urlscan Terms of Service: https://api.urlscan.io/terms/
- urlscan FAQ / commercial use: https://api.urlscan.io/docs/faq/
- urlscan API documentation: https://urlscan.io/docs/api/
- Wappalyzer Terms of Service: https://www.wappalyzer.com/terms/
- Wappalyzer API FAQ: https://www.wappalyzer.com/faq/api/
- BuiltWith Terms of Use: https://builtwith.com/terms
- BuiltWith Domain API: https://api.builtwith.com/domain-api
