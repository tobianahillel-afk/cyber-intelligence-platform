# Lots 01–05 — Final Audit and Ownership Lock

## Status

`FINAL_AUDIT_COMPLETE_IMPLEMENTATION_PENDING`

Tracker: issue #173.  
Recovery branch: `agent/lots-01-05-finality-recovery`.  
Audit baseline: `8d7184b8a6f494ceb407ab489d8971f4d015bab6` (`main`, 2026-08-17).

This document is the final pre-implementation audit of historical Lots 01–05. It amends the initial recovery audit where this deeper review found additional scope or a more precise historical acceptance requirement.

If this document and the earlier `LOTS_01_05_IMPLEMENTATION_GAP_AUDIT.md` differ on a recovery requirement, this final audit is authoritative for issue #173. The numbered product roadmap itself remains governed by `docs/PROJECT_DELIVERY_PLAN.md`.

## Audit objective

The audit answers four questions for each historical lot:

1. What was actually expected by the original issue/roadmap, not merely what the merged PR happened to implement?
2. Does the current runtime implement that expected behavior to the intended production boundary?
3. If not, is the missing behavior a local Lots 01–05 recovery defect or is there already a later canonical owner?
4. Is every residual now represented by exactly one implementation/recovery owner, one later owner, a terminal proof, or an explicit exclusion?

The audit does **not** assume that a closed historical issue means the intended end state is complete. It also does not reopen later capabilities that were deliberately deferred and are now implemented or explicitly owned elsewhere.

## Sources inspected

The final audit re-read and compared:

- the authoritative current delivery plan for Lots 01–05;
- historical issues #2, #4, #17 and #19 and their implementation PRs;
- historical deferred issues #3, #5 and #6 plus current ownership reconciliation comments;
- current collection scheduler/worker/lease/checkpoint runtime;
- current TED Search client, collector, schema and mapper;
- current BOAMP client, collector, schema and mapper;
- current opportunity lifecycle, review, score-override and API paths;
- current product metric policy;
- later canonical ownership in Lots 25, 28, 29, 30, 31 and Source Activation.

## Final conclusion

The historical Lots 01–05 are **not empty or placeholder implementations**. Their core architecture and first production source paths are real and remain valid foundations. However, the final audit confirms that they were not fully final against the stronger end-state expected for production completeness.

The final ownership register contains:

- **7 active recovery findings**: F01–F07;
- **1 terminal historical deferred finding already implemented elsewhere**: F08;
- **2 explicit later-owner findings**: F09–F10;
- no currently known ownerless Lots 01–05 residual after this ownership lock.

R01-L08 must still perform a final code-level re-audit after implementation; therefore this document is a final **pre-implementation scope audit**, not a claim that the fixes themselves are already complete.

---

# Lot 01 — Core architecture, persistence, provenance and governance foundation

## Intended boundary

Lot 01 was expected to establish the modular architecture, PostgreSQL/Alembic persistence, provenance/freshness/retention/suppression foundations, source-account lifecycle, typed API/UI shell and measurable product-governance targets.

## Current assessment

### Proven sufficiently complete for the historical boundary

The final audit did not identify a new standalone Lot01 runtime defect requiring its own recovery micro-lot.

The modular/persistence/provenance foundations are used by later modules rather than remaining scaffolding. PostgreSQL is the system of record; migrations, retention/suppression primitives, source governance and provenance fields are all real runtime concepts.

Optional Redis/OpenSearch scale/read-model infrastructure is **not** considered a missing Lot01 implementation. The current architecture deliberately treats those systems as optional/rebuildable projections rather than mandatory system-of-record dependencies.

### Provenance strengthening inherited by R01-L03

Lot01's provenance principle is affected by F02: scheduled collection jobs preserve the resolved runtime values but not an exact stable schedule identity/revision/fingerprint. The technical owner is Lot02/recovery R01-L03 because the defect sits in scheduling, but closing R01-L03 also strengthens the Lot01 provenance promise.

### Product metrics are defined, but measurement belongs with Lot03/Lot25

`policies/product_metrics.yml` already defines product targets including precision@10, opportunity acceptance rate and false-positive rate. The missing **first measured ground-truth baseline** is an explicit Lot03 acceptance requirement and is therefore handled by F06/R01-L07, with production calibration/feedback remaining Lot25.

### Historical deferred privacy capability

End-to-end privacy-rights operations were intentionally beyond the original primitive suppression foundation. They are not ownerless: F09 records Lot31/#5 as the single implementation owner.

## Lot01 final disposition

**Historical bounded core: `TERMINAL_ALREADY_PROVEN`.**  
No new standalone local recovery finding.  
Cross-cutting provenance enhancement: F02/R01-L03.  
End-to-end privacy rights: F09 -> Lot31/#5.

---

# Lot 02 — Scheduler, worker, leases, checkpoints, retries and recovery

## Intended boundary

The historical scheduler/worker lot required persisted idempotent jobs, versioned schedules, bounded leases, restart/concurrency safety, transactional checkpoints, replay safety, retries/circuits/dead letters, source lag/freshness and safe recovery.

## F01 — Healthy long-running work can outlive its lease without driving heartbeat

**Severity:** high.  
**Disposition:** `RECOVERY_LOCAL`.  
**Owner:** R01-L02.

The durable queue already implements a heartbeat primitive and ownership checks. The ordinary worker, however, claims the job, leaves that transaction and executes `adapter.collect(...)` without driving lease renewal during the potentially long external operation.

Consequences:

- healthy work can exceed the initial lease;
- another worker can recover/reclaim the same logical job;
- duplicate external work may occur before stale completion is rejected;
- current final ownership validation prevents some stale writes but does not provide single-owner execution finality.

R01-L02 must wire the existing heartbeat primitive into ordinary execution and add cooperative stop boundaries for looped provider/browser work. It must not create another queue/lease implementation.

## F02 — Schedule versioning exists only as resolved values/file schema, not exact trigger revision lineage

**Severity:** high auditability/replay gap.  
**Disposition:** `RECOVERY_LOCAL`.  
**Owner:** R01-L03.

The original Lot02 language required versioned schedules. Current schedule loading validates a schedule-file schema version and copies cadence/lease/retry values into jobs, but it does not persist a stable `schedule_id`, schedule revision and canonical fingerprint identifying the exact schedule definition that caused a historical job to exist.

R01-L03 must add stable schedule identity/revision/fingerprint provenance, a reversible migration, legacy-row semantics and tests showing that schedule v1 and v2 remain distinguishable historically.

## Historical deferred capabilities from the scheduler phase

The early collection PR deliberately separated browser/download, privacy and supply-chain work. Those reports must remain visible in the final audit rather than disappearing because the scheduler itself later became stable.

### F08 — Browser isolation and download quarantine

**Disposition:** `TERMINAL_ALREADY_PROVEN`.  
**Historical tracker:** #3.  
**Terminal owner/proof:** SA16.

The browser/authentication programme subsequently implemented isolated Chromium, challenge pause/resume, controlled downloads/quarantine and related runtime behavior. This must not be rebuilt in R01.

The residual DNS-resolution-pinning/rebinding concern from the browser work is separately owned by Lot30/#169 and is already represented by the existing `dns_address_safety_and_broad_resilience` handoff.

### F09 — End-to-end privacy rights/deletion/non-resurrection

**Disposition:** `OWNED_BY_EXISTING_LATER_SCOPE`.  
**Owner:** Lot31.  
**Tracker:** #5.

The tracker remains open intentionally until the complete rights-request workflow, downstream deletion/correction/restriction propagation, restore non-resurrection and audit/SLA gate are implemented.

### F10 — Lockfiles, deterministic release supply chain, SBOM/attestation and repository protection

**Disposition:** `OWNED_BY_EXISTING_LATER_SCOPE`.  
**Owner:** Lot29.  
**Tracker:** #6.

This was missing from the first version of the R01 manifest and is now explicitly restored. It includes deterministic Python/npm dependency resolution, lockfiles, `npm ci`/locked Python installs, SBOMs, attestation/signing, branch/repository protection, secret scanning, release/rollback/rotation runbooks and the historical Starlette/TestClient dependency-maintenance path.

## Lot02 final disposition

Local recovery: F01 -> R01-L02, F02 -> R01-L03.  
Historical deferred: F08 complete via SA16, F09 -> Lot31/#5, F10 -> Lot29/#6.  
No additional ownerless queue/checkpoint/retry/circuit defect was found in this final audit.

---

# Lot 03 — Opportunity engine, analyst Inbox, review actions and measurable quality

## Intended boundary

The original opportunity issue required a live backend-fed Inbox, evidence-linked opportunities, versioned rules, explainable/freshness-aware scoring, analyst qualification/rejection/snooze/enrichment actions, ability to modify score components, E2E signal->opportunity->review behavior, product metrics including precision@10/acceptance/false positives, and a first measurement on a ground-truth set.

## What is actually implemented and must not be reimplemented

The current opportunity runtime already contains:

- opportunity lifecycle/state;
- evidence-linked signals/opportunities;
- versioned score/config components;
- analyst reviews/actions including qualification, rejection, snooze and enrichment request;
- score override persistence/API;
- protected API/UI paths.

Those are **not** recovery gaps.

## F06 — Ground-truth and first product-quality measurement were never closed to the original acceptance boundary

**Severity:** high commercial-quality proof gap.  
**Disposition:** `SPLIT_RECOVERY_AND_HANDOFF`.  
**Recovery owner:** R01-L07.  
**Advanced owner:** Lot25.

The first recovery draft correctly identified the absence of a labelled evaluation corpus, but this final audit tightens the requirement: the original acceptance criteria explicitly required product-quality metrics and the first ground-truth measurement.

R01-L07 must therefore deliver, at minimum:

- one versioned safe labelled benchmark contract/corpus;
- positive, negative, ambiguous and research-only cases;
- deterministic baseline evaluation;
- **precision@10** measurement with defined ranking/tie semantics;
- **false-positive rate** measurement;
- **opportunity acceptance-rate** computation/measurement where review labels/sample semantics are valid;
- currentness/false-urgency and ambiguous-overpromotion checks where useful;
- sample-size handling consistent with the product metric policy;
- one reproducible baseline artifact/result in CI or closeout evidence;
- a regression test proving an intentionally degraded rule/ranking is detected;
- a clear handoff contract so Lot25 reuses the same label/benchmark semantics rather than defining a second truth system.

R01-L07 must **not** claim the production scoring system is calibrated merely because this historical baseline exists.

Lot25 remains owner of:

- calibration datasets informed by analyst outcomes;
- service/segment-specific calibration;
- production score-version comparison;
- overrides/outcome feedback workflow beyond the historical review primitives;
- drift/bias/false-positive monitoring and recalibration operations.

## Lot03 final disposition

Core opportunity workflow/actions/overrides: already implemented.  
Missing historical quality proof: F06 -> R01-L07.  
Advanced production calibration: Lot25.  
No second opportunity/feedback engine may be created by recovery.

---

# Lot 04 — TED procurement acquisition

## Intended boundary

The historical TED issue required official TED Search API collection, targeted cyber queries with bounded pagination, strict response validation, deterministic incremental checkpointing, provenance, buyer resolution, public-tender signals/opportunities, replay safety and accurate documentation of actual collection limitations.

The final audit finds this lot materially less final than its historical closed status suggests.

## F03 — TED collection is page-1 bounded and cannot prove complete incremental traversal

**Severity:** critical.  
**Disposition:** `RECOVERY_LOCAL`.  
**Owner:** R01-L04.

The current client hard-codes page 1 with a 100-record limit, and the collector invokes that client once. If more relevant records exist before the prior checkpoint is reached, ordinary collection cannot traverse them.

R01-L04 must implement a provider-supported, bounded, resumable full traversal strategy rather than merely adding a `page=2` loop. At implementation time the current official TED Search pagination/iteration contract must be verified and represented explicitly in tests/checkpoints.

Required proof includes:

- multi-page or provider-cursor/iteration traversal well beyond one page;
- request/page/record/time budgets;
- safe partial progress;
- duplicate/reordered boundary handling;
- interruption/resume convergence;
- source mutation during traversal;
- no committed high-watermark ahead of untraversed records.

## F07 — TED query scope and high-watermark ordering are not strong enough for deterministic incremental finality

**Severity:** critical.  
**Disposition:** `RECOVERY_LOCAL`.  
**Owner:** R01-L04 together with F03.

This is a distinct gap found only by the final audit.

Current TED collection:

- uses a broad query with `scope=ALL` and no explicit provider-side active/recent time/deadline boundary;
- does not request an explicit stable sort/order in the client payload;
- then treats the first returned notice as the latest high-watermark candidate;
- uses only `latest_publication_number` as the historical checkpoint.

That means the implementation cannot currently prove that `response.notices[0]` is the deterministic newest record for every run, nor that a large `ALL` result set will encounter the previous checkpoint within bounded work.

R01-L04 is normatively amended to include F07. The final design must:

1. verify the current official TED Search ordering/filter/pagination or iteration guarantees;
2. establish an explicit deterministic sort/high-watermark contract, or use a provider iteration/cursor mechanism that does not rely on an implicit first-row ordering assumption;
3. define provider-side recent/active/incremental query boundaries or deterministic time/query partitions sufficient to make bounded collection complete for the intended acquisition scope;
4. version checkpoint state and query-plan identity;
5. overlap/deduplicate where provider mutation/snapshot guarantees require it;
6. prove that a restart cannot skip records that were behind an uncommitted frontier;
7. keep historical/backfill needs separate from current incremental collection while allowing eventual convergence.

The historical wording “pagination bornée” is therefore not satisfied merely by one bounded page; the recovery must close both traversal and deterministic incremental-frontier semantics.

## F04 — TED discovery taxonomy and relevance admission are underdeveloped

**Severity:** high.  
**Disposition:** `RECOVERY_LOCAL`.  
**Owner:** R01-L05.

Current TED transport contains its own static cyber query while the canonical service taxonomy already owns the complete service-family vocabulary. The mapper then admits/drops notices primarily from the notice title even though selected structured procurement metadata can provide materially better relevance evidence.

R01-L05 must deliver:

- versioned provider-aware query plan;
- coverage across all canonical cyber service families relevant to procurement;
- deterministic query partitioning if provider query-size/syntax requires it;
- no unmanaged second taxonomy in TED transport;
- relevance assessment across reviewed title/contract title/CPV/descriptors or other approved selected fields;
- explicit matched fields/families/rule version;
- multilingual fixtures;
- negative fixtures for physical/non-cyber `security`;
- dedup when several query partitions match one publication.

This improves deterministic discovery/relevance, not calibrated opportunity ranking. Lot25 remains calibration owner.

## Controlled live proof

Deterministic fixtures and integration tests do not by themselves prove the current real provider remains usable. Controlled current-provider validation/completeness remains a Source Activation responsibility (SA20 or the currently authoritative successor if the activation roadmap changes before implementation).

## Lot04 final disposition

F03 -> R01-L04.  
F07 -> R01-L04 (new final-audit amendment).  
F04 -> R01-L05.  
Controlled live provider proof -> Source Activation.  
This is the historical lot with the largest finality gap among 01–05.

---

# Lot 05 — BOAMP acquisition and executable architecture gates

## Intended boundary

The BOAMP lot required official/public BOAMP collection, bounded fields/pagination, incremental checkpointing, procurement publication-type distinctions where available, buyer/evidence/signal/opportunity projection, provenance/idempotence/freshness, error classification and executable architecture/code-size/coverage gates.

## What is already materially stronger than TED

BOAMP already has deterministic ordering and true page traversal up to a configured safety budget. Its relevance mapper also uses broader searchable procurement text rather than a title-only test. The final audit found no evidence supporting a fabricated TED-equivalent taxonomy defect for BOAMP.

The architecture/code-structure gates are also real repository tests and are not reopened by recovery.

## F05 — Dense windows terminate safely but do not converge automatically

**Severity:** high under current full-finality expectations.  
**Disposition:** `RECOVERY_LOCAL`.  
**Owner:** R01-L06.

Current behavior pages in bounded 100-record chunks and intentionally raises a typed window error rather than silently truncate when the configured page budget is exceeded. That was a defensible safety boundary at the time of the historical lot.

Under the current source-completeness/finality target, however, the terminal behavior is insufficient because the same valid dense window can remain forever uncollected.

R01-L06 must retain boundedness while adding deterministic adaptive partition/frontier semantics.

Mandatory edge case: if one calendar day itself contains more than the old page/window budget, splitting only by date is not sufficient. Implementation must verify and use a provider-supported stable secondary key/range or another valid traversal strategy; otherwise it must surface a concrete provider limitation/activation prerequisite rather than falsely claim complete convergence.

Required proof:

- old normal sparse behavior unchanged;
- >old-budget multi-day collection converges;
- >old-budget same-day case is solved by a real supported strategy or explicitly blocked with exact provider reason/owner;
- interruption/resume from partition frontier;
- provider mutation/overlap dedup;
- typed bounded safety ceiling if adaptive partition depth itself is exhausted;
- final canonical output equals uninterrupted traversal.

## Lot05 final disposition

F05 -> R01-L06.  
No additional supported BOAMP local defect found in the final audit.  
Controlled real-provider live proof remains Source Activation where not already current/proven.

---

# Final finding register

| ID | Historical scope | Finding | Final owner | Disposition before implementation |
|---|---|---|---|---|
| F01 | Lot02 | long-running worker does not drive lease heartbeat | R01-L02 | recovery local |
| F02 | Lot02/Lot01 provenance | no stable schedule ID/revision/fingerprint lineage | R01-L03 | recovery local |
| F03 | Lot04 | TED single-page collection / incomplete bounded traversal | R01-L04 | recovery local |
| F04 | Lot04 | TED duplicated query vocabulary + title-only relevance | R01-L05 | recovery local |
| F05 | Lot05 | BOAMP dense window safely fails but does not converge | R01-L06 | recovery local |
| F06 | Lot03 | no labelled first ground-truth measurement/KPI baseline | R01-L07 + Lot25 | split recovery/handoff |
| F07 | Lot04 | TED implicit ordering/high-watermark + unbounded `ALL` query scope | R01-L04 | recovery local |
| F08 | Lot02 historical deferred | isolated browser/download quarantine | SA16 | terminal already proven |
| F09 | Lot01/02 historical deferred | complete privacy-rights/deletion/non-resurrection | Lot31 / #5 | later owner locked |
| F10 | Lot02 historical deferred | deterministic supply chain/release/repo protection | Lot29 / #6 | later owner locked |

## Existing cross-cutting later handoffs preserved

The recovery manifest must also continue to preserve:

- advanced scoring/calibration/feedback -> Lot25;
- platform-wide derived-state reconciliation/reactive invalidation -> Lot28/#171;
- supply-chain/release provenance/repository protection -> Lot29/#6;
- DNS/address safety and broader resilience -> Lot30/#169;
- privacy rights/deletion/non-resurrection -> Lot31/#5;
- residual real-provider live proof/completeness -> Source Activation/SA20 or the authoritative successor at implementation time.

## Explicit non-gaps

The final audit deliberately does **not** create work for the following because the evidence does not support calling them unfinished Lots 01–05 requirements:

- optional Redis/OpenSearch scale read models;
- a new Opportunity Inbox/review workflow (already present);
- a second score-override mechanism (already present);
- a second Chromium/browser/download runtime (SA16 already owns/completed it);
- a separate BOAMP taxonomy engine mirroring TED's defect;
- a second cross-module event/outbox architecture (Lot28 owns it);
- production analyst-feedback calibration inside R01 (Lot25 owns it).

## Normative amendments to existing R01 micro-lots

### R01-L04 amendment

R01-L04 owns **both F03 and F07**. It may not close after merely adding multi-page calls. It must prove deterministic query scope, ordering/high-watermark semantics, traversal, checkpoint/frontier versioning, interruption/restart and provider-mutation convergence.

### R01-L07 amendment

R01-L07 owns the historical first-measurement requirement. It must compute/reproduce precision@10, false-positive rate and opportunity acceptance-rate semantics where the benchmark/review sample supports them, enforce sample-size/unknown semantics, record a first baseline and detect an intentionally degraded ranking/rule.

### R01-L08 amendment

The final adversarial closeout must verify not only recovery-local F01–F07 but also that F08 remains terminally satisfied by SA16 and F09/F10 remain explicitly owned by their still-open future trackers. It must fail if any later-owner issue is silently closed, renamed or removed without equivalent implemented proof/ownership.

## Final ownership verdict

After this final pre-implementation audit:

- every currently identified Lots 01–05 defect has an implementation owner;
- every historical deferred capability has a terminal proof or explicit later owner;
- the previously missing Lot29/#6 handoff is now part of the final scope;
- the newly identified TED incremental-query/high-watermark defect is owned by R01-L04;
- the Lot03 metric requirement is now explicit rather than implied;
- no known finding is left in generic `later`, `manual`, `blocked`, `future hardening` or ownerless state.

This verdict locks **scope and ownership only**. Runtime completion remains pending until R01-L01–L07 are implemented and R01-L08 passes on the exact final SHA.
