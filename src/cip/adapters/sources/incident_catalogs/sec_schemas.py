from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

_MAX_RECENT_FILINGS = 2_000


class SecRecentFilings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    accessionNumber: list[str] = Field(max_length=_MAX_RECENT_FILINGS)
    filingDate: list[date] = Field(max_length=_MAX_RECENT_FILINGS)
    reportDate: list[str] = Field(max_length=_MAX_RECENT_FILINGS)
    acceptanceDateTime: list[datetime] = Field(max_length=_MAX_RECENT_FILINGS)
    form: list[str] = Field(max_length=_MAX_RECENT_FILINGS)
    items: list[str] = Field(max_length=_MAX_RECENT_FILINGS)

    @model_validator(mode="after")
    def validate_parallel_arrays(self) -> SecRecentFilings:
        lengths = {
            len(self.accessionNumber),
            len(self.filingDate),
            len(self.reportDate),
            len(self.acceptanceDateTime),
            len(self.form),
            len(self.items),
        }
        if len(lengths) != 1:
            raise ValueError("SEC recent filing arrays must have identical lengths")
        return self


class SecFilings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    recent: SecRecentFilings


class SecSubmissionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    cik: str | int
    name: str = Field(min_length=1, max_length=500)
    filings: SecFilings


class SecCyberFilingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accession_number: str = Field(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
    form: str = Field(min_length=1, max_length=40)
    item: str = Field(min_length=1, max_length=100)
    filing_date: date
    accepted_at: datetime
