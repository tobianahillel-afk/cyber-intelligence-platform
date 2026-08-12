# SA-15 L06/L07 — Search diversity and governed dork library

## Scope

This increment implements two SA-15 search work items without overstating provider activation:

- **L06** — add a current independent general web-search provider implementation path through Marginalia Search API2;
- **L07** — replace the three generic search templates with the complete versioned analyst dork/query library required by the SA-15 roadmap.

Search-result metadata remains discovery material. It does not become evidence merely because a provider returned it; downstream retrieval still goes through the governed search-to-acquisition routing path.

## L06 — Marginalia Search API2

### Implemented

- production client targets `https://api2.marginalia-search.com/search`;
- API key is sent through the provider-documented `API-Key` header;
- response parsing is bounded and schema validated for `query`, `license`, and result `url` / `title` / `description` fields;
- redirects are disabled;
- response body size is bounded;
- HTTP 429 and 5xx responses are classified retryable;
- transport failures are classified retryable;
- schema/content-type failures fail closed;
- the provider's shared `public` development key is explicitly rejected by the production client;
- source policy, portfolio state, activation truth, and entitlement prerequisites are represented separately;
- deterministic tests use `httpx.MockTransport` and never rely on provider network access.

### Current activation truth

`marginalia-web-search-metadata` is **not live tested** and is not production-authorized yet.

Current proven stages:

`catalogued -> reviewed -> mapped -> adapter_present`

Missing prerequisites remain owned work:

1. legitimate commercial API key;
2. commercial-use entitlement evidence;
3. Provider Onboarding secret reference;
4. exact deployment authorization for host/path/purpose;
5. controlled production-adapter real-endpoint validation;
6. exact-head CI/live proof before `live_tested` may be added.

The shared development key is not an acceptable substitute for these prerequisites.

## L07 — versioned dork/query library

The registry is upgraded from three generic templates to version-2 coverage for:

- `site:` company/domain research;
- `filetype:` document discovery;
- `intitle:` and `inurl:` research patterns;
- procurement and contracts;
- cyber products/providers;
- SOC/SIEM/MDR/XDR/SOAR;
- IAM/PAM/IGA/Zero Trust;
- cloud/Kubernetes;
- AppSec/DevSecOps/SAST/DAST/SCA/SBOM;
- pentest/red-team/purple-team;
- GRC/NIS2/DORA/ISO 27001/SOC 2/PCI DSS/HDS;
- incident/ransomware/breach/regulator signals;
- recruitment and security-team growth;
- architecture/migration/transformation;
- partner/customer/case-study evidence;
- annual reports, presentations, standards and technical publications;
- code/package/developer evidence.

Every checked-in template is disabled by default. `build_google_analyst_search_url()` renders an analyst-opened Google search URL locally and performs no network request. Automated Google collection therefore remains unavailable until a legitimate provider/API entitlement and governed execution path are implemented.

## Deterministic gates

Tests enforce:

- exact required template inventory;
- unique template patterns;
- template version 2;
- one `{organization}` placeholder per template;
- disabled-by-default behavior;
- explicit `site:`, `filetype:`, `intitle:`, and `inurl:` coverage;
- representative SA-15 cybersecurity coverage terms;
- deterministic analyst-link URL rendering;
- Marginalia commercial entitlement fail-closed behavior;
- rejection of the shared development key;
- current API2 host/path/header/query contract;
- HTTP and schema failure classification.

## Exit state

- **L07:** implementation-complete once the PR exact-head CI is green.
- **L06:** adapter/governance prerequisite implementation complete, but provider activation remains open until legitimate commercial access exists and the exact production adapter receives controlled real-endpoint live proof.

No `live_tested` stage is added by this increment for Marginalia.
