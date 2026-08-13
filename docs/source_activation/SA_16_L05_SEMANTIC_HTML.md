# SA-16 L05 — Bounded semantic HTML and structured-data extraction

## Status

`FINAL_EXACT_HEAD_REVALIDATION_PENDING`.

L05 extends the merged SA16-L01/L02/L03/L04 static public-web path with bounded extraction of public semantic HTML metadata, JSON-LD and selected public embedded JSON state. The pre-documentation implementation candidate `0059f7c07b0efe6ab24095d7f69ef3df23cf1639` passed complete repository CI and the dedicated real-network SA-16 L05 workflow against a natural public Kubernetes documentation page.

Because this closeout document changes the pull-request content tree, those runs are candidate evidence only. The documentation head produced by this commit must independently repeat complete CI and the dedicated live workflow before merge.

L05 does not add browser rendering, JavaScript execution, authenticated navigation, CAPTCHA/MFA automation, browser-profile storage or anti-bot bypass behavior.

## Capability

```text
public HTML response
-> existing visible-text/title/lang/robots extraction
-> bounded semantic HTML extraction
   -> selected meta/OpenGraph/Twitter fields
   -> selected article timestamps
   -> bounded application/ld+json
   -> bounded application/json public state
-> normalized canonical PublicResourceVersion
   -> title fallback without overriding a real HTML <title>
   -> published_at / source_updated_at when supported
-> PublicClaim projection
   -> visible/meta-derived claims: TARGET_CONTENT
   -> JSON structured claims: STRUCTURED_DATA
-> extraction profile persisted in the durable public-web checkpoint
```

The raw JSON payload is not persisted as a new opaque evidence blob. L05 extracts only bounded, whitelisted scalar values needed by the canonical projection.

## Bounded semantic extraction

`semantic_html.py` applies explicit limits to structured extraction:

- at most 8 structured scripts per page;
- at most 50,000 characters considered per structured script;
- at most 128 extracted scalar values;
- maximum structured nesting depth of 12;
- maximum normalized scalar value length of 500 characters.

Supported structured script MIME types are `application/ld+json` and `application/json`. Malformed JSON is ignored for semantic extraction without crashing the normal page collection path.

Selected semantic metadata includes public description/title/site/application fields, OpenGraph/Twitter title and description fields, and article publish/modified timestamps. JSON structured extraction uses a bounded public-field allowlist rather than persisting arbitrary application state.

## Sensitive-key exclusion

Structured keys that indicate credentials or session material are rejected before scalar extraction. The blocked markers include token, secret, password/passwd, API-key variants, authorization, credential, session and cookie markers.

This is intentionally a minimization boundary: public embedded state may contain operational values that are technically visible in HTML but are not appropriate evidence for this pipeline. L05 does not treat page visibility as permission to persist arbitrary application state.

## Canonical mapping and provenance

L05 reuses the existing public-footprint canonical model rather than introducing a parallel semantic-data store.

- A real HTML `<title>` remains authoritative when present.
- OpenGraph/Twitter title can provide a fallback when the normal title is absent.
- Supported structured/public semantic timestamps populate existing `published_at` and `source_updated_at` fields.
- Claims derived from visible/semantic target content keep `ClaimEvidenceBasis.TARGET_CONTENT`.
- Claims derived from JSON-LD or allowed public embedded JSON use `ClaimEvidenceBasis.STRUCTURED_DATA`.
- Existing `noindex` behavior remains authoritative and suppresses semantic/structured claims together with other indexable page claims.

## Extraction-profile replay compatibility

L04 introduced durable HTTP validators. That creates a migration problem for an extraction-only enhancement: a legacy page whose HTTP body is unchanged could immediately return `304`, preventing the new L05 parser from ever seeing its existing HTML.

L05 therefore versions the extraction profile in the existing durable public-web checkpoint. Missing legacy values load as profile 1; L05 HTML projection is profile 2.

For a legacy HTML representation at profile 1:

1. the previous representation metadata remains available;
2. ETag/Last-Modified validators are omitted for one governed re-fetch of that page;
3. the same body may be re-projected with the new semantic extractor without inventing a different content hash;
4. the checkpoint advances to extraction profile 2;
5. subsequent recrawls resume the normal L04 conditional ETag/Last-Modified/304 path.

This is a processing-version migration, not evidence that the source content changed. Existing content-version identity can be reused while newly derivable claims are attached through the normal projection path.

## Safety invariants

- Source Governance, robots, same-origin/path scope, redirect limits and crawl budgets remain authoritative before and during acquisition.
- No structured payload authorizes additional URLs or acquisition scope.
- Raw structured JSON is not persisted as a new opaque evidence object.
- Secret/session-like keys are excluded from structured scalar extraction.
- Structured extraction limits prevent unbounded script count, recursion depth, scalar count or value size.
- Malformed JSON does not cause a source page to become a trusted structured record.
- `STRUCTURED_DATA` describes the evidence basis; it does not imply independent corroboration or provider authority.
- `noindex` remains authoritative for claim projection.
- No browser, authenticated-session, CAPTCHA/MFA or anti-bot bypass path is introduced.

## Deterministic validation

The L05 deterministic tests prove, among other cases:

1. OpenGraph/meta values and JSON-LD are extracted through their distinct evidence bases;
2. secret-like structured keys are not indexed;
3. malformed structured JSON does not break normal collection;
4. date-only, offset, UTC and naive structured timestamps normalize deterministically;
5. structured arrays/scalars are bounded and deduplicated;
6. script-count and nesting-depth limits are enforced;
7. `noindex` suppresses semantic and structured claims;
8. a legacy extraction-profile checkpoint causes one re-fetch/re-projection without the old validator;
9. the checkpoint then advances to profile 2 and normal conditional ETag/304 behavior resumes;
10. unchanged source bytes do not require a fabricated new content version merely because the extraction profile changed.

## Validation history

### Rejected synthetic live surfaces

Early L05 live attempts used HTTPBingo's `/base64` helper to serve deterministic HTML. Those attempts are not counted as production evidence:

- the first URL exceeded the canonical `source_locator` length bound;
- a compact URL initially omitted required Base64 padding and received HTTP 400;
- after correcting the encoding, the echo-style response still did not provide the natural semantic HTML behavior required for a strong L05 live proof.

The canonical `source_locator` limit and semantic assertions were not weakened. The live contract was changed to use natural public documentation pages instead of reflected synthetic HTML.

### Coverage correction

An intermediate implementation had all tests passing but branch-aware repository coverage of 89.97%, below the required 90.00% threshold. The threshold was not lowered. Additional deterministic tests were added specifically for L05 parser bounds, timestamp fallbacks, list/scalar handling and deduplication.

### Validated pre-documentation candidate — `0059f7c07b0efe6ab24095d7f69ef3df23cf1639`

Normal CI #2041 (`31689172023`) passed completely on the candidate content:

- dependency consistency: PASS;
- Python dependency audit: no known vulnerabilities;
- Ruff: PASS;
- strict Mypy: PASS on 703 source files;
- architecture/release contracts: 36 passed;
- reversible migrations: PASS;
- backend suite: 1512 passed;
- branch-aware repository coverage: 90.03%;
- `semantic_html.py` coverage: 94.17%;
- frontend dependency audit/typecheck/build: PASS.

SA-16 L05 Live Validation #5 (`31689172008`) passed on that exact head. The workflow explicitly checked out `0059f7c07b0efe6ab24095d7f69ef3df23cf1639` and exercised the production `PublicWebClient` and collector against natural public HTML.

The successful live surface was:

- URL: `https://kubernetes.io/docs/home/`;
- canonical title: `Kubernetes Documentation | Kubernetes`;
- structured claim: `kubernetes`;
- evidence basis: `STRUCTURED_DATA`.

That proves a real public page can enter the governed static public-web path and produce a canonical structured-data claim through the L05 extractor. These runs are pre-documentation evidence and do not substitute for validation of this documentation head.

## Controlled real-network validation contract

`scripts/live_validate_sa16_l05.py` tries a small deterministic set of natural public technical-documentation pages through governed automatic public-web targets. It uses the production `PublicWebClient` and collector and succeeds only if a real page produces:

- at least one observation and canonical projection;
- a non-empty canonical title;
- at least one `PublicClaim` whose evidence basis is `STRUCTURED_DATA`;
- extraction profile 2 persisted in the checkpoint.

Per-surface HTTP/policy/projection failures are recorded as diagnostics. The workflow fails if none of the real public pages satisfies the contract. A mock, a reflected synthetic HTML helper, a skipped workflow, a previous SHA or deterministic unit tests alone do not satisfy the live gate.

## Exit gate

L05 is complete only when the final documentation PR head has all of the following on that exact content:

1. frontend audit/typecheck/build green;
2. dependency consistency and Python audit green;
3. Ruff green;
4. strict Mypy green;
5. architecture/release contracts green;
6. reversible migrations green;
7. complete backend tests and branch-aware coverage >= 90% green;
8. the SA-16 L05 real-network natural-semantic-HTML workflow green;
9. zero unresolved review threads;
10. PR mergeability confirmed;
11. squash-merged Git tree proven identical to the validated final head tree.

Until those conditions hold, this document intentionally keeps L05 at `FINAL_EXACT_HEAD_REVALIDATION_PENDING` rather than claiming completion.
