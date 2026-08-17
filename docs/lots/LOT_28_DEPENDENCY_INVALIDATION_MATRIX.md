# Lot 28 — Derived dependency and invalidation matrix

## Status

`PLANNED_LOCKED`.

Parent scope: `LOT_28_DERIVED_STATE_RECONCILIATION_RECOVERY.md`.

Tracking issue: #171.

## Purpose

This matrix is the normative routing reference for Lot 28 implementation. It prevents two opposite failures:

1. an upstream change that should invalidate downstream state but does not;
2. an upstream observation being over-promoted into a commercial conclusion that its evidence cannot support.

`DIRTY` means the subject must be scheduled for deterministic reconciliation. It does **not** mean the downstream conclusion is automatically true.

## Platform-level dependency graph

```text
RawObservation / immutable provider revision
  |
  +-> organization identity ------------------------------+
  |                                                       |
  +-> procurement ------------------------------------+   |
  |                                                   |   |
  +-> public footprint / documents -------------------|---|---+
  |                                                   |   |   |
  +-> vulnerability knowledge/advisories ------+      |   |   |
  |                                            |      |   |   |
  +-> passive technology/exposure ------------|--+   |   |   |
  |                                            |  |   |   |   |
  +-> incident claims -------------------------|--|---|---|---|--+
  |                                            |  |   |   |   |  |
  +-> corporate/regulatory changes ------------|--|---|---|---|--|--+
  |                                            |  |   |   |   |  |  |
  +-> source-native relationship evidence -----|--|---|---|---|--|--|--+
  |                                            |  |   |   |   |  |  |  |
  +-> professional context --------------------|--|---|---|---|--|--|--|--+
                                               |  |   |   |   |  |  |  |  |
                                               v  v   |   |   |  |  |  |  |
                                      applicability  |   |   |  |  |  |  |
                                               |      |   |   |  |  |  |  |
                                               +------+---+---+--+--+--+--+
                                                      |
                                                      v
                                             corporate graph
                                                      |
                         +----------------------------+-------------------+
                         |                                                |
                         v                                                v
                 commercial signal synthesis                    professional/contact
                         |                                       relevance/context
                         v
                 need-hypothesis reconcile
                         |
                         v
                 score/opportunity reconcile
                         |
                         v
                 publication/readiness gate
                         |
                         v
                     analyst UI
```

The graph is not necessarily the source for commercial-signal synthesis. Some signals should be synthesized directly from canonical evidence and merely share organization identity/lineage with graph projections. The dependency registry must avoid turning the graph into an opaque inference shortcut.

## Current-state gap matrix by historical lot

| Historical lot | Canonical capability already present | Current automatic local reconciliation | Current missing cross-lot finality | Lot 28 owner |
| --- | --- | --- | --- | --- |
| 13 | vulnerability knowledge/exploitation state | source snapshots/canonical vulnerability projection | organization-specific downstream dirty routing when advisory/range knowledge changes | L01/L04/L07/L10 |
| 14 | incident claims and reconciled incident | claim persistence/reconciliation on write | graph + signal + hypothesis/opportunity invalidation; no generic time/rebuild trigger | L01/L06/L07/L08/L09/L10 |
| 15 | threat indicators/telemetry | indicator canonical projection | only organization-specific evidence may become commercial context; prevent IOC->compromise promotion; derived dirty routing where legitimate | L01/L07 |
| 16 | passive assets/technology observations | passive canonical snapshots/projections | applicability trigger, graph trigger, signal trigger, time expiry propagation | L04/L06/L07/L10 |
| 17 | advisory ranges and applicability model/persistence | assessment history updates when explicitly invoked | no production dependency reactor joining changed technology/advisory/identity/time | L04 |
| 18 | corporate/regulatory change claims/events | claim/event reconcile on write | graph + signal + hypothesis/opportunity cascade; stale transition without write | L06/L07/L08/L09/L10 |
| 19 | relationship model/history + procurement mapping function | relationship reconcile when evidence explicitly persisted | procurement mapping not wired into normal persistence; time/current state and downstream cascade | L05/L06/L07/L10 |
| 20 | temporal graph + resolution decisions | graph reconciles when refresh invoked | ordinary correctness depends on explicit refresh; scoped dependency-driven/time-driven refresh missing | L06/L10/L11 |
| 21 | professional people/roles/reporting/contact context | module persistence/privacy lifecycle when explicitly written | no common source-worker projection path; no shared reconciliation trigger contract; professional context must remain an enabler rather than automatic need | L01/L03/L07/L10/L11, provider activation remains SA19 |
| 22 | conditional-provider governance/control plane | provider eligibility/pause/kill behavior | provider-state change needs consistent derived publication routing only where stored-use policy changes; no blanket deletion | L01/L10/L11 |
| 23 | governed research orchestration | persisted research plans/results/provenance validation | promoted evidence must join common canonical-change path; weak research result must not bypass evidence qualification | L01/L07/L11 |
| 24 | generalized commercial signals/need fusion | signal upsert; hypothesis fusion when explicitly recomputed | no general canonical->signal synthesis, desired-set hypothesis retirement, or automatic global trigger; legacy SIEM/SOC direct path remains | L07/L08/L09/L10 |

## Canonical trigger matrix

| Upstream change | Applicability | Relationship | Graph | Commercial signal | Need hypothesis | Score/opportunity | Publication |
| --- | --- | --- | --- | --- | --- | --- | --- |
| organization identity exact binding created/changed | `DIRTY` for affected org/assets | `DIRTY` for unresolved/resolved endpoints | `DIRTY` | `DIRTY` for org-scoped mappings | transitively | transitively | `DIRTY` |
| organization merge/split/reversal | `DIRTY` old+new scopes | `DIRTY` old+new endpoints | `DIRTY` | `DIRTY` old+new scopes | `DIRTY` old+new | `DIRTY` old+new | `DIRTY` |
| procurement award/new contract | no | `DIRTY` | after relationship | `DIRTY` contract intent/lifecycle | after signals | after hypotheses | `DIRTY` |
| procurement amendment | no | `DIRTY` | after relationship | `DIRTY` | after signals | after hypotheses | `DIRTY` |
| procurement cancellation | no | `DIRTY` retraction/historical | after relationship | `DIRTY` negative/withdraw | `DIRTY` | `DIRTY` | `DIRTY` |
| contract end/renewal becomes due by time | no | `DIRTY` | after relationship | `DIRTY` renewal/lifecycle | `DIRTY` | `DIRTY` | `DIRTY` |
| passive asset discovered | possibly if technology is present | no | `DIRTY` | only if mapped/eligible | transitively | transitively | `DIRTY` |
| passive technology/version changed | `DIRTY` | no | `DIRTY` | `DIRTY` technology/exposure mapping | `DIRTY` | `DIRTY` | `DIRTY` |
| passive observation expires | `DIRTY` | no | `DIRTY` | `DIRTY` withdraw/negative/no signal | `DIRTY` | `DIRTY` | `DIRTY` |
| advisory/range added or corrected | `DIRTY` matching technologies | no | after applicability | only via current applicability where organization-specific | `DIRTY` if signal changed | transitively | `DIRTY` |
| advisory/range withdrawn | `DIRTY` | no | after applicability | withdraw applicability-derived signals | `DIRTY` | `DIRTY` | `DIRTY` |
| global CVE/EPSS/KEV change without org-specific technology | no automatic positive applicability | no | global knowledge only if graph models it | **NO direct organization need signal** | no | no | knowledge views only |
| incident allegation/report changes | no | no | `DIRTY` | `DIRTY`, preserving allegation/report class | `DIRTY` | `DIRTY` | `DIRTY` |
| incident official confirmation | no | no | `DIRTY` | `DIRTY` stronger incident state | `DIRTY` | `DIRTY` | `DIRTY` |
| incident denial/retraction | no | no | `DIRTY` | `DIRTY` contradiction/withdraw | `DIRTY` | `DIRTY` | `DIRTY` |
| corporate/regulatory change fresh revision | no | maybe only if explicit relationship semantics | `DIRTY` | `DIRTY` | `DIRTY` | `DIRTY` | `DIRTY` |
| corporate change becomes stale by time | no | no | `DIRTY` currentness if represented | `DIRTY` freshness/withdraw | `DIRTY` | `DIRTY` | `DIRTY` |
| relationship assertion/correction | no | local current state | `DIRTY` | `DIRTY` relationship/provider context | `DIRTY` | `DIRTY` | `DIRTY` |
| relationship retraction/expiry | no | local/time reconcile | `DIRTY` | `DIRTY` withdraw/negative | `DIRTY` | `DIRTY` | `DIRTY` |
| professional role/contact revision | no | no | only if product explicitly models person-role graph there; otherwise no | usually no need signal; update relevance/contact context | only if a separate weak-signal rule is explicitly approved | opportunity role recommendation may update, not need basis by default | `DIRTY` contact/readiness |
| research result persisted but not promoted to canonical evidence | no | no | no | **NO** | no | no | research workspace only |
| research result promoted with validated evidence provenance | route by promoted canonical type | route by type | route by type | route by type | transitively | transitively | `DIRTY` |
| source disabled for future execution only | no | no | no | no automatic deletion | no | no | source health/status only |
| stored-use authorization revoked / data made non-publishable | `DIRTY` where basis affected | `DIRTY` where basis affected | `DIRTY` | `DIRTY` | `DIRTY` | `DIRTY` | immediate block |
| suppression/deletion | `DIRTY` | `DIRTY` | `DIRTY` | `DIRTY` | `DIRTY` | `DIRTY` | immediate block/pending invalidation |
| mapper/taxonomy/rule version changes | potentially by matching logic | potentially by classification logic | if graph mapping version changes | `DIRTY` affected subjects | `DIRTY` | `DIRTY` | `DIRTY` until current generation |

## Truth-preserving no-upgrade matrix

| Input fact | Forbidden automatic conclusion | Permitted derived behavior |
| --- | --- | --- |
| CVE exists / KEV listed / EPSS high | organization is vulnerable/exposed | enrich global risk; schedule applicability only when org-specific technology evidence exists |
| passive technology name only | exact affected version or verified exposure | technology context; applicability may remain unknown/review-required |
| passive port/service observation | exploitable internet exposure | passive exposure signal with explicit uncertainty if mapping policy permits |
| IOC associated with malware/campaign | named organization compromised | global threat context; organization signal only with separate org-specific evidence |
| ransomware/actor claim | official incident confirmation | alleged/weak incident state with penalties and corroboration requirement |
| media report copied by many sites | many independent sources | one corroboration/syndication group as appropriate |
| public partner directory listing | contracted/current commercial relationship | claimed/inferred relationship evidence according to reviewed source semantics |
| case study | current incumbent relationship forever | dated relationship evidence with validity/staleness rules |
| job posting | guaranteed capability gap | hiring/program-build hypothesis with uncertainty and expiry |
| professional role/person found | cybersecurity need exists | buying-committee/relevance context only unless independent need evidence exists |
| research search result/snippet | canonical evidence | discovery lead until fetched/validated/promoted through governed evidence path |
| analyst qualification | evidence can never later be withdrawn | preserve analyst decision history while current generated basis can become stale/withdrawn |

## Time-driven subjects

These transitions can become due without a new canonical write and therefore require L10 scheduling.

| Subject | Time field / policy | Expected reconcile |
| --- | --- | --- |
| passive observation | `expires_at` / freshness policy | passive current state, applicability, graph, signal |
| applicability | technology/advisory validity | assessment current state, graph, signal |
| relationship | `valid_until`, `expires_at`, renewal window | relationship, graph, signal |
| corporate change | staleness threshold/claim expiry | change event, graph, signal |
| commercial signal | `expires_at` | hypothesis desired set |
| need hypothesis | `expires_at` | hypothesis lifecycle, score/opportunity |
| score | score TTL/config validity | rescore/readiness |
| opportunity generated basis | hypothesis/score currentness | current-basis/readiness, while preserving analyst workflow history |
| publication/read model | quality/freshness SLA | readiness downgrade/block |

## Write-path ownership

### Provider/source adapters

Allowed responsibilities:

- governed acquisition;
- provider payload validation;
- immutable observations/provider revisions;
- typed source-native canonical projections defined by their approved adapter contract.

Forbidden responsibilities:

- direct graph refresh;
- direct need-hypothesis creation as a provider-specific shortcut;
- direct score/opportunity table writes;
- hidden cross-module retries outside the common reconciliation mechanism.

### Canonical bounded contexts

Allowed responsibilities:

- immutable history;
- local current-state reconciliation;
- emit minimal canonical-change facts in the same transaction when material current state may have changed.

### Derived reconciliation module

Responsibilities:

- route dirty changes;
- durable/coalesced jobs;
- call application-level projector ports;
- retry/dead-letter;
- time-due work;
- projection readiness/fingerprint.

It does not own provider network access or domain-specific truth rules.

### Lot 25 scoring

Owns scoring semantics; consumes dirty current hypotheses and returns deterministic versioned scores.

### Lot 26 commercial operations

Owns analyst lifecycle/tasks/alerts. It consumes generated-basis changes without erasing analyst history.

### Lot 27 workspace

Owns presentation of current/stale/failed state and lineage.

### Lot 31 privacy

Owns legal/privacy request workflow and non-resurrection. It uses the generic invalidation mechanisms from Lot 28.

## Required current-state lifecycle separation

A minimum conceptual separation is mandatory:

```text
Domain truth state
  e.g. confirmed / alleged / stale / retracted

Derived reconciliation readiness
  current / stale / reconciling / failed / non-publishable

Analyst workflow state
  needs_review / qualified / rejected / snoozed / ...
```

One field must not be overloaded to represent all three concerns.

## Coalescing and ordering rules

- delivery is at least once;
- projector result is idempotent;
- newest canonical/effective version wins according to domain chronology, not queue arrival order;
- repeated dirty events may coalesce by projector+subject;
- coalescing must retain enough version/fingerprint information to detect that a newer canonical state exists;
- stale job completion must not overwrite a newer successful generation;
- analyst mutation with a version/fingerprint precondition cannot be silently undone by older background work;
- zero desired outputs is a valid reconcile result and may withdraw previous current output.

## Rebuild scopes

Support progressively larger controlled scopes:

1. one projector + one subject;
2. one organization;
3. one canonical aggregate type/date partition;
4. one projector all subjects in bounded pages;
5. complete derived-state rebuild for controlled recovery/qualification.

Every scope must be resumable and observable.

## Final acceptance matrix

Lot 28 cannot close until every row below has deterministic evidence.

| Property | Required proof |
| --- | --- |
| atomic dirty-event creation | PostgreSQL rollback/commit tests |
| at-least-once safety | duplicate/crash replay tests |
| no stale overwrite | concurrent version/fingerprint tests |
| applicability automation | passive/advisory/identity/time E2E |
| relationship automation | procurement award/amend/cancel/time E2E |
| graph automation | upstream change without HTTP refresh E2E |
| generalized signal synthesis | mapping-family positive/negative/retraction tests |
| hypothesis negative reconciliation | desired-set empty/withdraw/expire tests |
| opportunity current-basis invalidation | preserved analyst state + non-current basis test |
| time-only correctness | due-time sweep tests |
| suppression/deletion propagation | non-resurrection/old-job safety tests |
| identity propagation | merge/split/reversal tests |
| incremental/backfill/replay convergence | deterministic fingerprint comparison |
| failure visibility | stale/reconciling/failed API/UI/operator tests |
| rebuild recoverability | restore/rebuild fingerprint test |
| truth hierarchy | no-upgrade regression suite |
| final repository health | exact-head CI + coverage/security/architecture/migration/frontend gates |
