# SA-21 — Initial Microlot Decomposition

## Purpose

This document converts the SA-21 recovery umbrella into independently implementable units without dropping any owned capability.

The decomposition is planning-level. Each microlot must receive its own kickoff, deterministic tests, controlled live proof where legitimate provider access exists, exact-head validation, and closeout before it can be considered complete.

## Search/provider activation microlots

### SA21-L01 — Independent search redundancy

Owns:

- Bing or another approved independent general web-search provider;
- provider selection and entitlement review;
- normalized SERP adapter/runtime registration;
- governed evidence-discovery routing;
- controlled live proof.

Exit gate: one additional independent general search provider is fully integrated and live-tested, or an explicit product-owner decision records why the capability is excluded.

### SA21-L02 — Brave live completion

Owns final credential/onboarding/live-proof promotion for Brave Search.

Exit gate: legitimate deployment entitlement, secret onboarding, non-empty production-adapter live proof, truthful activation promotion and exact-head CI.

### SA21-L03 — Mojeek live completion

Owns final API entitlement, durable-storage-rights confirmation, onboarding and live-proof promotion.

Exit gate: legitimate provider access and reviewed storage rights are exercised through the production adapter on the exact validated head.

### SA21-L04 — Marginalia commercial activation

Owns commercial entitlement, storage/use rights, Source Governance, approved endpoint scope, secret onboarding and real-provider live proof.

Exit gate: either fully integrated under legitimate commercial rights or explicitly excluded by product-owner decision.

### SA21-L05 — Current USPTO / PatentsView ODP

Owns replacement of the revoked historical PatentsView route with the reviewed current USPTO Open Data Portal contract.

Exit gate: current endpoint/schema/auth/terms are implemented provider-specifically and live-tested; the historical endpoint remains revoked.

### SA21-L06 — Google eligible automated route

Owns one legitimate automated Google route or an explicitly approved fully integrated equivalent replacement.

Exit gate: eligible official API, independently verified provider-authorized browser route, or equivalent canonical replacement is genuinely live; analyst-opened links alone do not satisfy the gate.

### SA21-L07 — Current-generation GDELT provider activation

Owns all provider activation for current-generation GDELT:

- official current contract;
- endpoint/product generation;
- schemas/query semantics;
- quotas/failure behavior;
- storage/use/retention terms;
- Source Governance;
- adapter/runtime/checkpoints;
- controlled real-provider live proof.

Exit gate: a current provider-specific production path is fully integrated and live-tested, or the capability is explicitly excluded/replaced under the standard terminal outcomes.

Dependency rule: SA-18 may consume GDELT-derived news/CTI evidence only after this microlot establishes the provider path. SA-18 does not own GDELT provider activation.

## Corporate/regulatory/relationship microlots

### SA21-L08 — Corporate and regulatory first-party acquisition

Owns:

- official corporate disclosures;
- official regulatory change notices.

Work must decompose generic families into concrete first-party/provider-specific acquisition paths and retain analyst review where semantic interpretation is source-specific.

### SA21-L09 — Relationship evidence acquisition

Owns:

- official relationship disclosures;
- public partner directories;
- public case studies;
- public certificate relationship metadata where relationship semantics are explicit.

The microlot must preserve `claimed` versus `contracted/current` truth, chronology and independence. Directory presence, marketing language or certificate issuance alone must not be promoted into current commercial incumbency.

## Licensed-data microlots

### SA21-L10 — Licensed corporate news

Owns concrete licensed corporate-news provider selection, commercial/customer-facing rights, fields, attribution, retention, credentials, quotas, adapter/runtime controls and controlled live proof.

### SA21-L11 — Commercial licensed dataset disposition

Owns decomposition of the historical generic commercial dataset family into concrete useful providers/datasets.

Each selected provider must receive lawful-purpose review, field restrictions, customer-facing rights, retention/deletion rules, adapter/runtime design and live proof. If no concrete useful provider remains justified, the product owner must explicitly exclude the generic family rather than leave it permanently blocked.

## SA21-L12 — Final orphan and ownership audit

After L01-L11 dispositions are complete, generate a machine-derived audit covering all historical Source Activation records and useful OSINT Framework candidates.

Required output fields include:

- canonical capability/provider;
- historical source/wave;
- current owner SA/lot;
- adapter present;
- authorized deployment path;
- executable;
- scheduled/invokable;
- live tested;
- remaining prerequisite;
- terminal disposition;
- evidence supporting replacement/duplicate/exclusion where applicable.

Exit gate: no useful historical capability remains `manual`, `blocked`, `planned`, adapter-only or otherwise unfinished without an explicit open remediation owner.

## Sequencing

Recommended order:

1. L01 independent search redundancy;
2. L02-L07 provider-specific search/news recovery based on legitimate prerequisite availability;
3. L08-L09 corporate/regulatory/relationship provider decomposition;
4. L10-L11 licensed-provider decisions and activation;
5. L12 final orphan audit.

Provider prerequisite availability may change the execution order, but it must not remove or silently close any item.
