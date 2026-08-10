# SA-05 — Governed local OSINT and Sherlock

Status: implementation contract for issue #87.

Reviewed on: 2026-08-10.

## Purpose

SA-05 turns selected local OSINT tooling into governed analyst capabilities without granting blanket authorization to every site, module or upstream supported by those tools. Local execution is still source acquisition: Source Governance, lawful purpose, target scope, retention and evidence semantics remain mandatory.

## Sherlock

Sherlock is implemented as a local-tool adapter that projects only public profile-presence metadata into the existing Lot 21 `professional_context` model.

The checked-in target registry is empty. A deployment target must explicitly provide:

- one existing canonical organization or professional person context;
- a bounded filename-safe username;
- one to twenty-five explicitly reviewed Sherlock site names;
- a lawful-basis reference, purpose, review timestamp and retention deadline;
- `enabled: true` only after that review.

The runtime also requires an absolute deployment-provided Sherlock executable and an explicitly approved version string. The adapter never installs Sherlock as an application dependency.

Execution uses an argv list with `shell=False`, Sherlock's native CSV report, `--print-found`, `--no-color`, an isolated temporary output directory, a bounded per-site timeout and explicit repeated `--site` arguments. It never enables Tor, proxies, browsing, response dumps, NSFW expansion or any username/site outside the reviewed target.

Only `Claimed` rows for the exact approved username and approved sites survive parsing. Returned profile URLs must be HTTPS and contain no embedded credentials. Output/schema/scope mismatches fail closed.

Every surviving result becomes a Lot 21 `PublicCommunityContext` with:

- `context_type = public_professional_profile_presence`;
- `CommunityAcquisitionMode.GOVERNED_LOCAL_TOOL`;
- `ProfessionalReviewState.REVIEW_REQUIRED`;
- `metadata_only = true`;
- confidence `0.5` because provider/site behavior can create false positives;
- the original public profile URL as source/provenance;
- the reviewed lawful basis and retention lifecycle.

A username match never creates a new `ProfessionalPersonReference`, never merges people and never proves that two profiles belong to the same human. The existing Lot 21 persistence path is reused; there is no Sherlock-specific database silo.

Sherlock results never directly authorize source automation or outreach and never create a commercial signal, need hypothesis, score, opportunity or contact target.

### Sherlock activation disposition

`source_id: sherlock-local` remains **planned / SA-05** with `catalogued`, `reviewed`, `mapped`, `adapter_present` while the repository has no reviewed deployment executable/version and no approved site/target set. This is intentional: implemented code is not equivalent to network authorization.

A deployment may move it to `authorized`/`executable` only after the exact binary/version and every target/site are reviewed. `live_tested` remains false until a controlled authorized live proof exists.

## Other named local OSINT frameworks

The repository catalogue names Amass, theHarvester, SpiderFoot, Recon-ng and Maltego. None can be granted blanket execution authority because each can aggregate multiple upstreams/modules with different licences, authentication requirements, commercial-use rules and active/passive behavior.

### Amass

`amass-local` is **blocked as a blanket local executor** in SA-05. Active enumeration/brute-force/probing modes are outside prospect policy. Provider-backed/passive modules must be decomposed into the already governed DNS/CT/RDAP/provider-specific paths before execution. Cloudflare DoH, Cert Spotter and RDAP remain independent evidence sources rather than being hidden behind Amass.

### theHarvester

`theharvester-local` is **blocked as a blanket local executor** in SA-05. It fans out to many search engines, APIs and data providers; each upstream requires its own authorization, quota, licence and evidence mapping. Approved search/archive and passive-provider paths must be used directly instead of granting the framework global authority.

### SpiderFoot

`spiderfoot-local` is **blocked as a blanket local executor** in SA-05. Its modules span passive APIs through potentially active network interactions. Module-by-module decomposition is required; prospect-facing active modules remain prohibited.

### Recon-ng

`recon-ng-local` is **blocked as a blanket local executor** in SA-05. Its marketplace/modules are separate acquisition paths and cannot inherit authorization from the framework. Only provider-specific modules separately mapped into Source Activation may execute.

### Maltego

`maltego-local` is **manual** in SA-05. It may be used by an analyst as a visualization/investigation client over already authorized evidence, but transforms/connectors do not become server-side automated acquisition without provider-specific review. Importing Maltego graph relationships never increases evidence confidence by itself.

## Completion contract

SA-05 closes only when:

1. the Sherlock adapter, target registry, bounded runner, deterministic CSV parser, Lot 21 mapping and Lot 21 persistence runtime exist;
2. checked-in Sherlock targets remain empty and therefore produce no network traffic;
3. username/site scope escape, unsafe URLs, unreviewed lawful basis and malformed result schemas fail closed;
4. `sherlock-local`, `amass-local`, `theharvester-local`, `spiderfoot-local`, `recon-ng-local` and `maltego-local` have explicit Source Activation dispositions and are represented in the Coverage Matrix;
5. no local-tool umbrella grants authorization to upstream modules/providers;
6. privacy semantics remain professional/business-only and prohibit de-anonymization/private-life profiling;
7. deterministic runtime/privacy/reconciliation tests pass;
8. one exact final SHA passes the complete backend and frontend CI;
9. review threads are clear;
10. `live_tested` stays false unless a separately authorized controlled live proof is recorded.

Only after the squash merge may SA-06 begin.
