# Cyber Intelligence Platform

A compliance-first platform for cyber threat intelligence, company research, passive exposure analysis, and B2B opportunity discovery.

## Purpose

The platform correlates lawful public or licensed data to help identify organizations that may need cybersecurity services or products. It is designed to answer:

- What public cyber events affect an organization?
- Which technologies and externally visible assets are publicly associated with it?
- Which published vulnerabilities are relevant to those technologies?
- Which professional roles are appropriate contacts?
- What evidence supports a timely, factual, non-manipulative outreach?

## Planned capabilities

- Company and domain intelligence
- Public incident and ransomware-event aggregation
- Vulnerability and technology correlation
- Search-engine dork management for lawful public research
- Professional organization mapping
- Evidence-backed opportunity scoring
- Source provenance, confidence, freshness, and retention controls
- Human-reviewed outreach preparation

## Operating principles

1. **Public or licensed sources only.** Every connector must have a documented legal and contractual basis.
2. **Passive by default.** No intrusive scan, exploitation, authentication attempt, or unsolicited security test.
3. **No stolen-data repository.** Store event metadata, indicators, summaries, and source references—not credential dumps, victim files, private conversations, or extorted content.
4. **Professional data minimization.** Collect only data relevant to a person's professional role and the stated B2B purpose.
5. **Evidence before scoring.** Every signal must be traceable to a source and timestamp.
6. **Human review before outreach.** The platform does not autonomously contact organizations.
7. **No crisis manipulation.** Recent incidents may create a relevant service need, but outreach must remain factual, respectful, and non-coercive.

## Dorking scope

The project may generate and manage advanced search queries for public search engines. Dorking is treated as a discovery mechanism, not authorization to access restricted systems or download sensitive material.

Allowed examples include:

- locating official company documents and security contacts;
- identifying publicly indexed technology documentation;
- finding public incident notices, tenders, job postings, and regulatory publications;
- detecting potentially exposed public pages for manual, non-intrusive review.

The platform must not bypass authentication, defeat access controls, brute-force resources, exploit a discovered weakness, or collect secrets and personal files.

## Initial architecture

```text
apps/
  api/                 FastAPI application
  worker/              ingestion and enrichment jobs
packages/
  domain/              core entities and scoring models
  collectors/          source-specific connectors
  compliance/          source policy and data controls
docs/
  PRODUCT.md
  ARCHITECTURE.md
  SOURCE_POLICY.md
  DATA_MODEL.md
policies/
  sources.example.yml
  retention.yml
tests/
```

## Status

Bootstrap phase. The first milestone is a source registry, normalized event model, company records, evidence storage, and a small set of official/public feeds.

## Security

Do not commit API keys, credentials, personal-data exports, leaked datasets, or proprietary source content. See `SECURITY.md`.
