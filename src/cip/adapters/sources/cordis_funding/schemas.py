from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SparqlValue(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    type: str
    value: str
    datatype: str | None = None
    xml_lang: str | None = Field(default=None, alias="xml:lang")

    @field_validator("type", "value")
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("CORDIS SPARQL value cannot be blank")
        return value


class CordisFundingBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: SparqlValue
    project_title: SparqlValue
    organisation_name: SparqlValue
    role_label: SparqlValue | None = None
    start_date: SparqlValue | None = None
    end_date: SparqlValue | None = None
    eu_contribution: SparqlValue | None = None


class SparqlHead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vars: tuple[str, ...]


class CordisFundingResults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bindings: tuple[CordisFundingBinding, ...]


class CordisFundingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    head: SparqlHead
    results: CordisFundingResults
