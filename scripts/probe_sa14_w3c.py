from __future__ import annotations

from collections.abc import Mapping
from json import dumps
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

BASE = "https://api.w3.org"
OUTPUT = Path("w3c-probe.json")


def main() -> None:
    summary: dict[str, Any] = {}
    try:
        with httpx.Client(timeout=30.0, follow_redirects=False) as client:
            affiliation, participation = _find_controlled_affiliation(client, summary)
            summary["affiliation"] = _select(affiliation, "id", "name", "status", "type")
            summary["affiliation_keys"] = sorted(affiliation.keys())
            summary["participation_keys"] = sorted(participation.keys())
            links = participation.get("_links", {})
            if not isinstance(links, Mapping):
                raise RuntimeError("W3C participation links are missing")
            summary["participation_link_keys"] = sorted(links.keys())
            summary["participation_links"] = _safe_links(links)
            group_href = _first_href(links, "group")
            if group_href is None:
                raise RuntimeError("W3C participation has no group link")
            group_url = urljoin(BASE, group_href)
            summary["group_url"] = group_url
            group_response = client.get(group_url, headers={"Accept": "application/json"})
            group_response.raise_for_status()
            group = group_response.json()
            if not isinstance(group, Mapping):
                raise RuntimeError("W3C group response is not a mapping")
            summary["group"] = _select(group, "id", "name", "shortname", "type", "state")
            summary["group_keys"] = sorted(group.keys())
            group_links = group.get("_links", {})
            if not isinstance(group_links, Mapping):
                raise RuntimeError("W3C group links are missing")
            summary["group_link_keys"] = sorted(group_links.keys())
            summary["group_links"] = _safe_links(group_links)
            specifications_href = _first_href(group_links, "specifications")
            if specifications_href is None:
                specifications_href = f"{group_url.rstrip('/')}/specifications"
            specifications_url = urljoin(BASE, specifications_href)
            summary["specifications_url"] = specifications_url
            response = client.get(
                specifications_url,
                params={"items": 5, "page": 1, "embed": 1},
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, Mapping):
                raise RuntimeError("W3C specification response is not a mapping")
            summary["specifications_top_keys"] = sorted(payload.keys())
            embedded = payload.get("_embedded", {})
            if not isinstance(embedded, Mapping):
                raise RuntimeError("W3C specifications _embedded is not a mapping")
            summary["specifications_embedded_keys"] = sorted(embedded.keys())
            specs = next((value for value in embedded.values() if isinstance(value, list)), [])
            summary["specifications_count_in_probe"] = len(specs)
            if specs and isinstance(specs[0], Mapping):
                spec = specs[0]
                summary["specification"] = _select(
                    spec,
                    "shortname",
                    "title",
                    "status",
                    "description",
                )
                summary["specification_keys"] = sorted(spec.keys())
                spec_links = spec.get("_links", {})
                if isinstance(spec_links, Mapping):
                    summary["specification_link_keys"] = sorted(spec_links.keys())
                    summary["specification_links"] = _safe_links(spec_links)
    except Exception as exc:
        summary["error"] = f"{type(exc).__name__}: {exc}"
        OUTPUT.write_text(dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        raise
    OUTPUT.write_text(dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def _find_controlled_affiliation(
    client: httpx.Client,
    summary: dict[str, Any],
) -> tuple[Mapping[str, object], Mapping[str, object]]:
    response = client.get(
        f"{BASE}/affiliations",
        params={"items": 30, "page": 1, "embed": 1},
        headers={"Accept": "application/json"},
    )
    summary["affiliations_status"] = response.status_code
    response.raise_for_status()
    payload = response.json()
    summary["affiliations_top_keys"] = sorted(payload.keys())
    embedded = payload.get("_embedded", {})
    if not isinstance(embedded, Mapping):
        raise RuntimeError("W3C affiliations _embedded is not a mapping")
    summary["affiliations_embedded_keys"] = sorted(embedded.keys())
    affiliations = embedded.get("affiliations", [])
    if not isinstance(affiliations, list):
        raise RuntimeError("W3C affiliations collection is not a list")
    summary["affiliation_samples"] = [
        _select(item, "id", "name", "status", "type")
        for item in affiliations[:15]
        if isinstance(item, Mapping)
    ]
    summary["affiliation_sample_keys"] = [
        sorted(item.keys()) for item in affiliations[:3] if isinstance(item, Mapping)
    ]
    attempts: list[dict[str, object]] = []
    for affiliation in affiliations:
        if not isinstance(affiliation, Mapping):
            continue
        affiliation_id = affiliation.get("id")
        if not isinstance(affiliation_id, (int, str)):
            continue
        participation_response = client.get(
            f"{BASE}/affiliations/{affiliation_id}/participations",
            params={"items": 5, "page": 1, "embed": 1},
            headers={"Accept": "application/json"},
        )
        attempts.append(
            {
                "id": affiliation_id,
                "name": affiliation.get("name"),
                "status": participation_response.status_code,
            }
        )
        if participation_response.status_code == 404:
            continue
        participation_response.raise_for_status()
        participation_payload = participation_response.json()
        participation_embedded = participation_payload.get("_embedded", {})
        if not isinstance(participation_embedded, Mapping):
            continue
        summary["participations_top_keys"] = sorted(participation_payload.keys())
        summary["participations_embedded_keys"] = sorted(participation_embedded.keys())
        participations = next(
            (value for value in participation_embedded.values() if isinstance(value, list)),
            [],
        )
        if participations and isinstance(participations[0], Mapping):
            summary["participation_attempts"] = attempts
            return affiliation, participations[0]
    summary["participation_attempts"] = attempts
    raise RuntimeError("first W3C affiliations returned no public group participations")


def _select(value: Mapping[str, object], *keys: str) -> dict[str, object]:
    return {key: value.get(key) for key in keys if key in value}


def _safe_links(links: Mapping[str, object]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in links.items():
        if not isinstance(value, Mapping):
            continue
        href = value.get("href")
        if isinstance(href, str):
            result[key] = href
    return result


def _first_href(links: Mapping[str, object], key: str) -> str | None:
    value = links.get(key)
    if isinstance(value, Mapping):
        href = value.get("href")
        return href if isinstance(href, str) else None
    return None


if __name__ == "__main__":
    main()
