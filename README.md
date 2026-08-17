# Cyber Intelligence Platform

Cyber Intelligence Platform is a standalone cyber revenue-intelligence and commercial-operations system. It collects approved public or licensed evidence, resolves it into reviewable company and cyber context, converts that evidence into explainable cybersecurity need hypotheses, and lets analysts investigate, qualify, assign, and track potential clients.

The product is evidence-first. Observation, claim, evidence, resolved fact, commercial signal, need hypothesis, score, opportunity and outreach authorization remain separate states. An attacker allegation is not an official confirmation; a technology mention is not proof of deployment; a passive observation is not proof of vulnerability applicability or verified exposure; a global vulnerability or IOC is not proof that a named organization is affected or compromised; and duplicated reporting is not independent corroboration.

## Product objective

The platform should answer:

- Which organizations show a current or emerging cybersecurity need?
- What independent evidence supports or contradicts that need?
- Is the signal explicit buying intent, urgency, transformation, renewal timing, product risk, provider displacement, or only a weak lead?
- Which services or products fit the evidence?
- Which professional roles and lawful business contact channels are relevant?
- What should a human analyst do next?

The product covers the complete canonical cybersecurity service taxonomy rather than treating SIEM/SOC as the default need.

## Current validated product baseline

The current validated product release is version `0.24.0`, covering normal product lots `00` through `24`.

That historical bounded-context baseline includes:

- source governance, provider onboarding, retention, suppression, provenance and durable source/runtime controls;
- PostgreSQL persistence, reversible migrations, scheduler/worker/checkpoint/retry/recovery mechanics;
- procurement and hiring intelligence;
- French/European organization identity and temporal entity resolution;
- canonical vulnerability, incident, threat-telemetry, passive-exposure, advisory/applicability, corporate-change and relationship intelligence;
- governed professional context and conditional-provider control planes;
- governed analyst research orchestration with explicit manual/automated execution boundaries;
- generalized signal fusion and cybersecurity need hypotheses across the 19 canonical service families and 12 canonical hypothesis classes, with independent-source/corroboration groups, contradiction and negative evidence, freshness/expiry, weak-research boundaries, rule/taxonomy versioning and source-contribution explanations.

Lot `24` remains the latest historically `IMPLEMENTED_VALIDATED` normal product lot; it is not the next planned lot. The next sequential product lot is **Lot 25 — Advanced scoring, calibration, explainability, and feedback**.

A later cross-module audit found an important finality boundary that the local Lots 13–24 validations did not close: the runtime does not yet guarantee one durable automatic chain from every canonical change through applicability/relationships/graph/signals/hypotheses/opportunities **and the reverse invalidation chain for correction, retraction, expiry, suppression, deletion and identity changes**. That composed property is now explicit mandatory **Lot 28** scope tracked by issue #171. The historical lot numbers are not reopened, but their cross-lot reactive finality must not be represented as already complete.

## Product roadmap truth

[`docs/PROJECT_DELIVERY_PLAN.md`](docs/PROJECT_DELIVERY_PLAN.md) is the authoritative normal-product roadmap. The post-SA16 orphan audit and ownership repair is recorded in [`docs/PRODUCT_LOT_ORPHAN_RECONCILIATION.md`](docs/PRODUCT_LOT_ORPHAN_RECONCILIATION.md).

- Lots `00–24`: historical `IMPLEMENTED_VALIDATED` bounded-context baseline.
- Lots `25–27`: advanced scoring/calibration, native commercial operations, and Company 360/analyst workspace.
- Lot `28`: data quality, reconciliation, lineage and publication gates **plus the mandatory derived-state reconciliation/reactive invalidation recovery L01–L12 tracked by issue #171**.
- Lot `29`: supply-chain/release provenance/repository protection, including the historical Starlette/TestClient dependency-maintenance path.
- Lot `30`: observability, performance, resilience and recovery **plus the historical DNS-resolution-pinning / DNS-rebinding hardening residual**.
- Lot `31`: **end-to-end privacy rights, lawful-basis operations, correction/restriction/erasure and deletion propagation**.
- Lot `32`: controlled pilot and production gate, only after mandatory Lots 28, 30 and 31 have passed their own exit gates.

The old deferred Lot 31 browser/download scope is not future product work anymore. The browser/authentication/download runtime was subsequently implemented through SA-16. It must not be rebuilt as a competing normal-product runtime.

## Source Activation is separate

Product implementation does not itself activate a provider. Provider/source activation is a separate governed programme under [`docs/source_activation/`](docs/source_activation/).

A modeled source, adapter, browser runtime or research option is not automatically authorized, entitled, scheduled or live-tested. Provider execution requires the exact applicable Source Governance, target/purpose/category, onboarding, secret/identity, entitlement, storage/use rights, capability, quota/cost, schedule and live-proof gates.

SA-16 materially delivered the governed company-web/browser/authentication acquisition layer: automatic governed targets/schedules, recursive bounded public acquisition, semantic and structured extraction, bounded Chromium fallback, rendered network/script-state capture, reviewed browser actions, screenshots, controlled downloads/quarantine, delegated identities, reviewed login/session reuse, OAuth/OIDC/SSO and durable human checkpoints. Provider-specific execution remains separately authorized, and CAPTCHA/MFA/provider-security controls remain hard stop/resume boundaries rather than bypass targets.

SA-21 now owns the previously orphaned source-activation recovery items. That source-activation ownership must not be confused with normal product Lot 28/30/31 ownership. No SA-22 is created for the derived-state reconciliation gap because it is a normal product architecture responsibility.

## Evidence flow

Target product flow:

```text
source candidate
  -> source governance / onboarding / executable capability
  -> governed collection or approved ingestion
  -> immutable source record / RawObservation / claim
  -> canonical evidence and resolution
  -> commercial signal
  -> need hypothesis
  -> explainable score
  -> alert / task / company workspace / opportunity
  -> analyst decision and outcome feedback
```

The current `0.24.0` bounded contexts implement the individual layers, but the **platform-wide automatic propagation/invalidation guarantee between all of those layers is not yet final**. Lot 28 owns the durable canonical-change outbox, dependency-driven/time-driven reconciliation, desired-set invalidation, incremental/backfill/replay convergence and publication-readiness proof needed to make this diagram an ordinary runtime invariant rather than a sequence that is only correct when every necessary local recompute happens to be invoked.

Important invariants:

```text
CVE != organization applicability != verified exposure
IOC != compromise
attacker allegation != official confirmation
passive technology observation != vulnerability applicability
research result != evidence unless canonical provenance is validated
evidence != signal != need != opportunity
contact relevance != outreach authorization
```

## Product access model

The ordinary read experience does not require visitor registration. Collection is centralized and uses approved public feeds, official APIs, open-data sources, licensed providers and governed platform identities. Anonymous visitor sessions are never reused as identities on external services.

The product is database-first: ordinary page views read stored/indexed evidence and do not silently crawl providers on demand. Deployment-protected control-plane actions are explicit, audited and still subject to the relevant source/provider/runtime authorization.

## Architecture

The backend is a Python 3.12 modular monolith using FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic and durable scheduler/worker orchestration. The analyst interface is a Next.js application under `apps/web`.

Dependencies point inward:

```text
API / CLI / composition
  -> application
  -> domain

infrastructure implements application ports
```

Domain modules cannot depend on FastAPI, SQLAlchemy models, adapters, API packages or infrastructure implementations.

Canonical provider payloads never write directly to company, score, alert or opportunity projections.

Lot 28 must preserve that rule: provider adapters emit governed source-native/canonical data, while a separate durable reconciliation layer reacts to committed canonical changes through application-level projector contracts. The fix must not introduce provider-specific direct graph/hypothesis/opportunity writes or cross-module infrastructure shortcuts.

## Quality gates

Every pull request must pass on one final SHA:

1. dependency consistency and security audits;
2. Ruff;
3. strict Mypy;
4. architecture, complexity, dependency, safety, release and roadmap contracts;
5. reversible PostgreSQL migrations;
6. backend branch-aware coverage at or above the repository threshold;
7. frontend dependency audit, TypeScript typecheck and production build.

Core code limits include:

- handwritten Python file: maximum 400 lines;
- function/method: maximum 120 lines;
- class: maximum 300 lines;
- function parameters: maximum 10;
- control-flow nesting: maximum 6;
- React component: maximum 300 lines;
- no test/coverage weakening merely to pass CI.

Normal-lot documentation has an explicit **no-orphan rule**: every useful accepted limitation must be owned by a named later product lot, a named Source Activation lot, or an explicit product/security/legal exclusion. Generic `future hardening`, `manual`, `blocked` or `deferred` wording is not sufficient ownership by itself.

For derived-state correctness, `works when explicitly recomputed`, `refresh endpoint exists`, `domain reconciler is correct when invoked`, or `local tests pass` is also not sufficient terminal evidence. Ordinary runtime propagation, reverse invalidation, time transitions and replay convergence must be proven.

## Source and data safety

Never commit API keys, sessions, prospect lists, collected personal data, proprietary datasets or production evidence. Tests use synthetic, provider-published, minimized, licensed or redistributable fixtures.

The platform does not:

- interact with threat actors or enter victim negotiation portals;
- download victim files, stolen datasets or malware merely for collection;
- validate leaked credentials;
- bypass authentication, paywalls, CAPTCHA, MFA, invitations or access controls;
- actively scan, probe, exploit or credential-test prospects;
- create fake accounts or cycle identities after bans;
- use proxy rotation for access-control evasion;
- perform autonomous outreach;
- treat a source/provider/account/licence/dossier as execution authorization by itself;
- turn a research result or weak observation directly into a commercial conclusion.

## Current orphan-reconciliation ownership

### Lot 28 — Derived-state reconciliation and reactive invalidation

[`docs/lots/LOT_28_DERIVED_STATE_RECONCILIATION_RECOVERY.md`](docs/lots/LOT_28_DERIVED_STATE_RECONCILIATION_RECOVERY.md) is the canonical amendment. Implementation is tracked by issue #171.

Lot 28 owns the missing composed finality across the already implemented bounded contexts, including:

- transactional canonical-change outbox and durable idempotent reconciliation jobs;
- explicit dependency routing;
- automatic applicability/relationship/graph reconciliation;
- versioned canonical-to-commercial signal synthesis with truth-preserving no-upgrade rules;
- desired-set need-hypothesis invalidation, including zero-result withdrawal/expiry;
- migration away from the legacy SIEM/SOC private orchestration path into one generalized pipeline;
- separation of analyst workflow state from generated-basis currentness;
- time-only expiry/staleness/validity sweeps;
- incremental/backfill/shuffled replay/restore convergence;
- `current / stale / reconciling / failed` readiness and publication gates;
- exact-head E2E proof of both forward propagation and reverse invalidation.

The current release is still `0.24.0`; this work targets Lot 28 / `0.28.0` and does not make the current package pretend to be newer.

### Lot 30 — DNS/address safety

The historical Lot 12 DNS-resolution-pinning risk is now explicitly owned by Lot 30 and tracked in [`docs/lots/LOT_30_NETWORK_HARDENING_AMENDMENT.md`](docs/lots/LOT_30_NETWORK_HARDENING_AMENDMENT.md).

Lot 30 must prove a shared fail-closed outbound-address policy across static HTTP, browser-backed acquisition, authenticated flows, redirects/retries/reconnects and controlled downloads. An authorized hostname must never become permission to reach loopback/private/link-local/reserved or otherwise forbidden addresses through DNS rebinding, CNAME/address-family tricks or stale connection authorization. TLS hostname verification and source host/path authorization must not be weakened to implement the defense.

### Lot 31 — Privacy rights and deletion propagation

[`docs/lots/LOT_31_PRIVACY_RIGHTS_AND_DELETION_PROPAGATION.md`](docs/lots/LOT_31_PRIVACY_RIGHTS_AND_DELETION_PROPAGATION.md) is the canonical detailed scope.

Lot 31 owns:

- processing-purpose/data-category/lawful-basis state and legitimate-interest references where applicable;
- protected rights-request API/UI, ownership, due dates, SLA/escalation and completion evidence;
- access/rectification/erasure/objection/restriction and applicable export/portability workflows;
- suppression keys and non-resurrection before ingestion, replay, backfill, resolution, projection publication and restore;
- correction/restriction/deletion propagation across product-owned database records, read models, caches/indexes, exports and commercial/engagement projections;
- invalidation/recomputation of downstream signals, needs, scores, opportunities and contact recommendations when their data basis changes;
- connector-aware upstream propagation where supported, explicit local suppression where upstream mutation is unavailable, and durable per-destination status;
- audit proof without retaining the deleted personal payload;
- jurisdiction/channel/transfer matrix and operator/privacy-incident runbooks.

Lot 31 cannot be marked complete while deleted personal data can silently reappear after fresh ingestion, replay, projection rebuild, cache/index refresh, export or backup restoration.

## Local development

Requirements:

- Python 3.12;
- Node.js 24;
- Docker with Compose.

```bash
cp .env.example .env
docker compose up -d postgres
python -m pip install -e '.[dev]'
alembic upgrade head
uvicorn cip.main:app --reload
```

In separate terminals:

```bash
cip-scheduler
cip-worker
```

Frontend:

```bash
cd apps/web
npm install
npm run dev
```

## Validation commands

```bash
python -m pip check
pip-audit --skip-editable
ruff check .
mypy
pytest tests/architecture
alembic upgrade head
alembic downgrade base
alembic upgrade head
pytest --cov=cip --cov-branch --cov-report=term-missing --cov-fail-under=90
```

```bash
cd apps/web
npm audit --audit-level=high
npm run typecheck
npm run build
```

## Key project documents

- [`docs/PRODUCT.md`](docs/PRODUCT.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md)
- [`docs/COMMERCIAL_INTELLIGENCE_INTEGRATION_ARCHITECTURE.md`](docs/COMMERCIAL_INTELLIGENCE_INTEGRATION_ARCHITECTURE.md)
- [`docs/CYBER_SERVICE_NEED_TAXONOMY.md`](docs/CYBER_SERVICE_NEED_TAXONOMY.md)
- [`docs/SOURCE_POLICY.md`](docs/SOURCE_POLICY.md)
- [`docs/OSINT_COLLECTION_CATALOG.md`](docs/OSINT_COLLECTION_CATALOG.md)
- [`docs/LIVE_CYBER_THREAT_SOURCE_CATALOG.md`](docs/LIVE_CYBER_THREAT_SOURCE_CATALOG.md)
- [`docs/DEVELOPMENT_STANDARDS.md`](docs/DEVELOPMENT_STANDARDS.md)
- [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md)
- [`docs/SOURCE_INTEGRATION_TEST_MATRIX.md`](docs/SOURCE_INTEGRATION_TEST_MATRIX.md)
- [`docs/PROJECT_DELIVERY_PLAN.md`](docs/PROJECT_DELIVERY_PLAN.md)
- [`docs/PRODUCT_LOT_ORPHAN_RECONCILIATION.md`](docs/PRODUCT_LOT_ORPHAN_RECONCILIATION.md)
- [`docs/LOT_24_SIGNAL_FUSION_CLOSEOUT.md`](docs/LOT_24_SIGNAL_FUSION_CLOSEOUT.md)
- [`docs/lots/LOT_28_DERIVED_STATE_RECONCILIATION_RECOVERY.md`](docs/lots/LOT_28_DERIVED_STATE_RECONCILIATION_RECOVERY.md)
- [`docs/lots/LOT_28_REACTIVE_RECONCILIATION_MICROLOTS.md`](docs/lots/LOT_28_REACTIVE_RECONCILIATION_MICROLOTS.md)
- [`docs/lots/LOT_28_DEPENDENCY_INVALIDATION_MATRIX.md`](docs/lots/LOT_28_DEPENDENCY_INVALIDATION_MATRIX.md)
- [`docs/lots/LOT_28_IMPLEMENTATION_GAP_AUDIT.md`](docs/lots/LOT_28_IMPLEMENTATION_GAP_AUDIT.md)
- [`docs/lots/LOT_30_NETWORK_HARDENING_AMENDMENT.md`](docs/lots/LOT_30_NETWORK_HARDENING_AMENDMENT.md)
- [`docs/lots/LOT_31_PRIVACY_RIGHTS_AND_DELETION_PROPAGATION.md`](docs/lots/LOT_31_PRIVACY_RIGHTS_AND_DELETION_PROPAGATION.md)
- [`docs/source_activation/SA_16_COMPLETION_AUDIT_AND_REMAINING_LOTS.md`](docs/source_activation/SA_16_COMPLETION_AUDIT_AND_REMAINING_LOTS.md)
- [`docs/source_activation/SA_21_ORPHANED_SOURCE_ACTIVATION_RECOVERY.md`](docs/source_activation/SA_21_ORPHANED_SOURCE_ACTIVATION_RECOVERY.md)
- [`SECURITY.md`](SECURITY.md)