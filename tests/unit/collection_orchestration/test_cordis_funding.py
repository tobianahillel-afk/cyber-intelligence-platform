from __future__ import annotations

import csv
import io
import zipfile
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from cip.adapters.sources.cordis_funding.client import (
    CordisFundingClient,
    CordisFundingResponseError,
)
from cip.adapters.sources.cordis_funding.collector import (
    CordisFundingCheckpoint,
    CordisFundingCollectionBatch,
    CordisFundingCollectionDeniedError,
    collect_cordis_funding,
)
from cip.adapters.sources.cordis_funding.mapper import map_cordis_funding_record
from cip.adapters.sources.cordis_funding.parser import (
    CordisFundingArchiveError,
    CordisFundingSchemaError,
    parse_cordis_archive,
)
from cip.adapters.sources.cordis_funding.schemas import CordisOrganizationRecord
from cip.modules.collection_orchestration.application import (
    cordis_funding_adapter as adapter_module,
)
from cip.modules.collection_orchestration.application.cordis_funding_adapter import (
    CordisFundingAdapter,
)
from cip.modules.collection_orchestration.application.ports import AdapterExecutionError
from cip.modules.source_governance.infrastructure.registry import (
    SourceRegistryEntry,
    load_source_registry,
)

NOW = datetime(2026, 8, 11, 10, 15, tzinfo=UTC)
RETENTION = NOW + timedelta(days=3650)
POLICY_PATH = Path("policies/sources.procurement_funding.yml")


def test_cordis_client_fetches_bounded_zip() -> None:
    archive = _archive([_row()])

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL(_entry().policy.base_url)
        assert "application/zip" in request.headers["Accept"]
        return httpx.Response(
            200,
            headers={"content-type": "application/zip", "etag": '"snapshot-1"'},
            content=archive,
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        result = CordisFundingClient(
            http_client, archive_url=_entry().policy.base_url
        ).fetch()
    assert result.body == archive
    assert result.etag == '"snapshot-1"'


def test_cordis_client_rejects_unsafe_content_type_and_size() -> None:
    responses = [
        ("text/html", "1", b"x"),
        ("application/zip", "100000001", b"PK"),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        content_type, content_length, body = responses.pop(0)
        return httpx.Response(
            200,
            headers={"content-type": content_type, "content-length": content_length},
            content=body,
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = CordisFundingClient(http_client, archive_url=_entry().policy.base_url)
        with pytest.raises(CordisFundingResponseError, match="content type"):
            client.fetch()
        with pytest.raises(CordisFundingResponseError, match="size limit"):
            client.fetch()


def test_cordis_parser_reads_observed_schema_and_bounds_rows() -> None:
    rows = [_row(project_id=str(index), organisation_id=f"ORG-{index}") for index in range(3)]
    first = parse_cordis_archive(_archive(rows), offset=0, max_records=2)
    second = parse_cordis_archive(_archive(rows), offset=2, max_records=2)
    assert [record.projectID for record in first.records] == ["0", "1"]
    assert first.next_offset == 2
    assert first.has_more is True
    assert [record.projectID for record in second.records] == ["2"]
    assert second.has_more is False


def test_cordis_parser_rejects_missing_member_and_schema_drift() -> None:
    with pytest.raises(CordisFundingArchiveError, match="organization.csv is missing"):
        parse_cordis_archive(_zip_members({"project.csv": b"x\n"}), offset=0)

    invalid = _row()
    invalid.pop("organisationID")
    with pytest.raises(CordisFundingSchemaError, match="validation failed"):
        parse_cordis_archive(_archive([invalid]), offset=0)


def test_cordis_mapper_preserves_organisation_funding_semantics() -> None:
    record = CordisOrganizationRecord.model_validate(_row())
    observation, claim = map_cordis_funding_record(
        record,
        collection_job_id=uuid4(),
        collected_at=NOW,
        retention_until=RETENTION,
    )
    assert observation.source_record_key == "101000001:ORG-42"
    assert claim.claimed_organization_name == "Example Cyber Research SAS"
    assert claim.organization_id is None
    assert "CORDIS organisation ecContribution field: 2500000" in claim.excerpt
    assert "coordinator" in claim.excerpt


def test_cordis_collector_checkpoints_snapshot_and_replay() -> None:
    archive = _archive([_row(), _row(project_id="101000002", organisation_id="ORG-43")])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/zip"},
            content=archive,
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = CordisFundingClient(http_client, archive_url=_entry().policy.base_url)
        batch = collect_cordis_funding(
            client,
            _entry(),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )
        replay = collect_cordis_funding(
            client,
            _entry(),
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
            checkpoint=batch.checkpoint,
        )
    assert len(batch.observations) == 2
    assert len(batch.claims) == 2
    assert batch.checkpoint.archive_sha256 == sha256(archive).hexdigest()
    assert batch.checkpoint.complete is True
    assert replay.not_modified is True
    assert replay.observations == ()


def test_cordis_collector_denies_before_network() -> None:
    requested = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requested
        requested = True
        return httpx.Response(500, request=request)

    denied = _entry("ademe-financial-aid")
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        pytest.raises(CordisFundingCollectionDeniedError),
    ):
        collect_cordis_funding(
            CordisFundingClient(http_client, archive_url=denied.policy.base_url),
            denied,
            collection_job_id=uuid4(),
            collected_at=NOW,
            retention_until=RETENTION,
        )
    assert requested is False


def test_cordis_runtime_adapter_round_trips_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}
    archive_hash = "a" * 64

    def fake_collect(*args: object, **kwargs: object) -> CordisFundingCollectionBatch:
        seen["checkpoint"] = kwargs["checkpoint"]
        return CordisFundingCollectionBatch(
            observations=(),
            claims=(),
            checkpoint=CordisFundingCheckpoint(
                archive_sha256=archive_hash, offset=1000, complete=False
            ),
            not_modified=False,
        )

    monkeypatch.setattr(adapter_module, "collect_cordis_funding", fake_collect)
    batch = CordisFundingAdapter(_entry()).collect(
        collection_job_id=uuid4(),
        checkpoint_payload={
            "archive_sha256": archive_hash,
            "offset": 500,
            "complete": False,
        },
        collected_at=NOW,
        retention_until=RETENTION,
    )
    assert isinstance(seen["checkpoint"], CordisFundingCheckpoint)
    assert batch.checkpoint_payload == {
        "archive_sha256": archive_hash,
        "offset": 1000,
        "complete": False,
    }

    with pytest.raises(AdapterExecutionError) as exc_info:
        CordisFundingAdapter(_entry()).collect(
            collection_job_id=uuid4(),
            checkpoint_payload={"archive_sha256": "bad", "offset": 0},
            collected_at=NOW,
            retention_until=RETENTION,
        )
    assert exc_info.value.error_code == "invalid_checkpoint"


def _row(
    *, project_id: str = "101000001", organisation_id: str = "ORG-42"
) -> dict[str, str]:
    return {
        "projectID": project_id,
        "projectAcronym": "CYBER-EU",
        "organisationID": organisation_id,
        "vatNumber": "",
        "name": "Example Cyber Research SAS",
        "shortName": "ECR",
        "SME": "true",
        "activityType": "PRC",
        "street": "",
        "postCode": "",
        "city": "Paris",
        "country": "FR",
        "nutsCode": "",
        "geolocation": "",
        "organizationURL": "https://example.invalid",
        "contactForm": "",
        "contentUpdateDate": "2026-06-17",
        "rcn": "1",
        "order": "1",
        "role": "coordinator",
        "ecContribution": "2500000",
        "netEcContribution": "2500000",
        "totalCost": "3000000",
        "endOfParticipation": "2028-12-31",
        "active": "true",
    }


def _archive(rows: list[dict[str, str]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(_row().keys()), delimiter=";")
    writer.writeheader()
    writer.writerows(rows)
    return _zip_members({"organization.csv": output.getvalue().encode()})


def _zip_members(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def _entry(source_id: str = "cordis-eu-funded-projects") -> SourceRegistryEntry:
    return next(
        entry for entry in load_source_registry(POLICY_PATH) if entry.policy.id == source_id
    )
