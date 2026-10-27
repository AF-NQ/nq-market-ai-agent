import argparse
import os
from .config import CONFIG
from .sources import collect
from .verify import relevance
from .storage import Store
from .calendar import preopen_state
from .analyzer import analyze, report, urgent_messages
from .earnings import upcoming_earnings
from .finviz import collect_finviz
from .hedge_funds import collect_13f
from .cme_radar import format_radar, enrich_test_directions
from .telegram import send


def run_once():
    store = Store(CONFIG.database_path)
    # Keep the premarket-send marker shared between the dedicated workflow and
    # the main monitor fallback, while preserving each workflow's event store.
    premarket_store = Store(os.getenv("PREMARKET_STATE_PATH", CONFIG.database_path))
    raw = collect()
    for x in raw:
        s, l, r = relevance(x)
        x.update(score=s, level=l, reasons=r)
    new = store.new_events(raw)
    ranked = analyze(new)
    op, mins, is_pre = preopen_state(minutes=CONFIG.preopen_minutes, window=CONFIG.preopen_window_minutes)
    last_pre = premarket_store.get("last_preopen_date")
    today = op.date().isoformat()
    force_premarket = os.getenv("FORCE_PREMARKET", "").strip() == "1"
    premarket_enabled = os.getenv("PREMARKET_REPORT_ENABLED", "1").strip() != "0"
    premarket_only = os.getenv("PREMARKET_ONLY", "0").strip() == "1"
    earnings = upcoming_earnings(days=5)
    finviz = collect_finviz(days=5)
    funds = collect_13f()

    if premarket_enabled and (is_pre or force_premarket) and (force_premarket or last_pre != today):
        # The same headline-level equity-pressure enrichment used by the
        # Premarket Test is now part of the production report. Preserve the
        # original engine direction so CME Radar can independently map each
        # catalyst to the named contract.
        original_directions = [x.get("direction", "NEUTRAL") for x in ranked]
        enrich_test_directions(ranked)

        msg = report(ranked, op, mins, "source-check", earnings=earnings, finviz=finviz)
        if funds:
            msg += "\n\n🏦 13F / HEDGE-FUND DISCOVERY\n" + "\n".join(
                f'• {x["title"]} — {x["source"]}' for x in funds[:5]
            )

        # Restore the engine directions before CME mapping. Contract-specific
        # rules must not inherit broad NQ/SPX headline pressure blindly.
        for x, original in zip(ranked, original_directions):
            x["direction"] = original

        # Keep CME Radar in production in the same position as the tested
        # premarket message: after news, verification, earnings, Finviz and 13F.
        radar_text = format_radar(ranked, limit=18)
        msg += "\n\n" + radar_text

        sent = send(CONFIG.telegram_token, CONFIG.telegram_chat_id, msg)
        print({"premarket_send_ok": bool(sent), "forced": force_premarket, "target_open": op.isoformat()})
        if not force_premarket:
            premarket_store.set("last_preopen_date", today)

    # Urgent alerts are intraday-only; the main premarket report already contains
    # the catalysts, earnings, Finviz insider activity, 13F discovery and CME Radar.
    if (not is_pre or not premarket_enabled) and not premarket_only:
        for msg in urgent_messages(ranked):
            send(CONFIG.telegram_token, CONFIG.telegram_chat_id, msg)

    return {
        "collected": len(raw), "new": len(new), "preopen": is_pre,
        "open": op.isoformat(), "minutes": mins, "earnings": len(earnings),
        "finviz_earnings": len(finviz.get("earnings", [])),
        "finviz_insiders": len(finviz.get("insiders", [])),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true")
    args = p.parse_args()
    result = run_once()
    print(result)
