## Summary

Describe the problem and the smallest complete change that solves it.

## Validation

- [ ] Ruff passes
- [ ] Mypy passes
- [ ] Tests pass with at least 90% line and branch coverage
- [ ] Dependency consistency and audit pass
- [ ] Migrations upgrade and downgrade successfully, when applicable

## Architecture

- [ ] Module ownership is clear
- [ ] No cross-module infrastructure import was added
- [ ] No source-specific payload escaped its adapter
- [ ] File and function size thresholds are respected

## Data and security

- [ ] No secret, credential, private communication, victim file, or production personal data is included
- [ ] Source-policy and authorization effects are documented
- [ ] Retention, suppression, deletion, and provenance effects are covered
- [ ] Logs and fixtures are redacted or synthetic

## Rollback

Explain how to reverse the change safely.
