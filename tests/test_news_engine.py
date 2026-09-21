from src.news_engine import build_catalysts, categories, direction, publisher


def item(title, pub="Reuters", link="https://example.com/a", published="2026-09-21T18:00:00+00:00"):
    return {
        "title": title,
        "summary": "",
        "publisher": pub,
        "source": "Google Finance News",
        "link": link,
        "published": published,
        "priority": 100,
    }


def test_publisher_metadata_is_preferred():
    x = item("Nvidia earnings outlook")
    assert publisher(x) == "Reuters"


def test_categories_and_direction():
    x = item("Nvidia shares rise as AI demand boosts earnings outlook")
    assert "AI / SEMICONDUCTORS" in categories(x)
    assert "EARNINGS" in categories(x)
    assert direction(x) == "BULLISH"


def test_similar_headlines_become_one_catalyst():
    items = [
        item("Nvidia earnings lift Nasdaq futures ahead of results", "Reuters", "https://example.com/1"),
        item("Nasdaq futures rise as Nvidia earnings approach", "CNBC", "https://example.com/2"),
        item("US stock futures steady ahead of Nvidia earnings", "Yahoo Finance", "https://example.com/3"),
    ]
    catalysts = build_catalysts(items)
    assert len(catalysts) == 1
    assert catalysts[0]["source_count"] == 3
    assert catalysts[0]["cluster_size"] == 3


def test_different_catalysts_remain_separate():
    items = [
        item("Fed officials signal rates may stay higher for longer", "Reuters", "https://example.com/fed"),
        item("Oil prices fall after ceasefire reduces supply concerns", "Reuters", "https://example.com/oil"),
    ]
    catalysts = build_catalysts(items)
    assert len(catalysts) == 2
    assert {x["categories"][0] for x in catalysts} >= {"FED / RATES", "OIL / ENERGY"}
