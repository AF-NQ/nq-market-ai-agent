"""Free SEC 13F/hedge-fund filing discovery via public Google News RSS."""
from urllib.parse import quote_plus
import re
import feedparser

QUERIES = [
    'SEC 13F filing hedge fund holdings stake',
    'site:sec.gov 13F investment manager holdings',
    'hedge fund quarterly 13F new position reduced increased stake',
    'institutional investor 13F filing position change',
]

# Keep 13F discovery, but reject generic educational/SEO/editorial roundup pages.
GENERIC_PATTERNS = (
    "what is 13f", "what is 13-f", "13f filing explained", "13f explained",
    "using 13f", "how to use 13f", "13f databases", "13f database",
    "13f requirements", "filing requirements", "registration requirements",
    "13f registration", "13f comparison", "comparison of 13f", "learn from 13f",
    "explained", "guide to 13f", "introduction to 13f", "understanding 13f",
    "how to file", "filing guide", "form 13f guide",
    "situational awareness", "institutional investors reveal", "institutional investors' 13f filings",
    "13f filings reveal", "quarterly 13f filings", "quarterly 13f filing",
    "tug-of-war in tech stocks", "bright spot",
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

GENERIC_EVENT_PHRASES = (
    "institutional investors", "institutional investor", "hedge funds",
    "hedge fund investors", "us institutional investors", "quarterly filings",
    "13f filings", "13f filing",
)

TICKER_RE = re.compile(r"\$[A-Z]{1,5}\b|\b[A-Z]{2,5}\b")


def _is_real_13f_event(title):
    low = title.lower()
    if not low or any(pattern in low for pattern in GENERIC_PATTERNS):
        return False
    if not any(signal in low for signal in EVENT_SIGNALS):
        return False

    # Prefer concrete filing/position/stake changes. A generic "13F filings"
    # headline without a named company/fund is not useful as a discovery item.
    specific_change = any(x in low for x in (
        "position opened", "new position", "new stake", "stake in ",
        "bought ", "sold ", "added ", "trimmed", "reduced ", "increased ",
        "decreased ", "filed by ", "filing by ", "disclosed by ",
    )) or "$" in title
    if specific_change:
        return True

    if any(phrase in low for phrase in GENERIC_EVENT_PHRASES):
        return bool(TICKER_RE.search(title))
    return True


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
