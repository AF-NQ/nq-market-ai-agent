"""Free SEC 13F/hedge-fund filing discovery via public Google News RSS."""
from urllib.parse import quote_plus
import feedparser

QUERIES = [
    'SEC 13F filing hedge fund holdings',
    'site:sec.gov 13F investment manager holdings',
    'hedge fund quarterly 13F new position stake',
    'institutional investor 13F increased stake decreased stake',
]

# Keep the 13F section, but remove educational/SEO pages that do not report
# an actual filing, holding change, or institutional positioning event.
GENERIC_PATTERNS = (
    "what is 13f", "what is 13-f", "13f filing explained", "13f explained",
    "using 13f", "how to use 13f", "13f databases", "13f database",
    "13f requirements", "filing requirements", "registration requirements",
    "13f registration", "13f comparison", "comparison of 13f", "learn from 13f",
    "explained", "guide to 13f", "introduction to 13f", "understanding 13f",
    "how to file", "filing guide", "form 13f guide",
)

EVENT_SIGNALS = (
    "13f filing", "13f filings", "13f", "13-f", "filed", "filing", "holdings",
    "holding", "stake", "position", "portfolio", "institutional investor",
    "institutional investors", "investment manager", "shares", "bought", "buying",
    "sold", "selling", "added", "trimmed", "increased", "decreased", "new position",
    "quarterly holdings", "holdings report", "sec filing",
)

LOW_VALUE_SOURCES = (
    "investopedia", "nerdwallet", "the balance", "corporate finance institute",
)


def _is_real_13f_event(title):
    low = title.lower()
    if not low or any(pattern in low for pattern in GENERIC_PATTERNS):
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
                if not _is_real_13f_event(title):
                    continue
                low = title.lower()
                # Generic/educational publishers can still slip through via RSS;
                # reject them unless the headline explicitly describes a filing,
                # stake, or position event.
                if any(src in low for src in LOW_VALUE_SOURCES) and not any(
                    x in low for x in ("filing", "stake", "position", "holdings", "shares")
                ):
                    continue
                key = low
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
    return out[:6]
