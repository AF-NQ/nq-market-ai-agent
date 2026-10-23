import requests


def send(token, chat_id, text):
    if not token or not chat_id:
        raise RuntimeError("Telegram delivery is not configured: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is empty")
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
        payload = r.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram API rejected sendMessage: {payload}")
        result = payload.get("result", {})
        chat = result.get("chat", {})
        print({
            "telegram_delivery_accepted": True,
            "telegram_message_id": result.get("message_id"),
            "telegram_chat_id": chat.get("id"),
            "telegram_chat_type": chat.get("type"),
            "telegram_chat_title": chat.get("title") or chat.get("username") or chat.get("first_name"),
            "chunk_chars": len(c),
        })
    return True
