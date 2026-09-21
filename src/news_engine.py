import re
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse


TIER1 = {
    "reuters", "bloomberg", "cnbc", "wall street journal", "financial times",
    "associated press", "ap", "federal reserve", "u.s. federal reserve",
    "u.s. bureau of labor statistics", "bureau of labor statistics", "sec",
}
TIER2 = {
    "yahoo finance", "marketwatch", "investing.com", "barron's", "the economist",
    "economic times", "nasdaq", "cme group", "white house", "u.s. treasury",
    "seeking alpha", "benzinga", "the hill", "politico", "kitco",
}
LOW_QUALITY_PATTERNS = {
    "latest news from", "breaking news from", "news from", "google finance news",
}
GENERIC_PUBLISHERS = {
    "google finance news", "latest news from", "news from", "unknown", "",
}

CATEGORY_RULES = {
    "FED / RATES": ["fed", "federal reserve", "fomc", "interest rate", "rate cut", "rate hike", "powell", "hawkish", "dovish"],
    "INFLATION / MACRO": ["cpi", "ppi", "inflation", "core inflation", "pce", "retail sales", "gdp", "ism", "consumer confidence"],
    "LABOR": ["payroll", "nonfarm", "jobs report", "jobless claims", "unemployment", "employment", "jolts", "wage growth"],
    "TREASURIES / YIELDS": ["treasury", "yield", "yields", "10-year", "2-year", "bond auction", "real yield"],
    "USD": ["dollar", "dxy", "usd", "greenback"],
    "OIL / ENERGY": ["oil", "crude", "brent", "wti", "opec", "energy"],
    "GEOPOLITICS": ["iran", "israel", "ukraine", "russia", "china", "taiwan", "war", "ceasefire", "missile", "strike", "sanction", "geopolit"],
    "AI / SEMICONDUCTORS": ["nvidia", "nvda", "amd", "broadcom", "avgo", "semiconductor", "chip", "ai", "artificial intelligence", "tsmc", "micron", "intel", "arm"],
    "MEGA-CAP": ["apple", "aapl", "microsoft", "msft", "amazon", "amzn", "alphabet", "google", "meta", "tesla", "tsla"],
    "EARNINGS": ["earnings", "revenue", "profit", "eps", "guidance", "forecast", "quarterly results", "outlook"],
    "TARIFFS / TRADE": ["tariff", "trade war", "import duty", "export control", "trade restriction"],
    "REGULATION": ["sec", "antitrust", "regulator", "regulation", "lawsuit", "investigation", "approval", "ban"],
    "INDEX / FUTURES": ["nasdaq", "nasdaq futures", "s&p 500", "spx", "qqq", "nq futures", "stock futures", "index futures"],
}

BULLISH_WORDS = ["rise", "rises", "rally", "rallies", "jump", "jumps", "surge", "surges", "gain", "gains", "lower yields", "rate cut", "eases", "cooling inflation"]
BEARISH_WORDS = ["fall", "falls", "drop", "drops", "plunge", "plunges", "selloff", "sell-off", "surge in yields", "higher yields", "rate hike", "tariff escalation", "war"]

ANCHORS = {
    "nvda": "NVDA", "nvidia": "NVDA", "amd": "AMD", "broadcom": "AVGO", "apple": "AAPL",
    "microsoft": "MSFT", "amazon": "AMZN", "alphabet": "GOOGL", "google": "GOOGL", "meta": "META",
    "tesla": "TSLA", "fed": "FED", "fomc": "FED", "powell": "FED", "cpi": "CPI", "ppi": "PPI",
    "payroll": "JOBS", "nonfarm": "JOBS", "unemployment": "JOBS", "treasury": "YIELDS", "yield": "YIELDS",
    "oil": "OIL", "crude": "OIL", "iran": "IRAN", "tariff": "TARIFFS", "nasdaq": "NQ", "s&p": "SPX",
}

DIRECT_NQ_TERMS = [
    "nasdaq", "nasdaq 100", "nq futures", "qqq", "stock futures", "index futures",
    "technology stocks", "tech stocks", "ai stocks", "semiconductor stocks",
    "nvidia", "nvda", "amd", "broadcom", "avgo", "micron", "intel", "meta",
]
US_EQUITY_CONTEXT = [
    "wall street", "u.s. stocks", "us stocks", "s&p 500", "dow", "equities", "stocks",
]


def _clean(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def _tokens(text):
    words = re.findall(r"[a-z0-9$%.-]{3,}", text.lower())
    stop = {"the", "and", "for", "with", "from", "ahead", "after", "into", "that", "this", "are", "will", "over", "stock", "stocks", "market", "markets", "today"}
    return set(w for w in words if w not in stop)


def _anchors(text):
    t = text.lower()
    return {v for k, v in ANCHORS.items() if k in t}


def _title_publisher(title):
    """Recover the real publisher from Google News titles when feed metadata is polluted."""
    t = _clean(title)
    if " - " not in t:
        return ""
    suffix = _clean(t.rsplit(" - ", 1)[1])
    low = suffix.lower()
    mapping = {
        "finance.yahoo.com": "Yahoo Finance",
        "yahoo finance": "Yahoo Finance",
        "the economic times": "Economic Times",
        "economictimes.com": "Economic Times",
        "reuters": "Reuters",
        "cnbc": "CNBC",
        "marketwatch": "MarketWatch",
        "investing.com": "Investing.com",
    }
    for key, value in mapping.items():
        if key in low:
            return value
    if any(x in low for x in LOW_QUALITY_PATTERNS):
        return ""
    # Keep recognizable publisher suffixes, but do not treat arbitrary geographic
    # wrappers such as "Latest news from Azerbaijan" as a publisher.
    if low.startswith("latest news") or low.startswith("news from"):
        return ""
    return suffix if len(suffix) <= 60 else ""


def publisher(item):
    p = _clean(item.get("publisher") or "")
    if p and p.lower() not in GENERIC_PUBLISHERS and not any(x in p.lower() for x in LOW_QUALITY_PATTERNS):
        return p
    recovered = _title_publisher(item.get("title", ""))
    if recovered:
        return recovered
    src = _clean(item.get("source") or "")
    if src and src.lower() not in GENERIC_PUBLISHERS and not any(x in src.lower() for x in LOW_QUALITY_PATTERNS):
        return src
    try:
        host = urlparse(item.get("link", "")).netloc.lower().replace("www.", "")
        if "reuters" in host: return "Reuters"
        if "cnbc" in host: return "CNBC"
        if "yahoo" in host: return "Yahoo Finance"
        if "economictimes" in host: return "Economic Times"
    except Exception:
        pass
    return recovered or "Unknown"


def source_quality(item):
    p = publisher(item).lower()
    if any(x in p for x in LOW_QUALITY_PATTERNS) or p in GENERIC_PUBLISHERS:
        return 25
    if any(x in p for x in TIER1): return 100
    if any(x in p for x in TIER2): return 82
    return 55


def categories(item):
    text = (item.get("title", "") + " " + item.get("summary", "")).lower()
    out = []
    for cat, keys in CATEGORY_RULES.items():
        if any(k in text for k in keys):
            out.append(cat)
    return out or ["OTHER"]


def direction(item):
    text = (item.get("title", "") + " " + item.get("summary", "")).lower()
    bull = sum(text.count(k) for k in BULLISH_WORDS)
    bear = sum(text.count(k) for k in BEARISH_WORDS)
    if bull >= bear + 1 and bull >= 1: return "BULLISH"
    if bear >= bull + 1 and bear >= 1: return "BEARISH"
    if bull and bear: return "MIXED"
    return "NEUTRAL"


def freshness_hours(item, now=None):
    now = now or datetime.now(timezone.utc)
    raw = item.get("published")
    if not raw: return 24.0
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (now - dt).total_seconds() / 3600)
    except Exception:
        try:
            dt = parsedate_to_datetime(raw)
            return max(0.0, (now - dt).total_seconds() / 3600)
        except Exception:
            return 24.0


def nq_directness(item):
    text = (item.get("title", "") + " " + item.get("summary", "")).lower()
    if any(k in text for k in DIRECT_NQ_TERMS):
        return 25
    if any(k in text for k in US_EQUITY_CONTEXT):
        return 14
    # Pure geopolitical/commodity stories can matter, but should not outrank
    # direct Nasdaq/US-equity catalysts merely because they contain many categories.
    return 5


def _similar(a, b):
    ta, tb = _tokens(a.get("title", "")), _tokens(b.get("title", ""))
    if not ta or not tb: return False
    shared_anchors = _anchors(a.get("title", "") + " " + a.get("summary", "")) & _anchors(b.get("title", "") + " " + b.get("summary", ""))
    j = len(ta & tb) / max(1, len(ta | tb))
    shared = len(ta & tb)
    return j >= 0.50 or (shared_anchors and shared >= 3 and j >= 0.25)


def cluster_items(items):
    clusters = []
    for item in items:
        placed = False
        for cluster in clusters:
            if _similar(item, cluster[0]):
                cluster.append(item)
                placed = True
                break
        if not placed:
            clusters.append([item])
    return clusters


def score_item(item, cluster_size=1):
    cats = categories(item)
    # Category contribution is capped so a generic macro headline cannot score
    # highly just by mentioning oil + yields + geopolitics + rates together.
    cat_weights = {
        "FED / RATES": 18, "INFLATION / MACRO": 16, "LABOR": 16,
        "TREASURIES / YIELDS": 15, "AI / SEMICONDUCTORS": 18,
        "MEGA-CAP": 17, "EARNINGS": 16, "GEOPOLITICS": 8,
        "OIL / ENERGY": 8, "TARIFFS / TRADE": 9, "REGULATION": 9,
        "INDEX / FUTURES": 18,
    }
    relevance = min(30, sum(cat_weights.get(cat, 3) for cat in cats))
    direct = nq_directness(item)
    text = (item.get("title", "") + " " + item.get("summary", "")).lower()
    impact_terms = ["unexpected", "emergency", "surprise", "beats", "misses", "guidance", "ceasefire", "strike", "tariff", "sanction", "default", "halt", "decision"]
    impact = min(20, sum(4 for x in impact_terms if x in text))
    quality = round(source_quality(item) * 0.15)
    fresh = max(0, round(12 - min(12, freshness_hours(item) * 1.2)))
    confirmation = min(10, max(0, (cluster_size - 1) * 4))
    score = min(100, relevance + direct + impact + quality + fresh + confirmation)
    level = "HIGH" if score >= 75 else "MEDIUM" if score >= 55 else "LOW"
    return score, level


def build_catalysts(items):
    clusters = cluster_items(items)
    catalysts = []
    for cluster in clusters:
        ranked = sorted(cluster, key=lambda x: (source_quality(x), -freshness_hours(x)), reverse=True)
        lead = ranked[0].copy()
        pubs = []
        for x in cluster:
            p = publisher(x)
            if p != "Unknown" and p not in pubs: pubs.append(p)
        cats = categories(lead)
        score, level = score_item(lead, len(cluster))
        lead.update({
            "publisher": publisher(lead),
            "categories": cats,
            "direction": direction(lead),
            "score": score,
            "level": level,
            "sources": pubs[:6],
            "source_count": len(pubs),
            "cluster_size": len(cluster),
            "nq_directness": nq_directness(lead),
        })
        catalysts.append(lead)
    return diversified_rank(catalysts)


def diversified_rank(items):
    remaining = sorted(items, key=lambda x: (x.get("score", 0), source_quality(x)), reverse=True)
    out, used_categories = [], Counter()
    while remaining:
        best = None
        best_value = None
        for x in remaining:
            primary = x.get("categories", ["OTHER"])[0]
            penalty = min(15, used_categories[primary] * 7)
            value = x.get("score", 0) - penalty
            if best is None or value > best_value:
                best, best_value = x, value
        remaining.remove(best)
        used_categories[best.get("categories", ["OTHER"])[0]] += 1
        out.append(best)
    return out


def catalyst_summary(items, limit=8):
    return build_catalysts(items)[:limit]
