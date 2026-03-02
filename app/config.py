from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    hetzner_token: str = os.getenv("HETZNER_TOKEN", "")
    traffic_limit_tb: float = float(os.getenv("TRAFFIC_LIMIT_TB", "20"))
    rotate_threshold: float = float(os.getenv("ROTATE_THRESHOLD", "0.9"))
    check_interval_minutes: int = int(os.getenv("CHECK_INTERVAL_MINUTES", "5"))
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    timezone: str = os.getenv("TZ", "UTC")


settings = Settings()
