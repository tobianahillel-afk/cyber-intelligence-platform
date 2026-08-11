from __future__ import annotations

from collections.abc import Mapping

import httpx

BASE = "https://api.w3.org"
TARGET_NAMES = ("Mozilla", "Google", "Microsoft")


def main() -> None:
    with httpx.Client(timeout=30.0, follow_redirects=False) as client:
        affiliation = _find_affiliation(client)
        print(
            "W3C_PROBE_AFFILIATION",
            {
                "id": affiliation.get("id"),
                "name": affiliation.get("name"),
                "keys": sorted(affiliation.keys()),
            },
        )
        affiliation_id = affiliation.get("id")
        if not isinstance(affiliation_id, int):
            raise RuntimeError("W3C affiliation id is not an integer")
        response = client.get(
            f"{BASE}/affiliations/{affiliation_id}/participations",
            params={"items": 5, "page": 1, "embed": "true"},
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
        print("W3C_PROBE_PARTICIPATIONS_TOP_KEYS", sorted(payload.keys()))
        embedded = payload.get("_embedded", {})
        if not isinstance(embedded, Mapping):
            raise RuntimeError("W3C participations _embedded is not a mapping")
        print("W3C_PROBE_EMBEDDED_KEYS", sorted(embedded.keys()))
        items = next(
            (value for value in embedded.values() if isinstance(value, list)),
            [],
        )
        if not items:
            raise RuntimeError("W3C controlled affiliation returned no participations")
        item = items[0]
        if not isinstance(item, Mapping):
            raise RuntimeError("W3C participation is not a mapping")
        print("W3C_PROBE_PARTICIPATION_KEYS", sorted(item.keys()))
        links = item.get("_links", {})
        if isinstance(links, Mapping):
            print("W3C_PROBE_PARTICIPATION_LINK_KEYS", sorted(links.keys()))
            for name, value in links.items():
                if isinstance(value, Mapping):
                    href = value.get("href")
                    if isinstance(href, str):
                        print("W3C_PROBE_LINK", name, href)


def _find_affiliation(client: httpx.Client) -> Mapping[str, object]:
    for page in range(1, 21):
        response = client.get(
            f"{BASE}/affiliations",
            params={"items": 100, "page": page},
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
        embedded = payload.get("_embedded", {})
        if not isinstance(embedded, Mapping):
            continue
        affiliations = embedded.get("affiliations", [])
        if not isinstance(affiliations, list):
            continue
        for affiliation in affiliations:
            if not isinstance(affiliation, Mapping):
                continue
            name = affiliation.get("name")
            if isinstance(name, str) and any(
                candidate.casefold() in name.casefold() for candidate in TARGET_NAMES
            ):
                return affiliation
    raise RuntimeError("no controlled W3C affiliation target found")


if __name__ == "__main__":
    main()
