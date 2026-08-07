from __future__ import annotations

from pathlib import Path
import re


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f"expected {label} text not found: {old[:120]}")
    return text.replace(old, new, 1)


def sync_readme() -> None:
    path = Path("README.md")
    text = path.read_text(encoding="utf-8")
    replacements = (
        (
            "The current validated release is version `0.19.0`, covering lots `00` through `18`.",
            "The current validated release is version `0.20.0`, covering lots `00` through `19`.",
            "release baseline",
        ),
        (
            "- source-aware corporate and regulatory change intelligence with immutable claim history, syndication-aware corroboration, explicit confirmation/report/speculation/dispute/correction/retraction states, separate service mappings, protected APIs, and the Corporate Changes workspace.\n",
            "- source-aware corporate and regulatory change intelligence with immutable claim history, syndication-aware corroboration, explicit confirmation/report/speculation/dispute/correction/retraction states, separate service mappings, protected APIs, and the Corporate Changes workspace;\n- temporal provider, customer, partner, supplier, reseller, integrator, auditor, insurer, MSSP/MDR, cloud-provider, technology-vendor, and subcontractor relationship intelligence with immutable evidence history, explicit evidence classes, reversible chronology, protected APIs, and the Relationships workspace.\n",
            "relationship capability",
        ),
        (
            "Lot `18` provides source-aware public corporate and regulatory change intelligence. It separates official filings, regulator notices, company disclosures, media reporting, analyst commentary, speculation, disputes, corrections, retractions, syndication, and staleness; preserves immutable revisions and distinct event/publication/update times; bounds stored excerpts; and keeps service-family mappings separate from raw evidence. A repeated report is not independent corroboration, reporting is not official confirmation, and a raw change event is not a need, opportunity, or authorization to contact. All newly modeled change-intelligence providers remain unauthorized, unscheduled, and non-executable candidates.\n\nThe next planned implementation lot is `19`: temporal provider, customer, partner, supplier, integrator, auditor, insurer, MSSP, and other relationship intelligence.",
            "Lot `18` provides source-aware public corporate and regulatory change intelligence. It separates official filings, regulator notices, company disclosures, media reporting, analyst commentary, speculation, disputes, corrections, retractions, syndication, and staleness; preserves immutable revisions and distinct event/publication/update times; bounds stored excerpts; and keeps service-family mappings separate from raw evidence. A repeated report is not independent corroboration, reporting is not official confirmation, and a raw change event is not a need, opportunity, or authorization to contact. All newly modeled change-intelligence providers remain unauthorized, unscheduled, and non-executable candidates.\n\nLot `19` provides temporal, directed, evidence-backed organization relationships. It separates claimed, observed, contracted, historical, and inferred evidence; preserves source/target direction, endpoint identity review, validity, expiry, corrections and retractions; and keeps contract/product/service contexts separate from source evidence. Marketing claims are not contract evidence, historical or inferred relationships are not current incumbents, and relationship evidence is not a need, opportunity, or authorization to contact. New relationship providers remain unauthorized, unscheduled, and non-executable candidates.\n\nThe next planned implementation lot is `20`: entity resolution and the temporal corporate knowledge graph.",
            "Lot 19 release boundary",
        ),
        (
            "Selected corporate-change schemas and deterministic mappings are implemented for:\n\n- official corporate disclosures;\n- official regulatory change notices;\n- licensed corporate-news metadata with bounded excerpts and explicit syndication identity.\n\nEvery newly modeled passive, advisory, or corporate-change candidate is `draft`, has missing authorization, has no approved hosts or paths, has no schedule or registered runtime adapter, and is marked `executable: false`.",
            "Selected corporate-change schemas and deterministic mappings are implemented for:\n\n- official corporate disclosures;\n- official regulatory change notices;\n- licensed corporate-news metadata with bounded excerpts and explicit syndication identity.\n\nSelected relationship schemas and deterministic mappings are implemented for:\n\n- official relationship disclosures;\n- public partner directories;\n- bounded public case-study metadata;\n- public certificate relationship metadata.\n\nEvery newly modeled passive, advisory, corporate-change, or relationship candidate is `draft`, has missing authorization, has no approved hosts or paths, has no schedule or registered runtime adapter, and is marked `executable: false`.",
            "relationship provider portfolio",
        ),
        (
            "The `/research`, `/vulnerabilities`, `/incidents`, `/threat-intelligence`, `/passive-exposure`, `/vulnerability-applicability`, and `/corporate-changes` workspaces and their APIs search persisted data only.",
            "The `/research`, `/vulnerabilities`, `/incidents`, `/threat-intelligence`, `/passive-exposure`, `/vulnerability-applicability`, `/corporate-changes`, and `/relationships` workspaces and their APIs search persisted data only.",
            "relationships workspace",
        ),
        (
            "4. evidence, observations, public claims, vulnerability snapshots, incident claims, telemetry snapshots, passive observation snapshots, advisory revisions, and corporate-change claim revisions;\n5. resolved organizations, incidents, vulnerabilities, indicators, passive assets, technologies, products, providers, material changes, roles, and temporal relationships;",
            "4. evidence, observations, public claims, vulnerability snapshots, incident claims, telemetry snapshots, passive observation snapshots, advisory revisions, corporate-change claim revisions, and relationship evidence snapshots;\n5. resolved organizations, incidents, vulnerabilities, indicators, passive assets, technologies, products, providers, material changes, business relationships, roles, and temporal relationships;",
            "architecture layers",
        ),
        (
            "- lots `00–18`: implemented and validated foundations, procurement, hiring, identity, onboarding, source runtime, contracts, public footprint, vulnerability knowledge, public incident intelligence, defensive telemetry, passive technographic evidence, vendor advisories, vulnerability applicability, and corporate/regulatory change intelligence;\n- lot `19`: provider, customer, partner, supplier, integrator, auditor, insurer, MSSP, and other temporal relationship intelligence;",
            "- lots `00–19`: implemented and validated foundations, procurement, hiring, identity, onboarding, source runtime, contracts, public footprint, vulnerability knowledge, public incident intelligence, defensive telemetry, passive technographic evidence, vendor advisories, vulnerability applicability, corporate/regulatory change intelligence, and temporal relationship intelligence;\n- lot `20`: entity resolution and temporal corporate knowledge graph;",
            "roadmap summary",
        ),
        (
            "- corporate change intelligence cannot import network clients, collection adapters, opportunity modules, contacts, or outreach modules.\n",
            "- corporate change intelligence cannot import network clients, collection adapters, opportunity modules, contacts, or outreach modules;\n- relationship intelligence cannot import network clients, collection adapters, or opportunity modules.\n",
            "relationship architecture boundary",
        ),
        (
            "- turn a public/media material-change report directly into an official confirmation, service need, opportunity, contact target, or outreach action.\n",
            "- turn a public/media material-change report directly into an official confirmation, service need, opportunity, contact target, or outreach action;\n- treat a marketing claim as contract evidence or an active incumbent;\n- treat a historical or inferred organization relationship as a verified current relationship.\n",
            "relationship safety boundary",
        ),
        (
            "- [`docs/lots/LOT_18_VALIDATION_REPORT.md`](docs/lots/LOT_18_VALIDATION_REPORT.md)\n- [`SECURITY.md`](SECURITY.md)",
            "- [`docs/lots/LOT_18_VALIDATION_REPORT.md`](docs/lots/LOT_18_VALIDATION_REPORT.md)\n- [`docs/lots/LOT_19_RELATIONSHIP_INTELLIGENCE.md`](docs/lots/LOT_19_RELATIONSHIP_INTELLIGENCE.md)\n- [`docs/lots/LOT_19_VALIDATION_REPORT.md`](docs/lots/LOT_19_VALIDATION_REPORT.md)\n- [`SECURITY.md`](SECURITY.md)",
            "Lot 19 document links",
        ),
    )
    for old, new, label in replacements:
        text = replace_once(text, old, new, label)
    path.write_text(text, encoding="utf-8")


def sync_roadmap() -> None:
    path = Path("docs/PROJECT_DELIVERY_PLAN.md")
    text = path.read_text(encoding="utf-8")
    text, count = re.subn(
        r"(?m)^(\| 19 \|.*?\| )`PLANNED_LOCKED`( \|)$",
        r"\1`IMPLEMENTED_VALIDATED`\2",
        text,
        count=1,
    )
    if count == 0 and not re.search(
        r"(?m)^\| 19 \|.*?\| `IMPLEMENTED_VALIDATED` \|$", text
    ):
        raise SystemExit("Lot 19 roadmap table row not found")
    match = re.search(r"(?ms)(^## Lot 19\b.*?)(?=^## Lot 20\b)", text)
    if not match:
        raise SystemExit("Lot 19 roadmap section not found")
    section = match.group(1)
    if "**Status:** `IMPLEMENTED_VALIDATED`" not in section:
        section = section.replace(
            "**Status:** `PLANNED_LOCKED`",
            "**Status:** `IMPLEMENTED_VALIDATED`",
            1,
        )
    if "**Outcome:**" not in section:
        section = section.replace("**Primary business outcome:**", "**Outcome:**", 1)
    text = text[: match.start(1)] + section + text[match.end(1) :]
    boundary = """## Current release boundary

Version `0.20.0` implements and validates lots `00–19`. Lot 19 installs directed temporal business relationships, immutable evidence snapshots, claimed/observed/contracted/historical/inferred evidence classes, explicit endpoint identity review, validity and renewal chronology, contract-backed current state, reversible persistence, protected APIs, and the Relationships workspace.

Existing persisted procurement contracts can project into contracted relationship evidence without authorizing new network collection. Generic public/provider relationship schemas cannot emit contracted evidence. New relationship source candidates remain authorization-missing, unscheduled, non-executable, and forbidden from private portals, personal networks, automatic opportunity creation, contact enrichment, or outreach.

Lot 20 is the next locked implementation lot. It must start from the merged Lot 19 `main` commit and preserve reversible identity decisions, temporal validity, source lineage, evidence class, relationship direction, confidence, correction, suppression, and review state. Claimed or inferred edges must not silently become verified facts merely because they enter the graph.
"""
    text, count = re.subn(
        r"(?ms)^## Current release boundary\n.*\Z",
        boundary,
        text,
        count=1,
    )
    if count != 1:
        raise SystemExit("Current release boundary not found")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    sync_readme()
    sync_roadmap()


if __name__ == "__main__":
    main()
