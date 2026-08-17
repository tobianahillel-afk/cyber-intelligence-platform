# SA-21 — Orphaned Source Activation Recovery

## Purpose

SA-21 owns useful Source Activation work that remained unfinished after historical SA closeouts and was not given an explicit future Source Activation owner in SA-17 through SA-20.

This SA exists to eliminate ownership gaps. It does not weaken provider authorization, commercial, security, evidence, or live-validation requirements. A missing key, entitlement, provider permission, stable contract, target, account, or deployment configuration remains unfinished work until resolved, replaced by an equivalent fully integrated canonical source, or explicitly excluded by product-owner decision.

## Scope boundary

SA-21 is a recovery/ownership wave. It owns only the orphaned or ambiguously handed-off capabilities listed below.

It does not reopen capabilities already explicitly owned by SA-17, SA-18, SA-19, or SA-20.

## Search and deferred-provider recovery

SA-21 owns final activation for the following search/deferred-provider capabilities that remain incomplete after SA-15 and have no later explicit Source Activation owner:

1. **Brave Search API**
   - provision legitimate deployment subscription/token;
   - complete Provider Onboarding and secret configuration;
   - run controlled non-empty production-adapter live validation;
   - promote activation state only on the exact validated final SHA.

2. **Mojeek Web Search**
   - provision legitimate API access;
   - confirm durable-result-storage rights for the metadata CIP persists;
   - complete Provider Onboarding/secret configuration;
   - run controlled non-empty production-adapter live validation.

3. **Marginalia Search**
   - obtain legitimate commercial entitlement;
   - record reviewed commercial-use/storage rights;
   - configure approved host/path/purpose and Provider Onboarding secret references;
   - run controlled non-empty production-adapter live validation.

4. **PatentsView / current USPTO Open Data Portal route**
   - do not revive or relabel the historical revoked `search.patentsview.org` route;
   - review the current USPTO/ODP endpoint, authentication model, schemas, quotas, terms and retention rules;
   - implement the current provider-specific adapter/runtime/checkpoint path;
   - run controlled non-empty exact-head live validation.

5. **Google automated search route**
   - close through one legitimate provider-approved route only:
     - eligible official API entitlement; or
     - explicit independently verified provider-authorized browser automation route; or
     - approved equivalent canonical replacement whose own capability is fully integrated and live-tested;
   - analyst-opened Google links do not count as automated provider live proof.

6. **Bing or another approved independent general web-search provider**
   - select a concrete provider that is genuinely independent of the existing canonical search routes;
   - document provider terms, storage/retention rights, credentials, quotas and governance;
   - implement provider-specific normalized SERP adapter/runtime registration;
   - feed governed evidence-discovery routing;
   - obtain controlled production-adapter live proof.

## Corporate, regulatory and relationship acquisition recovery

SA-21 also owns the provider-specific activation path for useful SA-06 families that historically remained `manual` and were never assigned a later Source Activation owner.

A family placeholder itself must not become an executable generic endpoint. SA-21 must select concrete providers or first-party acquisition contracts where useful.

7. **Official corporate disclosures**
   - define concrete first-party/provider-specific discovery and acquisition paths;
   - retain analyst review where semantics are provider/company-specific;
   - preserve Lot 18 corporate-change evidence boundaries;
   - live-validate any executable production acquisition path introduced.

8. **Official regulatory change notices**
   - identify concrete regulator/provider records for material regulatory-change intelligence outside incident-only CTI scope;
   - implement provider-specific governed acquisition where useful;
   - preserve evidence class and chronology;
   - run controlled live proof for executable providers.

9. **Official relationship disclosures**
   - define concrete first-party/provider-specific acquisition routes;
   - preserve `claimed` versus `contracted/current` relationship truth;
   - live-validate executable production paths.

10. **Public partner directories**
    - select useful concrete partner-directory providers;
    - implement governed acquisition and canonical relationship-evidence mapping;
    - do not infer current commercial contracts from directory presence alone;
    - run controlled live proof.

11. **Public case studies**
    - select useful concrete first-party/provider-specific sources;
    - implement bounded acquisition and chronology/version handling;
    - preserve historical-versus-current relationship semantics;
    - run controlled live proof for executable providers.

12. **Public certificate relationship metadata**
    - define the narrow cases where certificate material has explicit relationship semantics;
    - keep technical certificate telemetry under SA-17 and relationship interpretation under this SA;
    - require review and independent evidence where certificate issuance alone is insufficient;
    - live-validate any executable relationship-specific path.

## Licensed corporate/news and dataset recovery

13. **Licensed corporate news metadata**
    - select one or more concrete licensed provider(s) where product value justifies it;
    - establish customer-facing use, storage, redistribution, attribution and retention rights;
    - implement provider-specific adapter/runtime/secret/quota controls;
    - run controlled live proof before activation promotion.

14. **Commercial licensed dataset**
    - decompose the historical generic family into concrete provider-specific datasets only where useful;
    - document lawful purpose, permitted fields, customer-facing rights, storage/retention, quotas and deletion obligations;
    - implement and live-test each approved concrete provider;
    - otherwise explicitly exclude the generic family by product-owner decision rather than leaving it permanently blocked.

## GDELT handoff clarification

15. **GDELT current-generation provider activation** is owned by **SA-21**, not SA-18.

The responsibility split is explicit:

- **SA-21 owns provider activation**: current official contract review, exact endpoint/product generation, schemas, quotas, storage/use terms, Source Governance, adapter/runtime/checkpoints and controlled real-provider live proof.
- **SA-18 owns CTI/news consumption semantics only after SA-21 activation**: incident/news evidence classification, claim-state handling, source independence, chronology and downstream CTI/ransomware/phishing use.

SA-18 must not implement a separate GDELT provider adapter, relabel a historical GDELT endpoint as current generation, or claim GDELT live integration before SA-21 closes the provider activation path.

The historical SA-15 GDELT dependency is therefore handed forward to SA-21 and should no longer be described as ambiguously shared with SA-18.

## Explicit non-scope

The following remain owned by their already assigned waves and are not SA-21 work:

- SA-17: DNS/CT/RDAP passive infrastructure, Shodan/Censys/SecurityTrails/urlscan/VirusTotal/GreyNoise/AbuseIPDB/Spamhaus/Wappalyzer/BuiltWith/HTTP Archive/licensed passive providers and local OSINT frameworks;
- SA-18: vulnerability, CERT/vendor advisory, incident, ransomware, phishing, malware/IOC and CTI consumption semantics;
- SA-19: LinkedIn, Reddit, Discord, BrixHub and professional/community providers;
- SA-20: document/media expansion, developer ecosystems and residual identity/procurement/ATS live proof.

## Mandatory decomposition

SA-21 is an ownership umbrella and must be decomposed into independently implementable micro-lots before substantive provider coding. Each micro-lot should own one coherent vertical capability and one exact exit gate.

Suggested decomposition:

- SA21-L01: second independent search provider selection + adapter/live proof;
- SA21-L02: Brave final live promotion;
- SA21-L03: Mojeek final live promotion;
- SA21-L04: Marginalia commercial activation;
- SA21-L05: current USPTO/PatentsView ODP implementation;
- SA21-L06: Google eligible automated route;
- SA21-L07: current GDELT provider activation;
- SA21-L08+: concrete corporate/regulatory/relationship provider activations;
- final SA21 closeout: licensed corporate news/commercial dataset decisions and machine-derived orphan audit.

The decomposition may change as provider prerequisites are resolved, but no item in this SA may silently disappear.

## Exit gate

SA-21 may close only when all fifteen owned items have exactly one truthful terminal outcome:

1. fully integrated through a real production path and controlled live proof;
2. replaced by a demonstrably equivalent fully integrated canonical capability;
3. duplicate of a fully integrated canonical capability; or
4. explicitly excluded from product scope by product-owner decision.

The following are not terminal completion states for a useful SA-21 item:

- missing API key;
- missing paid entitlement;
- missing provider permission;
- missing deployment account/target;
- `manual` fallback without an explicit manual-only product decision;
- `blocked` prerequisite;
- adapter-only readiness;
- deterministic/mock CI without provider live proof;
- an issue or documentation note without an executable owner.

Before closeout, generate a machine-derived orphan audit proving that no useful historical Source Activation capability remains without a named remediation SA/lot.

## Validation requirements

Every implementation micro-lot must satisfy repository standards, including deterministic network-free unit tests, provider contract fixtures, architecture checks, complete backend regression coverage requirements, controlled live validation through production adapters after legitimate authorization, exact-final-SHA validation, and no unresolved review blockers before merge.
