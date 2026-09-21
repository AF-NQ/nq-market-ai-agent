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
MAX_CATALYST_AGE_HOURS = 48.0

CATEGORY_RULES = {
    "FED / RATES": ["fed", "federal reserve", "fomc", "interest rate", "rate cut", "rate hike", "powell", "hawkish", "dovish"],
    "INFLATION / MACRO": ["cpi", "ppi", "inflation", "core inflation", "pce", "retail sales", "gdp", "ism", "consumer confidence"],
    "LABOR": ["payroll", "nonfarm", "jobs report", "jobless claims", "unemployment", "employment", "jolts", "wage growth"],
    "TREASURIES / YIELDS": ["treasury", "yield", "yields", "10-year", "2-year", "bond auction", "real yield"],
    "USD": ["dollar", "dxy", "usd", "greenback"],
    "GLOBAL FX": ["yen", "jpy", "yuan", "renminbi", "cny", "euro", "eur", "sterling", "gbp", "australian dollar", "aud", "rupee", "inr", "fx", "foreign exchange", "currency intervention"],
    "JAPAN / BOJ": ["japan", "nikkei", "topix", "boj", "bank of japan", "jgb", "japanese stocks", "japanese shares"],
    "CHINA / PBOC": ["china", "shanghai composite", "shenzhen", "hang seng", "csi 300", "pboc", "people's bank of china", "chinese stocks", "chinese shares", "yuan", "renminbi"],
    "ASIA / SEMICONDUCTORS": ["kospi", "south korea", "samsung", "sk hynix", "taiex", "taiwan", "tsmc", "taiwan semiconductor", "asia chip", "asian semiconductor"],
    "EUROPE / ECB": ["europe", "eurozone", "dax", "stoxx", "cac", "ftse", "ecb", "european central bank", "european stocks", "european shares"],
    "OIL / ENERGY": ["oil", "crude", "brent", "wti", "opec", "energy", "strait of hormuz", "shipping route"],
    "GEOPOLITICS": ["iran", "israel", "ukraine", "russia", "china", "taiwan", "war", "ceasefire", "missile", "strike", "sanction", "geopolit", "taiwan strait", "middle east", "red sea", "hormuz"],
    "AI / SEMICONDUCTORS": ["nvidia", "nvda", "amd", "broadcom", "avgo", "semiconductor", "chip", "ai", "artificial intelligence", "tsmc", "micron", "intel", "arm"],
    "MEGA-CAP": ["apple", "aapl", "microsoft", "msft", "amazon", "amzn", "alphabet", "google", "meta", "tesla", "tsla"],
    "EARNINGS": ["earnings", "revenue", "profit", "eps", "guidance", "forecast", "quarterly results", "outlook"],
    "TARIFFS / TRADE": ["tariff", "trade war", "import duty", "export control", "trade restriction", "export restriction", "rare earth", "rare-earth"],
    "REGULATION": ["sec", "antitrust", "regulator", "regulation", "lawsuit", "investigation", "approval", "ban"],
    "INDEX / FUTURES": ["nasdaq", "nasdaq futures", "s&p 500", "spx", "qqq", "nq futures", "stock futures", "index futures", "nikkei", "topix", "kospi", "taiex", "dax", "stoxx", "cac", "ftse", "hang seng", "shanghai composite", "csi 300"],
}

BULLISH_WORDS = ["rise", "rises", "rally", "rallies", "jump", "jumps", "surge", "surges", "gain", "gains", "lower yields", "rate cut", "eases", "cooling inflation"]
BEARISH_WORDS = ["fall", "falls", "drop", "drops", "plunge", "plunges", "selloff", "sell-off", "surge in yields", "higher yields", "rate hike", "tariff escalation", "war"]

ANCHORS = {
    "nvda": "NVDA", "nvidia": "NVDA", "amd": "AMD", "broadcom": "AVGO", "apple": "AAPL",
    "microsoft": "MSFT", "amazon": "AMZN", "alphabet": "GOOGL", "google": "GOOGL", "meta": "META",
    "tesla": "TSLA", "fed": "FED", "fomc": "FED", "powell": "FED", "cpi": "CPI", "ppi": "PPI",
    "payroll": "JOBS", "nonfarm": "JOBS", "unemployment": "JOBS", "treasury": "YIELDS", "yield": "YIELDS",
    "oil": "OIL", "crude": "OIL", "iran": "IRAN", "tariff": "TARIFFS", "nasdaq": "NQ", "s&p": "SPX",
    "trump": "TRUMP", "xi": "XI", "china": "CHINA", "rare earth": "RARE_EARTHS",
    "nikkei": "NIKKEI", "topix": "NIKKEI", "boj": "BOJ", "yen": "JPY", "jpy": "JPY", "jgb": "JGB",
    "hang seng": "HANG_SENG", "shanghai": "CHINA_EQ", "shenzhen": "CHINA_EQ", "csi 300": "CHINA_EQ", "pboc": "PBOC", "yuan": "CNY", "renminbi": "CNY",
    "kospi": "KOSPI", "samsung": "KOREA_SEMIs", "sk hynix": "KOREA_SEMIs", "taiex": "TAIEX", "tsmc": "TSMC",
    "dax": "DAX", "stoxx": "EUROPE_EQ", "cac": "EUROPE_EQ", "ftse": "EUROPE_EQ", "ecb": "ECB", "euro": "EUR",
    "rbi": "RBI", "nifty": "NIFTY", "sensex": "SENSEX", "rba": "RBA", "asx": "ASX",
}

DIRECT_NQ_TERMS = [
    "nasdaq", "nasdaq 100", "nq futures", "qqq", "stock futures", "index futures",
    "technology stocks", "tech stocks", "ai stocks", "semiconductor stocks",
    "nvidia", "nvda", "amd", "broadcom", "avgo", "micron", "intel", "meta",
    "tsmc", "taiwan semiconductor", "sk hynix", "samsung", "asian semiconductor",
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
    t = _clean(title)
    if " - " not in t:
        return ""
    suffix = _clean(t.rsplit(" - ", 1)[1])
    low = suffix.lower()
    mapping = {
        "finance.yahoo.com": "Yahoo Finance", "yahoo finance": "Yahoo Finance",
        "the economic times": "Economic Times", "economictimes.com": "Economic Times",
        "reuters": "Reuters", "cnbc": "CNBC", "marketwatch": "MarketWatch",
        "investing.com": "Investing.com",
    }
    for key, value in mapping.items():
        if key in low:
            return value
    if any(x in low for x in LOW_QUALITY_PATTERNS): return ""
    if low.startswith("latest news") or low.startswith("news from"): return ""
    return suffix if len(suffix) <= 60 else ""


def publisher(item):
    p = _clean(item.get("publisher") or "")
    if p and p.lower() not in GENERIC_PUBLISHERS and not any(x in p.lower() for x in LOW_QUALITY_PATTERNS): return p
    recovered = _title_publisher(item.get("title", ""))
    if recovered: return recovered
    src = _clean(item.get("source") or "")
    if src and src.lower() not in GENERIC_PUBLISHERS and not any(x in src.lower() for x in LOW_QUALITY_PATTERNS): return src
    try:
        host = urlparse(item.get("link", "")).netloc.lower().replace("www.", "")
        if "reuters" in host: return "Reuters"
        if "cnbc" in host: return "CNBC"
        if "yahoo" in host: return "Yahoo Finance"
        if "economictimes" in host: return "Economic Times"
        if "motleyfool" in host: return "Motley Fool"
    except Exception: pass
    return recovered or "Unknown"


def source_quality(item):
    p = publisher(item).lower()
    if any(x in p for x in LOW_QUALITY_PATTERNS) or p in GENERIC_PUBLISHERS: return 25
    if any(x in p for x in TIER1): return 100
    if any(x in p for x in TIER2): return 82
    return 55


def _category_hits(text, keys):
    return sum(1 for k in keys if k in text)


def categories(item):
    title = (item.get("title", "") or "").lower()
    summary = (item.get("summary", "") or "").lower()
    out = []
    for cat, keys in CATEGORY_RULES.items():
        if any(k in title for k in keys): out.append(cat)
    for cat in ("FED / RATES", "INFLATION / MACRO", "LABOR", "TREASURIES / YIELDS", "USD", "GLOBAL FX", "JAPAN / BOJ", "CHINA / PBOC", "ASIA / SEMICONDUCTORS", "EUROPE / ECB", "OIL / ENERGY", "TARIFFS / TRADE", "GEOPOLITICS", "INDEX / FUTURES"):
        if cat not in out and _category_hits(summary, CATEGORY_RULES[cat]) >= 2: out.append(cat)
    return out[:3] or ["OTHER"]


def direction(item):
    title = (item.get("title", "") or "").lower()
    summary = (item.get("summary", "") or "").lower()
    bull = 2 * sum(title.count(k) for k in BULLISH_WORDS) + sum(summary.count(k) for k in BULLISH_WORDS)
    bear = 2 * sum(title.count(k) for k in BEARISH_WORDS) + sum(summary.count(k) for k in BEARISH_WORDS)
    if bull >= bear + 2 and bull >= 2: return "BULLISH"
    if bear >= bull + 2 and bear >= 2: return "BEARISH"
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
        except Exception: return 24.0


def nq_directness(item):
    text = (item.get("title", "") + " " + item.get("summary", "")).lower()
    if any(k in text for k in DIRECT_NQ_TERMS): return 25
    if any(k in text for k in US_EQUITY_CONTEXT): return 14
    # International events get a smaller baseline; the stronger transmission
    # signals above (semiconductors, NQ, US equities) still dominate.
    if any(k in text for k in ["nikkei", "topix", "boj", "japan", "hang seng", "shanghai", "pboc", "china", "kospi", "taiex", "tsmc", "dax", "stoxx", "ecb", "euro", "yen", "yuan", "taiwan strait", "geopolit"]): return 10
    return 5


def _similar(a, b):
    ta, tb = _tokens(a.get("title", "")), _tokens(b.get("title", ""))
    if not ta or not tb: return False
    shared_anchors = _anchors(a.get("title", "") + " " + a.get("summary", "")) & _anchors(b.get("title", "") + " " + b.get("summary", ""))
    j = len(ta & tb) / max(1, len(ta | tb))
    shared = len(ta & tb)
    if j >= 0.50 or (shared_anchors and shared >= 3 and j >= 0.25): return True
    for group in (
        {"TRUMP", "XI"}, {"FED", "YIELDS"}, {"OIL", "IRAN"},
        {"BOJ", "JPY"}, {"PBOC", "CNY"}, {"TSMC", "TAIEX"},
        {"KOSPI", "KOREA_SEMIs"}, {"ECB", "EUR"},
    ):
        if group.issubset(shared_anchors): return True
    return False


def cluster_items(items):
    clusters = []
    for item in items:
        placed = False
        for cluster in clusters:
            if _similar(item, cluster[0]):
                cluster.append(item); placed = True; break
        if not placed: clusters.append([item])
    return clusters


def _freshness_component(item):
    return max(0, round(15 - freshness_hours(item) * 0.25))


def score_item(item, cluster_size=1):
    cats = categories(item)
    cat_weights = {
        "FED / RATES": 18, "INFLATION / MACRO": 16, "LABOR": 16, "TREASURIES / YIELDS": 15,
        "AI / SEMICONDUCTORS": 18, "MEGA-CAP": 17, "EARNINGS": 16, "GEOPOLITICS": 10,
        "OIL / ENERGY": 8, "TARIFFS / TRADE": 10, "REGULATION": 9, "INDEX / FUTURES": 18,
        "GLOBAL FX": 11, "JAPAN / BOJ": 10, "CHINA / PBOC": 11, "ASIA / SEMICONDUCTORS": 14,
        "EUROPE / ECB": 10,
    }
    relevance = min(30, sum(cat_weights.get(cat, 3) for cat in cats))
    direct = nq_directness(item)
    text = (item.get("title", "") + " " + item.get("summary", "")).lower()
    impact_terms = ["unexpected", "emergency", "surprise", "beats", "misses", "guidance", "ceasefire", "strike", "tariff", "sanction", "default", "halt", "decision", "intervention", "capital controls", "export ban", "export restriction"]
    impact = min(20, sum(4 for x in impact_terms if x in text))
    quality_score = source_quality(item)
    quality = round(quality_score * 0.18)
    fresh = _freshness_component(item)
    confirmation = min(10, max(0, (cluster_size - 1) * 4))
    low_quality_penalty = 8 if quality_score < 70 else 0
    score = min(100, max(0, relevance + direct + impact + quality + fresh + confirmation - low_quality_penalty))
    level = "HIGH" if score >= 75 else "MEDIUM" if score >= 55 else "LOW"
    return score, level
