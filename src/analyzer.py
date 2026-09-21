from datetime import datetime

from .news_engine import catalyst_summary
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


def report(items, open_time, minutes_to_open, confirmed_label):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "🔴 NQ PRE-MARKET — FINAL CHECK",
        f"Generated: {now}",
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
            sources = ", ".join(x.get("sources", [])[:4])
            confirmation = "CONFIRMED" if x.get("source_count", 1) >= 2 else "SINGLE SOURCE"
            lines.append(f"{i}. [{x['level']}] {x['title']}")
            lines.append(f"   Category: {cats}")
            lines.append(f"   NQ relevance: {x['score']}/100 | {direction}")
            lines.append(f"   Sources: {sources} | {confirmation}")
            lines.append(f"   {x['link']}")

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "🧭 NEWS ENGINE",
        "Clusters similar headlines into catalysts; separates publisher quality, freshness and cross-source confirmation.",
        "Direction is descriptive of the headline/event language, not a price forecast.",
        "",
        "⚠️ Verification: public-source collection and rule-based checks only. Absence of confirmation is not proof of falsity.",
    ]
    return "\n".join(lines)


def urgent_messages(items):
    out = []
    for x in items:
        if x.get("level") == "HIGH" and x.get("score", 0) >= 80:
            sources = ", ".join(x.get("sources", [])[:4])
            out.append(
                "🚨 NQ HIGH-IMPACT CATALYST\n"
                f"{x['title']}\n"
                f"Category: {', '.join(x.get('categories', ['OTHER'])[:3])}\n"
                f"NQ relevance: HIGH ({x['score']}/100)\n"
                f"Sources: {sources}\n"
                f"{x['link']}"
            )
    return out
