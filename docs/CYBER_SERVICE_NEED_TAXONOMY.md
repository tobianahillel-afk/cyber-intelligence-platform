# Cybersecurity Service and Need Taxonomy

## Purpose

Cyber Intelligence Platform must discover and qualify a broad range of cybersecurity needs. SIEM and SOC opportunities are important, but they are only one part of the commercial scope.

This document defines the canonical service families, need hypotheses, evidence signals, Google and search-dork discovery patterns, confidence rules, and implementation requirements used by source adapters, signal fusion, scoring, alerts, searches, company workspaces, and opportunities.

The taxonomy is evidence-first. A source mention creates an observation or weak signal. It does not by itself prove that an organization has a confirmed need, budget, vulnerable system, active project, or intention to purchase.

## Canonical service families

Every commercial signal and need hypothesis may map to one or more service families. The canonical identifiers are stable and provider-independent.

| ID | Service family | Typical offers |
|---|---|---|
| `security_strategy_vciso` | Security strategy and governance leadership | vCISO, security roadmap, maturity program, operating model, budget and KPI design |
| `risk_assessment_audit` | Risk assessment and security audit | maturity assessment, technical audit, organizational audit, gap analysis, due diligence |
| `grc_compliance` | Governance, risk and compliance | ISO 27001, NIS2, DORA, SOC 2, PCI DSS, HDS, GDPR security, policy and control frameworks |
| `penetration_testing` | Penetration testing | web, API, mobile, internal, external, Active Directory, cloud, wireless and authorized physical testing |
| `red_team_purple_team` | Adversary simulation and control validation | red team, purple team, breach-and-attack simulation, detection validation, threat-led testing |
| `vulnerability_management_asm` | Vulnerability and attack-surface management | vulnerability program, exposure management, external attack-surface management, remediation governance |
| `soc_siem_mdr_detection` | Security operations and detection | SOC build or transformation, SIEM, MDR, XDR, SOAR, detection engineering, use cases, threat hunting |
| `incident_response_dfir` | Incident response and forensics | emergency response, DFIR, compromise assessment, ransomware response, evidence preservation |
| `resilience_bcp_drp` | Cyber resilience and continuity | BCP, DRP, crisis exercises, ransomware readiness, tabletop exercises, backup and recovery review |
| `iam_pam_zero_trust` | Identity and access security | IAM, IGA, PAM, MFA, Active Directory and Entra hardening, Zero Trust, privileged-access review |
| `cloud_security` | Cloud and container security | AWS, Azure and GCP assessments, CSPM, CNAPP, Kubernetes, landing-zone security, cloud architecture |
| `application_security_devsecops` | Application security and DevSecOps | secure SDLC, threat modeling, code review, SAST, DAST, SCA, secrets, SBOM, CI/CD hardening |
| `network_security_sase` | Network and edge security | segmentation, firewall, WAF, IDS/IPS, NAC, SASE, SSE, ZTNA, DNS and email security |
| `data_security_privacy` | Data protection and cryptography | DLP, encryption, KMS, secrets management, data classification, privacy engineering |
| `third_party_supply_chain` | Third-party and supply-chain security | supplier risk, software supply chain, SBOM governance, partner assurance, acquisition due diligence |
| `ot_ics_iot_security` | OT, ICS and IoT security | industrial assessment, architecture, segmentation, asset visibility, IEC 62443 support |
| `security_awareness_training` | Awareness and skills development | awareness programs, phishing simulations, secure-development training, SOC and incident exercises |
| `product_integration_migration` | Product deployment and optimization | implementation, migration, integration, tuning, consolidation, licence rationalization, managed operation |
| `cyber_insurance_readiness` | Cyber-insurance readiness | control evidence, insurer questionnaires, remediation plan, renewal preparation |

A deployment may add product-specific subcategories, but must not replace these stable families with vendor-specific labels.

## Need hypothesis classes

A need hypothesis explains why an organization may benefit from one or more service families.

| Hypothesis | Meaning |
|---|---|
| `explicit_procurement` | A public tender, request, budget line, award or procurement document explicitly requests a capability. |
| `contract_renewal_or_replacement` | A known contract, incumbent or licence is approaching an evidenced or estimated renewal window. |
| `program_build_or_transformation` | Hiring, architecture, project documents or leadership statements indicate a new or changing security program. |
| `capability_gap` | Repeated public evidence indicates missing capacity, expertise, process or ownership. |
| `incident_urgency` | An incident, official disclosure or strongly corroborated claim creates an immediate response or recovery need. |
| `regulatory_deadline_or_gap` | Regulation, audit finding, enforcement action or published compliance objective creates a control need. |
| `technology_risk_or_lifecycle` | A product, version, end-of-support condition or applicable vulnerability creates remediation or migration need. |
| `external_exposure` | Fresh passive evidence indicates an externally visible asset or configuration requiring review. |
| `organizational_change` | Acquisition, expansion, restructuring, new leadership or outsourcing creates integration and governance needs. |
| `provider_dissatisfaction_or_transition` | Public evidence indicates replacement, consolidation, tendering or transition away from an incumbent. |
| `skills_and_training_need` | Hiring, repeated operational questions or published objectives indicate training or enablement demand. |
| `research_only_weak_signal` | A low-confidence clue worth analyst research but not sufficient for an alert or opportunity. |

## Signal-to-service mapping

### Procurement and contracts

Procurement notices, statements of work, awards, framework agreements, amendments and renewal evidence may map directly to any service family.

Examples:

- `audit de sécurité`, `audit organisationnel`, `homologation` -> `risk_assessment_audit` or `grc_compliance`;
- `test d'intrusion`, `pentest`, `red team` -> `penetration_testing` or `red_team_purple_team`;
- `SOC`, `SIEM`, `MDR`, `supervision` -> `soc_siem_mdr_detection`;
- `PCA`, `PRA`, `gestion de crise` -> `resilience_bcp_drp`;
- `IAM`, `PAM`, `annuaire`, `Zero Trust` -> `iam_pam_zero_trust`;
- `sécurité cloud`, `CSPM`, `Kubernetes` -> `cloud_security`;
- `DevSecOps`, `SAST`, `SCA`, `SBOM` -> `application_security_devsecops`;
- `NIS2`, `DORA`, `ISO 27001`, `PCI DSS`, `HDS` -> `grc_compliance`;
- `forensic`, `réponse à incident`, `ransomware` -> `incident_response_dfir`;
- `sensibilisation`, `formation`, `exercice de crise` -> `security_awareness_training` or `resilience_bcp_drp`.

Confirmed procurement is high-value evidence. Estimated renewals remain explicitly labelled as estimates.

### Hiring and team changes

Job postings can indicate investment, transformation or gaps but do not prove a purchase decision.

Examples:

- pentest or offensive-security hiring -> `penetration_testing`, `red_team_purple_team`;
- GRC, compliance or risk hiring -> `grc_compliance`, `risk_assessment_audit`;
- IAM or PAM roles -> `iam_pam_zero_trust`;
- cloud-security or Kubernetes roles -> `cloud_security`;
- AppSec or DevSecOps roles -> `application_security_devsecops`;
- DFIR or incident-response roles -> `incident_response_dfir`;
- SOC, detection or threat-hunting roles -> `soc_siem_mdr_detection`;
- OT-security roles -> `ot_ics_iot_security`.

Hiring may indicate internalization rather than external buying. The hypothesis explanation must show both possibilities.

### Incidents, ransomware and regulatory events

- official incident confirmation -> `incident_response_dfir`, `resilience_bcp_drp`, `risk_assessment_audit`;
- ransomware claim without confirmation -> weak, confidence-penalized incident signal;
- regulator notice or sanction -> `grc_compliance`, `data_security_privacy`, `risk_assessment_audit`;
- repeated service outages -> `resilience_bcp_drp`, potentially `network_security_sase`;
- supply-chain incident -> `third_party_supply_chain`, `application_security_devsecops`, `incident_response_dfir`.

An actor claim must never be treated as an official confirmation.

### Technologies, advisories and exposure

- known SIEM or EDR product -> product integration, migration or managed-operation context;
- end-of-life firewall or identity platform -> `network_security_sase` or `iam_pam_zero_trust`;
- applicable cloud or container advisory -> `cloud_security`;
- applicable library or CI/CD risk -> `application_security_devsecops`;
- fresh externally visible service -> `vulnerability_management_asm` or relevant architecture assessment;
- exposed industrial service from an approved passive source -> `ot_ics_iot_security`.

Technology-family evidence is not exact-version evidence. Passive observations are hypotheses, not active validation.

### Corporate and professional evidence

- acquisition or merger -> `third_party_supply_chain`, `security_strategy_vciso`, `iam_pam_zero_trust`, `cloud_security`;
- new CISO or security leader -> transformation context, not an automatic need;
- cloud migration statement -> `cloud_security`, `application_security_devsecops`, `iam_pam_zero_trust`;
- public certification objective -> `grc_compliance`;
- public engineering or support discussion -> weak professional signal requiring corroboration.

## Google and search-dork integration

Google dorking and equivalent search-provider queries are part of the product's governed public-research capability.

The objective is to discover public source documents and pages that reveal contracts, projects, technologies, providers, incidents, regulatory obligations and cybersecurity needs.

### Execution modes

- Google queries are generated as analyst links unless an approved official API or written authorization covers automated retrieval.
- Approved search APIs such as Brave Search or Bing may execute automatically under their source policy.
- Search-result metadata is discovery evidence only.
- The referenced document or page must be retrieved through an approved source path before it supports a fact or opportunity.
- The platform must not bypass search-engine restrictions, authentication, CAPTCHA, paywalls or access controls.

### Contract and procurement dork families

```text
"{organization}" (marché OR accord-cadre OR contrat OR attributaire OR titulaire OR renouvellement)
"{organization}" (appel d'offres OR consultation OR cahier des charges OR CCTP OR DCE) cybersecurity
site:boamp.fr "{organization}" (cybersécurité OR sécurité informatique)
site:ted.europa.eu "{organization}" (security OR cybersecurity)
site:{organization_domain} (contrat OR prestataire OR fournisseur OR intégrateur) filetype:pdf
site:{organization_domain} (marché OR appel d'offres OR accord-cadre) filetype:pdf
```

### Multi-service need dork families

```text
"{organization}" (pentest OR "test d'intrusion" OR "red team" OR "purple team")
"{organization}" (audit cybersécurité OR audit sécurité OR homologation OR analyse de risques)
"{organization}" (NIS2 OR DORA OR "ISO 27001" OR "SOC 2" OR "PCI DSS" OR HDS)
"{organization}" (IAM OR IGA OR PAM OR "Zero Trust" OR "Active Directory")
"{organization}" (SOC OR SIEM OR MDR OR XDR OR SOAR OR "threat hunting")
"{organization}" (DFIR OR forensic OR ransomware OR "incident response")
"{organization}" (PCA OR PRA OR "gestion de crise" OR "continuité d'activité")
"{organization}" (CSPM OR CNAPP OR Kubernetes OR "cloud security")
"{organization}" (AppSec OR DevSecOps OR SAST OR DAST OR SCA OR SBOM)
"{organization}" (DLP OR chiffrement OR KMS OR "data classification")
"{organization}" (OT security OR ICS security OR IEC62443 OR "sécurité industrielle")
"{organization}" (sensibilisation cybersécurité OR phishing simulation OR formation sécurité)
```

### Domain-focused discovery

```text
site:{organization_domain} (cybersécurité OR sécurité OR risque OR conformité) filetype:pdf
site:{organization_domain} (architecture OR migration OR transformation) (cloud OR IAM OR SOC OR sécurité)
site:{organization_domain} (prestataire OR partenaire OR intégrateur OR fournisseur) (cyber OR sécurité)
site:{organization_domain} (incident OR ransomware OR indisponibilité OR violation de données)
site:{organization_domain} (recrutement OR carrière OR jobs) (pentest OR GRC OR AppSec OR SOC OR IAM)
```

Templates must be versioned, localized, provider-aware, bounded, auditable and linked to a research case or scheduled approved search workflow.

## Evidence and confidence rules

Each mapping must record:

- service family and need hypothesis;
- evidence IDs and source independence;
- explicit or inferred status;
- confidence and uncertainty;
- event time, observation time and expiry;
- contradictory evidence;
- organization-resolution confidence;
- reason and analyst-readable explanation.

Typical confidence ordering:

1. current official procurement or contract evidence;
2. official company, regulator or authority statement;
3. authoritative registry or vendor/customer publication;
4. current official job posting or engineering publication;
5. licensed passive observation;
6. reputable media report;
7. public professional or community statement;
8. unverified pseudonymous statement.

Signals copied from the same upstream source do not count as independent corroboration.

## Opportunity behavior

- One organization may have several concurrent need hypotheses.
- Compatible hypotheses may be grouped into one commercial motion.
- Unrelated service families remain separate opportunities or opportunity tracks.
- A source refresh updates existing signals and opportunities rather than duplicating them.
- Historical evidence improves chronology but must not create a current alert without a current trigger.
- Analyst qualification, rejection and override history must survive recalculation.

Examples:

- a confirmed ransomware incident can create an urgent `incident_response_dfir` motion and a later `resilience_bcp_drp` review;
- an IAM tender and an Active Directory audit request may be grouped into one identity-security motion;
- an ISO 27001 objective and a separate mobile-app pentest remain distinct commercial motions;
- a SIEM job posting alone may remain a research signal until a tender, project statement or other independent evidence appears.

## Development ownership

- Lot 10 provides the machine-readable source and adapter runtime.
- Lot 11 supplies procurement, contracts, incumbents and renewal evidence across all service families.
- Lot 12 supplies governed corporate-web, document, archive and search-dork discovery.
- Lots 13 to 19 supply cyber, technology, incident, exposure and business-change evidence.
- Lots 20 to 23 resolve entities, professional context, conditional sources and research cases.
- Lot 24 implements the canonical service taxonomy, signal fusion and need hypotheses in code.
- Lot 25 calibrates scoring per service family and evidence pattern.
- Lots 26 and 27 expose the commercial workflow and complete company workspace.

## Mandatory tests

The release gates must include:

- at least one positive, negative and ambiguous scenario for every service family;
- multilingual synonyms and provider/product aliases;
- procurement text that maps to several services without duplicate opportunities;
- SIEM-heavy evidence that must not suppress unrelated pentest, audit, IAM or compliance needs;
- search-result metadata that cannot become a confirmed fact without retrieving the source page;
- copied search results that do not count as independent corroboration;
- hiring that may indicate internalization rather than external purchase;
- vulnerability evidence without organization applicability;
- historical contract evidence without a current renewal trigger;
- contradiction, correction, expiry and retraction propagation;
- stable deterministic signal and opportunity identities;
- explanation completeness for every service recommendation;
- benchmark precision, recall, false-positive rate and accepted-opportunity contribution by service family.

## Definition of done

The taxonomy is correctly integrated when:

- SIEM/SOC is one service family among the complete portfolio;
- Google and approved search dorks can discover public contracts and multi-service evidence through governed workflows;
- every signal can map to zero, one or several service families with explicit confidence;
- every opportunity explains the evidence, need hypothesis and proposed service family;
- weak evidence creates research tasks rather than unsupported sales claims;
- source refreshes, corrections and contradictions update existing commercial motions without duplication;
- commercial benchmarks demonstrate useful client discovery across several service families, not only SIEM.
