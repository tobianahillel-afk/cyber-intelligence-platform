# Priority B — Developer Ecosystem Authorization

## Scope

Priority B-2 collects bounded public repository and package **metadata** for exact organization-bound targets. It is not a code crawler, contributor harvester, package mirror, dependency scanner, or vulnerability scanner.

The checked-in target registry is empty and all schedules are disabled by default.

## GitHub

Acquisition uses the official GitHub REST organization-repositories endpoint under `api.github.com/orgs/<configured-org>/repos` with public repositories only and bounded pagination.

Excluded before persistence:

- owners/users;
- contributors and commit authors;
- email addresses and profiles;
- source code, release assets and repository archives;
- global GitHub search.

GitHub metadata is represented as public engineering context only. High-volume resale, person-data monetization, spam-oriented use, or a dataset mirror is outside this capability.

## GitLab

Acquisition uses the official GitLab REST group-projects endpoint for an exact configured public group. Requests are bounded to public/simple project metadata and provider pagination.

Excluded:

- group members/users;
- contributors/commit authors;
- email or profile harvesting;
- source-code/archive downloads;
- systematic bulk export of GitLab content;
- global project/user discovery.

## PyPI

Acquisition uses the public exact-project JSON endpoint `pypi/<configured-project>/json`.

The materialized schema contains only project name, current public version and bounded summary. Author, author email, maintainer, maintainer email, project distributions, wheels, sdists and package files are not materialized or downloaded.

## npm

Acquisition uses the public exact-package registry metadata endpoint at `registry.npmjs.org/<configured-package>`.

Only the normalized package name, bounded description and latest public dist-tag are materialized. Maintainers, authors, email addresses, version tarball URLs, package tarballs and source content are ignored before RawObservation creation.

## Maven Central

Acquisition uses the public Maven Central Search REST endpoint with an exact configured group ID and artifact ID, `rows=1`, and identity revalidation. Only public coordinate/version metadata is retained. JAR, POM, source and signature artifacts are never downloaded.

## Common evidence boundary

A repository or package being public is evidence that an organization-bound target has a public engineering artifact **only because an analyst/deployment explicitly configured that organization-to-provider identity binding**. It does not prove:

- deployment in the organization's production environment;
- current use of the technology;
- version exposure;
- vulnerability applicability;
- compromise;
- cyber need;
- commercial opportunity;
- contact or outreach authorization.

B-2 creates no automatic PublicClaim, CommercialSignal, NeedHypothesis, score, opportunity or outreach action.

## Runtime and activation

All five providers use the shared collection scheduler/worker and existing Lot 12 Public Footprint persistence. The target registry is empty by default and the five schedules are disabled. `live_tested` remains false until a separately authorized controlled provider validation is recorded on an exact release candidate.
