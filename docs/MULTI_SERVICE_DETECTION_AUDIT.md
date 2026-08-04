# Multi-Service Detection and Search-Dork Consistency Audit

## Scope

This audit verifies that the expanded source portfolio, product definition, roadmap, data flow, tests and commercial model support cybersecurity needs beyond SIEM and SOC.

Reviewed documents:

- `PRODUCT.md`;
- `COMMERCIAL_INTELLIGENCE_INTEGRATION_ARCHITECTURE.md`;
- `PROJECT_DELIVERY_PLAN.md`;
- `OSINT_COLLECTION_CATALOG.md`;
- `LIVE_CYBER_THREAT_SOURCE_CATALOG.md`;
- `DATA_MODEL.md`;
- `TEST_STRATEGY.md`;
- `SOURCE_INTEGRATION_TEST_MATRIX.md`;
- `ROADMAP_AND_ARCHITECTURE_AUDIT.md`;
- current lot 09 onboarding implementation and pull request.

## Findings

### 1. The product boundary was broad but examples were SIEM-heavy

The product already targeted penetration-testing firms, audit firms, incident response, GRC, SOC, MDR, cybersecurity vendors and independent consultants. However, the alert examples emphasized SIEM, SOC and detection roles.

**Correction:** `PRODUCT.md` now states explicitly that the platform is not a SIEM-only lead generator and lists the complete service portfolio.

### 2. A canonical service taxonomy was missing

The architecture used generic `service_fit` fields without a stable list of service families, need classes, synonyms and evidence rules.

**Correction:** `CYBER_SERVICE_NEED_TAXONOMY.md` now defines stable service-family identifiers, need-hypothesis classes, evidence mappings, confidence rules, opportunity behavior, lot ownership and mandatory tests.

### 3. Google dorking was present but not explicit enough in the product contract

`OSINT_COLLECTION_CATALOG.md` already contained Google and search-dork families for tenders, contracts, products, incidents, jobs and documents. The roadmap placed corporate websites, documents, search and archives in lot 12. The product definition did not state clearly enough that this is a first-class discovery workflow.

**Correction:** Google and equivalent search dorks are now explicit in `PRODUCT.md` and `CYBER_SERVICE_NEED_TAXONOMY.md`.

The governed behavior is:

```text
versioned query template
  -> Google analyst link or approved search API
  -> result metadata
  -> approved retrieval of the referenced source
  -> canonical evidence
  -> signal and need hypothesis
```

Search-result metadata alone cannot confirm a contract, technology, incident or need.

### 4. Contract discovery applies to every cyber service family

Contracts and procurement are not limited to SIEM. The new taxonomy covers audit, pentest, red team, GRC, incident response, continuity, IAM, cloud, AppSec, network security, data protection, supply chain, OT, awareness and product integration.

Lot 11 owns structured procurement history, awards, incumbents and renewal timing. Lot 12 owns governed web, document, archive and search-dork discovery. They feed the same canonical contract, evidence and need-hypothesis models.

### 5. A company may have several needs without duplicate opportunities

The correct model is not one score or one service per company.

- one observation may support several service fits;
- compatible hypotheses may form one commercial motion;
- unrelated services remain separate tracks;
- duplicated sources do not duplicate the motion;
- refreshes update existing motions;
- historical evidence does not create a current alert without a current trigger.

Example:

```text
ransomware confirmation
  -> urgent incident-response motion
  -> later resilience and audit motion

ISO 27001 objective
  -> GRC motion

mobile application launch
  -> separate application-pentest motion
```

### 6. Hiring evidence requires two-sided interpretation

Recruitment can indicate a capability gap, transformation or budget. It can also indicate that the organization is internalizing the capability instead of buying external services.

Every hiring-based hypothesis must expose both interpretations and remain lower confidence until corroborated by procurement, project, contract, leadership, technology or other independent evidence.

### 7. Vulnerability and exposure evidence cannot directly become a sales claim

The revised sequence remains:

```text
vulnerability knowledge
  + passive technology or asset observation
  + vendor advisory and version applicability
  -> qualified risk hypothesis
```

A CVE, product family or passive banner alone cannot establish that the prospect is vulnerable.

### 8. Current lot 09 must not implement future scoring concerns

Lot 09 remains correctly scoped to provider onboarding and secret lifecycle. Adding multi-service classification code to this pull request would mix lots and make validation harder.

The correct implementation sequence is:

- lot 10: source runtime and machine-readable catalog;
- lot 11: structured contracts and renewals;
- lot 12: corporate crawling, documents, archives and governed dorks;
- lots 13–23: evidence families and resolution;
- lot 24: service taxonomy, signal fusion and need hypotheses in executable code;
- lot 25: scoring calibration by service family;
- lots 26–27: commercial workflows and Company 360.

## Canonical service coverage

The future executable taxonomy must cover at least:

1. security strategy and vCISO;
2. risk assessment and audit;
3. GRC and compliance;
4. penetration testing;
5. red and purple teaming;
6. vulnerability and attack-surface management;
7. SOC, SIEM, MDR, XDR, SOAR and detection engineering;
8. incident response and DFIR;
9. resilience, BCP, DRP and crisis exercises;
10. IAM, IGA, PAM and Zero Trust;
11. cloud and container security;
12. application security and DevSecOps;
13. network, edge, SASE and email security;
14. data protection, encryption and secrets management;
15. third-party and supply-chain security;
16. OT, ICS and IoT security;
17. awareness and training;
18. product deployment, migration and optimization;
19. cyber-insurance readiness.

## Test consistency

The taxonomy document makes the following future tests mandatory:

- positive, negative and ambiguous cases for every service family;
- multilingual terminology and product aliases;
- contracts containing several service categories;
- unrelated needs remaining separate;
- SIEM signals not suppressing pentest, audit, IAM or GRC signals;
- search metadata not becoming a confirmed fact;
- copied sources not increasing source independence;
- internal hiring versus external-purchase ambiguity;
- historical contract without a current renewal trigger;
- corrections, expiry, contradiction and retraction propagation;
- deterministic signal and opportunity identities;
- precision, recall, false-positive rate and accepted value per service family.

These requirements complement `SOURCE_INTEGRATION_TEST_MATRIX.md`; implementation belongs to the relevant future lots rather than the lot 09 codebase.

## Duplicate and contradiction review

No new direct adapter-to-opportunity path was introduced.

The canonical path remains:

```text
source
  -> immutable source record
  -> observation or claim
  -> entity and event resolution
  -> corroboration and contradiction
  -> commercial signal
  -> need hypothesis
  -> commercial motion and opportunity
```

This structure prevents:

- one contract creating several duplicate opportunities because it contains several keywords;
- the same incident being duplicated by several aggregators;
- a Google result and its target page being counted as independent evidence;
- a historical document being treated as a current need;
- one broad SIEM rule becoming the default classification for all cyber needs.

## Remaining implementation work

The documentation is now coherent, but the following are not yet implemented:

- machine-readable executable service taxonomy;
- lot 12 dork template registry and approved search-provider adapters;
- cross-language service classifier;
- service-specific signal fusion;
- multi-motion opportunity grouping;
- labelled commercial benchmark datasets per service family;
- UI filters and explanations for all service families.

These items are intentionally assigned to future lots. They should not be presented as current lot 09 functionality.

## Conclusion

The product goal is now explicit and coherent:

> discover organizations with evidence-backed cybersecurity needs across the full service portfolio, explain the supporting evidence and uncertainty, identify the correct professional context, and manage distinct commercial motions without duplicate or unsupported claims.

SIEM and SOC remain supported service families, but they are no longer the default or dominant definition of a cybersecurity opportunity.
