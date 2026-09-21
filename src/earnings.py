"""Free earnings/filing discovery.

Primary free signal: Nasdaq public earnings-calendar endpoint where available.
Secondary: SEC filing discovery through Google News RSS for 10-Q/10-K/8-K/13F.
This is informational and must not be treated as a guaranteed complete calendar.
"""
import requests
from datetime import datetime

WATCHLIST = {
    "NVDA":"NVIDIA", "AAPL":"Apple", "MSFT":"Microsoft", "AMZN":"Amazon",
    "GOOGL":"Alphabet", "META":"Meta", "AVGO":"Broadcom", "TSLA":"Tesla",
    "AMD":"AMD", "NFLX":"Netflix", "MU":"Micron", "ORCL":"Oracle",
    "COST":"Costco", "ADBE":"Adobe", "INTC":"Intel", "QCOM":"Qualcomm"
}

def upcoming_earnings(date_str=None):
    date_str=date_str or datetime.utcnow().strftime('%Y-%m-%d')
    url=f"https://api.nasdaq.com/api/calendar/earnings?date={date_str}"
    headers={"User-Agent":"Mozilla/5.0","Accept":"application/json, text/plain, */*","Referer":"https://www.nasdaq.com/"}
    try:
        r=requests.get(url,headers=headers,timeout=15); r.raise_for_status(); data=r.json()
        rows=((data.get('data') or {}).get('rows') or [])
        wanted=[]
        for row in rows:
            sym=row.get('symbol','')
            if sym in WATCHLIST:
                wanted.append({"symbol":sym,"company":WATCHLIST[sym],"date":date_str,"time":row.get('time',''),"eps":row.get('epsForecast',''),"revenue":row.get('revenueForecast','')})
        return wanted
    except Exception:
        return []
