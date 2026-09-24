"""Explainable market-event scoring for NQ / S&P 500 news.

The public-facing scores deliberately separate four concepts:
- market_impact: importance of the underlying event itself;
- index_relevance: how directly the event can transmit to NQ or S&P 500;
- direction: descriptive equity-pressure direction;
- direction_confidence: confidence in that directional interpretation.

Source quality, freshness and cross-source coverage affect confidence/ranking,
not the intrinsic impact of the event.
"""

import re

from .news_engine import categories, direction, freshness_hours, nq_directness, source_quality
from .priority_watch import is_priority_catalyst, priority_direction, priority_urgency_score


# Approximate thematic importance, intentionally not source- or freshness-weighted.
IMPACT_BASE = {
    "FED / RATES": 72,
    "INFLATION / MACRO": 70,
    "LABOR": 68,
    "TREASURIES / YIELDS": 64,
    "AI / SEMICONDUCTORS": 66,
    "MEGA-CAP": 60,
    "EARNINGS": 68,
    "TARIFFS / TRADE": 62,
    "GEOPOLITICS": 55,
    "INDEX / FUTURES": 62,
    "OIL / ENERGY": 52,
    "REGULATION": 50,
    "CHINA / PBOC": 52,
    "JAPAN / BOJ": 48,
    "ASIA / SEMICONDUCTORS": 58,
    "EUROPE / ECB": 44,
    "GLOBAL FX": 42,
    "USD": 50,
}

NQ_BASE = {
    "FED / RATES": 86,
    "INFLATION / MACRO": 82,
    "LABOR": 80,
    "TREASURIES / YIELDS": 84,
    "AI / SEMICONDUCTORS": 91,
    "MEGA-CAP": 88,
    "EARNINGS": 78,
    "TARIFFS / TRADE": 70,
    "GEOPOLITICS": 58,
    "INDEX / FUTURES": 94,
    "OIL / ENERGY": 50,
    "REGULATION": 56,
    "CHINA / PBOC": 53,
    "JAPAN / BOJ": 40,
    "ASIA / SEMICONDUCTORS": 70,
    "EUROPE / ECB": 36,
    "GLOBAL FX": 40,
    "USD": 62,
}

SPX_BASE = {
    "FED / RATES": 90,
    "INFLATION / MACRO": 88,
    "LABOR": 86,
    "TREASURIES / YIELDS": 88,
    "AI / SEMICONDUCTORS": 68,
    "MEGA-CAP": 78,
    "EARNINGS": 82,
    "TARIFFS / TRADE": 76,
    "GEOPOLITICS": 64,
    "INDEX / FUTURES": 94,
    "OIL / ENERGY": 60,
    "REGULATION": 58,
    "CHINA / PBOC": 56,
    "JAPAN / BOJ": 42,
    "ASIA / SEMICONDUCTORS": 56,
    "EUROPE / ECB": 40,
    "GLOBAL FX": 44,
    "USD": 66,
}

NQ_DIRECT_TERMS = (
    "nasdaq", "nasdaq-100", "nasdaq 100", "nq futures", "qqq", "ndx",
    "technology stocks", "tech stocks", "ai stocks", "semiconductor stocks",
    "nvidia", "nvda", "amd", "broadcom", "avgo", "micron", "intel", "meta",
    "tsmc", "taiwan semiconductor", "sk hynix", "samsung",
)

SPX_DIRECT_TERMS = (
    "s&p 500", "s&p500", "spx", "spy", "s&p futures", "s&p 500 futures",
    "wall street", "u.s. stocks", "us stocks", "stock market", "index futures",
)

STRONG_EVENT_TERMS = (
    "unexpected", "surprise", "emergency", "decision", "announces", "announced",
    "approved", "rejected", "cuts", "cut", "hikes", "hike", "raises", "raised",
    "lowers", "lowered", "guidance", "beats", "beat", "misses", "missed",
    "intervention", "ceasefire", "strike", "sanction", "default", "halt", "ban",
    "export control", "tariff", "record", "warning",
)

REALIZED_MOVE_TERMS = (
    "soars", "soared", "surges", "surged", "rally", "rallies", "jumps", "jumped",
    "plunge", "plunges", "plunged", "selloff", "sell-off", "sharply", "slumps",
    "falls", "drops", "gains", "rises", "record close", "record high",
)

BULLISH_EQUITY_TERMS = (
    "rally", "rallies", "rise", "rises", "rose", "gain", "gains", "gained", "surge",
    "surges", "soars", "soared", "jump", "jumps", "record close", "record high",
    "lower yields", "rate cut", "rate cuts", "cooling inflation", "disinflation",
    "ceasefire", "de-escalation", "eases", "easing",
)

BEARISH_EQUITY_TERMS = (
    "fall", "falls", "fell", "drop", "drops", "dropped", "plunge", "plunges", "plunged",
    "selloff", "sell-off", "surge in yields", "higher yields", "rate hike", "rate hikes",
    "tariff escalation", "war", "strike", "sanction escalation", "recession warning",
)

# Events where a direct mechanical relationship is more reliable than headline verbs.
DIRECTION_RULES = (
    ("higher yields", "BEARISH"),
    ("surge in yields", "BEARISH"),
    ("rate hike", "BEARISH"),
    ("rate hikes", "BEARISH"),
    ("rate cut", "BULLISH"),
    ("rate cuts", "BULLISH"),
    ("cooling inflation", "BULLISH"),
    ("tariff escalation", "BEARISH"),
    ("de-escalation", "BULLISH"),
    ("ceasefire", "BULLISH"),
)


def _text(item):
    return ((item.get("title", "") or "") + " " + (item.get("summary", "") or "")).lower()


def _contains_any(text, terms):
    return any(term in text for term in terms)


def market_impact(item):
    """Estimate intrinsic event significance, 0-100, without source/freshness bias."""
    cats = categories(item)
    impact = max((IMPACT_BASE.get(cat, 25) for cat in cats), default=25)
    text = _text(item)

    strong_hits = sum(1 for term in STRONG_EVENT_TERMS if term in text)
    realized_hits = sum(1 for term in REALIZED_MOVE_TERMS if term in text)

    # A concrete decision/surprise/action is more material than a generic mention.
    impact += min(16, strong_hits * 4)
    # A large realized market move is evidence that the event was material,
    # but this is still kept separate from direction.
    impact += min(10, realized_hits * 3)

    if _contains_any(text, ("earnings", "quarterly results", "guidance", "outlook")):
        impact += 6
    if _contains_any(text, ("fed", "fomc", "powell")) and _contains_any(text, ("decision", "rate", "hike", "cut", "policy")):
        impact += 7

    # Rare geopolitical/energy combinations get a fast-path floor. Without this,
    # a generic category base can score a market-moving Hormuz development as only
    # medium impact even when the event directly changes global energy-flow risk.
    if is_priority_catalyst(item):
        impact = max(impact, priority_urgency_score(item))

    return max(0, min(100, int(impact)))


def index_relevance(item, index):
    """Estimate transmission relevance to the named index, independent of direction."""
    text = _text(item)
    direct_terms = NQ_DIRECT_TERMS if index == "NQ" else SPX_DIRECT_TERMS
    base_map = NQ_BASE if index == "NQ" else SPX_BASE

    if _contains_any(text, direct_terms):
        direct = 94 if index == "NQ" else 92
    else:
        direct = 0

    cats = categories(item)
    thematic = max((base_map.get(cat, 20) for cat in cats), default=20)
    value = max(thematic, direct)

    # Broad macro/rates events transmit to both indices even when the headline
    # does not mention an equity index.
    if any(cat in cats for cat in ("FED / RATES", "INFLATION / MACRO", "LABOR", "TREASURIES / YIELDS")):
        value = max(value, 84 if index == "NQ" else 88)

    # NQ has a stronger semiconductor/mega-cap transmission channel.
    if index == "NQ" and any(cat in cats for cat in ("AI / SEMICONDUCTORS", "MEGA-CAP")):
        value = max(value, 90)

    # S&P is broader, so an isolated mega-cap/AI headline is less index-direct
    # than it is for NQ unless the headline explicitly references the S&P.
    if index == "SPX" and "AI / SEMICONDUCTORS" in cats and not _contains_any(text, SPX_DIRECT_TERMS):
        value = min(value, 72)

    # Hormuz is an unusually direct cross-asset transmission channel through oil,
    # inflation expectations, rates and risk appetite.
    if is_priority_catalyst(item):
        value = max(value, 84 if index == "NQ" else 82)

    return max(0, min(100, int(value)))


def equity_direction(item):
    """Directional pressure on US equities, not a futures-contract forecast."""
    text = _text(item)

    priority_d = priority_direction(item)
    if priority_d:
        return priority_d

    for term, label in DIRECTION_RULES:
        if term in text:
            return label

    bull = sum(2 for term in BULLISH_EQUITY_TERMS if term in text)
    bear = sum(2 for term in BEARISH_EQUITY_TERMS if term in text)

    # Oil/commodity direction is not automatically equity direction; without
    # a clear transmission phrase, keep it neutral rather than guessing.
    if any(k in text for k in ("oil prices", "crude prices", "wti", "brent")) and bull == 0 and bear == 0:
        return "NEUTRAL"

    if bull >= bear + 2 and bull >= 2:
        return "BULLISH"
    if bear >= bull + 2 and bear >= 2:
        return "BEARISH"
    if bull and bear:
        return "MIXED"
    return direction(item)


def direction_confidence(item):
    """Confidence in the directional interpretation; source/freshness are inputs here."""
    text = _text(item)
    d = equity_direction(item)
    if d == "NEUTRAL":
        base = 58
    elif d == "MIXED":
        base = 52
    else:
        base = 62

    # Explicit transmission language is more reliable than generic sentiment words.
    explicit = sum(1 for term in DIRECTION_RULES if term[0] in text)
    base += min(18, explicit * 9)

    if _contains_any(text, ("nasdaq", "s&p 500", "stock futures", "wall street", "equities")):
        base += 7

    # Priority events get a modest confidence lift only when the fast-path rule
    # supplies an explicit directional interpretation. This does not mean the
    # event is guaranteed to move the market in that direction.
    if priority_direction(item):
        base += 12

    quality = source_quality(item)
    base += 8 if quality >= 100 else 4 if quality >= 82 else 0 if quality >= 55 else -8

    age = freshness_hours(item)
    base -= min(12, int(age / 8))

    return max(20, min(97, int(base)))


def score_event(item):
    """Return the explainable public metrics plus an internal ranking score."""
    impact = market_impact(item)
    nq = index_relevance(item, "NQ")
    spx = index_relevance(item, "SPX")
    d = equity_direction(item)
    confidence = direction_confidence(item)

    # Ranking is intentionally separate from Impact. Freshness/source quality
    # help decide what to show first, but do not change the event's impact value.
    freshness = max(0, min(100, round(100 - freshness_hours(item) * 3)))
    quality = source_quality(item)
    quality_norm = round(quality * 0.82)
    ranking = round(0.42 * impact + 0.28 * nq + 0.15 * confidence + 0.10 * freshness + 0.05 * quality_norm)

    return {
        "market_impact": impact,
        "nq_relevance": nq,
        "spx_relevance": spx,
        "equity_direction": d,
        "direction_confidence": confidence,
        "ranking_score": max(0, min(100, ranking)),
    }
