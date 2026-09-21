"""Free SEC 13F/hedge-fund filing discovery via public Google News RSS."""
from urllib.parse import quote_plus
import feedparser

QUERIES=[
    'SEC 13F filing hedge fund',
    'site:sec.gov 13F investment manager',
    'hedge fund quarterly 13F holdings'
]

def collect_13f():
    out=[]
    for q in QUERIES:
        url='https://news.google.com/rss/search?q='+quote_plus(q)+'&hl=en-US&gl=US&ceid=US:en'
        try:
            f=feedparser.parse(url)
            for e in f.entries[:10]:
                out.append({"source":"SEC/13F discovery","title":getattr(e,'title',''),'link':getattr(e,'link','')})
        except Exception: pass
    return out
