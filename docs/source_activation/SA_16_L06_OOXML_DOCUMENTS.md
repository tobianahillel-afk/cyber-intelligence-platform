# SA-16 L06 — Bounded Office Open XML document extraction

## Status

`FINAL_EXACT_HEAD_REVALIDATION_PENDING`.

L06 extends the merged SA16-L01/L02/L03/L04/L05 governed public-web path with bounded extraction of macro-free Office Open XML documents: DOCX, XLSX and PPTX.

The pre-documentation implementation candidate `14ef28d1d811fb4f10e1cb24086ca6e3a7645cd6` passed complete repository CI and the dedicated real-network SA-16 L06 workflow against a public Microsoft OfficeDev DOCX fixture retrieved through the production `PublicWebClient` and collector.

Because this closeout document changes the pull-request content tree, those runs are candidate evidence only. The documentation head produced by this commit must independently repeat complete CI and the dedicated live workflow before merge.

L06 does not add arbitrary ZIP extraction, macro-enabled Office formats, VBA execution, relationship traversal, embedded-object execution, JavaScript/browser rendering, authenticated navigation, CAPTCHA/MFA automation or anti-bot bypass behavior.

## Capability

```text
approved public-web document URL
-> existing governed HTTP collection
   -> source policy / crawl scope / budgets
   -> bounded response body
   -> exact response MIME or bounded OOXML detection for application/octet-stream
-> OOXML package validation
   -> ZIP structure and expansion limits
   -> safe entry paths
   -> no duplicate or encrypted entries
   -> no VBA payloads
   -> exact [Content_Types].xml main-part match
   -> DTD/ENTITY rejection before XML parsing
-> bounded type-specific extraction
   -> DOCX document text
   -> XLSX shared/inline/string cell text
   -> PPTX slide text
   -> optional bounded core-properties title
-> existing PublicResource / PublicResourceVersion
   -> DOCUMENT resource kind
   -> content hash / byte size / MIME / excerpt / extracted-text hash
-> existing PublicClaim projection
-> existing durable public-web checkpoint
```

The OOXML package is parsed only as an untrusted bounded document container. Relationships, embedded payloads, macros and active content are not followed or executed.

## Supported document types

L06 admits only the three macro-free OOXML MIME types:

- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (`.docx`);
- `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (`.xlsx`);
- `application/vnd.openxmlformats-officedocument.presentationml.presentation` (`.pptx`).

The public-web client advertises these types in its normal document `Accept` header. Existing PDF and plain-text behavior remains unchanged.

When a provider returns `application/octet-stream`, L06 may normalize the representation to one of the supported OOXML MIME types only when all of the following hold:

1. the body is a bounded ZIP package;
2. the URL path has the matching macro-free OOXML extension;
3. the package contains `[Content_Types].xml`;
4. the expected OOXML main part exists;
5. the content-type override for that exact main part matches the expected package type;
6. archive safety validation succeeds.

Extension alone is therefore not treated as sufficient evidence of document type.

## Package bounds

`ooxml_parsing.py` applies explicit limits before or during extraction:

- maximum compressed package size: 5,000,000 bytes;
- maximum ZIP entries: 256;
- maximum total uncompressed size: 20,000,000 bytes;
- maximum individual entry size: 2,000,000 bytes;
- maximum per-entry compression ratio: 100:1;
- maximum extracted text: 100,000 characters;
- maximum extracted core title: 1,000 characters;
- ZIP64 is not enabled for parsing.

These limits are independent of and additional to the existing public-web target and response budgets.

## Archive and XML safety invariants

L06 rejects an OOXML package when any governed parser invariant fails, including:

- empty or oversized package;
- non-ZIP or malformed ZIP payload;
- missing/invalid required main part;
- MIME/package-type mismatch;
- unsafe absolute or parent-traversal ZIP paths;
- duplicate ZIP entry names;
- encrypted ZIP entries;
- `vbaProject.bin` macro payloads;
- per-entry size overflow;
- total expansion overflow;
- excessive compression ratio;
- malformed required XML;
- XML containing `DOCTYPE` or `ENTITY` declarations.

The parser never executes document content and never follows OOXML relationships to acquire additional network resources.

## Type-specific minimized extraction

### DOCX

Only text nodes from `word/document.xml` are collected for the canonical text projection. A present `docProps/core.xml` title may provide the canonical document title after whitespace normalization and the explicit title bound.

### XLSX

L06 reads worksheet cell values only from bounded worksheet XML parts. It supports:

- shared-string references when a valid shared-string index exists;
- inline strings;
- string-valued cells.

Invalid shared-string indices and unsupported/non-string cell forms do not become fabricated text.

### PPTX

L06 reads text nodes from bounded `ppt/slides/slide*.xml` parts in deterministic sorted order.

### Missing metadata

A missing or blank core title remains `None`. L06 does not invent a title from the filename or body text.

## Canonical mapping and provenance

L06 reuses the existing public-footprint model and projection path. It does not add an OOXML-specific canonical data store.

- DOCX/XLSX/PPTX responses map to `PublicResourceKind.DOCUMENT`.
- `PublicResourceVersion.mime_type` preserves the validated macro-free OOXML MIME type.
- `byte_size` records the bounded fetched package size.
- the normal resource content hash is calculated from the fetched package bytes.
- extracted text produces the existing `extracted_text_hash_sha256` and bounded excerpt.
- the normal source locator, discovery lineage, collection timestamps, retention and checkpoint behavior remain authoritative.
- normal public-web claim projection consumes the minimized extracted text rather than a raw opaque Office payload.
- raw Office package contents are not introduced as an unrestricted parallel evidence store by L06.

## Governance boundary

Supporting a document MIME type does not expand acquisition authority.

L06 remains behind the existing Source Governance and public-web scope controls:

- approved source entry;
- approved host/origin and path scope;
- robots policy where applicable;
- redirect validation;
- page/resource/byte/time budgets;
- same-origin and discovery constraints;
- retention and canonical evidence rules.

An OOXML document can therefore be parsed only after the existing governed collector has legitimately acquired it inside the target scope.

## Deterministic validation

The L06 deterministic tests prove, among other cases:

1. representative DOCX, XLSX and PPTX packages produce bounded canonical extracted text;
2. an octet-stream response is promoted to an OOXML MIME only when extension and internal content type agree;
3. unsupported MIME, empty, oversized and non-ZIP payloads are rejected;
4. malformed ZIP packages are converted to safe parser failures;
5. duplicate ZIP entries are rejected;
6. missing main parts or content-type declarations are rejected;
7. missing or blank core title remains unset;
8. invalid XLSX shared-string indices are ignored without fabricating values;
9. malformed or incomplete packages are not accepted by MIME detection;
10. high-compression-ratio packages are rejected;
11. malformed required XML is rejected;
12. unsafe paths, encrypted content, macro-bearing packages and forbidden XML declarations are rejected;
13. extraction remains bounded for package, entry, expansion, title and text limits;
14. existing public-web resource classification and canonical projection behavior include only the supported OOXML types.

The repository quality gates additionally enforce architecture, file/function size, type, dependency, migration, frontend and branch-aware coverage requirements.

## Validation history

### Implementation hardening

L06 was developed as a bounded parser inside the existing public-web adapter rather than by adding a generic archive execution facility.

The implementation hardened several ambiguous or unsafe cases instead of weakening the project contracts:

- macro-enabled or macro-bearing packages are rejected rather than partially trusted;
- MIME normalization from `application/octet-stream` requires internal OOXML package validation rather than extension-only guessing;
- duplicate, encrypted and traversal-capable archive entries are parser failures;
- XML entity/DTD declarations are rejected before `ElementTree` parsing;
- relationships, embedded objects and active content are intentionally outside this lot;
- malformed metadata does not create guessed canonical fields;
- architecture/test line-size requirements were satisfied without lowering repository gates.

### Validated pre-documentation candidate — `14ef28d1d811fb4f10e1cb24086ca6e3a7645cd6`

Normal CI #2059 (`31692883828`) passed on the candidate content.

Backend evidence from that run includes:

- dependency consistency: PASS;
- Python dependency audit: no known vulnerabilities;
- Ruff: PASS;
- strict Mypy: PASS on 704 source files;
- architecture/release contracts: 36 passed;
- reversible PostgreSQL migration cycle: PASS;
- backend suite: 1,532 passed;
- branch-aware repository coverage: 90.05%;
- frontend dependency audit: PASS;
- frontend TypeScript typecheck: PASS;
- frontend Next.js production build: PASS.

SA-16 L06 Live Validation #11 (`31692883768`) passed on that exact pull-request head. The workflow explicitly checked out `14ef28d1d811fb4f10e1cb24086ca6e3a7645cd6` rather than the synthetic pull-request merge commit.

The controlled live surface was:

- URL: `https://raw.githubusercontent.com/OfficeDev/Word-Add-in-MarkdownConversion/master/TestWordDocument.docx`;
- provider/context: public Microsoft OfficeDev sample document hosted on GitHub raw content;
- validated MIME: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`;
- fetched bytes: 16,605;
- canonical resource kind: document;
- non-empty extracted-text hash and excerpt: proven;
- checkpoint representation MIME: proven.

The observed excerpt began with:

`A Sample Document (first level header) This document has it all; bolded text, italicized text, bookmark links, a web lin...`

The live fixture had no usable core-properties title, so the canonical title correctly remained unset rather than being fabricated.

These CI and live runs are pre-documentation candidate evidence. They do not substitute for exact validation of the documentation head created by this closeout commit.

## Controlled real-network validation contract

`scripts/live_validate_sa16_l06.py` exercises a real public DOCX through an automatically provisioned governed target and the production `PublicWebClient`/collector path.

The workflow succeeds only if the controlled run proves:

- exactly one public-web observation and canonical projection for the target document;
- `PublicResourceKind.DOCUMENT` classification;
- exact validated DOCX MIME;
- non-zero body size within the 5 MB lot budget;
- non-empty bounded extracted text and extracted-text hash;
- durable checkpoint representation metadata for the same document.

The live workflow fails when those production-path conditions are not satisfied. Unit fixtures, mocks, a previous SHA or a pull-request merge ref do not satisfy the live gate.

## Out of scope for L06

L06 intentionally does not implement:

- `.docm`, `.xlsm`, `.pptm` or legacy binary Office formats;
- VBA or Office macro execution;
- OLE/ActiveX/embedded-object execution;
- OOXML relationship traversal or external-resource fetching;
- generic ZIP/archive ingestion;
- Apache Tika or ExifTool;
- OCR or image extraction;
- browser-rendered acquisition;
- authenticated-web acquisition;
- reverse-image/visual research.

Those broader document/browser/media capabilities remain owned by the later SA-16/SA-20 roadmap decomposition.

## Exit gate

L06 is complete only when the final documentation pull-request head has all of the following on that exact content:

1. frontend audit/typecheck/build green;
2. dependency consistency and Python audit green;
3. Ruff green;
4. strict Mypy green;
5. architecture/release contracts green;
6. reversible migrations green;
7. complete backend tests and branch-aware coverage >= 90% green;
8. the SA-16 L06 controlled real-network OOXML workflow green;
9. zero unresolved actionable review threads;
10. PR mergeability confirmed;
11. squash-merged Git tree proven identical to the validated final head tree.

Until those conditions hold, this document intentionally keeps L06 at `FINAL_EXACT_HEAD_REVALIDATION_PENDING` rather than claiming completion.
