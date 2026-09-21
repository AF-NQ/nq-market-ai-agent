import argparse
from .config import CONFIG
from .sources import collect
from .verify import relevance
from .storage import Store
from .calendar import preopen_state
from .analyzer import analyze, report, urgent_messages
from .earnings import upcoming_earnings
from .finviz import collect_finviz
from .hedge_funds import collect_13f
from .telegram import send


def run_once():
    store = Store(CONFIG.database_path)
    raw = collect()
    for x in raw:
        s, l, r = relevance(x)
        x.update(score=s, level=l, reasons=r)
    new = store.new_events(raw)
    ranked = analyze(new)
    op, mins, is_pre = preopen_state(minutes=CONFIG.preopen_minutes, window=CONFIG.preopen_window_minutes)
    last_pre = store.get("last_preopen_date")
    today = op.date().isoformat()
    earnings = upcoming_earnings(days=5)
    finviz = collect_finviz(days=5)
    funds = collect_13f()

    if is_pre and last_pre != today:
        msg = report(ranked, op, mins, "source-check", earnings=earnings, finviz=finviz)
        if funds:
            msg += "\n\n🏦 13F / HEDGE-FUND DISCOVERY\n" + "\n".join(
                f'• {x["title"]} — {x["source"]}' for x in funds[:5]
            )
        send(CONFIG.telegram_token, CONFIG.telegram_chat_id, msg)
        store.set("last_preopen_date", today)

    # Urgent alerts are intraday-only; the main premarket report already contains
    # the catalysts, earnings, Finviz insider activity and 13F discovery.
    if not is_pre:
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
