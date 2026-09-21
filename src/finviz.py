"""Free Finviz enrichment for earnings and material insider transactions.

Finviz is used as a secondary public-source cross-check, not as the sole source of
truth. Earnings dates are merged with the existing Nasdaq calendar and insider
activity is filtered to NQ/SPX-relevant companies.
"""
from datetime import date, datetime, timedelta
from html import unescape
import re

import requests
from bs4 import BeautifulSoup

from .earnings import WATCHLIST, index_memberships

UA = "NQ-Market-AI-Free/5.2 (+https://github.com/AF-NQ/nq-market-ai-agent)"
FINVIZ_EARNINGS = "https://finviz.com/calendar/earnings?dateFrom={date}"
FINVIZ_INSIDER = "https://finviz.com/insidertrading"

INSIDER_MIN_VALUE = 1_000_000
INSIDER_BUY_MIN_VALUE = 500_000
MAX_INSIDERS = 8


def _get(url):
    r = requests.get(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.text


def _money(value):
    raw = str(value or "").replace("$", "").replace(",", "").strip()
    try:
        return float(raw)
    except Exception:
        return 0.0


def _date_from_text(value):
    raw = re.sub(r"\s+", " ", unescape(str(value or "")).strip())
    for fmt in ("%b %d '%y", "%b %d %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except Exception:
            pass
    return None


def _weekdays(start):
    monday = start - timedelta(days=start.weekday())
    return [monday + timedelta(days=i) for i in range(5)]


def collect_earnings(days=5, start_date=None):
    """Return watchlist earnings from Finviz for the current trading week."""
    start = start_date or date.today()
    try:
        html = _get(FINVIZ_EARNINGS.format(date=start.isoformat()))
    except Exception:
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []
    week_dates = _weekdays(start)
    cutoff = start + timedelta(days=max(0, days - 1))

    tables = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header = " ".join(c.get_text(" ", strip=True).lower() for c in rows[0].find_all(["th", "td"]))
        if "ticker" in header and "company" in header and "time" in header:
            tables.append(table)

    for table_index, table in enumerate(tables[:5]):
        if table_index >= len(week_dates):
            break
        day = week_dates[table_index]
        if day < start or day > cutoff:
            continue
        for row in table.find_all("tr")[1:]:
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            if len(cells) < 3:
                continue
            symbol = re.sub(r"[^A-Z0-9.\-]", "", cells[0].upper())
            if symbol not in WATCHLIST:
                continue
            timing = cells[2].upper()
            if timing == "BMO":
                timing = "BEFORE OPEN"
            elif timing == "AMC":
                timing = "AFTER CLOSE"
            else:
                timing = timing or "TIME N/A"
            results.append({
                "symbol": symbol,
                "company": WATCHLIST[symbol],
                "date": day.isoformat(),
                "time": timing,
                "indexes": index_memberships(symbol),
                "finviz": True,
                "source": "Finviz",
            })
    return results


def collect_insider_activity(days=7, start_date=None):
    """Return recent material insider buys/sales for NQ/SPX watchlist names."""
    start = start_date or date.today()
    cutoff = start - timedelta(days=max(1, days))
    try:
        html = _get(FINVIZ_INSIDER)
    except Exception:
        return []

    soup = BeautifulSoup(html, "html.parser")
    table = None
    for candidate in soup.find_all("table"):
        rows = candidate.find_all("tr")
        if not rows:
            continue
        header = " ".join(c.get_text(" ", strip=True).lower() for c in rows[0].find_all(["th", "td"]))
        if "ticker" in header and "owner" in header and "transaction" in header and "value" in header:
            table = candidate
            break
    if table is None:
        return []

    out = []
    for row in table.find_all("tr")[1:]:
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
        if len(cells) < 8:
            continue
        symbol = re.sub(r"[^A-Z0-9.\-]", "", cells[0].upper())
        if symbol not in WATCHLIST:
            continue
        d = _date_from_text(cells[3])
        if not d or d < cutoff or d > start + timedelta(days=1):
            continue
        transaction = cells[4].upper()
        if transaction not in {"BUY", "SALE", "PROPOSED SALE"}:
            continue
        value = _money(cells[7])
        minimum = INSIDER_BUY_MIN_VALUE if transaction == "BUY" else INSIDER_MIN_VALUE
        if value < minimum:
            continue
        out.append({
            "symbol": symbol,
            "company": WATCHLIST[symbol],
            "owner": cells[1],
            "relationship": cells[2],
            "date": d.isoformat(),
            "transaction": transaction,
            "cost": cells[5],
            "shares": cells[6],
            "value": value,
            "value_display": f"${value:,.0f}",
            "indexes": index_memberships(symbol),
            "source": "Finviz",
            "link": FINVIZ_INSIDER,
        })

    out.sort(key=lambda x: (x["transaction"] == "BUY", x["value"]), reverse=True)
    seen = set()
    unique = []
    for item in out:
        key = (item["symbol"], item["owner"], item["date"], item["transaction"], item["value"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
        if len(unique) >= MAX_INSIDERS:
            break
    return unique


def collect_finviz(days=5, start_date=None):
    """Collect Finviz earnings cross-checks and material insider activity."""
    return {
        "earnings": collect_earnings(days=days, start_date=start_date),
        "insiders": collect_insider_activity(days=7, start_date=start_date),
    }
