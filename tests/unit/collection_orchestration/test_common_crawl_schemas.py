import pytest

from cip.adapters.sources.common_crawl.schemas import CommonCrawlCollection


@pytest.mark.parametrize(
    "crawl_id",
    (
        "CC-MAIN-2026-30",
        "CC-MAIN-2012",
        "CC-MAIN-2009-2010",
        "CC-MAIN-2008-2009",
    ),
)
def test_common_crawl_accepts_published_collection_identity_forms(crawl_id: str) -> None:
    collection = CommonCrawlCollection.model_validate(
        {
            "id": crawl_id,
            "name": f"{crawl_id} Index",
            "timegate": f"https://index.commoncrawl.org/{crawl_id}/",
            "cdx-api": f"https://index.commoncrawl.org/{crawl_id}-index",
            "from": "2008-01-01T00:00:00",
            "to": "2026-12-31T23:59:59",
        }
    )
    assert collection.id == crawl_id
    assert collection.to_at.tzinfo is not None


def test_common_crawl_rejects_unpublished_collection_identity_shape() -> None:
    with pytest.raises(ValueError, match="collection id is invalid"):
        CommonCrawlCollection.model_validate(
            {
                "id": "CC-MAIN-anything-goes",
                "name": "Invalid",
                "timegate": "https://index.commoncrawl.org/invalid/",
                "cdx-api": "https://index.commoncrawl.org/invalid-index",
                "from": "2026-01-01T00:00:00",
                "to": "2026-01-02T00:00:00",
            }
        )