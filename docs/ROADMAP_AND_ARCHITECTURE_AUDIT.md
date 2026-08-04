# Roadmap and Architecture Consistency Audit

## Scope

This audit reviews the product definition, accountless-access model, architecture, canonical data model, source policy, provider onboarding, OSINT catalogs, live cyber source catalog, test strategy, current branch version, completed lots, and future delivery sequence.

The objective is to ensure that the expanded source portfolio strengthens the original product goal: finding and qualifying organizations that may need cybersecurity services or products.

## Findings and resolutions

### 1. Lot 08 delivery status was stale

**Finding:** Lot 08 had already delivered organization identity in version `0.9.0`, but the roadmap and README still described it as planned or omitted its adapters.

**Risk:** Future development could duplicate organization identity work, misstate the current product baseline, or build source adapters against an outdated entity model.

**Resolution:** The roadmap now marks lot 08 `IMPLEMENTED_VALIDATED`. The README lists API Recherche d'entreprises, GLEIF, and BODACC and identifies `0.9.0` as the validated baseline.

### 2. Lot 09 number collision

**Finding:** The current provider-onboarding issue and PR used lot 09, while the old roadmap also assigned lot 09 to procurement history.

**Risk:** Two different implementations could claim the same lot number, violating the continuous immutable lot rule and breaking roadmap contracts.

**Resolution:** Lot 09 is now authoritatively assigned to provider onboarding and secret lifecycle. Procurement history moves to lot 11 after a new common source-portfolio runtime in lot 10.

### 3. Catalogs were disconnected from executable delivery

**Finding:** The OSINT and live cyber catalogs contained many useful candidates, but no shared roadmap lot converted catalog entries into capability manifests, backfills, freshness, health, schema drift, cost controls, or measurable value.

**Risk:** Each source could implement its own orchestration, checkpoint semantics, health states, and data path, creating duplication and inconsistent behavior.

**Resolution:** Lot 10 now provides the machine-readable catalog, common adapter SDK, capability registry, backfill and incremental modes, freshness, source health, schema drift, and value metadata before broad source expansion.

### 4. Source breadth was not explicitly tied to client discovery

**Finding:** Existing plans described many data families but did not require every source to explain which commercial need, service fit, alert, or opportunity it enabled.

**Risk:** The product could become a large OSINT lake with weak commercial relevance.

**Resolution:** `COMMERCIAL_INTELLIGENCE_INTEGRATION_ARCHITECTURE.md` defines a mandatory source-to-opportunity chain and business-value map. Every source must prove incremental client-finding value.

### 5. Canonical data model lacked several integration layers

**Finding:** The previous model jumped from sources and evidence to domain entities and opportunities. It did not formally describe source catalog entries, onboarding, adapter capabilities, collection runs, immutable source records, generic observations, temporal relationships, commercial signals, or need hypotheses.

**Risk:** Provider-specific data could leak into canonical models or adapters could bypass evidence and write directly to opportunities.

**Resolution:** `DATA_MODEL.md` now separates all layers and defines deterministic identities, correction propagation, temporal relationships, signal and hypothesis objects, and opportunity grouping.

### 6. Architecture data flow was too coarse

**Finding:** The previous flow used a generic observation envelope and did not show catalog, onboarding, source records, claims, contradiction handling, signal fusion, or need hypotheses.

**Risk:** Module ownership and dependency direction were ambiguous for future adapters.

**Resolution:** `ARCHITECTURE.md` now defines the full canonical component chain and prohibits provider transports from writing directly to projections.

### 7. Testing focused on code correctness more than product correctness

**Finding:** The existing strategy covered parsing, security, resilience, and scoring, but did not make source incremental value, copied-upstream detection, false urgency, backfill/incremental convergence, or source-to-opportunity behavior mandatory for every adapter.

**Risk:** A technically correct source could still create duplicate opportunities, false urgency, or no useful client signals.

**Resolution:** `SOURCE_INTEGRATION_TEST_MATRIX.md` and the revised `TEST_STRATEGY.md` add twelve source release gates, cross-source scenarios, commercial benchmarks, source ablation, and cost-per-accepted-opportunity measures.

### 8. Live threat maps and machine-readable sources were mixed

**Finding:** Visual attack maps can be useful context but often expose only one vendor's sensor telemetry and may not provide reusable structured evidence.

**Risk:** A visualization could be treated as proof that a named organization was attacked.

**Resolution:** The live source catalog separates APIs and feeds from visualization-only context. Telemetry cannot independently confirm company compromise.

### 9. Incident claims needed stronger event clustering

**Finding:** Many ransomware aggregators copy the same upstream actor post.

**Risk:** Copied reports could appear as independent corroboration and create several incidents or opportunities.

**Resolution:** Lot 14 and the canonical model require one event cluster with separate claims, upstream-dependency awareness, source independence, confirmation, denial, correction, and retraction states.

### 10. Vulnerability and exposure sequencing was ambiguous

**Finding:** Vulnerability facts, passive technology observations, vendor advisories, and organization applicability were spread across adjacent lots without a strict dependency chain.

**Risk:** The product could claim a prospect is vulnerable based on a CVE and imprecise product-family observation.

**Resolution:** Lot 13 builds vulnerability knowledge; lot 16 builds passive technology and asset observations; lot 17 performs vendor advisory and version applicability matching. Exact precision and freshness remain visible.

### 11. BrixHub was named but not placed in a safe integration phase

**Finding:** BrixHub appeared in catalogs and policy but lacked one explicit roadmap position connected to the shared runtime, entity resolution, import, deletion, and value tests.

**Risk:** It could be implemented too early as a special-case scraper or omitted despite being a named requirement.

**Resolution:** Lot 22 owns BrixHub and other conditional sources. BrixHub remains non-executable until approved, then must use historical import, incremental refresh, field allowlists, provenance, correction, deletion, and unique-value benchmarks.

### 12. LinkedIn, Discord, and public-community signals needed distinct handling

**Finding:** Professional identity, public discussion, licensed professional data, official platform APIs, and administrator-consented connectors were not clearly separated in the roadmap.

**Risk:** Weak public statements could be attributed to an employer or platform-specific collection could bypass the common evidence path.

**Resolution:** Lot 21 owns governed professional and public-community signals. Lot 22 owns official, licensed, or consented platform integrations. Public pseudonyms remain pseudonyms unless their owner publicly links them to a professional identity.

### 13. Accountless access and commercial operations needed separate trust planes

**Finding:** The product is intended to have no ordinary visitor registration, but it also contains source administration and native opportunity operations.

**Risk:** Documentation could imply that anonymous visitors can mutate sources or commercial state, or that ordinary visitor accounts are required.

**Resolution:** The architecture separates an accountless read data plane from a deployment-protected administrative and commercial control plane. Protection is an infrastructure boundary, not mandatory visitor registration.

### 14. Browser automation could block the roadmap

**Finding:** The old browser lot was deferred but appeared before release and resilience lots in a sequential roadmap.

**Risk:** A deferred lot could make later lot sequencing ambiguous.

**Resolution:** The optional isolated browser runtime is now lot 31. The pilot can proceed without it when no approved pilot source requires browser-only collection.

## Duplicate-prevention architecture

The revised design prevents duplication at seven levels:

1. source replay;
2. mutable provider record;
3. canonical observation;
4. entity and temporal relationship;
5. event cluster;
6. commercial signal;
7. opportunity and commercial motion.

A new source must identify which existing records it overlaps and prove its unique contribution before release.

## Contradiction architecture

The platform preserves rather than overwrites:

- actor claim and organization denial;
- public report and official confirmation;
- old and amended contract dates;
- current and former professional roles;
- technology provider disagreements;
- historical and current provider relationships;
- product-family and exact-version evidence;
- legal registry conflicts;
- corrections and retractions.

Derived signals and hypotheses are recalculated when the contradiction state changes.

## Revised dependency logic

```text
00-08 validated foundations
      |
      v
09 provider onboarding
      |
      v
10 common source portfolio runtime
      |
      +--> 11 procurement history
      +--> 12 corporate footprint
      +--> 13 vulnerability knowledge
      +--> 14 live incidents
      +--> 15 IOC and telemetry
      +--> 16 passive exposure
      +--> 18 business and regulatory change
                    |
                    v
17 applicability and 19 relationships
                    |
                    v
20 temporal knowledge graph
                    |
          +---------+----------+
          v                    v
21 professional context   22 conditional sources
          +---------+----------+
                    v
23 governed research
                    v
24 signal fusion and need hypotheses
                    v
25 calibrated scoring
                    v
26 commercial operations
                    v
27 company workspace
                    v
28-32 production assurance and pilot
```

## Remaining implementation risks

The documentation is now structurally aligned, but the following remain implementation work:

- lot 09 must complete and pass CI on one final SHA;
- lot 10 does not yet have code or a machine-readable catalog;
- the new canonical source-record, generic observation, signal, and need-hypothesis models are architectural targets, not all current database tables;
- no adapters from the new live cyber catalog are implemented yet beyond existing CISA KEV support;
- BrixHub remains quarantined;
- commercial-value benchmarks need labelled datasets and analyst outcomes;
- data-quality publication gates and source ablation do not yet exist;
- current CI contracts may need updates to recognize the revised roadmap and documents.

## Audit conclusion

The revised architecture keeps the product centered on client discovery while allowing a much larger OSINT and cyber-intelligence portfolio.

The key decision is to avoid implementing sources directly into opportunities. All future sources must pass through one common, testable, reversible chain:

```text
source -> record -> observation or claim -> resolution -> signal -> need hypothesis -> opportunity
```

This structure is the basis for future implementation, tests, deduplication, contradiction handling, data quality, and commercial value measurement.
