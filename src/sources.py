import hashlib, time
from datetime import datetime, timezone
from urllib.parse import quote_plus
import feedparser

UA = "NQ-Market-AI-Free/5.0 (+https://github.com/)"

# Public RSS/search feeds. Reuters is deliberately represented through Google News RSS
# discovery rather than bypassing Reuters controls or a paid API.
FEEDS = [
    ("Reuters Markets", "https://news.google.com/rss/search?q=" + quote_plus("site:reuters.com markets Nasdaq stocks futures") + "&hl=en-US&gl=US&ceid=US:en", 100),
    ("Reuters Trump", "https://news.google.com/rss/search?q=" + quote_plus("site:reuters.com Trump tariffs markets") + "&hl=en-US&gl=US&ceid=US:en", 100),
    ("Reuters Global", "https://news.google.com/rss/search?q=" + quote_plus("site:reuters.com global markets Fed oil yields") + "&hl=en-US&gl=US&ceid=US:en", 100),
    ("Fed", "https://www.federalreserve.gov/feeds/press_all.xml", 100),
    ("SEC", "https://www.sec.gov/news/pressreleases.rss", 100),
    ("BLS", "https://www.bls.gov/feed/bls_latest.rss", 95),
    ("White House", "https://www.whitehouse.gov/feed/", 95),
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
                published = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
                if published:
                    ts = datetime.fromtimestamp(time.mktime(published), tz=timezone.utc).isoformat()
                else:
                    ts = datetime.now(timezone.utc).isoformat()
                summary = (getattr(e, "summary", "") or "").strip()
                out.append({
                    "id": _id(title, link),
                    "source": source,
                    "publisher": _publisher(e, source),
                    "priority": priority,
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "published": ts,
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
