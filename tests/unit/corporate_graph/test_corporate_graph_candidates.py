from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from cip.modules.corporate_graph.domain.models import GraphNodeSnapshot, GraphNodeType
from cip.modules.corporate_graph.domain.resolution import ResolutionMethod
from cip.modules.corporate_graph.infrastructure.candidate_generation import (
    generate_resolution_candidates,
)
from cip.modules.corporate_graph.infrastructure.models import EntityResolutionCandidateRecord
from cip.modules.corporate_graph.infrastructure.projections import persist_graph_nodes
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import create_database_engine, create_session_factory

NOW = datetime(2026, 8, 8, 21, 0, tzinfo=UTC)


def test_conflicting_exact_source_bindings_create_review_candidates() -> None:
    session = _session()
    first = _organization(session, "Acme France", "https://acme-fr.example")
    second = _organization(session, "Acme Global", "https://acme-global.example")
    persist_graph_nodes(
        session,
        (
            _node("identity:acme", "Acme", first.id, "registry-a"),
            _node("identity:acme", "Acme", second.id, "registry-b"),
        ),
        now=NOW,
    )

    candidates = generate_resolution_candidates(session, now=NOW)

    assert len(candidates) == 2
    assert {item.method for item in candidates} == {
        ResolutionMethod.EXACT_SOURCE_BINDING.value
    }
    assert all(item.requires_review for item in candidates)
    assert all(item.conflicting_organization_ids_json != "[]" for item in candidates)


def test_same_name_homonyms_never_auto_merge() -> None:
    session = _session()
    _organization(session, "Acme", "https://acme-one.example")
    _organization(session, "ACME", "https://acme-two.example")
    persist_graph_nodes(
        session,
        (_node("brand:acme", "Acme", None, "public-footprint"),),
        now=NOW,
    )

    candidates = generate_resolution_candidates(session, now=NOW)

    assert len(candidates) == 2
    assert {item.method for item in candidates} == {
        ResolutionMethod.PROBABILISTIC_CONTEXT.value
    }
    assert all(item.state == "pending" for item in candidates)
    assert all(item.requires_review for item in candidates)


def test_reused_domain_creates_review_candidates_for_each_organization() -> None:
    session = _session()
    _organization(session, "Old Owner", "https://shared.example")
    _organization(session, "New Owner", "https://www.shared.example/about")
    persist_graph_nodes(
        session,
        (
            _node(
                "domain:shared.example",
                "shared.example",
                None,
                "passive-exposure",
                GraphNodeType.DOMAIN,
            ),
        ),
        now=NOW,
    )

    first = generate_resolution_candidates(session, now=NOW)
    second = generate_resolution_candidates(session, now=NOW)
    stored = tuple(session.scalars(select(EntityResolutionCandidateRecord)).all())

    assert len(first) == 2
    assert len(second) == 2
    assert len(stored) == 2
    assert {item.method for item in stored} == {ResolutionMethod.DOMAIN_OWNERSHIP.value}
    assert all(item.requires_review for item in stored)


def _session():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    return create_session_factory(engine)()


def _organization(session, name: str, website_url: str) -> OrganizationRecord:
    record = OrganizationRecord(
        id=uuid4(),
        canonical_name=name,
        legal_name=name,
        country_code="FR",
        website_url=website_url,
        registration_ids=[],
        created_at=NOW,
        updated_at=NOW,
    )
    session.add(record)
    session.flush()
    return record


def _node(
    node_key: str,
    display_name: str,
    organization_id,
    source_module: str,
    node_type: GraphNodeType = GraphNodeType.BRAND,
) -> GraphNodeSnapshot:
    return GraphNodeSnapshot(
        node_key=node_key,
        node_type=node_type,
        display_name=display_name,
        source_module=source_module,
        source_entity_type=node_type.value,
        source_record_key=f"{source_module}:{node_key}",
        organization_id=organization_id,
        observed_at=NOW,
        confidence=0.9,
    )
