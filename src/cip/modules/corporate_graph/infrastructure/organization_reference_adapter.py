from __future__ import annotations

from collections import Counter
from hashlib import sha256
from urllib.parse import urlparse

from cip.modules.corporate_graph.application.batches import GraphProjectionBatch
from cip.modules.corporate_graph.domain.models import (
    GraphClaimType,
    GraphEdgeSnapshot,
    GraphEdgeType,
    GraphNodeSnapshot,
    GraphNodeType,
    GraphReviewState,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord


def project_organization_references(
    organizations: tuple[OrganizationRecord, ...],
) -> GraphProjectionBatch:
    alias_counts = Counter(_legal_alias(record) for record in organizations if _legal_alias(record))
    identifier_counts = Counter(
        _normalize_identifier(identifier)
        for record in organizations
        for identifier in record.registration_ids
        if _normalize_identifier(identifier)
    )
    nodes: list[GraphNodeSnapshot] = []
    edges: list[GraphEdgeSnapshot] = []
    for organization in organizations:
        nodes.append(_organization_node(organization))
        _append_domain_graph(nodes, edges, organization)
        _append_alias_graph(nodes, edges, organization, alias_counts)
        _append_identifier_graph(nodes, edges, organization, identifier_counts)
    return GraphProjectionBatch(nodes=tuple(nodes), edges=tuple(edges))


def _organization_node(record: OrganizationRecord) -> GraphNodeSnapshot:
    return GraphNodeSnapshot(
        node_key=f"organization:{record.id}",
        node_type=GraphNodeType.ORGANIZATION,
        display_name=record.canonical_name,
        source_module="organizations",
        source_entity_type="organization",
        source_record_key=str(record.id),
        source_entity_id=record.id,
        organization_id=record.id,
        observed_at=record.updated_at,
        valid_from=record.created_at,
        confidence=1.0,
    )


def _append_domain_graph(
    nodes: list[GraphNodeSnapshot],
    edges: list[GraphEdgeSnapshot],
    record: OrganizationRecord,
) -> None:
    domain = _website_domain(record.website_url)
    if domain is None:
        return
    nodes.append(
        GraphNodeSnapshot(
            node_key=f"domain:{domain}",
            node_type=GraphNodeType.DOMAIN,
            display_name=domain,
            source_module="organizations",
            source_entity_type="website_domain",
            source_record_key=f"organization-website:{record.id}:{domain}",
            organization_id=record.id,
            source_url=record.website_url,
            observed_at=record.updated_at,
            confidence=0.9,
        )
    )
    edges.append(
        GraphEdgeSnapshot(
            edge_key=f"organization-domain:{record.id}:{domain}",
            source_node_key=f"organization:{record.id}",
            target_node_key=f"domain:{domain}",
            edge_type=GraphEdgeType.USES_DOMAIN,
            source_module="organizations",
            source_record_key=f"organization-website:{record.id}:{domain}",
            source_evidence_class="declared_website",
            claim_type=GraphClaimType.ASSERTION,
            review_state=GraphReviewState.UNREVIEWED,
            observed_at=record.updated_at,
            source_url=record.website_url,
            confidence=0.9,
        )
    )


def _append_alias_graph(
    nodes: list[GraphNodeSnapshot],
    edges: list[GraphEdgeSnapshot],
    record: OrganizationRecord,
    alias_counts: Counter[str],
) -> None:
    alias = _legal_alias(record)
    if alias is None:
        return
    key = _stable_text_key("alias", alias)
    nodes.append(
        GraphNodeSnapshot(
            node_key=key,
            node_type=GraphNodeType.ALIAS,
            display_name=record.legal_name or record.canonical_name,
            source_module="organizations",
            source_entity_type="legal_name_alias",
            source_record_key=f"legal-name:{record.id}:{alias}",
            organization_id=record.id,
            observed_at=record.updated_at,
            valid_from=record.created_at,
            confidence=1.0,
        )
    )
    edges.append(
        _organization_reference_edge(
            record=record,
            node_key=key,
            source_record_key=f"legal-name:{record.id}:{alias}",
            edge_type=GraphEdgeType.ALIAS_OF,
            evidence_class="canonical_legal_alias",
            review_required=alias_counts[alias] > 1,
        )
    )


def _append_identifier_graph(
    nodes: list[GraphNodeSnapshot],
    edges: list[GraphEdgeSnapshot],
    record: OrganizationRecord,
    identifier_counts: Counter[str],
) -> None:
    for raw_identifier in record.registration_ids:
        identifier = _normalize_identifier(raw_identifier)
        if not identifier:
            continue
        key = _stable_text_key("identifier", identifier)
        source_record_key = f"registration-id:{record.id}:{identifier}"
        nodes.append(
            GraphNodeSnapshot(
                node_key=key,
                node_type=GraphNodeType.IDENTIFIER,
                display_name=identifier,
                source_module="organizations",
                source_entity_type="registration_identifier",
                source_record_key=source_record_key,
                organization_id=record.id,
                observed_at=record.updated_at,
                valid_from=record.created_at,
                confidence=1.0,
            )
        )
        edges.append(
            _organization_reference_edge(
                record=record,
                node_key=key,
                source_record_key=source_record_key,
                edge_type=GraphEdgeType.IDENTIFIES,
                evidence_class="registration_identifier",
                review_required=identifier_counts[identifier] > 1,
            )
        )


def _organization_reference_edge(
    *,
    record: OrganizationRecord,
    node_key: str,
    source_record_key: str,
    edge_type: GraphEdgeType,
    evidence_class: str,
    review_required: bool,
) -> GraphEdgeSnapshot:
    return GraphEdgeSnapshot(
        edge_key=f"{edge_type.value}-organization:{node_key}:{record.id}",
        source_node_key=node_key,
        target_node_key=f"organization:{record.id}",
        edge_type=edge_type,
        source_module="organizations",
        source_record_key=source_record_key,
        source_evidence_class=evidence_class,
        claim_type=GraphClaimType.ASSERTION,
        review_state=(
            GraphReviewState.REVIEW_REQUIRED
            if review_required
            else GraphReviewState.CONFIRMED
        ),
        observed_at=record.updated_at,
        confidence=1.0,
    )


def _legal_alias(record: OrganizationRecord) -> str | None:
    legal_name = record.legal_name
    if legal_name is None:
        return None
    normalized = _normalize_name(legal_name)
    if not normalized or normalized == _normalize_name(record.canonical_name):
        return None
    return normalized


def _normalize_name(value: str) -> str:
    return " ".join(value.casefold().split())


def _normalize_identifier(value: object) -> str:
    return str(value).strip().casefold()


def _stable_text_key(prefix: str, value: str) -> str:
    digest = sha256(value.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _website_domain(url: str | None) -> str | None:
    if url is None or not url.strip():
        return None
    value = url.strip()
    parsed = urlparse(value if "://" in value else f"https://{value}")
    if parsed.hostname is None:
        return None
    normalized = parsed.hostname.casefold().rstrip(".")
    return normalized[4:] if normalized.startswith("www.") else normalized
