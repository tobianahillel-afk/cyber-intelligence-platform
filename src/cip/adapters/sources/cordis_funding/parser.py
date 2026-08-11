from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath

from pydantic import ValidationError

from cip.adapters.sources.cordis_funding.schemas import CordisOrganizationRecord

TARGET_MEMBER = "organization.csv"
MAX_ARCHIVE_MEMBERS = 32
MAX_TARGET_UNCOMPRESSED_BYTES = 250_000_000
MAX_COMPRESSION_RATIO = 100
MAX_RECORDS_PER_BATCH = 500


class CordisFundingArchiveError(RuntimeError):
    """CORDIS archive violates bounded parsing rules."""


class CordisFundingSchemaError(RuntimeError):
    """CORDIS organization CSV no longer matches the observed schema."""


@dataclass(frozen=True, slots=True)
class CordisParsedBatch:
    records: tuple[CordisOrganizationRecord, ...]
    next_offset: int
    has_more: bool


def parse_cordis_archive(
    body: bytes,
    *,
    offset: int,
    max_records: int = MAX_RECORDS_PER_BATCH,
) -> CordisParsedBatch:
    if offset < 0:
        raise ValueError("offset cannot be negative")
    if max_records < 1 or max_records > MAX_RECORDS_PER_BATCH:
        raise ValueError("max_records outside configured bounds")
    try:
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            info = _validated_target_info(archive)
            with archive.open(info) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
                return _parse_rows(text, offset=offset, max_records=max_records)
    except (zipfile.BadZipFile, UnicodeDecodeError) as exc:
        raise CordisFundingArchiveError("invalid CORDIS bulk archive") from exc


def _validated_target_info(archive: zipfile.ZipFile) -> zipfile.ZipInfo:
    infos = archive.infolist()
    if len(infos) > MAX_ARCHIVE_MEMBERS:
        raise CordisFundingArchiveError("CORDIS archive has too many members")
    for info in infos:
        _validate_member_path(info.filename)
    try:
        target = archive.getinfo(TARGET_MEMBER)
    except KeyError as exc:
        raise CordisFundingArchiveError("CORDIS organization.csv is missing") from exc
    if target.flag_bits & 0x1:
        raise CordisFundingArchiveError("CORDIS organization.csv is encrypted")
    if target.file_size > MAX_TARGET_UNCOMPRESSED_BYTES:
        raise CordisFundingArchiveError("CORDIS organization.csv exceeds size limit")
    if target.compress_size == 0 and target.file_size:
        raise CordisFundingArchiveError("CORDIS organization.csv has invalid compression")
    if target.compress_size:
        ratio = target.file_size / target.compress_size
        if ratio > MAX_COMPRESSION_RATIO:
            raise CordisFundingArchiveError("CORDIS organization.csv compression ratio unsafe")
    return target


def _validate_member_path(filename: str) -> None:
    path = PurePosixPath(filename)
    if path.is_absolute() or ".." in path.parts:
        raise CordisFundingArchiveError("CORDIS archive contains unsafe member path")


def _parse_rows(
    source: io.TextIOBase,
    *,
    offset: int,
    max_records: int,
) -> CordisParsedBatch:
    reader = csv.DictReader(source, delimiter=";")
    records: list[CordisOrganizationRecord] = []
    for index, row in enumerate(reader):
        if index < offset:
            continue
        if len(records) == max_records:
            return CordisParsedBatch(
                records=tuple(records),
                next_offset=offset + len(records),
                has_more=True,
            )
        try:
            records.append(CordisOrganizationRecord.model_validate(row))
        except ValidationError as exc:
            raise CordisFundingSchemaError(
                f"CORDIS organization CSV validation failed at row {index + 2}"
            ) from exc
    return CordisParsedBatch(
        records=tuple(records),
        next_offset=offset + len(records),
        has_more=False,
    )
