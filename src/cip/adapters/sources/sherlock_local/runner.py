from __future__ import annotations

import csv
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

from cip.adapters.sources.sherlock_local.registry import SherlockTarget

_MAX_CAPTURE_BYTES = 250_000
_EXPECTED_COLUMNS = {
    "username",
    "name",
    "url_main",
    "url_user",
    "exists",
    "http_status",
    "response_time_s",
}


class SherlockExecutionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SherlockExecutionConfig:
    executable: Path
    expected_version: str
    process_timeout_seconds: int = 90
    per_site_timeout_seconds: int = 20

    def __post_init__(self) -> None:
        if not self.executable.is_absolute():
            raise ValueError("Sherlock executable path must be absolute")
        if not self.expected_version.strip() or len(self.expected_version) > 100:
            raise ValueError("Sherlock expected version must be explicit and bounded")
        if not 1 <= self.process_timeout_seconds <= 180:
            raise ValueError("Sherlock process timeout must be between 1 and 180 seconds")
        if not 1 <= self.per_site_timeout_seconds <= 60:
            raise ValueError("Sherlock per-site timeout must be between 1 and 60 seconds")


@dataclass(frozen=True, slots=True)
class SherlockFinding:
    username: str
    site_name: str
    profile_url: str


class SherlockLocalRunner:
    def __init__(self, config: SherlockExecutionConfig) -> None:
        self._config = config

    def collect(self, target: SherlockTarget) -> tuple[SherlockFinding, ...]:
        if not target.enabled:
            raise SherlockExecutionError("Sherlock target is disabled")
        self._verify_version()
        with TemporaryDirectory(prefix="cip-sherlock-") as directory:
            output_dir = Path(directory)
            command = build_sherlock_command(self._config, target, output_dir)
            stdout_path = output_dir / "stdout.log"
            stderr_path = output_dir / "stderr.log"
            with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
                try:
                    result = subprocess.run(
                        command,
                        stdin=subprocess.DEVNULL,
                        stdout=stdout,
                        stderr=stderr,
                        check=False,
                        timeout=self._config.process_timeout_seconds,
                        shell=False,
                        env=_subprocess_environment(),
                    )
                except (OSError, subprocess.TimeoutExpired) as exc:
                    raise SherlockExecutionError("Sherlock local execution failed") from exc
            _enforce_capture_bounds(stdout_path, stderr_path)
            if result.returncode != 0:
                raise SherlockExecutionError("Sherlock returned a non-zero exit status")
            return parse_sherlock_csv(output_dir / f"{target.username}.csv", target)

    def _verify_version(self) -> None:
        try:
            result = subprocess.run(
                [str(self._config.executable), "--version"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                check=False,
                timeout=10,
                shell=False,
                env=_subprocess_environment(),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SherlockExecutionError("Sherlock version check failed") from exc
        output = (result.stdout + result.stderr)[:_MAX_CAPTURE_BYTES].decode(
            "utf-8", errors="replace"
        )
        if result.returncode != 0 or self._config.expected_version not in output:
            raise SherlockExecutionError("Sherlock executable version is not approved")


def build_sherlock_command(
    config: SherlockExecutionConfig,
    target: SherlockTarget,
    output_dir: Path,
) -> list[str]:
    command = [
        str(config.executable),
        "--csv",
        "--print-found",
        "--no-color",
        "--folderoutput",
        str(output_dir),
        "--timeout",
        str(config.per_site_timeout_seconds),
    ]
    for site in target.sites:
        command.extend(("--site", site))
    command.append(target.username)
    return command


def parse_sherlock_csv(path: Path, target: SherlockTarget) -> tuple[SherlockFinding, ...]:
    if not path.is_file() or path.stat().st_size > _MAX_CAPTURE_BYTES:
        raise SherlockExecutionError("Sherlock CSV result is missing or oversized")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or set(reader.fieldnames) != _EXPECTED_COLUMNS:
            raise SherlockExecutionError("Sherlock CSV schema is unexpected")
        findings: list[SherlockFinding] = []
        allowed_sites = {site.casefold(): site for site in target.sites}
        seen: set[tuple[str, str]] = set()
        for row in reader:
            finding = _parse_claimed_row(row, target, allowed_sites)
            if finding is None:
                continue
            key = (finding.site_name.casefold(), finding.profile_url)
            if key not in seen:
                findings.append(finding)
                seen.add(key)
        return tuple(findings)


def _parse_claimed_row(
    row: dict[str, str | None],
    target: SherlockTarget,
    allowed_sites: dict[str, str],
) -> SherlockFinding | None:
    username = (row.get("username") or "").strip()
    site_name = (row.get("name") or "").strip()
    profile_url = (row.get("url_user") or "").strip()
    status = (row.get("exists") or "").strip()
    if status != "Claimed":
        return None
    if username != target.username or site_name.casefold() not in allowed_sites:
        raise SherlockExecutionError("Sherlock result escaped the approved target scope")
    parsed = urlparse(profile_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise SherlockExecutionError("Sherlock returned an unsafe profile URL")
    return SherlockFinding(
        username=username,
        site_name=allowed_sites[site_name.casefold()],
        profile_url=profile_url,
    )


def _enforce_capture_bounds(*paths: Path) -> None:
    if any(path.stat().st_size > _MAX_CAPTURE_BYTES for path in paths):
        raise SherlockExecutionError("Sherlock process output exceeded the configured bound")


def _subprocess_environment() -> dict[str, str]:
    environment = {"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
    if path := os.environ.get("PATH"):
        environment["PATH"] = path
    return environment
