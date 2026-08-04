# Live Cyber Threat and Incident Source Catalog

## Purpose

This catalog expands the source plan for near-real-time cyber incidents, ransomware claims, public attack telemetry, exploitation activity, malicious infrastructure, phishing, malware, advisories, and public research material.

It complements `OSINT_COLLECTION_CATALOG.md`. A source listed here is a candidate, not an automatic authorization to collect it.

The platform must distinguish:

- machine-readable intelligence that can drive an adapter;
- licensed or account-gated intelligence requiring onboarding;
- visualization-only threat maps useful for context but not suitable as evidence;
- public research datasets that can be imported historically;
- raw criminal infrastructure, victim files, private communications, or stolen data, which are not collected.

## Integration classes

| Class | Meaning |
|---|---|
| `priority_api` | High-value structured API or feed suitable for an early adapter after policy approval. |
| `licensed_api` | Useful structured provider requiring a commercial licence or approved account. |
| `public_feed` | Public downloadable feed, RSS, TAXII, STIX, CSV, JSON, or open dataset. |
| `research_dataset` | Historical or anonymized research material, not a live operational source. |
| `manual_context` | Useful visualization or analyst reference without a reviewed ingestion interface. |
| `quarantined` | Source identity, provenance, licence, or data categories still require validation. |

## 1. Ransomware victims, groups, claims, and public activity

### Priority structured sources

| Source | Candidate use | Class | Planned mode |
|---|---|---|---|
| Ransomware.live | Victims, groups, posts, sectors, countries, discovery dates, group profiles, public negotiation research metadata | `priority_api` | Historical import plus incremental API refresh |
| RansomLook | Live ransomware posts, group and market profiles, victims, ransom notes, crypto addresses, public actor activity | `priority_api` | API polling with checkpoints |
| Ransomwhere.org | Aggregated victim, group, news, statistics, and ransomware payment research data | `priority_api` | Cached API and upstream-source correlation |
| eCrime.ch | Structured ransomware events, leak sites, actors, screenshots, sectors, and geography | `licensed_api` | API import after account and licence review |
| Ransomch.at / Ransomchats | Anonymized, publicly released ransomware negotiation transcripts for research | `research_dataset` | Versioned historical import only |
| CISA StopRansomware | Official advisories, indicators, mitigations, and group information | `public_feed` | Advisory and RSS ingestion |
| CERT-FR | Alerts, advisories, incident summaries, and remediation guidance | `public_feed` | RSS and document ingestion |
| National CERT and NCSC feeds | Official incident and campaign reporting by country | `public_feed` | Provider-specific RSS/API adapters |
| ENISA publications | European threat landscape, sectors, campaigns, and trends | `public_feed` | Scheduled report ingestion |

### Commercial ransomware and dark-web intelligence candidates

These providers may expose ransomware mentions, actor infrastructure, marketplaces, Telegram sources, or dark-web monitoring through licensed interfaces. They remain licence-dependent candidates:

- DarkOwl Ransomware API;
- Searchlight Cyber;
- Flashpoint;
- KELA;
- Flare;
- Cybersixgill;
- Intel 471;
- Recorded Future;
- SOCRadar;
- Group-IB Threat Intelligence;
- ZeroFox;
- Constella Intelligence;
- SpyCloud, only for customer-authorized exposure monitoring;
- Darkfeed.io;
- VulnCheck threat and exploitation intelligence.

The platform may ingest public claim metadata and licensed summaries. It must not access victim portals, communicate with criminal actors, download victim files, or ingest raw stolen datasets.

## 2. Public ransomware negotiation research

The platform may analyze already published and anonymized negotiation corpora to understand:

- negotiation phases;
- demand changes;
- response timing;
- group communication patterns;
- proof-of-life requests;
- payment and discount patterns;
- public group-level tactics.

Approved candidates:

- Ransomch.at;
- the public Ransomchats JSON repository;
- anonymized negotiation datasets published through Ransomware.live;
- peer-reviewed datasets whose licence permits reuse.

Required controls:

- historical import only;
- preserve redactions and anonymization;
- do not attempt to identify undisclosed victims;
- no live access to negotiation portals;
- no direct interaction with attackers;
- no storage of victim credentials, private documents, or unredacted communications;
- use for group-level research and incident understanding, not victim targeting.

## 3. Internet-wide attack telemetry and live exploitation

### Machine-readable and high-value

| Source | Candidate use | Class |
|---|---|---|
| Cloudflare Radar APIs | Traffic anomalies, outages, BGP hijacks and route leaks, DDoS and application-attack trends | `priority_api` |
| CrowdSec CTI | IP behavior, attack patterns, linked CVEs, reputation, live exploit tracking, TAXII and offline replicas | `licensed_api` |
| GreyNoise | Internet scanner behavior, benign services, exploitation activity, CVE, vendor and C2 event feeds | `licensed_api` |
| SANS ISC / DShield | Top attacking sources, ports, honeypot observations, threat-intel labels, diaries, RSS and hourly feeds | `public_feed` |
| NETSCOUT Cyber Threat Horizon | DDoS attack source/target geography, attack type, size, duration, industry and historical trends | `manual_context` or licensed export if available |
| Shadowserver Foundation | Botnet, scanning, malware, exposed-service and sinkhole intelligence for authorized network owners | `licensed_api` or consented feed |
| MISP communities | Shared events, sightings, indicators, campaigns and taxonomies | `licensed_api` or community feed |
| OpenCTI live streams and TAXII | Continuous STIX intelligence exchange and connector orchestration | `priority_api` |

### Visualization and situational-awareness sources

These maps may represent only the provider's own sensors. They must not be treated as a complete record of global attacks or as proof that a named company was compromised:

- Check Point ThreatCloud live map;
- Fortinet FortiGuard threat map;
- Kaspersky Cyberthreat Real-Time Map;
- Bitdefender Threat Map;
- NETSCOUT Cyber Threat Horizon map;
- Radware Live Threat Map;
- SonicWall Capture Labs threat map;
- Akamai security visualizations;
- CrowdSec public activity visualizations;
- CyberVeille / CrowdSec honeypot map where available.

Use `manual_context` unless the provider exposes a documented API or licensed export.

## 4. Malware, command-and-control, malicious URLs, and indicators

### abuse.ch and Spamhaus ecosystem

| Source | Data | Class |
|---|---|---|
| ThreatFox | Recent IOCs, malware families, tags, confidence, first/last seen, references | `priority_api` |
| URLhaus | Malware-distribution URLs, active sites, payload hashes, CSV/JSON dumps, MISP events | `priority_api` |
| MalwareBazaar | Malware sample metadata, hashes, signatures, tags, detections, code-signing certificates | `priority_api` |
| Feodo Tracker | Botnet C2 IPs and Suricata rules | `public_feed` |
| SSLBL | Malicious certificate fingerprints, JA3 fingerprints, botnet C2 IP:port data | `public_feed` |
| Spamhaus DROP/EDROP and reputation datasets | Malicious networks, domains and infrastructure reputation | `licensed_api` or public feed depending dataset |

The project should ingest metadata and indicators. Malware binaries are not required for the commercial-intelligence product and remain excluded unless a separate isolated malware-analysis capability is explicitly approved.

### Additional IOC and reputation candidates

- AlienVault Open Threat Exchange;
- VirusTotal / Google Threat Intelligence;
- IBM X-Force Exchange;
- Cisco Talos Intelligence;
- Microsoft Defender Threat Intelligence / PassiveTotal successor services;
- Pulsedive;
- AbuseIPDB;
- CrowdSec CTI;
- GreyNoise;
- Emerging Threats Open rules;
- MISP warning lists and feeds;
- FIRST CSIRT feeds and member exchanges where licensed;
- Spamhaus datasets;
- Team Cymru Community Services and commercial threat intelligence;
- CIRCL passive DNS and related services where authorized.

## 5. Phishing, malicious domains, and fraud infrastructure

Candidate sources:

- PhishTank;
- OpenPhish;
- APWG eCrime Exchange under licence;
- URLhaus;
- Google Safe Browsing API;
- Microsoft SmartScreen or security intelligence feeds where available;
- Quad9 and DNS-filtering intelligence where licensed;
- Spamhaus DBL;
- CERT and brand-protection feeds;
- urlscan.io search and API;
- VirusTotal URL and domain intelligence;
- DomainTools Iris and threat intelligence;
- WhoisXML API threat intelligence;
- SecurityTrails;
- RiskIQ / Microsoft passive DNS data;
- newly registered and newly observed domain feeds;
- Certificate Transparency monitors;
- DShield new-domain and honeypot URL feeds.

Outputs should include domain, URL, brand target, first/last seen, status, hosting, certificate, DNS, redirect chain metadata, source confidence, and takedown state.

## 6. Vulnerabilities and exploitation in the wild

### Priority sources

- CVE.org;
- NVD API;
- CISA Known Exploited Vulnerabilities;
- FIRST EPSS;
- OSV;
- GitHub Security Advisories;
- CIRCL Vulnerability-Lookup and cve-search;
- vendor PSIRT and advisory feeds;
- CERT-FR advisories;
- ENISA and national CERT advisories;
- GreyNoise CVE and exploitation intelligence;
- CrowdSec Live Exploit Tracker;
- VulnCheck KEV and exploitation intelligence under licence;
- Exploit Prediction and proof-of-concept metadata providers;
- Exploit-DB as availability context, not evidence of exploitation;
- Metasploit module metadata as availability context;
- Packet Storm and Full Disclosure advisories after source review.

The platform must distinguish:

- vulnerability publication;
- public proof of concept;
- exploit module availability;
- observed scanning;
- observed exploitation;
- confirmed compromise;
- organization-specific applicability.

## 7. Exposure, domains, services, and technography

Passive and licensed candidates:

- Censys;
- Shodan;
- BinaryEdge;
- Netlas;
- ZoomEye;
- FOFA;
- ONYPHE;
- LeakIX;
- Criminal IP;
- Hunter.how;
- SecurityTrails;
- DomainTools;
- WhoisXML API;
- RDAP and official registries;
- crt.sh and Certificate Transparency logs;
- urlscan.io;
- PublicWWW;
- BuiltWith;
- Wappalyzer;
- HTTP Archive;
- DNSlytics;
- ViewDNS;
- Robtex;
- IPinfo;
- BGPView;
- RIPEstat;
- PeeringDB;
- Hurricane Electric BGP Toolkit;
- Cloudflare Radar ASN and BGP APIs;
- Internet measurement datasets such as Rapid7 Project Sonar where licensing permits.

Collection for prospects remains passive. The project does not actively scan, authenticate to, or test third-party assets.

## 8. Threat reports, campaigns, actors, and TTPs

Structured and unstructured sources:

- MITRE ATT&CK;
- MITRE CAPEC;
- MISP Galaxy and taxonomies;
- OpenCTI knowledge and connector ecosystem;
- AlienVault OTX pulses;
- Google / Mandiant threat intelligence reports;
- Microsoft Threat Intelligence;
- Unit 42;
- Cisco Talos;
- CrowdStrike threat research;
- SentinelLabs;
- Sophos X-Ops;
- ESET WeLiveSecurity;
- Kaspersky Securelist;
- FortiGuard Labs;
- Check Point Research;
- Rapid7 research;
- Proofpoint threat research;
- Trellix Advanced Research Center;
- Trend Micro Research;
- Sekoia.io threat research;
- CERT-FR;
- CISA alerts and advisories;
- NCSC reports;
- ENISA reports;
- national CERT and sector-ISAC publications;
- threat-research RSS feeds and newsletters after quality review.

Text extraction should normalize actors, malware, campaigns, sectors, countries, CVEs, TTPs, indicators, products, dates, confidence, and source claims into evidence-backed records.

## 9. Public company incident disclosures

High-value authoritative candidates:

- SEC EDGAR cybersecurity incident disclosures and company filings;
- national stock-exchange and market-regulator filings;
- company status pages and incident notices;
- official company press releases;
- regulator and data-protection authority notices;
- HHS OCR breach portal for covered US healthcare incidents;
- US state attorney-general breach-notification repositories;
- CNIL publications and sanctions;
- ICO enforcement and data-security publications;
- court filings and public procurement notices linked to incident response;
- national CERT and law-enforcement announcements.

Secondary corroboration sources may include reputable cybersecurity news publishers, but they must not replace primary evidence.

## 10. Cybersecurity news and incident reporting

Candidate secondary sources for rapid discovery and corroboration:

- BleepingComputer;
- The Record;
- SecurityWeek;
- CyberScoop;
- KrebsOnSecurity;
- Risky Business;
- Dark Reading;
- The Hacker News;
- SC Media;
- Infosecurity Magazine;
- CSO Online;
- Help Net Security;
- DataBreaches.net;
- Hackmageddon;
- vendor threat-research blogs;
- national and regional cybersecurity media.

These are discovery and secondary-reporting sources. The system must preserve the difference between a media report, an actor claim, an official confirmation, and an analyst inference.

## 11. CTI platforms and orchestration tools

The following are not all upstream data sources, but they provide import, enrichment, normalization, graphing, and automation capabilities useful to the platform:

- MISP;
- OpenCTI;
- IntelOwl;
- TheHive and Cortex analyzers;
- Maltego;
- SpiderFoot;
- Recon-ng;
- MSTICpy;
- Timesketch;
- Yeti threat intelligence;
- OpenTAXII;
- Cabby and TAXII clients;
- STIX 2 libraries;
- Sigma and SigmaHQ;
- YARA and YARA rule repositories;
- Suricata and Emerging Threats rules;
- Zeek intelligence frameworks;
- OpenSearch and graph projections for local correlation.

## 12. BrixHub

BrixHub remains a named source candidate in the project and must not be omitted from planning.

Target integration after approval:

1. controlled historical import of the provider's available database or export;
2. strict schema validation and prohibited-field filtering;
3. entity resolution against organizations, domains, technologies, incidents, and providers;
4. content hashes and source provenance;
5. incremental refresh using API, export delta, cursor, timestamp, or bounded web adapter;
6. deletion, correction, and retraction handling;
7. freshness and source-health monitoring;
8. no exposure of raw provider credentials to users.

Current status remains `quarantined` until the exact access method and permitted fields are approved. No live adapter exists yet.

## 13. Data model for live incidents

Every incident observation should support:

```yaml
source_id: string
source_record_id: string
source_url: string
claim_type: actor_claim | public_report | official_confirmation | regulatory_notice | telemetry_observation | analyst_inference | retraction
organization_id: string | null
organization_name_raw: string
actor_or_group: string | null
incident_type: ransomware | data_extortion | ddos | intrusion | phishing | malware | supply_chain | outage | vulnerability_exploitation | other
sector: string | null
country: string | null
first_seen_at: datetime | null
published_at: datetime | null
collected_at: datetime
last_changed_at: datetime | null
status: new | monitoring | corroborated | confirmed | disputed | retracted | historical
technologies_mentioned: []
vulnerabilities_mentioned: []
indicators: []
ttps: []
impact_summary: string | null
data_claimed: string | null
source_confidence: number
entity_match_confidence: number
corroboration_count: integer
evidence_hash: string
freshness_state: string
```

## 14. Refresh classes

| Source family | Suggested cadence |
|---|---|
| ransomware posts and victim trackers | 2 to 15 minutes where API quotas allow |
| active IOC and malicious URL feeds | 5 to 60 minutes |
| exploitation and scanner telemetry | 5 to 60 minutes |
| official incident disclosures | 15 minutes to 6 hours |
| threat research and news RSS | 15 minutes to 2 hours |
| vulnerability and advisory feeds | 15 minutes to 6 hours |
| attack maps without API | manual context only |
| historical negotiation research | version or release based |
| slower legal and regulatory sources | daily |

Every adapter must use checkpoints, conditional requests where supported, bounded pagination, deduplication, retries, backoff, and source-specific rate limits.

## 15. Evidence and safety requirements

The platform may collect lawful public or licensed metadata about incidents and attacker claims. It must not:

- interact with threat actors;
- enter victim negotiation portals;
- download or republish victim files;
- ingest credentials, infostealer logs, private communications, or extorted datasets;
- treat an actor claim as an official confirmation;
- expose sensitive personal information from incident material;
- automatically accuse an organization of compromise without evidence and confidence labels;
- use visualization-only threat maps as proof of a company-specific incident.

## 16. Implementation order

### Wave 1

- Ransomware.live;
- RansomLook;
- Ransomwhere.org;
- ThreatFox;
- URLhaus;
- Feodo Tracker;
- SSLBL;
- CISA KEV;
- EPSS;
- CIRCL Vulnerability-Lookup;
- CERT-FR feeds;
- Cloudflare Radar anomalies and BGP events;
- SANS ISC / DShield;
- AlienVault OTX;
- urlscan.io.

### Wave 2

- eCrime.ch;
- CrowdSec CTI and Live Exploit Tracker;
- GreyNoise;
- VirusTotal / Google Threat Intelligence;
- MISP and OpenCTI TAXII connectors;
- PhishTank and OpenPhish;
- company and regulator incident disclosures;
- licensed passive DNS and infrastructure intelligence.

### Wave 3

- licensed ransomware and dark-web intelligence providers;
- broader commercial CTI providers;
- BrixHub after approval;
- visualization-only maps where a supported API or licensed export becomes available.

## Definition of done

This catalog is complete enough for planning when:

- every candidate has an owner, access method, licence state, data categories, cadence, retention rule, and project use case;
- API and feed candidates have sample schemas and adapter acceptance tests;
- display-only maps are clearly marked as non-evidentiary;
- public ransomware claims are separated from official confirmations;
- negotiation research is limited to published anonymized datasets;
- BrixHub has a documented historical-import and incremental-refresh design but remains disabled until approval;
- all live sources integrate with the database-first refresh architecture rather than crawling on each page view.
