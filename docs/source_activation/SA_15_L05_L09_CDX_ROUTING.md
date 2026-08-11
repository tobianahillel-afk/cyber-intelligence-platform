# SA-15 L05/L09 — Internet Archive CDX and governed SERP acquisition routing

## Status

Implemented for SA15-L05 and SA15-L09. Merge is permitted only after the exact final PR head passes both the normal repository CI and the dedicated `SA-15 Live Validation` provider workflow.

A skipped live job is never provider proof.

## SA15-L05 — Internet Archive CDX

### Production path

CIP reuses the production `InternetArchiveCdxAdapter` introduced during SA-02 rather than creating a validation-only provider implementation.

The governed source remains `internet-archive-cdx` at `https://web.archive.org/cdx/search/cdx`. Collection is bounded to CDX index metadata and keeps archived page-body retrieval outside this source path.

The adapter requests only:

- capture timestamp;
- original URL;
- MIME type;
- HTTP status code;
- digest;
- archived length.

The result remains a quarantined `ARCHIVE_SNAPSHOT` with zero automatic claims. Historical presence is not treated as current deployment, current vulnerability, current commercial need, or outreach authority.

### Controlled live target

The dedicated SA-15 live workflow executes the real production adapter against an exact first-party Internet Archive URL:

`https://archive.org/about/terms.php`

The exact URL is intentionally narrower than a host/prefix crawl so the provider proof tests the production CDX contract without turning the validation job into bulk archive enumeration.

The live gate requires:

- at least one and at most 50 real CDX observations;
- one quarantined archive projection per observation;
- zero claims;
- zero archived-body retrieval;
- preserved Wayback capture provenance;
- a converged single-target checkpoint.

The initial broad root-URL validation attempt was not accepted as proof because the provider request exceeded its original 30-second network window. The validation target was narrowed to the exact first-party URL and the controlled provider run then succeeded. The final merge candidate must repeat that success on its exact final SHA after all activation/documentation changes.

### Activation truth

`internet-archive-cdx` may carry `live_tested` only while an exact-head real-provider run of `scripts/live_validate_sa15_cdx.py` succeeds. The checked-in activation inventory now records this stage and a deterministic regression test prevents entitlement-gated Brave, Mojeek and PatentsView sources from being promoted by association.

## SA15-L09 — acquisition routing and consolidation

### Input boundary

L09 consumes the normalized `SearchDiscoveryCandidate` objects introduced by SA15-L01. Those candidates contain SERP discovery lineage and remain non-evidentiary until the discovered URL is retrieved through an approved acquisition path.

### Automatic public-web route

A candidate may be routed automatically to `PUBLIC_WEB` only when all of the following are true:

1. a checked-in/runtime `PublicWebTarget` belongs to the same canonical organization;
2. the target authorization is currently executable and not expired;
3. the candidate URL is same-origin with that target;
4. the URL falls inside the target crawl-scope path controls and current crawl budget admission rules;
5. exactly one governed target matches.

Successful routing changes the candidate state to `ROUTED_PUBLIC_WEB` and carries the governed target id. The router chooses an acquisition path; it does not itself fetch the resource or create Evidence.

### Source-review route

If the candidate is off-origin, out of the approved path scope, or has no currently executable organization-bound target, it changes to `REQUIRES_SOURCE_REVIEW`.

That state is intentionally fail-closed: CIP must review/onboard an appropriate source or target before retrieval rather than using a generic unrestricted HTTP fetch.

Ambiguous multiple-target matches fail closed with an error instead of selecting one arbitrarily.

## Invariants retained

- search-result metadata is discovery lineage, not a confirmed company fact;
- CDX index metadata proves a historical capture record, not the current contents of a page;
- neither L05 nor L09 creates a CommercialSignal, NeedHypothesis, Opportunity, contact target, or outreach authorization directly;
- provider/source governance is evaluated before acquisition;
- external content remains untrusted;
- no credential, CAPTCHA, MFA, authentication, or access-control bypass is introduced by these microlots.

## Tests and final proof

Deterministic tests cover routing to an executable governed target, off-origin review, path rejection, expired authorization, duplicate-target ambiguity, route ordering, and truthful source-activation stages.

The authoritative final proof is the exact-head GitHub Actions result on PR #123. Any content change after a successful provider/CI run requires both gates to run again before merge.
