from datetime import datetime
from html import escape

from .news_engine import catalyst_summary, freshness_hours
from .verify import relevance


def _link(text, url):
    if not url:
        return escape(text)
    return f'<a href="{escape(url, quote=True)}">{escape(text)}</a>'


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


def report(items, open_time, minutes_to_open, confirmed_label):
    now = datetime.now(open_time.tzinfo) if open_time.tzinfo else datetime.now()
    now_text = now.strftime("%Y-%m-%d %H:%M %Z")
    lines = [
        "🔴 NQ PRE-MARKET — FINAL CHECK",
        f"Generated: {now_text}",
        f"US regular open: {open_time.strftime('%Y-%m-%d %H:%M %Z')}",
        f"Approx. minutes to open: {minutes_to_open:.1f}",
        "",
        "🔥 KEY CATALYSTS",
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
            # Keep the Telegram message visually clean: the headline itself is
            # clickable instead of printing a long Google News URL underneath it.
            headline = _link(x["title"], x.get("link", ""))
            lines.append(f"{i}. [{x['level']}] {headline}")
            lines.append(f"   Category: {escape(cats)}")
            lines.append(f"   NQ relevance: {x['score']}/100 | {direction}")
            lines.append(f"   Sources: {escape(sources)} | {source_status} | {age}")

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "🧭 NEWS ENGINE",
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
            headline = _link(x["title"], x.get("link", ""))
            out.append(
                "🚨 NQ HIGH-IMPACT CATALYST\n"
                f"{headline}\n"
                f"Category: {escape(', '.join(x.get('categories', ['OTHER'])[:3]))}\n"
                f"NQ relevance: HIGH ({x['score']}/100)\n"
                f"Sources: {escape(sources)}"
            )
    return out
