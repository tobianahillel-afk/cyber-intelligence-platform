# SA-06 — Corporate change and relationship source activation

Status: implementation/reconciliation contract for issue #89.

## Reuse boundary

SA-06 does not introduce another crawler. Public discovery reuses the already-governed SA-02 / Priority-B-3 paths (Brave Search metadata, Internet Archive CDX, bounded public-web sitemap/feed/security/document collection). Canonical interpretation reuses Lot 18 `corporate_changes` and Lot 19 `relationship_intelligence` schemas/mappers.

A discovered page, feed item, certificate, partner page or case study is source material only. It is not automatically a material-change event, an independent corroborating source, a current contract, an incumbent provider, a service need or an opportunity.

## Terminal dispositions

### Official corporate disclosures

`official-corporate-disclosures` is `manual` / SA-06. Analysts may ingest or approve bounded first-party company disclosures found through the governed public-web/search/archive paths. The existing Lot 18 official-change mapper is the canonical path once the disclosure has been reviewed and structured. Generic automatic interpretation is not authorized because each company publishes different structures and semantics.

### Official regulatory change notices

`official-regulatory-change-notices` is `manual` / SA-06. Approved regulator notices may be discovered by the existing bounded web/search paths and mapped as regulator evidence only after source-specific review. A regulator mention does not become a company-confirmed event without the appropriate evidence class.

### Licensed corporate news

`licensed-corporate-news-metadata` is `blocked` and owned by SA-07 until a concrete provider, commercial/customer-facing licence, fields, attribution/retention conditions, credentials, quotas and runtime adapter are reviewed. A generic licensed family is not executable.

### Official relationship disclosures

`official-relationship-disclosures` is `manual` / SA-06. First-party statements can become Lot 19 relationship evidence after analyst review. Marketing language is `claimed` evidence and never silently becomes `contracted` or active incumbency.

### Public partner directories

`public-partner-directory-metadata` is `manual` / SA-06. A public directory entry is review-required relationship metadata. Directory presence does not prove a current commercial contract.

### Public case studies

`public-case-study-metadata` is `manual` / SA-06. Case studies are bounded public evidence and may be historical. They do not prove current incumbency, renewal timing or current product deployment.

### Public certificate relationship metadata

`public-certificate-relationship-metadata` is `manual` / SA-06. Certificate material can support a review candidate only when relationship semantics are explicit and independently reviewed. Certificate issuance alone never proves a provider/customer relationship; SA-03 certificate telemetry remains a separate evidence source.

## Safety and evidence boundary

SA-06 adds no autonomous page interpretation, no paywall/auth/CAPTCHA/MFA bypass, no private portals, no contact harvesting, no active probing and no outreach. Search-result metadata and the linked page share one discovery lineage. Syndicated copies remain one lineage. Historical relationships remain historical.

## Completion gate

SA-06 closes only when all seven modeled source families have explicit dispositions and owner waves, Source Activation truth and the Coverage Matrix agree, no generic family becomes executable, and the complete repository backend/frontend CI passes on one exact SHA. SA-07 may begin only after the squash merge.