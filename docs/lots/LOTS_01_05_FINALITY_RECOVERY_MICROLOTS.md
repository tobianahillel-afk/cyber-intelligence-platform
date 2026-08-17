# Lots 01–05 — Finality Recovery Micro-Lots

## Status

`PLANNED_LOCKED`

Parent: `LOTS_01_05_IMPLEMENTATION_FINALITY_RECOVERY.md`.  
Gap audit: `LOTS_01_05_IMPLEMENTATION_GAP_AUDIT.md`.  
Tracker: issue #173.

## Execution principles

This document is the implementation sequence for the corrective recovery overlay. Each micro-lot must be independently reviewable and own one coherent result. A micro-lot may refine exact file names after code review, but may not weaken the semantic requirement or move a known gap into an unnamed future state.

Every implementation PR states: findings owned; code surfaces; migration impact; failure/recovery behavior; tests by category; rollback/disablement; exact final SHA/CI; newly discovered adjacent gaps; and updated #173 disposition.

## Sequence

```text
R01-L01  exhaustive audit registry + ownership freeze
   |
   +--> R01-L02  long-running lease heartbeat integration
   +--> R01-L03  schedule identity/revision provenance
   +--> R01-L06  BOAMP adaptive dense-window recovery
   `--> R01-L04  TED complete bounded pagination
           -> R01-L05  TED versioned discovery/relevance

R01-L07  Lot03 labelled evaluation foundation + Lot25 contract

all completed/handoffs frozen
   -> R01-L08  adversarial cross-lot qualification + closeout
```

L02, L03 and L06 may proceed independently after L01. L04 precedes L05 because TED checkpoint/collector contracts may change. L07 may proceed after L01 but its final handoff must be reconciled against the current Lot25 contract before L08. L08 is terminal.

---

# R01-L01 — Exhaustive requirement/runtime audit and ownership registry

## Objective

Create the authoritative recovery finding registry and prove that every original Lots 01–05 promise, later accepted limitation and newly discovered runtime gap has one explicit disposition before implementation starts.

## Required work

### Historical requirement matrix

For every Lot 01–05 enumerate: roadmap outcome; surviving historical deliverables/closeout evidence; current runtime surfaces; relevant current normative standards; source-activation vs normal-product boundary; accepted limitations and their current owner/state.

### Finding registry

Every row records at minimum:

```text
finding_id
historical_lot
capability
expected_invariant
current_runtime_path
observed_gap_or_proof
severity
local_vs_handoff
canonical_owner
tracker
implementation_micro_lot
required_tests
terminal_disposition
verification_sha
```

### No-orphan executable gate

Add a deterministic repository validation, preferably over the explicit YAML manifest, that proves every open finding has one recognized owner and one implementation/handoff path; forbidden placeholder terminal states fail CI.

### Runtime tracing

At minimum re-audit persistence/provenance; scheduler/enqueue/claim/lease/adapter/persistence/checkpoint/health; retries/dead letters/circuits; Lot03 opportunity score/rules/persistence/API; TED request/pagination/mapping/checkpoint; BOAMP request/pagination/window/checkpoint; source-policy/portfolio state where later work changed early assumptions.

## Primary surfaces

```text
docs/lots/LOTS_01_05_*.md
docs/lots/lots_01_05_recovery_findings.yml
tests/architecture/test_lots_01_05_recovery_ownership.py
```

No production migration expected.

## Required tests

- duplicate finding IDs rejected;
- unknown owner/disposition rejected;
- forbidden terminal placeholders rejected;
- every recovery-local finding maps to one micro-lot;
- every handoff names a real roadmap/SA owner;
- historical Lots 01–05 statuses remain unchanged.

## Exit gate

One exhaustive, reviewable ownership register exists and every discovered issue is traceable from invariant to owner and final proof.

---

# R01-L02 — Long-running collection lease heartbeat and cooperative stop

## Finding

F01.

## Objective

Guarantee that a legitimately long collection remains owned by one worker while healthy, and lease loss prevents stale execution from becoming successful platform state.

## Reuse first

The repository already has lease owner/expiry columns, expired-lease recovery, `heartbeat_job(...)`, `owned_running_job(...)` and `LeaseLostError`. Reuse them. Do not create a second queue.

## Target runtime

```text
worker claims job
-> start lease guard/heartbeat
-> adapter collection runs
-> heartbeat renews before safety margin
-> healthy renewal: continue
-> lease lost/dependency failure:
     cancellation becomes monotonic
     no new provider page/request begins after next cooperative boundary
     no success/checkpoint advancement
-> stop heartbeat
-> final owned completion transaction
```

Heartbeat interval derives from claimed lease duration and leaves a deterministic safety margin; it is injectable for tests.

If adapters need cancellation awareness, introduce an application-level execution-control contract (`assert_active`, `checkpoint_boundary`, or equivalent) without SQLAlchemy imports. Pagination/browser loops should check it at bounded natural boundaries. Short indivisible calls retain stale-completion protection.

## Lease-loss semantics

- no success completion;
- no successful checkpoint advance;
- no success health/value event;
- stale worker may not mutate a newly claimed execution;
- safe partial progress only through existing ownership-checked partial contract;
- crash stops heartbeat and allows eventual reclaim.

## Primary surfaces

```text
src/cip/modules/collection_orchestration/application/worker.py
src/cip/modules/collection_orchestration/application/ports.py
src/cip/modules/collection_orchestration/infrastructure/repository_queue.py
src/cip/modules/collection_orchestration/infrastructure/repository_common.py
src/cip/modules/collection_orchestration/domain/models.py
optional: application/lease_guard.py
```

## Migration

Prefer none. Add durable heartbeat/fencing fields only if concurrency analysis proves existing fields insufficient; any such migration is additive/reversible.

## Required tests

- long fake adapter > original lease retains ownership with heartbeat;
- second worker cannot reclaim healthy job;
- wrong/expired owner cannot renew;
- forced heartbeat loss returns `LEASE_LOST` and no success/checkpoint advance;
- adapter loop observes cancellation before next simulated request;
- process/heartbeat stop permits later reclaim;
- human checkpoint stops guard cleanly;
- retry/partial/dead-letter paths preserve ownership;
- PostgreSQL concurrent renew/claim boundary has one winner.

## Observability

Safe metrics: renewal count/failure, lease safety margin, lease lost during collection, execution cancelled before next provider operation. Never log provider payloads/secrets.

## Exit gate

A job may exceed its initial lease without concurrent healthy execution, and a stale worker cannot produce successful platform state after ownership is lost.

---

# R01-L03 — Stable schedule identity, revision, fingerprint and trigger provenance

## Finding

F02.

## Objective

Make every new scheduled job explain exactly which schedule definition/revision caused it to be created.

## Domain contract

Add or compose immutable schedule provenance containing at minimum:

```text
schedule_id
schedule_schema_version
schedule_revision
schedule_fingerprint
source_id
adapter_id
interval/cadence
lease
retry/circuit config
enabled state
bundle/path identity where safe
```

Fingerprint uses canonical serialization of every execution-affecting field and never contains secrets.

## Trigger provenance

Distinguish scheduled cadence from manual/priority origin when supported. Retry/reclaim stays lineage of the original job, not a new trigger.

For scheduled jobs persist:

```text
trigger_kind = scheduled
schedule_id
schedule_revision
schedule_fingerprint
scheduled_for
```

## Persistence/migration

Expected additive job provenance fields (or a normalized schedule-revision table if clearly superior): `trigger_kind`, `schedule_id`, `schedule_revision`, `schedule_fingerprint`. Historical rows remain readable; do not fabricate old fingerprints that cannot be proven.

Schedule YAML gains stable IDs and revision semantics; duplicate IDs rejected across bundles.

## Primary surfaces

```text
src/cip/modules/collection_orchestration/domain/models.py
src/cip/modules/collection_orchestration/application/scheduler.py
src/cip/modules/collection_orchestration/infrastructure/schedule_loader.py
src/cip/modules/collection_orchestration/infrastructure/schedule_bundle.py
src/cip/modules/collection_orchestration/infrastructure/models.py
src/cip/modules/collection_orchestration/infrastructure/repository_queue.py
checked-in collection schedule YAML
alembic/versions/<revision>_collection_schedule_provenance.py
```

## Required tests

- fingerprint stable for semantically identical config and YAML key reordering;
- fingerprint changes when execution behavior changes;
- duplicate schedule ID rejected;
- v1/v2 schedule chronology preserved in jobs;
- legacy jobs remain readable with explicit unknown legacy provenance;
- scheduling idempotency remains correct;
- bundle-level duplicate ID rejected;
- persistence round-trip and migration upgrade/downgrade/upgrade.

## Exit gate

Any new scheduled job can be traced deterministically to its exact schedule identity, revision and execution-affecting configuration.

---

# R01-L04 — TED bounded complete pagination and resumable traversal

## Finding

F03.

## Objective

Consume all relevant TED results within explicit bounded work instead of only page 1, with replay-safe interruption/resume.

## Client

Replace page-1-only `fetch()` with an explicit current-provider page/cursor request such as `fetch_page(page_number, page_size, query_plan)`. During implementation verify the current TED API contract; do not assume undocumented pagination semantics.

Keep approved host/path, content type, byte limit and HTTP classification; add explicit page/size bounds.

## Collector

1. authorize before network;
2. fetch first page;
3. detect prior checkpoint;
4. continue while checkpoint not reached, provider has more data and budgets remain;
5. map deterministically;
6. deduplicate across boundaries;
7. advance durable high-watermark only when skipped/untraversed records cannot exist;
8. use existing partial-execution path on a safe later-page failure.

## Checkpoint

Evolve JSON checkpoint to a versioned in-progress scan contract. Conceptually it may include:

```text
checkpoint_version
previous_committed_high_watermark
scan_anchor/high_watermark
a resume page/cursor/query partition
query_plan_version
```

Invariant: **never advance the committed high-watermark past records an interrupted run has not safely traversed**.

Tests must model provider mutation during pagination. Use overlap/dedup or stable ordering appropriate to the real TED contract; page numbers must not be treated as snapshots unless provider guarantees it.

## Budgets

Page/record/request/time ceilings explicit and configurable. Budget exhaustion before safe completion is typed/resumable, never silent success.

## Primary surfaces

```text
src/cip/adapters/sources/ted_search/client.py
src/cip/adapters/sources/ted_search/collector.py
src/cip/adapters/sources/ted_search/schemas.py
src/cip/modules/collection_orchestration/application/ted_adapter.py
TED fixtures/contracts + worker partial-progress integration tests
```

No DB migration expected; checkpoint compatibility mandatory.

## Required tests

- >200 records/three pages consumed;
- checkpoint on page 2/3;
- short/empty last page;
- duplicate boundary record;
- page-2 429/5xx -> resumable partial state;
- page-2 schema drift -> safe failure/no false high-watermark;
- interruption after page 1 -> no gaps/duplicates;
- records inserted/updated during traversal -> convergence under reviewed strategy;
- malformed/oversized page rejected;
- budget exhaustion explicit/resumable;
- legacy checkpoint loads safely;
- repeat complete run idempotent/not-modified.

## Exit gate

TED result sets >100 are completely traversable under bounded budgets and interrupted/retried execution converges with uninterrupted canonical output.

---

# R01-L05 — TED versioned procurement discovery and relevance completeness

## Finding

F04.

## Objective

Replace duplicated static TED keyword logic and title-only admission with one auditable, provider-aware, versioned discovery/relevance contract tied to canonical service semantics.

## Non-goal

No score calibration here. This is acquisition recall/explainability and canonical classification; Lot25 owns calibrated ranking.

## Query plan

Introduce a versioned provider-aware plan with:

```text
query_plan_id
query_plan_version
provider_syntax_version
locales/languages
service families covered
generic cyber concepts
field strategy
provider query fragments
provenance
```

Generate from or validate against authoritative taxonomy/query definitions. Do not copy another unmanaged 19-family dictionary into TED.

If one provider query cannot safely express complete coverage, use deterministic query partitions and deduplicate by canonical publication identity; query partition/version becomes checkpoint/provenance context.

## Relevance admission

Assess reviewed selected fields, not title alone: notice title, contract title, CPV/classification and other approved descriptors/types where semantically useful.

Output should expose service families, matched terms/fields, relevance basis and rule/query version. Generic titles with strong cyber metadata must be testable as relevant; physical/non-cyber security ambiguity must have negative fixtures.

Search/provider match remains acquisition context, not a high-confidence commercial need by itself.

## Primary surfaces

```text
src/cip/adapters/sources/ted_search/client.py
src/cip/adapters/sources/ted_search/collector.py
src/cip/adapters/sources/ted_search/mapper.py
src/cip/adapters/sources/procurement_signals.py
src/cip/modules/service_taxonomy/domain/classifier.py  # reuse/authoritative extension only
possible ted_search/query_plan.py
```

## Required tests

- positive discovery/relevance fixture for all 19 canonical families;
- query-plan coverage assertion;
- generic cyber title;
- physical-security false positives;
- cyber CPV + generic title;
- cyber contract title + generic notice title;
- French/English and supported locales;
- multi-family notice without duplicate publication/opportunity;
- query-plan version/provenance behavior;
- overlapping query partitions deduplicate;
- architecture guard against hidden second taxonomy where practical.

## Exit gate

TED discovery is versioned/auditable across the complete canonical cyber-service portfolio and relevance no longer depends on a title-only gate.

---

# R01-L06 — BOAMP adaptive dense-window partitioning and resumable recovery

## Finding

F05.

## Objective

Preserve BOAMP bounded-resource behavior while guaranteeing legitimate dense publication windows can be fully consumed through deterministic subwindows/key partitions.

## Preserve

Selected fields, 100-record pages, deterministic ordering, policy-before-network, schema/size checks, canonical checkpoint identity, no raw mirroring, bounded budgets.

## Partition algorithm

```text
initial effective window
-> bounded fetch/count/pages
-> checkpoint/short page reached: complete
-> dense beyond budget:
     split deterministically
     process newest bounded partition
     persist remaining frontier
     continue until every partition completes
```

Implementation must verify current BOAMP API filtering precision. If date-only filtering cannot split a >N-record single day, use a provider-supported stable secondary-key boundary/range. Do not pretend date splitting alone solves same-day overflow.

## Checkpoint/frontier

Versioned bounded JSON, conceptually:

```text
checkpoint_version
committed_high_watermark_id/date
active window/key range
pending deterministic frontier/current partition
```

Do not store unbounded provider records in checkpoint state.

Safe completed partitions may persist via existing partial-progress semantics; a later failure must resume remaining frontier. No terminal source success until required work completes.

## Primary surfaces

```text
src/cip/adapters/sources/boamp/client.py
src/cip/adapters/sources/boamp/collector.py
src/cip/adapters/sources/boamp/schemas.py
src/cip/modules/collection_orchestration/application/boamp_adapter.py
BOAMP fixtures/contracts + worker partial-progress tests
```

Prefer checkpoint evolution without DB migration.

## Required tests

- normal <500 window unchanged;
- >500 multi-day automatically partitions;
- >500 same-day requires/uses valid secondary partition strategy;
- checkpoint in later partition;
- interruption after first partition resumes frontier;
- 429/5xx mid-partition retry;
- schema drift does not advance completed high-watermark;
- overlap dedup;
- new record during traversal -> safe convergence;
- bounded partition depth/request budget prevents runaway recursion and produces typed actionable state;
- legacy checkpoint compatible;
- retried final canonical fingerprint equals uninterrupted execution.

## Exit gate

No BOAMP data is abandoned merely because it exceeds the per-run page safety budget; the adapter partitions/resumes/converges while bounded.

---

# R01-L07 — Lot03 labelled evaluation foundation and Lot25 calibration handoff

## Finding

F06.

## Objective

Make historical Lot03 opportunity rules objectively testable against labelled cases without stealing Lot25 calibration ownership.

## R01-L07 owns

- benchmark schema;
- versioned safe labelled fixtures;
- deterministic baseline evaluator/metrics;
- label provenance/rationale;
- regression thresholds appropriate to historical rules;
- Lot25 handoff contract.

## Lot25 owns

- production analyst-outcome datasets;
- service/segment calibration;
- score optimization/calibration models;
- overrides/outcome-feedback workflow;
- drift/bias/false-positive production monitoring;
- score version comparison workflows.

## Benchmark schema

```text
case_id
benchmark_version
organization fixture identity
service family
hypothesis/historical opportunity type
input evidence fixture IDs
label: positive | negative | ambiguous | research_only
expected ordering/score band when justified
label rationale
independence/corroboration setup
freshness/time context
source types
```

No real unrestricted prospect personal data.

## Minimum cases

- public tender true positive;
- cyber hiring ambiguous internalization/external buying;
- stale evidence negative/currentness;
- duplicate/syndicated evidence;
- contradiction;
- historical award without current need;
- non-cyber security false positive;
- several service families, not SIEM-only;
- missing-data case;
- weak research-only case.

Expand representative positive/negative/ambiguous coverage across canonical families where current generalized rules can consume it, while clearly distinguishing historical Lot03 behavior from later Lot24 semantics.

## Metrics

- case/coverage counts;
- precision where denominator is meaningful;
- false-positive rate;
- false-urgency/currentness rate;
- pairwise/ranking positive-above-negative checks where applicable;
- ambiguous/research-only overpromotion rate;
- explanation/evidence completeness.

Recall only when sampling supports a meaningful denominator.

## Persistence boundary

Repository benchmark fixtures are minimum recovery requirement. Do not add production analyst-label tables just to satisfy recovery if Lot25 is correct owner. A reusable pure contract may be framework-free, with persistence explicitly deferred to Lot25.

## Likely surfaces

```text
tests/fixtures/opportunity_benchmarks/v1/
tests/commercial_value/test_lot03_opportunity_baseline.py
tests/commercial_value/test_opportunity_benchmark_contract.py
optional pure evaluation helper only if genuinely reusable
```

## Required tests

- schema validation;
- duplicate case/version rejected;
- unknown label rejected;
- deterministic metrics under shuffled fixture order;
- clear positive > clear negative in supported historical scenarios;
- weak/ambiguous overpromotion detected;
- explanation references expected evidence;
- no prohibited data fields;
- Lot25 handoff references same schema/version instead of redefining it.

## Exit gate

Lot03 has a reproducible labelled baseline capable of detecting commercial-quality regressions while full calibrated scoring/outcome feedback remains truthfully unimplemented until Lot25.

---

# R01-L08 — Cross-lot adversarial qualification and no-orphan closeout

## Objective

Prove the corrective recovery closes Lots 01–05 finality problems in composition and discover any remaining hidden gap before #173 can close.

## Mandatory scenarios

### Lease/recovery

- job >2x original lease with healthy heartbeat;
- competing worker claim attempt;
- heartbeat ownership loss mid-run;
- process/heartbeat disappearance then safe reclaim;
- partial progress + lease loss;
- no duplicate successful checkpoint/opportunity.

### Schedule provenance

- schedule revision v1 creates job A;
- changed cadence/retry creates v2 job B;
- A/B remain attributable to exact revisions;
- legacy semantics explicit;
- idempotency remains correct.

### TED

- >200 records/three pages;
- checkpoint beyond page 1;
- interruption/resume;
- provider mutation during traversal;
- query-plan overlap;
- all service families represented;
- non-cyber security negatives;
- no duplicate canonical publication/opportunity.

### BOAMP

- window above old five-page ceiling;
- same-day dense boundary;
- adaptive frontier;
- interruption/retry;
- changed/new record during traversal;
- same final canonical output as uninterrupted run.

### Opportunity-quality foundation

- deterministic benchmark load;
- clear positive/negative/ambiguous currentness cases;
- baseline metrics;
- intentionally degraded historical rule is caught;
- Lot25-only calibration features remain explicitly open.

## Cross-cutting assertions

Policy before network; approved host/path; bounded work; typed errors; no secret/private leakage; no failed-ownership/incomplete traversal checkpoint success; replay no duplicates; time semantics preserved; provenance to canonical state; no new Lot28-style derived chain; no hidden second taxonomy; no weakened architecture/coverage gates.

## Final re-audit

Re-run L01 against the **final recovery head**, not baseline. Search code/docs for TODO/FIXME tied to 01–05 capability, future-hardening/manual/blocked placeholders, terminal `max_pages`/window loss, page-1 assumptions, unused heartbeat paths, unexplained schedule provenance, and overstated calibration claims. Every relevant hit gets a disposition.

Create final `LOTS_01_05_FINALITY_RECOVERY_CLOSEOUT.md` only after implementation is complete; record every finding, final disposition, PR/SHA, migration, tests, CI, remaining limitation and later owner.

## Exact-head gate

Final documentation-complete SHA must pass dependency checks/audit, Ruff, strict Mypy, architecture/release/recovery ownership tests, PostgreSQL upgrade→downgrade→upgrade, complete pytest with coverage, changed recovery-code target coverage, frontend audit/typecheck/build, and zero blocking review threads. Any later commit invalidates the proof.

## Exit gate

Issue #173 closes only when final re-audit finds no ownerless Lots 01–05 capability and every recovery-local defect is proven under adversarial composed scenarios on one exact final SHA.
