from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

try:
    import pandas_market_calendars as mcal
except Exception:
    mcal = None

NY = ZoneInfo("America/New_York")

def next_open(now=None):
    now = now or datetime.now(NY)
    now = now.astimezone(NY)
    if mcal:
        cal = mcal.get_calendar("NYSE")
        start = now.date()
        end = start + timedelta(days=10)
        sched = cal.schedule(start_date=start, end_date=end)
        for idx, row in sched.iterrows():
            op = row["market_open"].to_pydatetime().astimezone(NY)
            if op > now:
                return op
    # Fallback for normal weekdays; holiday-aware precision comes from the calendar dependency.
    d = now.date()
    if now.time() >= time(9,30): d += timedelta(days=1)
    while d.weekday() >= 5: d += timedelta(days=1)
    return datetime.combine(d, time(9,30), NY)

def preopen_state(now=None, minutes=30, window=5):
    now = now or datetime.now(NY)
    op = next_open(now)
    delta = op - now
    mins = delta.total_seconds()/60
    return op, mins, (minutes <= mins <= minutes + window)
