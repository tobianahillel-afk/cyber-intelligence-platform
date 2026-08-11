# Lot 24 — Signal fusion, need hypotheses, and commercial taxonomy — Closeout

**Status:** `IMPLEMENTED_VALIDATED`

**Release line:** `0.24.0`

**Implementation PR:** #121

## Outcome

Lot 24 generalizes the historical SIEM/SOC-only commercial-intelligence path into a versioned, evidence-first cybersecurity need-detection layer.

The implementation now provides:

- the 19 canonical cybersecurity service families from `docs/CYBER_SERVICE_NEED_TAXONOMY.md`;
- backward-compatible parsing and querying for historical service-family identifiers already persisted by earlier lots;
- all 12 canonical `NeedHypothesisClass` values;
- generalized `CommercialSignal` metadata for procurement, hiring, contract lifecycle, regulatory, incident, vulnerability-applicability, passive-exposure, technology, corporate, relationship, professional-context, and research-discovery signals;
- supporting, contradicting, and negative signal polarity;
- independent-source and corroboration-group handling so syndicated or duplicated evidence does not count as multiple independent confirmations;
- freshness, explicit expiry, and historical-only handling;
- confidence, urgency, horizon, applicable-offer, and rationale outputs;
- source-contribution / ablation explanations;
- multiple concurrent service-need tracks for one organization;
- a research-only weak-signal fallback that prevents discovery metadata or a single weak observation from being treated as a confirmed commercial need;
- deterministic rule and taxonomy versioning for replay;
- additive and reversible PostgreSQL persistence;
- protected list, detail, and organization recompute APIs;
- an analyst `Need Hypotheses` list and detail workspace;
- compatibility with the existing opportunity Inbox and historical SIEM/SOC generation path.

## Canonical service taxonomy

The executable service-family identifiers are:

1. `security_strategy_vciso`
2. `risk_assessment_audit`
3. `grc_compliance`
4. `penetration_testing`
5. `red_team_purple_team`
6. `vulnerability_management_asm`
7. `soc_siem_mdr_detection`
8. `incident_response_dfir`
9. `resilience_bcp_drp`
10. `iam_pam_zero_trust`
11. `cloud_security`
12. `application_security_devsecops`
13. `network_security_sase`
14. `data_security_privacy`
15. `third_party_supply_chain`
16. `ot_ics_iot_security`
17. `security_awareness_training`
18. `product_integration_migration`
19. `cyber_insurance_readiness`

Historical Lot 11 identifiers remain readable and filterable. The migration rewrites historical service-family identifiers to the canonical vocabulary while query compatibility remains tolerant during rollout and rollback.

## Canonical need-hypothesis classes

The executable hypothesis identifiers are:

1. `explicit_procurement`
2. `contract_renewal_or_replacement`
3. `program_build_or_transformation`
4. `capability_gap`
5. `incident_urgency`
6. `regulatory_deadline_or_gap`
7. `technology_risk_or_lifecycle`
8. `external_exposure`
9. `organizational_change`
10. `provider_dissatisfaction_or_transition`
11. `skills_and_training_need`
12. `research_only_weak_signal`

## Evidence and inference contract

Lot 24 preserves the evidence hierarchy:

`provider payload → RawObservation / canonical projection → Evidence → CommercialSignal → NeedHypothesis → downstream scoring/opportunity`

A source observation is not automatically a commercial fact or opportunity.

The fusion engine groups correlated signals by independent/corroboration identity before confidence aggregation. Contradicting and negative signals reduce confidence and remain visible in the persisted explanation. Expired signals are excluded. Historical incident evidence is not promoted into current incident urgency. Signals for another organization cannot produce a hypothesis for the requested organization. Discovery-only evidence is capped as research-only unless stronger evidence exists.

## Persistence and compatibility

Migration `20260810_0024_signal_fusion_hypotheses.py` is additive and reversible from `20260809_0023`.

It introduces the generalized signal-fusion and need-hypothesis fields and canonicalizes historical taxonomy values. CI validates:

`alembic upgrade head → alembic downgrade base → alembic upgrade head`

The historical SIEM/SOC generator now persists through the same generalized `store_need_hypothesis` path, preserving the existing opportunity/review lifecycle instead of maintaining a second partial hypothesis representation.

Procurement-history filtering accepts canonical and historical service-family identifiers so existing stored data and old clients remain readable during migration.

## API and analyst workspace

The backend exposes protected hypothesis list, detail, and organization recompute routes.

The Next.js analyst workspace exposes:

- filters by hypothesis class, service family, and minimum confidence;
- current, high-urgency, contested, and research-only summaries;
- rationale, confidence, urgency, horizon, service families, applicable offers, and status;
- supporting, conflicting, and negative signal counts;
- independent source-contribution groups;
- contribution/ablation values;
- rule version and taxonomy version;
- generated and expiry timestamps;
- a dedicated detail view for provenance and evidence IDs.

The UI does not autonomously create outreach. Opportunity qualification remains a downstream human-controlled action.

## Deterministic guardrail coverage

The Lot 24 suite includes deterministic checks for:

- exact canonical 19-family taxonomy;
- historical taxonomy aliases;
- positive classification for every family;
- negative-only evidence for every family producing no need;
- ambiguous/research discovery for every family staying research-only;
- exact canonical 12 hypothesis classes;
- independent-source corroboration;
- syndicated/duplicate-source grouping;
- contradiction and negative-evidence confidence reduction;
- explicit procurement;
- historical incident downgrade;
- organization isolation for vulnerability-related signals;
- expired-signal exclusion;
- multi-service concurrent tracks;
- rule-version replay identity;
- generalized persistence round-trip;
- invalid persisted source-contribution payloads failing closed;
- protected hypothesis API list/detail/recompute behavior;
- legacy Procurement and Greenhouse regression compatibility.

## Exact-head validation before documentation closeout

Implementation head `34791a81876f724bc4784d71a0925f9896957640` passed GitHub Actions run `31540268888`:

- Python dependency consistency: pass;
- Python dependency audit: pass, no known vulnerabilities;
- Ruff: pass;
- Mypy: pass across 682 source files;
- architecture and release contracts: 36 passed;
- reversible migrations: pass;
- backend tests: **1411 passed**;
- backend line+branch coverage: **90.07%**;
- frontend dependency audit: pass;
- frontend typecheck: pass;
- frontend production build: pass.

The documentation commit that adds this closeout must itself receive a final exact-head CI result before merge because any later commit invalidates an earlier validation result.

## Exit-gate decision

Lot 24 is `IMPLEMENTED_VALIDATED` once the final documentation head is green and PR #121 is merged.

No provider live-test state is changed by this lot. Source activation remains governed separately by the Source Activation roadmap beginning with SA-15.