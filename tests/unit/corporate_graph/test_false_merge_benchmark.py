from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from cip.modules.corporate_graph.domain.models import GraphNodeSnapshot, GraphNodeType
from cip.modules.corporate_graph.infrastructure.candidate_generation import (
    generate_resolution_candidates,
)
from cip.modules.corporate_graph.infrastructure.models import EntityResolutionBindingRecord
from cip.modules.corporate_graph.infrastructure.projections import persist_graph_nodes
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 8, 21, 0, tzinfo=UTC)
FIXTURE_PATH = Path("tests/fixtures/corporate_graph/false_merge_cases.json")
CASES = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_false_merge_benchmark_never_creates_an_automatic_binding(case: dict[str, object]) -> None:
    session = _session()
    for organization in case["organizations"]:
        assert isinstance(organization, dict)
        _organization(session, organization)
    node_type = GraphNodeType(str(case["node_type"]))
    persist_graph_nodes(
        session,
        (
            GraphNodeSnapshot(
                node_key=str(case["node_key"]),
                node_type=node_type,
                display_name=str(case["display_name"]),
                source_module="false_merge_benchmark",
                source_entity_type=node_type.value,
                source_record_key=f"benchmark:{case['name']}",
                observed_at=NOW,
                confidence=0.6,
            ),
        ),
        now=NOW,
    )

    candidates = generate_resolution_candidates(session, now=NOW)
    bindings = tuple(session.scalars(select(EntityResolutionBindingRecord)).all())

    assert len(candidates) == int(case["expected_candidates"])
    assert all(candidate.requires_review for candidate in candidates)
    assert bindings == ()


def _organization(session, data: dict[str, object]) -> None:
    record = OrganizationRecord(
        id=uuid4(),
        canonical_name=str(data["name"]),
        legal_name=str(data["name"]),
        country_code="FR",
        website_url=str(data["website"]),
        registration_ids=list(data["registration_ids"]),
        created_at=NOW,
        updated_at=NOW,
    )
    session.add(record)
    session.flush()


def _session():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)()
