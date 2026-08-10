from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
import yaml

from cip.adapters.sources.sherlock_local.mapper import map_sherlock_finding
from cip.adapters.sources.sherlock_local.registry import SherlockTarget, load_sherlock_targets
from cip.adapters.sources.sherlock_local.runner import (
    SherlockExecutionConfig,
    SherlockExecutionError,
    SherlockFinding,
    build_sherlock_command,
    parse_sherlock_csv,
)
from cip.modules.professional_context.domain import (
    CommunityAcquisitionMode,
    LawfulBasis,
    ProfessionalReviewState,
)

NOW = datetime(2026, 8, 10, 14, 0, tzinfo=UTC)
ORG_ID = UUID("00000000-0000-0000-0000-000000000905")


def test_checked_in_sherlock_registry_is_empty() -> None:
    assert load_sherlock_targets(Path("policies/sherlock_targets.yml")) == ()


def test_target_requires_professional_context_safe_username_and_reviewed_basis() -> None:
    with pytest.raises(ValueError, match="exactly one organization or person"):
        _target(organization_id=None)
    with pytest.raises(ValueError, match="filename-safe"):
        _target(username="../secret")
    with pytest.raises(ValueError, match="reviewed lawful basis"):
        _target(lawful_basis=LawfulBasis.REVIEW_REQUIRED)


def test_registry_rejects_duplicate_professional_username_target(tmp_path: Path) -> None:
    payload = {
        "version": 1,
        "targets": [
            _target().model_dump(mode="json"),
            _target(target_id="second").model_dump(mode="json"),
        ],
    }
    path = tmp_path / "targets.yml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate Sherlock professional username"):
        load_sherlock_targets(path)


def test_command_is_bounded_explicit_and_contains_no_evasion_flags(tmp_path: Path) -> None:
    config = SherlockExecutionConfig(
        executable=Path("/opt/cip/bin/sherlock"),
        expected_version="0.16.0",
        process_timeout_seconds=90,
        per_site_timeout_seconds=12,
    )

    command = build_sherlock_command(config, _target(), tmp_path)

    assert command[0] == "/opt/cip/bin/sherlock"
    assert command[-1] == "securityalice"
    assert command.count("--site") == 2
    assert "GitHub" in command and "GitLab" in command
    assert "--csv" in command and "--print-found" in command and "--no-color" in command
    assert "--tor" not in command
    assert "--unique-tor" not in command
    assert "--proxy" not in command
    assert "--browse" not in command
    assert "--dump-response" not in command
    assert "--nsfw" not in command


def test_csv_parser_keeps_only_claimed_approved_https_profiles(tmp_path: Path) -> None:
    path = tmp_path / "securityalice.csv"
    _write_csv(
        path,
        [
            _row(
                site="GitHub",
                main_url="https://github.com",
                profile_url="https://github.com/securityalice",
                status="Claimed",
                http_status="200",
            ),
            _row(
                site="GitLab",
                main_url="https://gitlab.com",
                profile_url="https://gitlab.com/securityalice",
                status="Available",
                http_status="404",
            ),
        ],
    )

    findings = parse_sherlock_csv(path, _target())

    assert findings == (
        SherlockFinding("securityalice", "GitHub", "https://github.com/securityalice"),
    )


def test_csv_parser_fails_closed_on_scope_escape_or_unsafe_url(tmp_path: Path) -> None:
    path = tmp_path / "securityalice.csv"
    _write_csv(
        path,
        [
            _row(
                site="Reddit",
                main_url="https://reddit.com",
                profile_url="https://reddit.com/u/securityalice",
            )
        ],
    )
    with pytest.raises(SherlockExecutionError, match="escaped"):
        parse_sherlock_csv(path, _target())

    _write_csv(
        path,
        [
            _row(
                site="GitHub",
                main_url="https://github.com",
                profile_url="http://github.com/securityalice",
            )
        ],
    )
    with pytest.raises(SherlockExecutionError, match="unsafe profile URL"):
        parse_sherlock_csv(path, _target())


def test_mapper_reuses_lot21_review_required_metadata_only_context() -> None:
    context = map_sherlock_finding(
        _target(),
        SherlockFinding("securityalice", "GitHub", "https://github.com/securityalice"),
        observed_at=NOW,
    )

    assert context.organization_id == ORG_ID
    assert context.person_key is None
    assert context.acquisition_mode is CommunityAcquisitionMode.GOVERNED_LOCAL_TOOL
    assert context.review_state is ProfessionalReviewState.REVIEW_REQUIRED
    assert context.metadata_only is True
    assert context.source_id == "sherlock-local"
    assert context.source_url == "https://github.com/securityalice"
    assert context.authorizes_source_automation is False
    assert context.authorizes_outreach is False


def _target(**overrides: object) -> SherlockTarget:
    values: dict[str, object] = {
        "target_id": "sherlock-example",
        "organization_id": ORG_ID,
        "person_key": None,
        "username": "securityalice",
        "sites": ("GitHub", "GitLab"),
        "authorization_reference": "review/SA05/example",
        "lawful_basis": LawfulBasis.LEGITIMATE_INTERESTS,
        "purpose": "Review public professional profile presence for an approved research target.",
        "reviewed_at": NOW,
        "retention_until": NOW + timedelta(days=30),
        "enabled": True,
    }
    values.update(overrides)
    return SherlockTarget.model_validate(values)


def _row(
    *,
    site: str,
    main_url: str,
    profile_url: str,
    status: str = "Claimed",
    http_status: str = "200",
) -> list[str]:
    return [
        "securityalice",
        site,
        main_url,
        profile_url,
        status,
        http_status,
        "0.2",
    ]


def _write_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "username",
                "name",
                "url_main",
                "url_user",
                "exists",
                "http_status",
                "response_time_s",
            ]
        )
        writer.writerows(rows)
