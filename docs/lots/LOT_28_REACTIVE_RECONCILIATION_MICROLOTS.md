# Lot 28 — Reactive reconciliation micro-lot decomposition

## Status

`PLANNED_LOCKED`.

Parent scope: `LOT_28_DERIVED_STATE_RECONCILIATION_RECOVERY.md`.

Tracking issue: #171.

Target release: `0.28.0`.

## Execution rule

These micro-lots are the implementation order for the cross-module finality recovery. A later micro-lot may start only when its required contracts from earlier micro-lots are stable enough to consume without creating a parallel mechanism.

Each micro-lot must:

- start from the latest merged predecessor head;
- preserve module/domain boundaries;
- use migrations for persisted contracts;
- add deterministic tests before claiming completion;
- update operator/developer documentation when behavior changes;
- pass exact-head CI;
- record any accepted limitation with a named later micro-lot or explicit exclusion.

The micro-lots are:

```text
L01 contracts/dependency registry
 -> L02 transactional outbox + queue
 -> L03 collection/backfill/replay convergence foundation
 -> L04 applicability reactor
 -> L05 relationship reactor
 -> L06 graph reactor
 -> L07 canonical-to-commercial signal synthesis
 -> L08 desired-set need-hypothesis reconciliation
 -> L09 opportunity/scoring reconciliation migration
 -> L10 time/deletion/suppression/identity invalidation
 -> L11 readiness/lineage/observability/publication gates
 -> L12 full convergence qualification and closeout
```

L04–L07 may be developed in parallel only after L01–L03 contracts are stable. L08 depends on L07. L09 depends on L08 and the Lot 25 scoring contract. L11 consumes state from all previous reactors. L12 is terminal.

---

## L01 — Canonical-change contract and dependency registry

### Objective

Create one typed vocabulary for changes that can invalidate derived state and one explicit registry mapping those changes to projectors/subjects.

### Required implementation

Add a framework-free domain/application contract equivalent to:

- `CanonicalChangeEvent`;
- `CanonicalAggregateType` or equivalent stable aggregate identifiers;
- `CanonicalChangeKind`;
- `ReconciliationProjectorId` and version;
- `ReconciliationSubject`;
- dependency routing rules;
- bounded routing metadata validation;
- stable event/idempotency key derivation.

Suggested module ownership:

```text
src/cip/modules/derived_reconciliation/domain/events.py
src/cip/modules/derived_reconciliation/domain/models.py
src/cip/modules/derived_reconciliation/application/dependency_registry.py
src/cip/modules/derived_reconciliation/application/ports.py
```

Exact names may vary; semantics may not.

### Required change kinds

At minimum:

- create/update/revise;
- correct;
- retract/withdraw/deny where relevant;
- tombstone;
- suppress;
- delete;
- attribution/identity change;
- merge/split/reversal;
- validity/expiry due;
- rule/taxonomy/config/projector version change;
- rebuild/restore reconciliation request.

### Dependency rules to encode

At minimum:

- passive technology -> applicability -> graph -> commercial signal -> hypothesis -> scoring/opportunity -> publication;
- advisory/vulnerability range -> applicability -> graph -> signal -> hypothesis -> scoring/opportunity -> publication;
- procurement contract -> relationship -> graph -> contract/relationship signal -> hypothesis -> scoring/opportunity -> publication;
- incident -> graph + incident signal -> hypothesis -> scoring/opportunity -> publication;
- corporate change -> graph + change signal -> hypothesis -> scoring/opportunity -> publication;
- relationship -> graph + relationship/renewal signal -> hypothesis -> scoring/opportunity -> publication;
- organization identity decision -> affected canonical bindings + graph + all organization-scoped derived projectors;
- professional context -> contact/relevance/publication paths; it must not independently create a high-confidence need merely because a person/role exists;
- research result -> no commercial signal until canonical provenance/evidence qualification has succeeded.

### Architecture constraints

- no FastAPI/SQLAlchemy in domain;
- no provider HTTP/browser code;
- no cross-module infrastructure imports from the registry;
- no hidden string-based projector names without validation/version ownership.

### Required tests

- deterministic event key;
- invalid/oversized routing metadata rejected;
- every registered aggregate/change kind resolves to the intended projector set;
- explicit no-op rules are testable;
- CVE-only, IOC-only, professional-role-only and weak research inputs cannot route directly to a confirmed commercial conclusion;
- architecture boundary tests.

### Exit gate

There is exactly one documented, typed, versioned dependency registry for derived-state reconciliation and no future micro-lot needs to invent private trigger semantics.

---

## L02 — PostgreSQL transactional outbox and durable reconciliation queue

### Objective

Guarantee that a committed canonical change cannot be lost between source-of-truth persistence and derived reconciliation.

### Required persistence

Add migrations for equivalent durable records:

- canonical-change outbox;
- reconciliation jobs/queue;
- optional projector/subject state if introduced here rather than L11.

Required fields include:

- UUID/event identity;
- unique idempotency key;
- event/schema version;
- source module and aggregate identity;
- bounded routing keys;
- change kind;
- effective and occurrence timestamps;
- dispatch/queue state;
- projector ID/version;
- subject type/key;
- attempts and bounded retry settings;
- lease owner/expiry;
- next attempt time;
- terminal/dead-letter state;
- safe error code and timestamps.

### Transactional rule

The outbox event is inserted in the **same PostgreSQL transaction** as the canonical write that made derived state dirty.

Forbidden patterns:

- publish after commit without durable handoff;
- in-memory-only event bus as correctness mechanism;
- network broker write that can succeed/fail independently of the canonical DB commit unless a transactional handoff still exists;
- raw provider payload copied into queue rows.

### Queue behavior

- at-least-once delivery;
- idempotent processing;
- coalescing repeated dirty events by projector+subject without losing the newest relevant version;
- leases;
- bounded exponential/backoff policy consistent with repository worker conventions;
- dead-letter and operator requeue;
- safe cancellation when a newer event supersedes obsolete queued work where deterministic;
- oldest-pending and failure metrics.

### Integration with current worker

The normal collection success/partial-progress transaction already owns canonical persistence. Add event creation inside that transaction after canonical state changes are known.

Do **not** execute all downstream projectors synchronously inside `adapter.collect(...)`.

### Required tests

- canonical transaction rollback leaves no outbox event;
- canonical commit creates the event atomically;
- duplicate insertion is idempotent;
- worker crash after DB commit but before acknowledgement is safely replayed;
- lease loss and retry;
- duplicate delivery does not duplicate downstream work;
- dead-letter/requeue;
- coalescing preserves the newest dirty version;
- migration upgrade/downgrade as required;
- PostgreSQL concurrency tests.

### Exit gate

No committed canonical change can be permanently lost because a process crashed between persistence and derived work scheduling.

---

## L03 — Unified incremental, backfill, replay and rebuild projection contract

### Objective

Remove the current divergence between incremental collection and historical backfill before additional derived reactors are added.

### Current gap to close

The incremental worker calls the common local projection persistence path, while the historical backfill worker currently persists a smaller/different set of projection families and records zero commercial/identity projections in its value event.

### Required implementation

Create one application-level batch-application service used by both incremental and backfill modes for canonical persistence.

It must:

- insert immutable source observations through the existing safe path;
- persist every canonical projection family present in the batch using the same mapper/persistence contracts;
- emit canonical-change outbox events through L02;
- record execution mode separately from truth semantics;
- preserve effective/source time independently of ingestion time;
- avoid direct current opportunity creation while replaying each historical record;
- support a bounded final reconcile after a partition/batch set completes.

### Adapter batch evolution

Do not add **derived** outputs such as applicability, graph nodes or need hypotheses to provider adapter batches.

If later Source Activation providers legitimately produce source-native relationship/professional canonical observations, extend typed canonical batch/output contracts deliberately, with data-governance review, rather than creating provider-specific direct DB writes.

### Replay ordering

Current-state result must depend on effective chronology/version semantics, not on accidental ingestion order.

Test both:

- chronological ingestion;
- reverse/shuffled ingestion.

### Historical commercial behavior

Historical data may create immutable signals/hypothesis history if the model requires it, but only current eligible state may publish current alerts/opportunities. Backfill completion must not flood the analyst Inbox.

### Required tests

- same fixture through incremental and backfill yields same canonical fingerprint;
- reverse/shuffled replay yields same current fingerprint;
- correction/retraction order is effective-time safe;
- partial partition retry is idempotent;
- canonical projections present in batch are not silently skipped by one execution mode;
- historical-only evidence does not create a current Inbox flood;
- source health/value metrics distinguish mode without changing truth.

### Exit gate

For the same effective input history, incremental and historical paths produce the same canonical dirty events and the same post-reconciliation current state.

---

## L04 — Vulnerability-applicability reactor

### Objective

Make Lot 17 applicability automatically converge when either side of the applicability join changes.

### Inputs

- passive technology/version observation create/revise/expire/suppress;
- organization/asset attribution change;
- vulnerability/advisory revision;
- affected-version range correction/withdrawal;
- support-lifecycle change when it affects assessment semantics;
- explicit rebuild/version change.

### Impact selection

Implement bounded queries/indexes that identify only affected subjects, for example:

- changed technology snapshot -> candidate vulnerabilities/advisory ranges for normalized product identity;
- changed advisory/range -> current technology observations matching product identifiers;
- changed organization binding -> assessments for affected asset/technology records.

Avoid full cross-product scans.

### Desired-state semantics

For each impacted subject:

- load current eligible technology evidence;
- load current advisory/vulnerability evidence;
- run existing domain matcher;
- persist a new immutable assessment snapshot when the result changes;
- explicitly represent expiry/withdrawal/unknown/review-required outcome when support disappears;
- emit downstream change event if current applicability projection changed.

Do not turn applicability into active validation or verified exposure.

### Data-model review

Audit whether current assessment identity `(organization, asset, vulnerability, technology_snapshot)` is stable enough for desired-state invalidation. If a new technology snapshot creates a new identity while the old projection remains apparently current, introduce a stable current-subject key or current-selection rule without deleting immutable history.

### Required tests

- new applicable version creates/updates assessment automatically;
- corrected advisory changes state automatically;
- withdrawn advisory removes current support;
- technology expiry changes assessment without a new provider write via L10 time sweep;
- organization reassignment invalidates old organization applicability and recomputes new scope;
- duplicate events are idempotent;
- no CVE-only applicability upgrade;
- history remains immutable.

### Exit gate

No current applicability result depends on an operator manually calling matcher/persistence code after an upstream current-state change.

---

## L05 — Relationship-intelligence reactor

### Objective

Wire canonical relationship sources into Lot 19 and ensure relationship current state changes automatically.

### First mandatory bridge

Wire procurement contract changes through the existing procurement-to-relationship mapping semantics.

Changes include:

- award/new contract;
- amendment;
- cancellation;
- provider/consortium/subcontractor party change;
- organization-resolution change;
- start/end/renewal date change;
- service-family context change;
- correction/replay.

### Persistence behavior

- derive relationship evidence/context from current canonical procurement projection;
- persist immutable relationship evidence revisions;
- produce retraction/correction where the upstream contract semantics require it;
- reconcile current `BusinessRelationshipRecord`;
- emit graph/signal dirty event only if current relationship projection materially changed.

### Additional source-native relationships

Future SA21/SA19/provider work may supply official relationship disclosures, partner directories, case studies or licensed relationship data. Those adapters must map to the same canonical relationship evidence contracts and must not bypass this reactor with direct graph/opportunity writes.

Weak directory/case-study evidence must retain its evidence class; it cannot be upgraded to contracted/observed relationship without supporting evidence.

### Time behavior

Relationship reconciliation is time-aware but currently occurs on write. L10 must enqueue due subjects for `valid_until`, evidence expiry, stale thresholds and renewal windows.

### Required tests

- procurement award -> active relationship;
- cancellation -> retracted/historical relationship;
- amended provider party -> old/new relationship convergence;
- changed renewal date -> current relationship/renewal state update;
- relationship validity expires without source write;
- duplicate evidence does not duplicate relationship;
- weak evidence remains weak;
- graph dirty event produced only for material current-state change.

### Exit gate

Canonical procurement and approved direct relationship evidence automatically maintain Lot 19 current state and downstream dirty state.

---

## L06 — Corporate-graph reactor and scoped refresh

### Objective

Convert Lot 20 graph refresh from an explicit correctness dependency into an automatic derived projector.

### Preserve existing strengths

Reuse existing:

- graph loaders/adapters;
- immutable node/edge snapshots;
- time-aware domain reconciliation;
- entity-resolution binding behavior;
- blast-radius fingerprints and analyst decision safety.

Do not rewrite those parts without a demonstrated defect.

### Required implementation

Add scoped graph reconciliation subjects such as:

- organization;
- relationship key;
- passive asset/technology key;
- incident key;
- corporate-change event key;
- applicability assessment/current subject.

A changed upstream subject marks only affected graph nodes/edges dirty where possible.

Keep a protected full `refresh/rebuild` operation for repair/audit, but normal correctness must not depend on an analyst/admin invoking it.

### Missing-output handling

A projector must reconcile the desired current graph set, not only upsert newly returned snapshots. When an upstream binding/snapshot disappears from the desired current representation, the corresponding graph projection must become non-current/suppressed/review-required according to domain semantics while history remains available.

### Identity changes

Merge/split/reject/reversal decisions must:

- mark affected graph subjects dirty;
- preserve immutable decision history;
- recompute organization bindings;
- enqueue downstream commercial/hypothesis subjects affected by changed attribution;
- use current blast-radius/fingerprint protection for analyst mutations.

### Required tests

- relationship change updates graph without calling HTTP refresh;
- applicability change updates graph;
- incident/change revision updates graph;
- time expiry changes graph currentness;
- identity merge/split cascades deterministically;
- stale queued work cannot overwrite a newer analyst resolution decision;
- full rebuild fingerprint equals scoped incremental result.

### Exit gate

The graph is a deterministic current projection of canonical truth, not a manually refreshed cache whose correctness depends on operator action.

---

## L07 — Versioned canonical-to-commercial signal synthesis

### Objective

Implement the missing general bridge between canonical evidence models and Lot 24 `CommercialSignal` records.

### Projector families

At minimum review and implement justified mappings for:

- procurement/open buying intent;
- contract lifecycle/renewal/replacement;
- hiring/job context;
- official/qualified incidents;
- regulatory/corporate changes;
- vulnerability applicability;
- passive exposure/technology changes where organization attribution and freshness justify a signal;
- relationship/provider transition/renewal context;
- research discoveries only after canonical evidence promotion;
- professional context primarily as role/reachability context, not independent need evidence.

### Mapping contract

Every mapping has:

- mapping rule ID/version;
- required canonical state/evidence class;
- organization-resolution requirement;
- freshness/expiry calculation;
- service-family mapping;
- hypothesis-class mapping;
- polarity;
- confidence calculation;
- independence/corroboration key semantics;
- explicitness flag;
- historical-only handling;
- contradiction/negative/no-signal rules;
- deterministic idempotency identity.

### Truth-preserving gates

Examples:

- global CVE -> **no organization applicability signal**;
- IOC -> **no compromise signal** without organization-specific evidence;
- attacker allegation -> low/qualified incident signal, not official confirmation;
- passive technology observation -> not verified exposure;
- professional role -> enabler, not a need by itself;
- copied/syndicated reports -> same corroboration group where appropriate;
- retracted/denied evidence -> contradicting/negative/withdrawal behavior, not deletion of history.

### Desired-state reconciliation

Signal synthesis must reconcile current desired signals and retire obsolete ones when their canonical basis is no longer eligible. `store_commercial_signal` upsert alone is insufficient as the complete lifecycle.

### Required tests

For every mapping family:

- positive case;
- no-signal semantic boundary;
- correction/retraction;
- expiry;
- unresolved organization;
- conflicting source;
- duplicate/syndication;
- deterministic rule-version behavior;
- service taxonomy coverage;
- no semantic upgrade regression.

### Exit gate

Every commercially actionable canonical family has an explicit reviewed signal-mapping rule or an explicit documented no-signal decision; there is no hidden adapter-specific opportunity shortcut.

---

## L08 — Desired-set need-hypothesis reconciliation

### Objective

Turn generalized Lot 24 fusion into the canonical, automatically maintained current hypothesis layer.

### Required lifecycle model

Extend or separate system lifecycle so a generated hypothesis can explicitly become at least the semantic equivalent of:

- current/proposed;
- active/analyst accepted where applicable;
- dismissed by analyst;
- expired;
- withdrawn because supporting current evidence disappeared;
- superseded because rule/taxonomy/version replaced it;
- stale/reconciling/failed publication state as appropriate.

Analyst dismissal and system withdrawal are different facts.

### Desired-set algorithm

For one organization/subject:

1. load all current eligible signals;
2. run deterministic fusion with rule/taxonomy/config versions;
3. compute desired hypothesis keys;
4. upsert desired hypotheses and signal/evidence lineage;
5. compare with previously system-current hypotheses in scope;
6. transition absent hypotheses to the correct non-current reason;
7. emit downstream score/opportunity dirty event only on material current-state change;
8. persist reconciliation fingerprint/version.

### Query semantics

Default analyst-facing list/detail behavior must not present expired/withdrawn hypotheses as current. Historical/status filters may expose them deliberately.

### Rule/taxonomy upgrades

A mapping/fusion/taxonomy version change must schedule affected organizations for rebuild and preserve the previous generation for audit/reproducibility.

### Required tests

- new signal creates hypothesis automatically;
- second independent source changes confidence without duplicate hypothesis;
- negative/contradicting signal changes result;
- last supporting signal expiry withdraws old hypothesis even when new desired set is empty;
- analyst dismissal survives irrelevant recompute according to product policy;
- taxonomy/rule version rebuild supersedes old generation;
- default query hides non-current state;
- replay is idempotent.

### Exit gate

A stored hypothesis is current only because the latest desired-state reconcile still supports it, never merely because an older recompute once created it.

---

## L09 — Opportunity/scoring reconciliation and legacy-path migration

### Objective

Eliminate dual orchestration between the historical SIEM/SOC direct generator and generalized need-hypothesis flow while preserving analyst state.

### Ownership boundary with Lot 25

Lot 25 owns:

- scoring model;
- calibration;
- component weighting;
- versioning;
- feedback and explainability.

Lot 28 owns:

- **when** a current hypothesis/score/opportunity must be recalculated or invalidated;
- current-basis lifecycle;
- convergence and publication readiness.

### Required migration

Change source commercial projection behavior from:

```text
persist signal -> directly generate SIEM/SOC hypothesis+score+opportunity
```

to:

```text
persist signal -> emit organization/signal change
 -> L08 hypothesis reconcile
 -> scoring/re-score contract
 -> opportunity current-basis reconcile
```

The old SIEM/SOC rule may remain as a scoring/fusion rule if product-value tests justify it, but not as a private runtime pipeline.

### Opportunity identity

Define deterministic commercial-motion identity so a rescore/rebuild does not duplicate an existing opportunity.

Preserve:

- analyst qualification/rejection/snooze/enrichment decision history;
- notes/reviews;
- valid manual score overrides according to their version policy;
- stable links from tasks/engagement added by Lot 26.

### Generated-basis state

Separate analyst workflow state from whether generated evidence basis is current. A previously qualified opportunity can be historically qualified while its current generated basis is withdrawn/stale.

### Required tests

- legacy SIEM/SOC fixture migrates to same stable opportunity without duplicate;
- new generalized hypothesis creates/updates opportunity through one path;
- hypothesis withdrawal makes opportunity non-current without deleting analyst history;
- score expiry triggers rescore or stale state;
- score override behavior remains deterministic across recalculation;
- duplicate event delivery does not duplicate opportunities;
- list query does not show expired generated basis as normal current work unless product policy explicitly requests historical/stale view.

### Exit gate

There is one canonical hypothesis-to-score/opportunity orchestration path and legacy source-specific direct generation is no longer a correctness dependency.

---

## L10 — Time, suppression, deletion and identity invalidation sweep

### Objective

Handle truth changes that are not reliably represented by a fresh provider write.

### Time scheduler

Persist/derive `next_reconcile_at` for subjects affected by:

- signal expiry;
- hypothesis expiry;
- score/opportunity TTL;
- passive observation expiry;
- relationship validity/evidence expiry/renewal windows;
- corporate-change staleness;
- applicability technology-evidence expiry;
- publication freshness thresholds.

Use bounded indexed claims rather than unbounded scans.

### Suppression/deletion

Generic Lot 28 behavior:

- mark downstream projections dirty immediately when a product-owned source/canonical record becomes suppressed/deleted/non-publishable;
- ensure queued stale work cannot republish suppressed state;
- maintain lineage without retaining data that a later privacy-right deletion forbids.

Lot 31 remains the end-to-end privacy workflow owner.

### Identity invalidation

When entity resolution merge/split/reject/reversal changes organization attribution:

- recalculate organization-scoped applicability/relationships/signals/hypotheses/opportunities;
- withdraw the old organization's unsupported derived state;
- create/update the new organization's eligible state;
- preserve evidence and decision chronology;
- prevent a stale queued job from restoring the previous binding.

### Authorization/provider disablement nuance

Disabling future acquisition does **not automatically erase valid historical evidence**. Only route authorization changes into publication invalidation where governance policy says the already-stored data may no longer be used/published.

### Required tests

- each time-only transition occurs without an upstream write;
- suppression blocks republish after retry;
- deletion invalidates downstream state;
- merge then split produces correct old/new organization results;
- stale queued work cannot resurrect old identity/suppression state;
- provider disablement stops acquisition without incorrectly deleting legitimate retained history.

### Exit gate

Derived current state changes correctly when time, governance suppression/deletion or identity changes truth even in the absence of a new positive source record.

---

## L11 — Projection readiness, lineage, observability and publication gates

### Objective

Make reconciliation health visible and prevent failed/stale derived state from masquerading as current analyst-facing truth.

### Platform readiness vocabulary

Expose consistent semantics equivalent to:

- `current`;
- `stale`;
- `reconciling`;
- `failed`;
- `non_publishable/suppressed`.

Individual bounded contexts may retain their richer domain status; readiness is orthogonal to domain truth.

### Projection-state record

Track at least:

- projector ID/version;
- subject type/key;
- input fingerprint;
- rule/config/taxonomy version where relevant;
- latest triggering event/version;
- last success time;
- next due reconcile;
- current readiness state;
- safe last error code;
- lineage references to affected output keys.

### Publication gates

Analyst-facing read models must be able to block or visibly downgrade outputs when:

- required reconciliation is pending beyond policy;
- projector failed;
- evidence is stale beyond its domain threshold;
- lineage is broken;
- current output was built from a superseded rule/config generation;
- required deletion/suppression invalidation is pending.

Do not silently hide all degraded data if showing stale historical context is useful; show it explicitly as stale/non-current according to product workflow.

### Metrics

At minimum:

- pending jobs by projector;
- oldest pending age;
- retry/dead-letter count;
- reconcile latency;
- coalescing ratio;
- stale publication count;
- failed projector count;
- rebuild mismatch count;
- downstream changes/withdrawals per trigger class.

### Operator controls

Protected/audited controls for:

- inspect subject lineage;
- requeue failed job;
- force scoped reconcile;
- schedule bounded rebuild;
- compare fingerprints;
- acknowledge/resolve operational incident where appropriate.

### Required tests

- failed projector visible through API/read model;
- stale data cannot claim `current`;
- requeue/recovery clears state only after success;
- lineage resolves source/canonical/change/job/output chain;
- control-plane auth required;
- metrics do not expose secrets/personal payloads;
- frontend states for current/stale/reconciling/failed.

### Exit gate

An analyst/operator can determine whether every important derived projection is current and why, and a failed reconciliation cannot look like ordinary current truth.

---

## L12 — End-to-end convergence qualification and Lot 28 closeout

### Objective

Prove the complete product property on one exact final head.

### Required E2E scenarios

At minimum:

#### Scenario A — passive technology to commercial state

```text
passive current technology/version
 -> applicability
 -> graph
 -> commercial signal
 -> need hypothesis
 -> score/opportunity current basis
```

Then expire/correct the technology and prove reverse invalidation.

#### Scenario B — procurement lifecycle

```text
award/contract
 -> relationship
 -> graph
 -> renewal/provider signal
 -> need hypothesis
 -> opportunity
```

Then cancel/amend/reassign provider and prove convergence.

#### Scenario C — incident lifecycle

```text
actor/media claim
 -> qualified incident state
 -> weak/qualified signal
```

Then official confirmation or denial/retraction and prove correct truth-preserving downstream change.

#### Scenario D — corporate/regulatory change

Prove fresh -> stale and correction/retraction behavior without manual recompute.

#### Scenario E — identity reversal

Create evidence under an initially resolved organization, merge/rebind/split identity, and prove all organization-scoped derived state follows the final binding without duplication.

#### Scenario F — replay convergence

Apply one synthetic history through:

- incremental order;
- reverse/shuffled replay;
- historical backfill;
- restore then rebuild.

Compare canonical and derived fingerprints.

#### Scenario G — resilience

Crash after canonical commit, deliver duplicate outbox event, fail one projector, recover/requeue, and prove no lost change or duplicate opportunity.

### Required repository-wide gates

- migration tests;
- architecture tests;
- Ruff;
- strict Mypy;
- backend tests with branch-aware coverage >= repository threshold;
- critical new reconciliation code target >=95% line/branch where applicable;
- frontend affected tests/typecheck/build;
- security/privacy/data-governance tests;
- no permanent skip or weakened threshold;
- documentation truth audit;
- exact final SHA workflow validation.

### Completion audit

Create a Lot 28 completion audit that maps every finding in `LOT_28_IMPLEMENTATION_GAP_AUDIT.md` to:

- implementation commit/file;
- migration;
- deterministic test;
- runtime/operational proof;
- disposition `closed`, `explicit exclusion`, or named later owner.

No generic `later`, `hardening`, `manual`, `blocked`, or `deferred` disposition is terminal.

### Exit gate

Lot 28 is complete only when the platform proves that canonical truth and analyst-facing derived truth converge automatically in both forward and reverse directions, including time transitions, retries and rebuilds, with no manual refresh/recompute step required for ordinary correctness.