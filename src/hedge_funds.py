"""Free SEC 13F/hedge-fund filing discovery via public Google News RSS."""
from urllib.parse import quote_plus
import feedparser

QUERIES = [
    'SEC 13F filing hedge fund holdings',
    'site:sec.gov 13F investment manager holdings',
    'hedge fund quarterly 13F holdings stake',
    'institutional investor 13F filing position',
]

# Keep the 13F section, but remove educational/SEO pages that do not report
# an actual filing, holding change, institutional position, or disclosed stake.
GENERIC_PATTERNS = (
    "what is 13f", "what is 13-f", "13f filing explained", "13f explained",
    "using 13f", "how to use 13f", "13f databases", "13f database",
    "13f requirements", "filing requirements", "registration requirements",
    "13f registration", "13f comparison", "comparison of 13f", "learn from 13f",
    "explained", "guide to 13f", "introduction to 13f", "understanding 13f",
)

EVENT_SIGNALS = (
    "13f", "13-f", "institutional investor", "institutional investors",
    "hedge fund", "hedge funds", "fund stake", "funds stake", "stake filing",
    "disclosed stake", "sec filing", "quarterly holdings", "holdings report",
    "holdings", "portfolio", "position", "positions",
)


def _is_real_13f_event(title):
    low = title.lower()
    if any(pattern in low for pattern in GENERIC_PATTERNS):
        return False
    return any(signal in low for signal in EVENT_SIGNALS)


def collect_13f():
    out = []
    seen = set()
    for q in QUERIES:
        url = "https://news.google.com/rss/search?q=" + quote_plus(q) + "&hl=en-US&gl=US&ceid=US:en"
        try:
            f = feedparser.parse(url)
            for e in f.entries[:12]:
                title = getattr(e, "title", "").strip()
                link = getattr(e, "link", "")
                if not title or not _is_real_13f_event(title):
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
