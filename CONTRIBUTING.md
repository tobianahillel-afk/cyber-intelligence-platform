# Contributing

## Change workflow

1. Create a focused branch from `main`.
2. Open an issue or link an existing requirement when the change affects product scope, data collection, privacy, security, or architecture.
3. Keep commits focused and explain migrations or policy changes.
4. Open a draft pull request early.
5. Do not merge until required checks pass and code-owner review is complete.

Direct pushes to `main` are discouraged. Repository settings should require pull requests, passing checks, resolved conversations, and code-owner review.

## Local setup

```bash
cp .env.example .env
docker compose up -d postgres
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
alembic upgrade head
cip-api
```

On PowerShell, activate the environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Required checks

Before opening a pull request:

```bash
python -m pip check
pip-audit --strict
ruff check .
mypy
alembic upgrade head
pytest --cov=cip --cov-branch --cov-fail-under=90
```

## Source adapters

A new source requires:

- a source-registry entry;
- documented owner, terms, licence, purpose, and authorization state;
- allowed hosts, paths, categories, quotas, and retention;
- an isolated adapter directory;
- sanitized fixtures;
- parser, mapper, failure, checkpoint, and policy-denial tests;
- evidence that the source materially improves product outcomes.

Never add credentials, stolen data, private communications, victim files, CAPTCHA bypasses, disposable-account rotation, or access-control circumvention.

## Database changes

Every persistence change requires a reversible Alembic migration. Test both upgrade and downgrade. Domain modules own their tables; cross-module foreign keys require explicit review.

## Code size and boundaries

Follow `docs/DEVELOPMENT_STANDARDS.md`. Split transport, discovery, parsing, mapping, persistence, scoring, and API concerns. Do not create generic manager or utility modules containing unrelated logic.

## Tests

The repository requires at least 90% line and branch coverage. Critical governance and scoring modules target 95%. Coverage does not replace assertions for failures, boundaries, idempotence, security, and data quality.

## Security and personal data

Use synthetic fixtures. Do not place production exports or personal data in issues, pull requests, tests, logs, screenshots, or artifacts. Follow `SECURITY.md`, source policies, retention rules, and suppression controls.
