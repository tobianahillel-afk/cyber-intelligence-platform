# Lots 06–10 implementation finality recovery

Status: **THIRD_PASS_FINAL_AUDIT_COMPLETE_IMPLEMENTATION_PENDING**  
Recovery overlay: **R02**  
Tracking issue: **#175**  
Audited baseline: `main@8d7184b8a6f494ceb407ab489d8971f4d015bab6`

## Purpose

R02 reopens historical Lots 06–10 against the current ordinary runtime. Historical merged PRs, closed issues and historical green CI are evidence, not terminal proof. The third adversarial pass follows the full chain from provider registries and capability manifests through adapter traversal, immutable source mutations, identity binding, persistence, scheduler/worker/backfill execution, source health/value accounting, API state and current tests.

The optimization target is the most complete safe product, not the minimum old acceptance threshold. R02 remains a recovery overlay and does not renumber the normal Lots 00–32 roadmap.

## Historical scope

| Lot | Tracker | Capability | Third-pass disposition |
|---|---:|---|---|
| 06 | #21 | Greenhouse public cyber hiring signals | historical core retained; Lot10 mutation-capability truth adds F09 |
| 07 | #23 | Lever + SmartRecruiters + prudent reversible inter-ATS dedup | F01 + F07 |
| 08 | #25 | French/European organization identity foundation | internal core retained; ATS integration defect remains F07 |
| 09 | #27 | provider onboarding and secret lifecycle | F02 + F03 + F04 |
| 10 | #29 | source portfolio/runtime/backfill/freshness/health/value | F05 + F09 + F10 + F11 + F12; F06 remains Lot28; F08 bridges Lot09→Lot10 |

## Final finding register after third adversarial pass

| ID | Lot | Severity | Owner | Capability |
|---|---:|---|---|---|
| R02-F01 | 07 | HIGH | R02-L02 | durable/reversible inter-ATS duplicate decisions |
| R02-F02 | 09 | HIGH | R02-L03 | provider-specific credential/scope/connectivity verification |
| R02-F03 | 09 | HIGH | R02-L04 | legal onboarding transition graph |
| R02-F04 | 09 | HIGH | R02-L04 | revision-bound expiry/rotation/reverification lifecycle |
| R02-F05 | 10 | CRITICAL | R02-L05 | fail-closed Source Portfolio execution authority |
| R02-F06 | 10 | CRITICAL | Lot28/#171 | downstream derived-state convergence |
| R02-F07 | 07↔08 | HIGH | R02-L02 | ATS projection must consume resolved canonical organization identity |
| R02-F08 | 09→10 | CRITICAL | R02-L05 | execution eligibility must compose current onboarding authorization |
| R02-F09 | 10 | HIGH | R02-L06 | source-mutation capability truth and causal integrity |
| R02-F10 | 10 | CRITICAL | R02-L07 | durable backfill crash/partial-progress/circuit recovery |
| R02-F11 | 10 | HIGH | R02-L08 | source-quality population versus delta semantics |
| R02-F12 | 10 | HIGH | R02-L09 | truthful backfill value/ablation attribution |

## Third-pass additions

### R02-F09 — source mutation capability truth and causal integrity

Lot10 has a good immutable mutation vocabulary: `UPSERT`, `CORRECTION`, `TOMBSTONE`, `RETRACTION`, plus `supersedes_observation_id`. The current causal contract is nevertheless incomplete:

- persistence does not enforce `supersedes_observation_id` as a same-record predecessor relation;
- the reducer orders events by effective time and record key but does not validate the supersedes edge;
- invalid cross-record/cross-source/forked mutation chains are not rejected by the current state reducer;
- Greenhouse, Lever and SmartRecruiters capability manifests advertise corrections and tombstones, while their current collectors emit changed postings as ordinary UPSERT observations and represent disappearance only by absence from the next checkpoint.

The best final product is not to weaken the manifest. R02-L06 must make the advertised capability real: changed source records become causal corrections, complete successful traversal can emit safe tombstones for disappeared records, and every mutation chain is transactionally validated without destroying immutable source history.

This is upstream source truth. Lot28 still exclusively owns downstream propagation/invalidation caused by those valid mutations.

### R02-F10 — durable backfill crash, partial-progress and circuit recovery

Backfill partitions have state/cursor/attempts but no lease owner, lease expiry or retry availability timestamp. `claim_backfill_partition()` moves a partition to `RUNNING`; a worker crash can therefore strand it indefinitely because only PENDING/FAILED partitions are claimable.

The generic adapter contract also supports `AdapterPartialExecutionError` carrying a safe partial batch. Incremental execution persists that partial progress, whereas the backfill worker catches the parent `AdapterExecutionError` and discards the partial batch/checkpoint. Failed partitions are immediately reclaimable until the fixed attempt limit, without the collection circuit/backoff used by incremental jobs.

R02-L07 must provide one durable backfill ownership/recovery contract: lease/crash takeover, safe partial checkpoint persistence, bounded retry/backoff/circuit behavior, authorization recheck before network, and race-safe pause/disable/revoke behavior. Prefer reuse/shared primitives over a second incompatible queue implementation.

### R02-F11 — source-quality population versus delta semantics

Source quality currently feeds `evaluate_quality()` with `batch.observations`; its volume EWMA therefore measures emitted immutable changes. The ATS collectors, however, perform complete current-state traversals and emit observations only for changed postings. A healthy provider returning 1,000 jobs with one changed job can therefore be evaluated as `records_count=1` after the baseline warms up.

R02-L08 must separate provider/current-population health from delta/change volume. The shared batch contract should expose typed run-quality metrics such as current records seen, pages traversed, changed/removed counts, traversal completeness and representative schema/field population. Missing metrics must be represented as unavailable, never inferred from delta emissions.

### R02-F12 — truthful backfill source-value attribution

Lot10 explicitly owns commercial-value and source-ablation hooks. Incremental execution counts commercial and identity projections in `SourceValueEvent`; backfill currently records both as zero unconditionally even while the same batch may persist procurement or other projections.

R02-L09 must centralize value accounting so incremental and historical paths report what was actually accepted/persisted under the same semantics. Historical ingestion must remain distinguishable from fresh-trigger value so this fix does not create false historical-alert value.

## Deepened existing findings

### F04 profile revision is part of verification revision

`sync_provider_profiles()` can change `auth_mode`, required secret names and human-action requirements on an existing onboarding record. Today a non-blocking profile change does not intrinsically invalidate a prior `CONNECTED`/`last_verified_at` state. R02-L04 must therefore bind successful verification to both the current secret-reference revision and the current provider-profile/verification-contract revision.

### F08 activation presence is not authorization

Runtime bootstrap synchronizes onboarding and portfolio separately, then `reconcile_runtime_adapters()` can promote target-dependent sources based on adapter presence. Adapter availability is technical readiness, not authorization. R02-L05 must compose onboarding current authorization into the one execution eligibility verdict and recheck it at the last safe pre-network boundary.

## Explicit non-findings from the third pass

- Greenhouse traversal is bounded and validates the returned board count; no hidden pagination truncation finding was proven.
- Lever pagination advances `skip` until a short page and is bounded; no pagination finality gap was proven.
- SmartRecruiters validates offset/`totalFound`, detects premature empty pages and is bounded; no pagination finality gap was proven.
- Lot08 identifier persistence has a globally unique normalized `exact_key`; no new official-identifier collision finding was proven.
- Incremental collection has a real durable circuit breaker (`OPEN/HALF_OPEN/CLOSED`) and retry delay; the circuit defect is specifically backfill parity/recovery under F10.
- priority/manual refresh already uses `source_execution_allowed()` and the worker rechecks execution; F05/F08 fix the shared authority rather than creating another refresh-specific gate.
- ordinary portfolio synchronization preserves manually PAUSED/DISABLED state; no sync-reset finding is added.

## Locked recovery order

```text
R02-L01 ownership/no-orphan guard
  -> R02-L02 F01+F07 ATS identity binding + reversible dedup
  -> R02-L03 F02 provider-specific verification
  -> R02-L04 F03+F04 legal revision-bound onboarding lifecycle
  -> R02-L05 F05+F08 composed fail-closed execution authority
  -> R02-L06 F09 source mutation capability + causal integrity
  -> R02-L07 F10 durable backfill recovery
  -> R02-L08 F11 truthful source-quality semantics
  -> R02-L09 F12 truthful source-value attribution
  -> R02-L10 final adversarial qualification + closeout
```

## Ownership boundaries

- Lot28/#171 remains the only owner of cross-module derived-state propagation, invalidation and backfill/incremental/replay convergence.
- Lot29/#6 remains the owner of supply-chain/release/repository protection.
- Lot30/#169 remains the owner of DNS/address safety and broad resilience.
- Lot31/#5 remains the owner of privacy rights/deletion/non-resurrection.
- SA20/current activation successor remains the owner of controlled live-provider proof when implementation exists and activation evidence alone is missing.

## Terminal closeout gate

`docs/lots/LOTS_06_10_FINALITY_RECOVERY_CLOSEOUT.md` must not exist as proof until R02-L01–L09 are implemented and R02-L10 proves on one exact final SHA:

1. every local finding F01–F05 and F07–F12 is implemented/proven;
2. F06 remains correctly owned by Lot28 unless independently completed there;
3. migrations upgrade/downgrade/upgrade safely;
4. PostgreSQL concurrency, lease, replay and mutation-race tests pass;
5. source manifests match executable capability behavior;
6. provider secrets remain absent from DB/API/audit/logs;
7. no network occurs after an execution denial;
8. quality/value metrics are truthful for current-state, delta and historical paths;
9. architecture/backend/frontend-when-touched/security/full regression pass;
10. review threads are zero and exact-head CI is green.
