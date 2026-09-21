from datetime import datetime
from html import escape

from .news_engine import catalyst_summary, freshness_hours, nq_directness, publisher
from .scoring import score_event
from .verify import relevance


def _apply_event_scores(items):
    """Attach explainable public metrics without changing source collection."""
    for x in items:
        metrics = score_event(x)
        x.update(metrics)
        # Keep the old score for backwards compatibility/debugging only.
        x["legacy_score"] = x.get("score", 0)
        x["legacy_level"] = x.get("level", "LOW")
        # Public catalyst level is based on event impact + NQ relevance,
        # not publisher quality or freshness.
        materiality = round(0.55 * x["market_impact"] + 0.45 * x["nq_relevance"])
        x["public_materiality"] = materiality
        x["public_level"] = "HIGH" if materiality >= 75 else "MEDIUM" if materiality >= 55 else "LOW"
    return items


def analyze(items):
    for x in items:
        s, l, r = relevance(x)
        x["verification_score"] = s
        x["verification_level"] = l
        x["reasons"] = r
    catalysts = catalyst_summary(items, limit=20)
    _apply_event_scores(catalysts)
    # Rank for display with the new explainable score. Low-materiality articles
    # remain available to the engine but do not occupy key premarket slots.
    catalysts.sort(key=lambda x: x.get("ranking_score", 0), reverse=True)
    return [x for x in catalysts if x.get("public_materiality", 0) >= 55]


def _direction_label(direction):
    return {
        "BULLISH": "BULLISH PRESSURE",
        "BEARISH": "BEARISH PRESSURE",
        "MIXED": "MIXED PRESSURE",
        "NEUTRAL": "NEUTRAL",
    }.get(direction, "NEUTRAL")


def _index_relevance(item, index):
    # New explicit index relevance replaces the old reuse of the internal
    # news-engine ranking score. Keep a safe fallback for older callers/tests.
    key = "nq_relevance" if index == "NQ" else "spx_relevance"
    if key in item:
        return int(item[key])
    return int(item.get("score", 0))


def _source_link_label(item):
    """Use the normalized publisher instead of the final redirect URL host."""
    p = publisher(item).lower()
    if "reuters" in p: return "Read Reuters"
    if "cnbc" in p: return "Read CNBC"
    if "yahoo" in p: return "Read Yahoo Finance"
    if "economic times" in p or "economictimes" in p: return "Read Economic Times"
    if "motley fool" in p or "motleyfool" in p: return "Read Motley Fool"
    if "marketwatch" in p: return "Read MarketWatch"
    if "investing.com" in p or "investing" in p: return "Read Investing.com"
    if "seeking alpha" in p: return "Read Seeking Alpha"
    return f"Read {publisher(item)}" if publisher(item) not in {"Unknown", ""} else "Read article"


def _short_source_link(item):
    link = (item.get("link") or "").strip()
    if not link:
        return ""
    from html import escape as html_escape
    return f'<a href="{html_escape(link, quote=True)}">{html_escape(_source_link_label(item))}</a>'


def _normalize_earnings_time(raw):
    value = str(raw or "").strip().lower()
    if not value:
        return "TIME N/A"
    if any(x in value for x in ("after-hours", "after hours", "afterhours", "post-market", "post market")):
        return "AFTER CLOSE"
    if any(x in value for x in ("pre-market", "pre market", "premarket", "before-open", "before open")):
        return "BEFORE OPEN"
    if value in {"time-not-supplied", "not supplied", "tbd", "n/a", "na"}:
        return "TIME N/A"
    if value in {"during-market", "during market", "intraday", "market hours"}:
        return "INTRADAY"
    return str(raw).upper().replace("_", " ").replace("-", " ")


def _earnings_block(earnings, finviz_earnings=None):
    if not earnings:
        return []
    finviz_keys = {(e.get("date", ""), e.get("symbol", "")) for e in (finviz_earnings or [])}
    grouped = {}
    for e in earnings:
        grouped.setdefault(e.get("date", ""), []).append(e)
    lines = ["", "━━━━━━━━━━━━━━━━━━━━", "<b>📅 EARNINGS — NQ / S&amp;P 500</b>"]
    for date, rows in sorted(grouped.items()):
        try: label = datetime.strptime(date, "%Y-%m-%d").strftime("%a %b %d")
        except Exception: label = date
        lines.append(f"<b>{escape(label)}</b>")
        for e in rows:
            timing = _normalize_earnings_time(e.get("time"))
            indexes = e.get("indexes") or []
            index_label = " + ".join(indexes) if indexes else "Watchlist"
            cross = " | Finviz cross-check" if (date, e.get("symbol", "")) in finviz_keys else ""
            lines.append(
                f'• <b>{escape(e["symbol"])}</b> {escape(e["company"])} '
                f'— <b>{escape(index_label)}</b> — <b>{escape(timing)}</b>{escape(cross)}'
            )
    lines.append("<i>Times/calendar dates come from the free public calendar and should be treated as indicative until company-confirmed.</i>")
    if finviz_earnings:
        lines.append("<i>Finviz is used as a secondary calendar cross-check; it does not replace company confirmation.</i>")
    return lines


def _finviz_insider_block(insiders):
    if not insiders:
        return []
    lines = ["", "━━━━━━━━━━━━━━━━━━━━", "<b>🏦 FINVIZ — MATERIAL INSIDER ACTIVITY</b>"]
    for x in insiders[:8]:
        indexes = " + ".join(x.get("indexes") or []) or "Watchlist"
        transaction = x.get("transaction", "")
        marker = "🟢 BUY" if transaction == "BUY" else "🔴 SALE" if transaction == "SALE" else "🟠 PROPOSED SALE"
        lines.append(
            f'• <b>{escape(x.get("symbol", ""))}</b> {escape(x.get("company", ""))} '
            f'— <b>{escape(indexes)}</b> — {marker} — <b>{escape(x.get("value_display", ""))}</b>'
        )
        lines.append(
            f'  {escape(x.get("owner", ""))} ({escape(x.get("relationship", ""))}) — {escape(x.get("date", ""))}'
        )
    link = insiders[0].get("link")
    if link:
        lines.append(f'<a href="{escape(link, quote=True)}">Read Finviz insider transactions</a>')
    lines.append("<i>Insider buys/sales are factual filings; a sale can be routine or pre-planned and is not automatically bearish.</i>")
    return lines


def _catalyst_metrics_line(x):
    nq = _index_relevance(x, "NQ")
    spx = _index_relevance(x, "SPX")
    impact = int(x.get("market_impact", x.get("score", 0)))
    pressure = _direction_label(x.get("equity_direction", x.get("direction", "NEUTRAL")))
    confidence = int(x.get("direction_confidence", 0))
    return (
        f"<b>Market Impact:</b> <b>{impact}/100</b> | "
        f"<b>NQ Relevance:</b> <b>{nq}/100</b> | "
        f"<b>S&amp;P 500 Relevance:</b> <b>{spx}/100</b> | "
        f"<b>Equity Pressure:</b> {escape(pressure)} | "
        f"<b>Pressure Confidence:</b> <b>{confidence}/100</b>"
    )


def report(items, open_time, minutes_to_open, confirmed_label, earnings=None, finviz=None):
    now = datetime.now(open_time.tzinfo) if open_time.tzinfo else datetime.now()
    now_text = now.strftime("%Y-%m-%d %H:%M %Z")
    finviz = finviz or {}
    lines = [
        "<b>🔴 NQ PRE-MARKET — FINAL CHECK</b>",
        f"Generated: {escape(now_text)}",
        f"US regular open: {escape(open_time.strftime('%Y-%m-%d %H:%M %Z'))}",
        f"Approx. minutes to open: {minutes_to_open:.1f}",
        "", "<b>🔥 KEY CATALYSTS</b>",
    ]
    if not items:
        lines.append("No new material catalysts detected in the latest collection.")
    else:
        for i, x in enumerate(items[:8], 1):
            cats = ", ".join(x.get("categories", ["OTHER"])[:3])
            sources = ", ".join(x.get("sources", [])[:4]) or "Unknown"
            source_status = "MULTI-PUBLISHER" if x.get("source_count", 1) >= 2 else "SINGLE PUBLISHER"
            freshness = freshness_hours(x)
            age = f"{freshness:.1f}h old" if freshness < 48 else f"{freshness:.0f}h old"
            link = _short_source_link(x)
            level = x.get("public_level", x.get("level", "MEDIUM"))
            lines += [
                "",
                f"<b>{i}. [{escape(str(level))}] {escape(str(x['title']))}</b>",
                f"<b>Category:</b> {escape(cats)}",
                _catalyst_metrics_line(x),
                f"Sources: {escape(sources)} | {source_status} | {escape(age)}",
            ]
            if link: lines.append(link)

    lines += [
        "", "━━━━━━━━━━━━━━━━━━━━", "<b>🧭 NEWS ENGINE</b>",
        "<i>Market Impact = intrinsic significance of the event. NQ/SPX Relevance = estimated transmission to the index. Equity Pressure = descriptive bullish, bearish, mixed or neutral pressure on equities; it is not a price forecast.</i>",
        "<i>Pressure Confidence measures how strongly the rule-based engine supports the stated equity pressure. Source quality, freshness and cross-source coverage affect confidence/ranking; they do not inflate the event's Market Impact.</i>",
        "<i>Multi-publisher coverage does not necessarily mean independent confirmation; syndicated wire stories can appear under multiple publishers.</i>",
        "", "<i>⚠️ Verification: public-source collection and rule-based checks only. Absence of confirmation is not proof of falsity.</i>",
    ]
    lines.extend(_earnings_block(earnings or [], finviz.get("earnings", [])))
    lines.extend(_finviz_insider_block(finviz.get("insiders", [])))
    return "\n".join(lines)


def urgent_messages(items):
    out = []
    for x in items:
        impact = int(x.get("market_impact", x.get("score", 0)))
        nq = _index_relevance(x, "NQ")
        if x.get("public_level", x.get("level")) == "HIGH" and impact >= 88 and nq >= 80 and freshness_hours(x) <= 3:
            sources = ", ".join(x.get("sources", [])[:4]) or "Unknown"
            link = _short_source_link(x)
            msg = (
                "<b>🚨 NQ HIGH-IMPACT CATALYST</b>\n"
                f"<b>{escape(str(x['title']))}</b>\n"
                f"<b>Category:</b> {escape(', '.join(x.get('categories', ['OTHER'])[:3]))}\n"
                f"{_catalyst_metrics_line(x)}\n"
                f"Sources: {escape(sources)}"
            )
            if link: msg += f"\n{link}"
            out.append(msg)
    return out
