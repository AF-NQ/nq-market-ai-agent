from src.priority_watch import is_hormuz_catalyst, priority_direction, priority_urgency_score


def test_hormuz_reopening_talks_are_priority_catalyst():
    x = {
        "title": "US and Iran discuss phased deal to reopen Hormuz and end US blockade, sources say",
        "summary": "",
    }
    assert is_hormuz_catalyst(x)
    assert priority_direction(x) == "BULLISH"
    assert priority_urgency_score(x) == 90


def test_hormuz_closure_risk_is_priority_and_bearish_for_equities():
    x = {
        "title": "Iran warns of Hormuz closure as shipping is halted",
        "summary": "",
    }
    assert is_hormuz_catalyst(x)
    assert priority_direction(x) == "BEARISH"
