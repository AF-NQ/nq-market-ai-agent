from datetime import datetime
from .verify import relevance


def analyze(items):
    for x in items:
        s,l,r=relevance(x); x["score"]=s; x["level"]=l; x["reasons"]=r
    return sorted(items,key=lambda x:(x.get("score",0),x.get("priority",0)),reverse=True)

def report(items, open_time, minutes_to_open, confirmed_label):
    now=datetime.now().strftime("%Y-%m-%d %H:%M")
    lines=["🔴 NQ PRE-MARKET — FINAL CHECK",f"Generated: {now}",f"US regular open: {open_time.strftime('%Y-%m-%d %H:%M %Z')}",f"Approx. minutes to open: {minutes_to_open:.1f}","", "Top new market-moving events:"]
    if not items: lines.append("No new high-impact events detected in the latest collection.")
    for i,x in enumerate(items[:8],1):
        conf="TIER-1 / Reuters discovery" if x["source"].startswith("Reuters") else "public source"
        lines.append(f"{i}. [{x['level']}] {x['title']}")
        lines.append(f"   Source: {x['source']} | {conf} | NQ score {x['score']}")
        lines.append(f"   {x['link']}")
    lines += ["", "Verification: source-level and duplicate checks only; absence of confirmation is not proof of falsity.", "AI note: this Free v4 default uses transparent local/rule-based analysis; it does not claim to be ChatGPT or Claude."]
    return "\n".join(lines)

def urgent_messages(items):
    out=[]
    for x in items:
        if x.get("level")=="HIGH" and x.get("score",0)>=45:
            out.append(f"🚨 NQ HIGH-IMPACT EVENT\n{x['title']}\nSource: {x['source']}\nNQ relevance: HIGH ({x['score']}/100)\n{x['link']}")
    return out
