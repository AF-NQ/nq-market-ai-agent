import requests

def send(token,chat_id,text):
    if not token or not chat_id: return False
    url=f"https://api.telegram.org/bot{token}/sendMessage"
    # Telegram limit is ~4096 chars; split conservatively.
    chunks=[text[i:i+3800] for i in range(0,len(text),3800)] or [""]
    for c in chunks:
        r=requests.post(url,json={"chat_id":chat_id,"text":c,"disable_web_page_preview":True},timeout=20)
        r.raise_for_status()
    return True
