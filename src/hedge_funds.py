"""Free SEC 13F/hedge-fund filing discovery via public Google News RSS."""
from urllib.parse import quote_plus
import feedparser

QUERIES = [
    'SEC 13F filing hedge fund',
    'site:sec.gov 13F investment manager',
    'hedge fund quarterly 13F holdings',
]

# Keep the 13F section, but remove educational/SEO pages that do not report
# an actual filing, holding change, or institutional positioning event.
GENERIC = (
    "what is 13f", "13f filing explained", "using 13f", "13f databases",
    "13f requirements", "filing requirements", "13f explained", "comparison",
    "how to use 13f", "learn from 13f",
)


def collect_13f():
    out = []
    seen = set()
    for q in QUERIES:
        url = "https://news.google.com/rss/search?q=" + quote_plus(q) + "&hl=en-US&gl=US&ceid=US:en"
        try:
            f = feedparser.parse(url)
            for e in f.entries[:10]:
                title = getattr(e, "title", "").strip()
                link = getattr(e, "link", "")
                low = title.lower()
                if not title or low.startswith(GENERIC) or any(x in low for x in GENERIC):
                    continue
                key = title.lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append({
                    "source": "SEC/13F discovery",
                    "title": title,
                    "link": link,
                })
        except Exception:
            pass
    return out[:8]
