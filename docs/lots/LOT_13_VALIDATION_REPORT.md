# Lot 13 validation report

## Decision

- Implementation: `IMPLEMENTED_VALIDATED`
- Release: `0.14.0`
- Production activation of additional vulnerability providers: `NOT AUTHORIZED`
- Organizational exposure inference: `FORBIDDEN FROM GLOBAL VULNERABILITY DATA ALONE`

## Validation rule

A validation result applies only to the exact pull-request head that produced it. Any later code, configuration, migration, test, version, or documentation commit invalidates the earlier result and requires a new complete CI run.

The authoritative final head SHA and successful workflow run are recorded in pull request #37 after the last commit. This report documents the required evidence and the validated behavior; it must not be interpreted independently of the final green PR run.

## Scope reviewed

The validation covers:

- canonical vulnerability domain objects;
- exact identifier and alias reconciliation;
- CVSS and EPSS representation;
- affected product ranges and precision;
- exploitation dimensions;
- immutable provider history;
- canonical projection persistence;
- migration `20260806_0013`;
- CISA KEV transactional worker integration;
- CVE.org, NVD, EPSS, OSV, GitHub Advisory, and CIRCL-compatible mappings;
- source-policy and source-portfolio governance;
- protected API list and detail contracts;
- Next.js vulnerability list and detail workspaces;
- architecture, typing, dependency, migration, backend, frontend, and coverage regression gates.

## Required CI gates

The final pull-request head must pass:

1. Python dependency installation and consistency;
2. Python vulnerability audit;
3. Ruff;
4. Mypy strict;
5. architecture, complexity, dependency, release, and roadmap contracts;
6. PostgreSQL `upgrade -> downgrade -> upgrade`;
7. complete pytest suite with branch instrumentation and configured aggregate coverage threshold of at least 90%;
8. frontend dependency audit;
9. TypeScript typecheck;
10. Next.js production build.

## Preliminary complete functional validation

Before the release and documentation commits, GitHub Actions run `#665` (`31104374587`) passed on head:

`9e0b1e66fd47a9047bbe8bbff111b569cc160af2`

Results from the generated diagnostics artifact:

- backend tests: **621 passed**, 0 failed, 0 errors, 0 skipped;
- aggregate CI coverage: approximately **91.09%**;
- line coverage: approximately **93.87%**;
- branch coverage: approximately **78.85%**;
- Mypy strict: PASS across **286** source files;
- architecture and release contracts: **13 passed**;
- PostgreSQL reversible migration cycle: PASS;
- frontend dependency audit: PASS;
- TypeScript typecheck: PASS;
- Next.js production build: PASS.

This preliminary result proves the completed functional implementation, but it is not the final release-head evidence because the version and documentation commits followed it. The final PR run must repeat every gate.

## Domain validation

### Exact alias reconciliation

Validated behavior:

- exact CVE/GHSA/OSV aliases reconcile;
- CVE identifiers become canonical when present;
- former canonical identifiers remain aliases;
- similar titles without an exact alias do not merge;
- an alias connecting multiple existing canonical records raises an error.

### Conflicting scores

Validated behavior:

- multiple providers may retain different CVSS values and vectors;
- scores are never averaged or silently overwritten;
- identical score values can exist on different snapshots without SQL collisions;
- the list maximum is a convenience projection, not a replacement for source detail.

### EPSS

Validated behavior:

- EPSS is stored as a dated probability and percentile;
- EPSS does not create an exploitation assertion;
- changed daily values create source history;
- the list endpoint exposes the latest persisted value.

### Exploitation state

Validated behavior:

- proof of concept, observed exploitation, CISA KEV, and ransomware campaign use remain separate;
- an NVD `Exploit` reference becomes only a proof-of-concept assertion;
- KEV dates and remediation due dates remain explicit;
- exploitation facts retain confidence and chronology.

### Affected product ranges

Validated behavior:

- ecosystem, product, introduced, fixed, last-affected, and precision are preserved;
- exact, ecosystem-range, product-family, and unknown precision remain distinct;
- contradictory fixed and last-affected endings are rejected;
- family-level KEV data is never promoted to an exact installation match.

### Corrections, withdrawals, and replay

Validated behavior:

- identical replay is idempotent;
- provider changes create immutable new snapshots;
- withdrawal or rejection changes the current canonical lifecycle state without deleting older history;
- the current projection uses the latest revision from each source;
- older source snapshots remain available in the detail API.

## Transaction validation

CISA KEV collection now produces raw observations and vulnerability snapshots in one adapter batch.

The worker transaction persists:

- raw observations;
- canonical vulnerability projections;
- identity/commercial/procurement/public-footprint projections when present;
- checkpoint state;
- source health and value events;
- job completion.

An exception in the vulnerability projection prevents successful completion and checkpoint advancement. Empty vulnerability batches are a no-op, preserving compatibility with all other adapters and existing worker tests.

## Persistence validation

The migration creates eight tables and is reversible.

Validated constraints include:

- unique canonical identifier;
- globally unique exact alias;
- immutable unique snapshot digest;
- child uniqueness scoped to each source snapshot;
- cascading deletion from canonical vulnerability to its snapshots and children;
- indexed identifiers, source keys, lifecycle states, timestamps, exploitation kinds, ecosystems, and products.

A regression test proves two independent vulnerability snapshots may share an identical score and reference without collision.

## API and interface validation

Validated API behavior:

- control-plane authentication is required;
- list filtering supports lifecycle, source, exploitation dimension, and bounded query;
- detail lookup accepts a canonical identifier or exact alias;
- missing identifiers return 404;
- responses expose source history rather than flattened unsupported conclusions;
- every detail response includes the organizational-exposure disclaimer.

Validated frontend behavior:

- `/vulnerabilities` renders persisted list and filters;
- `/vulnerabilities/[identifier]` renders aliases, source chronology, scores, ranges, CWE, exploitation dimensions, and references;
- navigation includes the vulnerability workspace;
- page views do not initiate provider collection;
- audit, TypeScript, and production build pass.

## Provider-governance validation

CISA KEV continues to use its previously governed executable source path.

The following additional providers remain non-executable:

- CVE.org Services;
- NVD API 2.0;
- FIRST EPSS;
- OSV API;
- GitHub Global Security Advisories;
- CIRCL Vulnerability-Lookup.

For every additional provider, tests verify:

- source status `draft`;
- authorization missing;
- automation disabled;
- no approved hosts;
- portfolio status `candidate`;
- `executable: false`;
- no schedule;
- organization-exposure inference marked forbidden.

## Non-regression incidents found and fixed

The complete regression suite identified and prevented:

1. a constructor compatibility break after adding CISA vulnerability snapshots;
2. worker failures when adapters produced an empty vulnerability batch;
3. stale metadata-table assertions after adding the migration;
4. globally scoped child keys that could collide when two snapshots shared a score or reference;
5. an oversized provider-mapper module violating the 400-line architecture limit;
6. a Mypy tuple inference error in NVD exploitation mapping.

All were corrected without disabling tests, weakening assertions, raising architecture limits, or lowering coverage thresholds.

## Residual boundaries and risks

The release deliberately leaves these items outside the executable boundary:

- automated CVE.org, NVD, EPSS, OSV, GitHub, or CIRCL ingestion;
- organization-to-product installation matching;
- passive asset exposure;
- exact version applicability;
- vendor PSIRT supersession beyond selected generic mappings;
- incident and ransomware claim correlation;
- commercial signals or opportunities derived from vulnerability data.

These are addressed by later lots, especially 14, 16, 17, 20, and 24.

## Exit decision

Lot 13 may be merged only after the final PR head repeats the complete green CI sequence and no unresolved review thread remains.

After merge:

- version `0.14.0` is the authoritative baseline;
- lots `00–13` are implemented and validated;
- Lot 14 starts from the merged Lot 13 commit;
- no additional vulnerability provider becomes executable merely because Lot 13 is complete;
- no global vulnerability fact can independently claim organizational exposure or create an opportunity.
