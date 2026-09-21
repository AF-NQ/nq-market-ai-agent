from dataclasses import dataclass
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

@dataclass(frozen=True)
class Config:
    timezone: str = os.getenv("MARKET_TIMEZONE", "America/New_York")
    poll_minutes: int = int(os.getenv("POLL_MINUTES", "5"))
    preopen_minutes: int = int(os.getenv("PREOPEN_MINUTES", "30"))
    preopen_window_minutes: int = int(os.getenv("PREOPEN_WINDOW_MINUTES", "5"))
    database_path: str = os.getenv("STATE_PATH", str(DATA_DIR / "state.json"))
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")

CONFIG = Config()
