"""Fast-path detection for rare, market-moving catalysts.

These rules are intentionally narrow. They exist because a generic relevance
ranker can miss a headline whose market impact is driven by a specific event
combination (for example, Hormuz + reopening talks), even when the article is
new and from a high-quality publisher.
"""


def _text(item):
    return ((item.get("title", "") or "") + " " + (item.get("summary", "") or "")).lower()


HORMUZ_TERMS = ("hormuz", "strait of hormuz")
HORMUZ_ACTION_TERMS = (
    "reopen", "reopens", "reopening", "open the strait", "open hormuz",
    "close hormuz", "closure", "closed strait", "shipping halted",
    "phased deal", "phased path", "agreement", "deal", "talks", "negotiat",
    "blockade", "shipping", "navigation", "free passage",
)


def is_hormuz_catalyst(item):
    text = _text(item)
    return any(k in text for k in HORMUZ_TERMS) and any(k in text for k in HORMUZ_ACTION_TERMS)


def is_priority_catalyst(item):
    """Return True only for narrow combinations with plausible fast market transmission."""
    if is_hormuz_catalyst(item):
        return True

    text = _text(item)
    if "taiwan strait" in text and any(k in text for k in ("blockade", "invasion", "attack", "military action", "drill")):
        return True
    if "opec" in text and any(k in text for k in ("emergency", "production cut", "production increase", "output cut", "output increase")):
        return True
    if "fed" in text and any(k in text for k in ("emergency meeting", "unscheduled meeting", "emergency rate", "surprise rate")):
        return True
    return False


def priority_direction(item):
    """Directional equity pressure for the narrow fast-path events."""
    text = _text(item)
    if is_hormuz_catalyst(item):
        if any(k in text for k in ("reopen", "reopening", "open the strait", "open hormuz", "phased deal", "phased path", "free passage")):
            return "BULLISH"
        if any(k in text for k in ("close hormuz", "closure", "closed strait", "blockade of shipping", "shipping halted")):
            return "BEARISH"
    if "taiwan strait" in text and any(k in text for k in ("blockade", "invasion", "attack", "military action")):
        return "BEARISH"
    return ""


def priority_urgency_score(item):
    """Intrinsic event score for the fast path, separate from source quality/freshness."""
    if is_hormuz_catalyst(item):
        return 90
    if "taiwan strait" in _text(item):
        return 88
    if "opec" in _text(item):
        return 84
    if "fed" in _text(item):
        return 92
    return 0
