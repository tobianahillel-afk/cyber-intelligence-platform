from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class BlastRadiusPreview:
    node_key: str
    target_organization_key: str | None
    graph_nodes: int = 0
    graph_edges: int = 0
    organization_identities: int = 0
    business_relationships: int = 0
    applicability_assessments: int = 0
    commercial_signals: int = 0
    opportunities: int = 0

    def __post_init__(self) -> None:
        if not self.node_key.strip() or len(self.node_key) > 500:
            raise ValueError("node_key must be between 1 and 500 characters")
        if self.target_organization_key is not None:
            value = self.target_organization_key.strip()
            if not value or len(value) > 500:
                raise ValueError("target_organization_key must be between 1 and 500 characters")
        values = (
            self.graph_nodes,
            self.graph_edges,
            self.organization_identities,
            self.business_relationships,
            self.applicability_assessments,
            self.commercial_signals,
            self.opportunities,
        )
        if any(value < 0 for value in values):
            raise ValueError("blast-radius counts cannot be negative")

    @property
    def downstream_record_count(self) -> int:
        return (
            self.organization_identities
            + self.business_relationships
            + self.applicability_assessments
            + self.commercial_signals
            + self.opportunities
        )

    @property
    def requires_explicit_confirmation(self) -> bool:
        return self.graph_edges > 0 or self.downstream_record_count > 0

    @property
    def fingerprint(self) -> str:
        material = "|".join(
            (
                self.node_key,
                self.target_organization_key or "",
                str(self.graph_nodes),
                str(self.graph_edges),
                str(self.organization_identities),
                str(self.business_relationships),
                str(self.applicability_assessments),
                str(self.commercial_signals),
                str(self.opportunities),
            )
        )
        return sha256(material.encode("utf-8")).hexdigest()
