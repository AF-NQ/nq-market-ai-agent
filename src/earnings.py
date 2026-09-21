"""Free earnings-calendar discovery for NQ/S&P premarket monitoring.

Uses Nasdaq's public earnings calendar endpoint. Future dates are indicative until
confirmed by the company; this module is informational and not guaranteed complete.
"""
from datetime import datetime, timedelta
import requests

# Companies with meaningful index/sector relevance for NQ and/or S&P 500.
WATCHLIST = {
    # NQ / mega-cap / semiconductors
    "NVDA":"NVIDIA", "AAPL":"Apple", "MSFT":"Microsoft", "AMZN":"Amazon",
    "GOOGL":"Alphabet", "GOOG":"Alphabet", "META":"Meta", "AVGO":"Broadcom",
    "TSLA":"Tesla", "AMD":"AMD", "NFLX":"Netflix", "MU":"Micron",
    "ORCL":"Oracle", "ADBE":"Adobe", "INTC":"Intel", "QCOM":"Qualcomm",
    "AMAT":"Applied Materials", "LRCX":"Lam Research", "KLAC":"KLA",
    "MRVL":"Marvell Technology", "ARM":"Arm Holdings", "PANW":"Palo Alto Networks",
    "CRWD":"CrowdStrike", "PLTR":"Palantir", "CSCO":"Cisco", "INTU":"Intuit",
    # Broad S&P 500 / major sectors
    "JPM":"JPMorgan Chase", "BAC":"Bank of America", "WFC":"Wells Fargo",
    "GS":"Goldman Sachs", "MS":"Morgan Stanley", "V":"Visa", "MA":"Mastercard",
    "COST":"Costco", "WMT":"Walmart", "HD":"Home Depot", "LOW":"Lowe's",
    "KO":"Coca-Cola", "PEP":"PepsiCo", "MCD":"McDonald's", "NKE":"Nike",
    "DIS":"Walt Disney", "CRM":"Salesforce", "NOW":"ServiceNow", "IBM":"IBM",
    "GE":"GE Aerospace", "CAT":"Caterpillar", "BA":"Boeing", "XOM":"Exxon Mobil",
    "CVX":"Chevron", "UNH":"UnitedHealth", "JNJ":"Johnson & Johnson",
    "PFE":"Pfizer", "LLY":"Eli Lilly", "MRK":"Merck", "TMO":"Thermo Fisher",
    "C":"Citigroup", "BLK":"BlackRock", "GS":"Goldman Sachs",
}


def _get_day(date_str):
    url = f"https://api.nasdaq.com/api/calendar/earnings?date={date_str}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nasdaq.com/",
    }
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    rows = ((r.json().get("data") or {}).get("rows") or [])
    wanted = []
    for row in rows:
        sym = (row.get("symbol") or "").strip().upper()
        if sym in WATCHLIST:
            wanted.append({
                "symbol": sym,
                "company": WATCHLIST[sym],
                "date": date_str,
                "time": row.get("time", ""),
                "eps": row.get("epsForecast", ""),
                "revenue": row.get("revenueForecast", ""),
            })
    return wanted


def upcoming_earnings(days=5, start_date=None):
    """Return today's and next trading-day earnings for the relevant watchlist."""
    start = start_date or datetime.now().date()
    results = []
    checked = 0
    offset = 0
    # Look ahead far enough to cover 5 trading days while skipping weekends.
    while checked < days and offset < 10:
        d = start + timedelta(days=offset)
        offset += 1
        if d.weekday() >= 5:
            continue
        checked += 1
        try:
            results.extend(_get_day(d.isoformat()))
        except Exception:
            # One failed calendar date must not break the entire market report.
            continue
    return results
