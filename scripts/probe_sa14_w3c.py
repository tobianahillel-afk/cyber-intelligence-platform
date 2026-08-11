from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urljoin

import httpx

BASE = "https://api.w3.org"


def main() -> None:
    with httpx.Client(timeout=30.0, follow_redirects=False) as client:
        affiliation, participation = _find_controlled_affiliation(client)
        print(
            "W3C_PROBE_AFFILIATION",
            {
                "id": affiliation.get("id"),
                "name": affiliation.get("name"),
                "keys": sorted(affiliation.keys()),
            },
        )
        print("W3C_PROBE_PARTICIPATION_KEYS", sorted(participation.keys()))
        links = participation.get("_links", {})
        if not isinstance(links, Mapping):
            raise RuntimeError("W3C participation links are missing")
        print("W3C_PROBE_PARTICIPATION_LINK_KEYS", sorted(links.keys()))
        group_href = _first_href(links, "group")
        if group_href is None:
            raise RuntimeError("W3C participation has no group link")
        group_url = urljoin(BASE, group_href)
        print("W3C_PROBE_GROUP_URL", group_url)
        group_response = client.get(group_url, headers={"Accept": "application/json"})
        group_response.raise_for_status()
        group = group_response.json()
        if not isinstance(group, Mapping):
            raise RuntimeError("W3C group response is not a mapping")
        print(
            "W3C_PROBE_GROUP",
            {
                "id": group.get("id"),
                "name": group.get("name"),
                "shortname": group.get("shortname"),
                "type": group.get("type"),
                "keys": sorted(group.keys()),
            },
        )
        group_links = group.get("_links", {})
        if not isinstance(group_links, Mapping):
            raise RuntimeError("W3C group links are missing")
        print("W3C_PROBE_GROUP_LINK_KEYS", sorted(group_links.keys()))
        specifications_href = _first_href(group_links, "specifications")
        if specifications_href is None:
            specifications_href = f"{group_url.rstrip('/')}/specifications"
        specifications_url = urljoin(BASE, specifications_href)
        response = client.get(
            specifications_url,
            params={"items": 5, "page": 1},
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, Mapping):
            raise RuntimeError("W3C specification response is not a mapping")
        print("W3C_PROBE_SPECIFICATIONS_TOP_KEYS", sorted(payload.keys()))
        embedded = payload.get("_embedded", {})
        if not isinstance(embedded, Mapping):
            raise RuntimeError("W3C specifications _embedded is not a mapping")
        print("W3C_PROBE_SPECIFICATIONS_EMBEDDED_KEYS", sorted(embedded.keys()))
        specs = next(
            (value for value in embedded.values() if isinstance(value, list)),
            [],
        )
        if specs:
            spec = specs[0]
            if not isinstance(spec, Mapping):
                raise RuntimeError("W3C specification item is not a mapping")
            print(
                "W3C_PROBE_SPECIFICATION",
                {
                    "shortname": spec.get("shortname"),
                    "title": spec.get("title"),
                    "status": spec.get("status"),
                    "keys": sorted(spec.keys()),
                    "link_keys": sorted(
                        spec.get("_links", {}).keys()
                        if isinstance(spec.get("_links"), Mapping)
                        else []
                    ),
                },
            )
        else:
            print("W3C_PROBE_SPECIFICATIONS_EMPTY", True)


def _find_controlled_affiliation(
    client: httpx.Client,
) -> tuple[Mapping[str, object], Mapping[str, object]]:
    response = client.get(
        f"{BASE}/affiliations",
        params={"items": 30, "page": 1},
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()
    embedded = payload.get("_embedded", {})
    if not isinstance(embedded, Mapping):
        raise RuntimeError("W3C affiliations _embedded is not a mapping")
    affiliations = embedded.get("affiliations", [])
    if not isinstance(affiliations, list):
        raise RuntimeError("W3C affiliations collection is not a list")
    print(
        "W3C_PROBE_AFFILIATION_SAMPLES",
        [
            {"id": item.get("id"), "name": item.get("name")}
            for item in affiliations[:10]
            if isinstance(item, Mapping)
        ],
    )
    for affiliation in affiliations:
        if not isinstance(affiliation, Mapping):
            continue
        affiliation_id = affiliation.get("id")
        if not isinstance(affiliation_id, (int, str)):
            continue
        participation_response = client.get(
            f"{BASE}/affiliations/{affiliation_id}/participations",
            params={"items": 5, "page": 1},
            headers={"Accept": "application/json"},
        )
        if participation_response.status_code == 404:
            continue
        participation_response.raise_for_status()
        participation_payload = participation_response.json()
        participation_embedded = participation_payload.get("_embedded", {})
        if not isinstance(participation_embedded, Mapping):
            continue
        print(
            "W3C_PROBE_PARTICIPATIONS_TOP_KEYS",
            sorted(participation_payload.keys()),
        )
        print(
            "W3C_PROBE_PARTICIPATIONS_EMBEDDED_KEYS",
            sorted(participation_embedded.keys()),
        )
        participations = next(
            (
                value
                for value in participation_embedded.values()
                if isinstance(value, list)
            ),
            [],
        )
        if participations and isinstance(participations[0], Mapping):
            return affiliation, participations[0]
    raise RuntimeError("first W3C affiliations returned no public group participations")


def _first_href(links: Mapping[str, object], key: str) -> str | None:
    value = links.get(key)
    if isinstance(value, Mapping):
        href = value.get("href")
        return href if isinstance(href, str) else None
    return None


if __name__ == "__main__":
    main()
