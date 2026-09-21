import requests


def send(token, chat_id, text):
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Split only at line boundaries so HTML tags are never cut in half.
    # Telegram's effective message limit is ~4096 characters.
    lines = text.split("\n")
    chunks = []
    current = ""
    for line in lines:
        candidate = line if not current else current + "\n" + line
        if len(candidate) <= 3800:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = line
    if current or not chunks:
        chunks.append(current)

    for c in chunks:
        r = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": c,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=20,
        )
        r.raise_for_status()
    return True
