import hashlib, time
from datetime import datetime, timezone
from urllib.parse import quote_plus
import feedparser

UA = "NQ-Market-AI-Free/5.1 (+https://github.com/)"

# Public RSS/search feeds. Reuters is represented through Google News RSS
# discovery rather than bypassing Reuters controls or a paid API.
# The Global Markets layer deliberately watches major international markets,
# central banks, FX and geopolitical risk because these can transmit into NQ/SPX.
FEEDS = [
    ("Reuters Markets", "https://news.google.com/rss/search?q=" + quote_plus("site:reuters.com markets Nasdaq stocks futures") + "&hl=en-US&gl=US&ceid=US:en", 100),
    ("Reuters Trump", "https://news.google.com/rss/search?q=" + quote_plus("site:reuters.com Trump tariffs markets") + "&hl=en-US&gl=US&ceid=US:en", 100),
    ("Reuters Global", "https://news.google.com/rss/search?q=" + quote_plus("site:reuters.com global markets Fed oil yields") + "&hl=en-US&gl=US&ceid=US:en", 100),

    # Global Markets — Japan / China / Korea / Taiwan / Europe / India / Australia.
    ("Japan Markets", "https://news.google.com/rss/search?q=" + quote_plus("Japan Nikkei TOPIX BOJ yen JGB markets") + "&hl=en-US&gl=US&ceid=US:en", 90),
    ("China Markets", "https://news.google.com/rss/search?q=" + quote_plus("China Shanghai Shenzhen Hang Seng CSI 300 PBOC yuan markets") + "&hl=en-US&gl=US&ceid=US:en", 90),
    ("Korea Markets", "https://news.google.com/rss/search?q=" + quote_plus("South Korea KOSPI Samsung SK Hynix exports markets") + "&hl=en-US&gl=US&ceid=US:en", 85),
    ("Taiwan Markets", "https://news.google.com/rss/search?q=" + quote_plus("Taiwan TAIEX TSMC semiconductor markets") + "&hl=en-US&gl=US&ceid=US:en", 90),
    ("Europe Markets", "https://news.google.com/rss/search?q=" + quote_plus("Europe DAX STOXX CAC FTSE ECB euro markets") + "&hl=en-US&gl=US&ceid=US:en", 85),
    ("India Markets", "https://news.google.com/rss/search?q=" + quote_plus("India Nifty Sensex RBI rupee markets") + "&hl=en-US&gl=US&ceid=US:en", 75),
    ("Australia Markets", "https://news.google.com/rss/search?q=" + quote_plus("Australia ASX RBA Australian dollar markets") + "&hl=en-US&gl=US&ceid=US:en", 70),
    ("Global FX Central Banks", "https://news.google.com/rss/search?q=" + quote_plus("BOJ PBOC ECB Fed yen yuan euro dollar central banks markets") + "&hl=en-US&gl=US&ceid=US:en", 90),
    ("Global Geopolitics", "https://news.google.com/rss/search?q=" + quote_plus("Taiwan Strait China US Iran Israel Russia Ukraine sanctions war markets") + "&hl=en-US&gl=US&ceid=US:en", 95),

    ("Fed", "https://www.federalreserve.gov/feeds/press_all.xml", 100),
    ("SEC", "https://www.sec.gov/news/pressreleases.rss", 100),
    ("BLS", "https://www.bls.gov/feed/bls_latest.rss", 95),
    ("White House", "https://www.whitehouse.gov/feed/", 95),

    # Direct Investing.com RSS. This supplements Google News discovery so
    # Investing.com stories do not depend on aggregator indexing.
    ("Investing.com News", "https://www.investing.com/rss/investing_news.rss", 82),

    ("Google Finance News", "https://news.google.com/rss/search?q=" + quote_plus("Nasdaq NQ S&P 500 markets earnings Fed") + "&hl=en-US&gl=US&ceid=US:en", 75),
    ("AI Semiconductors", "https://news.google.com/rss/search?q=" + quote_plus("Nvidia AMD semiconductors AI Nasdaq") + "&hl=en-US&gl=US&ceid=US:en", 80),
    ("Oil Rates Dollar", "https://news.google.com/rss/search?q=" + quote_plus("oil Treasury yields dollar Fed markets") + "&hl=en-US&gl=US&ceid=US:en", 80),
]


def _id(title, link):
    return hashlib.sha256((title.strip() + "|" + link.strip()).encode()).hexdigest()


def _publisher(entry, fallback):
    src = getattr(entry, "source", None)
    if src:
        title = getattr(src, "title", "") or ""
        if title.strip():
            return title.strip()
    return fallback


def _entry_time(entry, field):
    value = getattr(entry, field, None)
    if value:
        return value
    parsed = getattr(entry, field + "_parsed", None)
    if parsed:
        return datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc).isoformat()
    return ""


def collect():
    out = []
    for source, url, priority in FEEDS:
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": UA})
            for e in feed.entries[:20]:
                title = (getattr(e, "title", "") or "").strip()
                link = (getattr(e, "link", "") or "").strip()
                if not title or not link:
                    continue

                published = _entry_time(e, "published")
                updated = _entry_time(e, "updated")
                if not published:
                    published = updated or datetime.now(timezone.utc).isoformat()

                summary = (getattr(e, "summary", "") or "").strip()
                out.append({
                    "id": _id(title, link),
                    "source": source,
                    "publisher": _publisher(e, source),
                    "priority": priority,
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "published": published,
                    "updated": updated,
                })
        except Exception:
            # A failed source must never stop the agent.
            continue

    # Exact deduplication. Semantic clustering happens later in news_engine.py.
    seen = set()
    unique = []
    for x in sorted(out, key=lambda z: (z["priority"], z["published"]), reverse=True):
        if x["id"] not in seen:
            seen.add(x["id"])
            unique.append(x)
    return unique
