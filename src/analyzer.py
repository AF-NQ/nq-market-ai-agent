from datetime import datetime
from html import escape
from urllib.parse import urlparse

from .news_engine import catalyst_summary, freshness_hours, nq_directness
from .verify import relevance


def analyze(items):
    # Keep the legacy relevance fields for compatibility with storage/tests.
    for x in items:
        s, l, r = relevance(x)
        x["legacy_score"] = s
        x["legacy_level"] = l
        x["reasons"] = r
    return catalyst_summary(items, limit=20)


def _direction_label(direction):
    return {
        "BULLISH": "BULLISH PRESSURE",
        "BEARISH": "BEARISH PRESSURE",
        "MIXED": "MIXED",
        "NEUTRAL": "NEUTRAL",
    }.get(direction, "NEUTRAL")


def _spx_directness(item):
    """Estimate broad S&P 500 relevance on the same 0-25 scale used for NQ directness."""
    text = (item.get("title", "") + " " + item.get("summary", "")).lower()
    direct_terms = [
        "s&p 500", "s&p500", "spx", "spy", "dow", "wall street", "u.s. stocks",
        "us stocks", "equities", "stock market", "stocks", "index futures",
    ]
    macro_terms = [
        "fed", "federal reserve", "fomc", "interest rate", "inflation", "cpi",
        "ppi", "payroll", "jobs report", "unemployment", "treasury", "yield",
        "dollar", "oil", "crude", "tariff", "trade war", "geopolitics",
    ]
    if any(k in text for k in direct_terms):
        return 25
    if any(k in text for k in macro_terms):
        return 21
    # Large-cap/semiconductor news can move SPX, but is generally less broad than NQ.
    if any(k in text for k in ["nvidia", "nvda", "apple", "microsoft", "amazon", "meta", "amd", "broadcom"]):
        return 18
    return 10


def _index_relevance(item, index):
    base = int(item.get("score", 0))
    if index == "NQ":
        return max(0, min(100, base))
    nq_component = int(item.get("nq_directness", nq_directness(item)))
    spx_component = _spx_directness(item)
    return max(0, min(100, base - nq_component + spx_component))


def _short_source_link(item):
    """Return a compact clickable Telegram link instead of exposing a raw URL."""
    link = (item.get("link") or "").strip()
    if not link:
        return ""
    try:
        host = urlparse(link).netloc.lower().replace("www.", "")
    except Exception:
        host = ""
    label = "Read article"
    if "reuters" in host:
        label = "Read Reuters"
    elif "cnbc" in host:
        label = "Read CNBC"
    elif "yahoo" in host:
        label = "Read Yahoo Finance"
    elif "economictimes" in host:
        label = "Read Economic Times"
    return f'<a href="{escape(link, quote=True)}">{label}</a>'


def report(items, open_time, minutes_to_open, confirmed_label):
    now = datetime.now(open_time.tzinfo) if open_time.tzinfo else datetime.now()
    now_text = now.strftime("%Y-%m-%d %H:%M %Z")
    lines = [
        "<b>🔴 NQ PRE-MARKET — FINAL CHECK</b>",
        f"Generated: {escape(now_text)}",
        f"US regular open: {escape(open_time.strftime('%Y-%m-%d %H:%M %Z'))}",
        f"Approx. minutes to open: {minutes_to_open:.1f}",
        "",
        "<b>🔥 KEY CATALYSTS</b>",
    ]

    if not items:
        lines.append("No new material catalysts detected in the latest collection.")
    else:
        for i, x in enumerate(items[:8], 1):
            cats = ", ".join(x.get("categories", ["OTHER"])[:3])
            direction = _direction_label(x.get("direction", "NEUTRAL"))
            sources = ", ".join(x.get("sources", [])[:4]) or "Unknown"
            source_status = "MULTI-PUBLISHER" if x.get("source_count", 1) >= 2 else "SINGLE PUBLISHER"
            freshness = freshness_hours(x)
            age = f"{freshness:.1f}h old" if freshness < 48 else f"{freshness:.0f}h old"
            nq = _index_relevance(x, "NQ")
            spx = _index_relevance(x, "SPX")
            link = _short_source_link(x)

            # Deliberate blank lines make each catalyst visually separable in Telegram.
            lines += [
                "",
                f"<b>{i}. [{escape(str(x['level']))}] {escape(str(x['title']))}</b>",
                f"<b>Category:</b> {escape(cats)}",
                f"<b>Impact:</b> NQ <b>{nq}/100</b> | S&amp;P 500 <b>{spx}/100</b> | {escape(direction)}",
                f"Sources: {escape(sources)} | {source_status} | {escape(age)}",
            ]
            if link:
                lines.append(link)

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "<b>🧭 NEWS ENGINE</b>",
        "Clusters duplicate/syndicated headlines into catalysts and weights direct NQ relevance, publisher quality, freshness and cross-source coverage.",
        "Multi-publisher coverage does not necessarily mean independent confirmation; syndicated wire stories can appear under multiple publishers.",
        "Direction is descriptive of the event/headline language, not a price forecast.",
        "",
        "⚠️ Verification: public-source collection and rule-based checks only. Absence of confirmation is not proof of falsity.",
    ]
    return "\n".join(lines)


def urgent_messages(items):
    """Intraday alerts only: very fresh, high-impact and directly relevant catalysts."""
    out = []
    for x in items:
        if (
            x.get("level") == "HIGH"
            and x.get("score", 0) >= 88
            and x.get("nq_directness", 0) >= 14
            and freshness_hours(x) <= 3
        ):
            sources = ", ".join(x.get("sources", [])[:4]) or "Unknown"
            link = _short_source_link(x)
            msg = (
                "<b>🚨 NQ HIGH-IMPACT CATALYST</b>\n"
                f"<b>{escape(str(x['title']))}</b>\n"
                f"<b>Category:</b> {escape(', '.join(x.get('categories', ['OTHER'])[:3]))}\n"
                f"<b>Impact:</b> NQ <b>{_index_relevance(x, 'NQ')}/100</b> | S&amp;P 500 <b>{_index_relevance(x, 'SPX')}/100</b> | {escape(_direction_label(x.get('direction', 'NEUTRAL')))}\n"
                f"Sources: {escape(sources)}"
            )
            if link:
                msg += f"\n{link}"
            out.append(msg)
    return out
