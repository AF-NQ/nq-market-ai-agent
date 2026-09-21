import argparse
from .config import CONFIG
from .sources import collect
from .verify import relevance
from .storage import Store
from .calendar import preopen_state
from .analyzer import analyze, report, urgent_messages
from .earnings import upcoming_earnings
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
    earnings = upcoming_earnings()

    if is_pre and last_pre != today:
        msg = report(ranked, op, mins, "source-check")
        if earnings:
            msg += "\n\n📅 MEGA-CAP EARNINGS TODAY\n" + "\n".join(
                f'{e["symbol"]} {e["company"]} — {e["time"] or "time n/a"}' for e in earnings
            )
        send(CONFIG.telegram_token, CONFIG.telegram_chat_id, msg)
        store.set("last_preopen_date", today)

    # Urgent alerts are intraday-only. During premarket the main report already
    # contains the ranked catalysts, so sending them again creates duplicate noise.
    if not is_pre:
        for msg in urgent_messages(ranked):
            send(CONFIG.telegram_token, CONFIG.telegram_chat_id, msg)

    return {
        "collected": len(raw),
        "new": len(new),
        "preopen": is_pre,
        "open": op.isoformat(),
        "minutes": mins,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true")
    args = p.parse_args()
    result = run_once()
    print(result)
