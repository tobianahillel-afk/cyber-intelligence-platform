from __future__ import annotations

from cip.modules.source_activation.domain.models import ActivationStage
from cip.modules.source_activation.infrastructure import load_activation_inventory
from cip.shared.config.settings import Settings


def test_sa15_promotes_only_search_provider_with_real_live_proof() -> None:
    records = {
        record.source_id: record
        for record in load_activation_inventory(Settings().source_activation_path)
    }

    internet_archive = records["internet-archive-cdx"]
    assert ActivationStage.LIVE_TESTED in internet_archive.stages
    assert internet_archive.is_fully_integrated is True

    for source_id in (
        "brave-search-api",
        "mojeek-web-search-metadata",
        "patentsview-patent-metadata",
    ):
        assert ActivationStage.LIVE_TESTED not in records[source_id].stages
