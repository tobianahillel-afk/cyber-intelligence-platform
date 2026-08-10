# SA-13 — Extended ATS acquisition and controlled live validation

## Result

SA-13 adds provider-specific public hiring adapters for Ashby, Recruitee and Teamtailor while reusing the existing collection scheduler/worker, immutable raw-observation path and canonical public-job mapping.

The implementation does not treat documentation or adapter presence as proof of live integration.

## Ashby

Source id: `ashby-job-board`.

Acquisition uses Ashby's documented public Job Postings API under `https://api.ashbyhq.com/posting-api/job-board/{board}` with no authentication. Collection is GET-only and target-bound. The adapter requests no compensation data, ignores unlisted jobs, validates the provider schema, enforces response and job-count bounds, fingerprints jobs for checkpoint/idempotence and maps only public posting metadata through `CanonicalPublicJob`.

Controlled live validation uses the provider's public `Ashby` board. The first successful provider proof retrieved 59 public jobs through the real `AshbyAdapter`. The real result contained no cyber-relevant posting under the current canonical classifier, so zero commercial projections were created; absence of a cyber match is preserved rather than converted into a synthetic signal.

## Recruitee

Source id: `recruitee-careers-site`.

Acquisition uses the unauthenticated Careers Site API `https://{company}.recruitee.com/api/offers/`. Candidate creation, applicant data and the authenticated ATS API are outside this adapter. The provider's structured department/location fields are normalized into the existing canonical job model.

The first live attempt correctly failed closed on a provider timestamp variant (`YYYY-MM-DD HH:MM:SS UTC`). The adapter was then changed to normalize only that UTC provider form plus the already accepted timezone-aware representation, and a deterministic regression test locks the observed format.

The subsequent controlled live proof used the configured public `peopleforpeople.recruitee.com` careers site and retrieved one public job through the real `RecruiteeAdapter`. The posting was not cyber-relevant, so no commercial signal was invented.

## Teamtailor

Source id: `teamtailor-public-jobs`.

The adapter implements Teamtailor's JSON:API public-jobs path, required `X-Api-Version`, bounded pagination, regional API hosts and an account-specific `Public + Read` token supplied only through the existing Provider Onboarding secret-reference path.

The checked-in Teamtailor account registry remains empty and its schedule disabled. Therefore the activation record is truthful: `catalogued`, `reviewed`, `mapped`, `adapter_present`, `authorized`, but not `executable`, `scheduled` or `live_tested`. A deployment must supply one reviewed account and its Public Read token before those stages can be promoted.

## Runtime and evidence boundaries

All three adapters reuse the existing collection runtime. SA-13 introduces no second scheduler, worker, source health subsystem or hiring persistence silo.

Provider payloads remain inside provider adapters. Surviving public postings are normalized through the existing canonical hiring path before any commercial projection. A job posting can support a capability/program signal only when the canonical classifier actually matches its content; provider presence alone never creates a need, score, opportunity, contact target or outreach action.

No application forms, resumes, screening data, candidate records, write endpoints, private data, browser automation, CAPTCHA/MFA handling or authentication bypass are part of SA-13.

## Controlled live validation

The dedicated workflow `.github/workflows/sa13-live-validation.yml` executes `scripts/live_validate_sa13.py` against the real approved public Ashby and Recruitee endpoints. It instantiates the production adapters, not provider-specific test clients, and requires non-empty provider checkpoints while printing only aggregate counts.

Successful proof observed before final reconciliation:

- workflow run `31439468235`;
- Ashby public jobs retrieved: `59`;
- Recruitee public jobs retrieved: `1`;
- cyber-relevant projections: `0` for both sources, truthfully preserved.

Because every code or documentation commit invalidates exact-head proof, the workflow is configured to rerun on every change to this PR. The final merge gate requires both the normal repository CI and the live workflow to pass on the final PR head.

## Completion gate

SA-13 may be squash-merged only when:

1. Ashby and Recruitee have provider-specific real adapters, runtime registration, source governance, portfolio entries, enabled schedules and controlled live proof;
2. Teamtailor has a real secret-aware adapter path but remains non-live until a deployment Public Read account/token exists;
3. Source Activation truth exposes Ashby/Recruitee as fully integrated and Teamtailor as an active unresolved integration rather than manufacturing green stages;
4. deterministic adapter, governance, checkpoint, schema, runtime and activation tests pass;
5. Ruff, strict Mypy, architecture/release tests, reversible migrations, the complete branch-aware coverage suite and frontend checks pass;
6. the dedicated live provider workflow passes on the exact final PR head;
7. reviews and review threads are clear before squash merge.
