from src.scoring import equity_direction, index_relevance, market_impact, score_event


def item(title, pub="Reuters", published="2026-09-21T18:00:00+00:00"):
    return {
        "title": title,
        "summary": "",
        "publisher": pub,
        "source": pub,
        "link": "https://example.com/a",
        "published": published,
    }


def test_impact_is_not_source_quality():
    good = market_impact(item("Fed decision: unexpected rate cut", "Reuters"))
    weak = market_impact(item("Fed decision: unexpected rate cut", "Unknown blog"))
    assert good == weak
    assert good >= 75


def test_index_relevance_differs_between_nq_and_spx_for_ai():
    x = item("Nvidia AI demand drives semiconductor rally")
    assert index_relevance(x, "NQ") > index_relevance(x, "SPX")


def test_direction_can_be_neutral_when_event_is_important_but_ambiguous():
    x = item('Trump pushes "super intelligence," dismisses AI risks and eyes China hotline')
    metrics = score_event(x)
    assert metrics["market_impact"] >= 50
    assert metrics["nq_relevance"] >= 70
    assert metrics["equity_direction"] == "NEUTRAL"


def test_explicit_rate_hike_is_bearish_for_equities():
    x = item("Fed official says more rate hikes likely needed to curb inflation")
    assert equity_direction(x) == "BEARISH"


def test_score_event_exposes_separate_metrics():
    x = item("Wall Street ends sharply higher as AI optimism reignites and Treasury yields retreat")
    metrics = score_event(x)
    assert set(("market_impact", "nq_relevance", "spx_relevance", "equity_direction", "direction_confidence", "ranking_score")) <= metrics.keys()
    assert metrics["market_impact"] > 0
    assert metrics["nq_relevance"] > 0
    assert 0 <= metrics["direction_confidence"] <= 100


def test_hormuz_reopening_talks_are_fast_path_market_catalyst():
    x = item("US and Iran discuss phased deal to reopen Hormuz and end US blockade, sources say")
    metrics = score_event(x)
    assert metrics["market_impact"] >= 88
    assert metrics["nq_relevance"] >= 80
    assert metrics["spx_relevance"] >= 80
    assert metrics["equity_direction"] == "BULLISH"
