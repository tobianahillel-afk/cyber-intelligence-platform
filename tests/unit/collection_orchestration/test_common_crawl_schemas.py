from cip.adapters.sources.common_crawl.schemas import CommonCrawlCollection


def test_common_crawl_accepts_published_legacy_collection_identity() -> None:
    collection = CommonCrawlCollection.model_validate(
        {
            "id": "CC-MAIN-2012",
            "name": "2012 Index",
            "timegate": "https://index.commoncrawl.org/CC-MAIN-2012/",
            "cdx-api": "https://index.commoncrawl.org/CC-MAIN-2012-index",
            "from": "2012-01-01T00:00:00",
            "to": "2012-12-31T23:59:59",
        }
    )
    assert collection.id == "CC-MAIN-2012"
    assert collection.to_at.tzinfo is not None
