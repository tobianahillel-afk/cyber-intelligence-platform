from __future__ import annotations

from cip.adapters.sources.incident_catalogs.sec_schemas import SecSubmissionResponse


def test_sec_submission_schema_accepts_empty_report_date_cells() -> None:
    response = SecSubmissionResponse.model_validate(
        {
            "cik": 320193,
            "name": "Example Issuer",
            "filings": {
                "recent": {
                    "accessionNumber": ["0000320193-26-000010"],
                    "filingDate": ["2026-08-09"],
                    "reportDate": [""],
                    "acceptanceDateTime": ["2026-08-09T20:00:00Z"],
                    "form": ["8-K"],
                    "items": ["1.05"],
                }
            },
        }
    )

    assert response.filings.recent.reportDate == [""]
