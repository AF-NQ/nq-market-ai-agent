import re
from collections import defaultdict

HIGH = [
    "fed", "federal reserve", "rate", "rates", "fomc", "inflation", "cpi", "ppi", "jobs", "payroll",
    "treasury", "yield", "bond", "oil", "tariff", "sanction", "war", "ceasefire", "trump", "executive order",
    "nvidia", "amd", "apple", "microsoft", "amazon", "alphabet", "meta", "tesla", "broadcom", "chip", "semiconductor",
    "nasdaq", "s&p 500", "futures", "earnings", "guidance", "sec", "default", "bank", "credit"
]

def relevance(item):
    t=(item["title"]+" "+item.get("summary","")).lower()
    score=0
    reasons=[]
    for k in HIGH:
        if k in t:
            score += 7 if k in ("fed","federal reserve","fomc","tariff","trump","nvidia","amd","nasdaq","futures","earnings") else 3
            reasons.append(k)
    if item["source"].startswith("Reuters"): score += 5
    score=min(score,100)
    level="HIGH" if score>=25 else "MEDIUM" if score>=15 else "LOW"
    return score,level,sorted(set(reasons))[:8]

def confirmation(items):
    # This is intentionally conservative: same story across independent source labels.
    domains=defaultdict(set)
    for x in items:
        key=re.sub(r"[^a-z0-9 ]","",x["title"].lower())[:80]
        domains[key].add(x["source"])
    return "MULTI_SOURCE" if any(len(v)>=2 for v in domains.values()) else "SINGLE_SOURCE"
