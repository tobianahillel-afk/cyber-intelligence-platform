# Lots 01–05 — Implementation Gap Audit

## Status

`AUDITED_HANDOFF_TO_RECOVERY`

Tracker: issue #173.

Baseline: `8d7184b8a6f494ceb407ab489d8971f4d015bab6`.

Canonical recovery parent: `LOTS_01_05_IMPLEMENTATION_FINALITY_RECOVERY.md`.

## Audit question

Do the merged implementations corresponding to historical Lots 01–05 satisfy the stronger production-finality expectations now documented by the repository, or are there still local correctness/completeness gaps that later product work would otherwise inherit?

**Answer:** the foundations are real and useful, but six concrete residuals require either local recovery implementation or an explicit handoff to an existing later owner.

## Method

The audit traces current runtime/code rather than relying only on historical lot status. Reviewed surfaces include the authoritative delivery-plan outcomes for Lots 01–05; collection schedule/domain models; scheduler job creation; durable queue/lease repository; ordinary collection worker; TED application adapter/client/collector/mapper and canonical service classifier; BOAMP application adapter/client/collector; opportunity score value object and Lot 25 roadmap ownership; current repository test layout and normative development/test requirements; and later ownership constraints from Lots 25, 28, 30, 31 and Source Activation.

## Finding register

### F01 — Worker heartbeat primitive exists but ordinary long-running collection does not use it

**Severity:** high correctness/recovery gap.  
**Historical capability:** Lot 02 durable worker leases/recovery.  
**Required implementation:** R01-L02.

Observed runtime:

- `claim_next_job(...)` creates a running lease with owner and expiry;
- `heartbeat_job(...)` exists and can extend the lease for the current owner;
- `run_worker_once(...)` claims a job in one session;
- the session closes;
- `adapter.collect(...)` then runs outside the database transaction;
- no heartbeat is scheduled or cooperatively invoked during that collection interval;
- completion opens another session and verifies ownership/lease, potentially returning `LEASE_LOST` after the work was already performed.

Failure mode:

```text
worker A claims job
-> long adapter call exceeds lease
-> lease expires
-> worker B recovers/reclaims same logical work
-> A and B may both perform provider requests
-> one eventually loses persistence ownership
```

The existing stale-completion protection is valuable but insufficient for single-owner execution finality. R01-L02 must reuse the current `heartbeat_job(...)`, lease ownership and `LeaseLostError` semantics rather than introduce a second queue/lease subsystem.

### F02 — Schedule provenance is value-only rather than identity/revision aware

**Severity:** medium-high auditability/replay gap.  
**Historical capabilities:** Lot 01 provenance + Lot 02 scheduler.  
**Required implementation:** R01-L03.

Observed runtime:

- YAML schedule documents have a file-level schema version;
- each parsed `SourceSchedule` contains source ID, adapter ID, cadence, lease, enabled state and retry policy;
- no stable `schedule_id`, revision or configuration fingerprint is carried by the domain object;
- `CollectionJob.from_schedule(...)` copies execution parameters but does not persist source schedule identity/revision;
- job idempotency is based on source + adapter + scheduled slot.

After schedule configuration changes, a historical job cannot unambiguously identify the schedule revision/configuration artifact that caused it to exist.

Desired lineage:

```text
schedule bundle path/version
-> stable schedule ID
-> schedule revision/fingerprint
-> scheduled slot
-> collection job
-> attempt/lease/checkpoint
-> observations/projections
```

### F03 — TED client hard-codes page 1 and 100 results

**Severity:** critical acquisition-completeness gap.  
**Historical capability:** Lot 04 TED procurement acquisition.  
**Required implementation:** R01-L04.

Observed runtime:

- `TedSearchClient.DEFAULT_LIMIT = 100`;
- request uses `paginationMode = PAGE_NUMBER`;
- request uses `page = 1`;
- `fetch()` accepts no page/cursor argument;
- collector calls `client.fetch()` once;
- checkpoint contains only `latest_publication_number`.

If more than 100 relevant current results exist before the previous checkpoint is encountered, records beyond page 1 cannot be reached by the ordinary adapter path.

### F04 — TED provider query and mapper relevance do not share one complete versioned discovery contract

**Severity:** high recall/maintainability gap.  
**Historical capability:** Lot 04 procurement signals.  
**Required implementation:** R01-L05.

Observed runtime:

- TED client contains one static hand-written `SEARCH_QUERY` string;
- canonical `service_taxonomy` independently contains the complete 19-family service vocabulary;
- TED mapper calls `matched_procurement_terms(title)` and drops a notice when the title has no matching term;
- procurement service classification also uses the title only;
- other selected TED fields such as CPV and contract title are present but not part of the relevance admission contract.

Risks include duplicated vocabulary drift, false negatives on generic titles with strong cyber metadata, and no query-plan version/coverage provenance. R01-L05 improves deterministic acquisition/relevance coverage only; Lot 25 remains scoring calibration owner.

### F05 — BOAMP bounded pagination fails a dense window instead of partitioning it

**Severity:** high acquisition/recovery gap.  
**Historical capability:** Lot 05 BOAMP procurement signals.  
**Required implementation:** R01-L06.

Observed runtime:

- BOAMP fetches 100-record pages with deterministic `dateparution desc,idweb desc` ordering;
- collector defaults to `max_pages=5`;
- it searches from the checkpoint publication date or a two-day bootstrap window;
- if the checkpoint/short page is not reached after the bounded page budget and total count is greater than consumed records, it raises `BoampSourceWindowError`;
- the application adapter maps that to `source_window_exceeded`, `retryable=False`.

The page budget is a good resource-control invariant. The missing capability is adaptive partition/recovery so legitimate dense windows converge automatically.

### F06 — Historical opportunity engine has reproducible score mechanics but no labelled objective baseline

**Severity:** high commercial-quality evidence gap, with split ownership.  
**Historical capability:** Lot 03 opportunity engine.  
**Required implementation:** R01-L07 plus Lot 25 handoff.

Observed runtime:

- `OpportunityScore` stores score/config versions;
- score is composed from explicit positive/penalty components;
- calculation is deterministic and hashed;
- no `ground truth` or calibration implementation was found by repository search on this baseline;
- current Lot 25 explicitly owns calibration datasets, offline evaluation, analyst overrides/outcomes, service/segment calibration, drift/bias/false-positive monitoring and score replay comparison.

R01-L07 therefore creates the benchmark contract, versioned labelled fixtures and baseline evaluator/metrics required to judge historical rules. Lot 25 consumes/extends that corpus for calibration and analyst-outcome feedback.

## Lot-by-lot disposition

### Lot 01

No standalone rewrite is justified by this audit. Lot 01 primitives remain the foundation. The direct enhancement touching provenance is schedule-to-job lineage in R01-L03. Stronger system-wide derived invalidation remains Lot 28, privacy rights/deletion remains Lot 31, and broad restore/resilience/network hardening stays with its named later owners.

### Lot 02

Two local finality gaps are confirmed: F01 heartbeat integration and F02 schedule revision provenance. Both belong here because they are direct scheduler/worker correctness properties.

### Lot 03

Core deterministic score representation is implemented. The missing ground-truth/evaluation foundation is recovered narrowly in R01-L07; statistical calibration and feedback remain Lot 25.

### Lot 04

Two local finality gaps are confirmed: F03 complete bounded pagination/resume and F04 versioned complete discovery/relevance coverage. Provider live activation claims remain Source Activation responsibilities after deterministic mechanics are corrected.

### Lot 05

BOAMP has one confirmed dense-window convergence gap F05. Existing architecture gates are not reopened. Provider live validation remains Source Activation responsibility where applicable.

## Handoff matrix

| Requirement | Recovery disposition | Canonical owner after recovery | No-duplication rule |
|---|---|---|---|
| long-job lease renewal | implement | R01-L02 | reuse current queue/heartbeat |
| schedule revision lineage | implement | R01-L03 | one schedule identity/fingerprint contract |
| TED multi-page traversal | implement | R01-L04 | no parallel TED collector |
| TED discovery/relevance completeness | implement | R01-L05 | no duplicated service taxonomy |
| BOAMP dense-window convergence | implement | R01-L06 | preserve bounded acquisition |
| labelled Lot03 benchmark foundation | implement narrow foundation | R01-L07 | no calibration optimizer |
| calibrated scoring/outcomes/drift | handoff | Lot 25 | benchmark contract only |
| canonical-change outbox/reactors | handoff | Lot 28 / #171 | no event bus here |
| DNS/address safety | handoff | Lot 30 / #169 | no provider-specific fork |
| privacy rights/deletion propagation | handoff | Lot 31 / #5 | no second privacy workflow |
| controlled provider live proof | handoff | Source Activation / SA-20 where applicable | deterministic CI != live proof |

## Findings that must be rechecked during implementation

The initial register is not a ceiling. Each micro-lot PR must re-read adjacent code/tests and add newly discovered gaps to issue #173 before claiming completion. The terminal closeout must specifically look for checkpoint gaps at page/window boundaries; lease expiry races; schedule configuration changes preserving the same source/adapter pair; page replay/reordering and provider updates during traversal; same-date BOAMP data beyond one offset/window budget; TED query/taxonomy drift and multilingual gaps; evidence/projection duplication caused by retry; any Lot 01–05 limitation described only as future/manual/blocked; and any recovery change duplicating later canonical ownership.

## Audit exit decision

This audit hands F01–F06 to the corrective recovery programme. It does not mark those findings fixed. Recovery completion requires code/migration/test evidence from R01-L02 through R01-L07 plus terminal R01-L08 adversarial qualification on one exact final SHA.
