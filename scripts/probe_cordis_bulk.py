from __future__ import annotations

import io
import zipfile

import httpx

BULK_URL = "https://cordis.europa.eu/data/cordis-HORIZONprojects-csv.zip"
MAX_ARCHIVE_BYTES = 100_000_000
MAX_HEADER_BYTES = 16_384


def main() -> None:
    with httpx.Client(timeout=120, follow_redirects=False) as client:
        response = client.get(BULK_URL)
    print(
        "CORDIS bulk probe: "
        f"status={response.status_code} "
        f"content_type={response.headers.get('content-type', 'missing')} "
        f"content_length={response.headers.get('content-length', 'missing')}"
    )
    if response.is_redirect:
        location = response.headers.get("location", "")
        print(f"CORDIS bulk redirect={location[:300]}")
        raise RuntimeError("CORDIS bulk URL redirected; review target before following")
    response.raise_for_status()
    if len(response.content) > MAX_ARCHIVE_BYTES:
        raise RuntimeError("CORDIS bulk archive exceeds probe size limit")
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
        csv_names = [name for name in names if name.lower().endswith(".csv")]
        print(
            f"CORDIS bulk members={len(names)} "
            f"csv_members={len(csv_names)} names={names[:20]}"
        )
        if not csv_names:
            raise RuntimeError("CORDIS bulk archive contains no CSV member")
        with archive.open(csv_names[0]) as source:
            header = source.readline(MAX_HEADER_BYTES).decode("utf-8-sig", errors="strict")
        print(f"CORDIS bulk first_csv={csv_names[0]} header={header.rstrip()[:4000]}")


if __name__ == "__main__":
    main()
