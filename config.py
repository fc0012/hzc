"""配置管理模块"""
import os
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    """应用配置"""

    # Hetzner配置
    hetzner_token: str = Field(default_factory=lambda: os.getenv("HETZNER_TOKEN", ""))

    # 流量监控配置
    traffic_limit_tb: float = Field(
        default_factory=lambda: float(os.getenv("TRAFFIC_LIMIT_TB", "20"))
    )
    rotate_threshold: float = Field(
        default_factory=lambda: float(os.getenv("ROTATE_THRESHOLD", "0.98"))
    )
    check_interval_minutes: int = Field(
        default_factory=lambda: int(os.getenv("CHECK_INTERVAL_MINUTES", "5"))
    )
    safe_mode: bool = Field(
        default_factory=lambda: os.getenv("SAFE_MODE", "true").lower()
        in ("1", "true", "yes", "on")
    )

    # Telegram配置
    telegram_bot_token: str = Field(
        default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", "")
    )
    telegram_chat_id: str = Field(
        default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", "")
    )

    # SSH配置
    ssh_user: str = Field(default_factory=lambda: os.getenv("SSH_USER", "root"))
    ssh_port: int = Field(
        default_factory=lambda: int(os.getenv("SSH_PORT", "22"))
    )

    # Web认证配置
    web_username: str = Field(
        default_factory=lambda: os.getenv("WEB_USERNAME", "admin")
    )
    web_password: str = Field(
        default_factory=lambda: os.getenv("WEB_PASSWORD", "")
    )
    secret_key: str = Field(
        default_factory=lambda: os.getenv("SECRET_KEY", "")
    )

    # 进程监控
    monitor_processes: List[str] = Field(
        default_factory=lambda: [
            p.strip()
            for p in os.getenv("MONITOR_PROCESSES", "").split(",")
            if p.strip()
        ]
    )

    # 其他配置
    tz: str = Field(default_factory=lambda: os.getenv("TZ", "Asia/Shanghai"))
    snapshot_price_per_gb: float = Field(
        default_factory=lambda: float(os.getenv("SNAPSHOT_PRICE_PER_GB", "0.011"))
    )

    # 持久化会话配置
    enable_remember_me: bool = Field(
        default_factory=lambda: os.getenv("ENABLE_REMEMBER_ME", "true").lower()
        in ("1", "true", "yes", "on")
    )
    remember_me_days: int = Field(
        default_factory=lambda: int(os.getenv("REMEMBER_ME_DAYS", "7"))
    )
    max_remember_me_days: int = Field(
        default_factory=lambda: int(os.getenv("MAX_REMEMBER_ME_DAYS", "30"))
    )

    def validate_required(self):
        """验证必填配置"""
        errors = []
        if not self.hetzner_token:
            errors.append("HETZNER_TOKEN is required")
        if not self.web_password:
            errors.append("WEB_PASSWORD is required")
        if not self.secret_key:
            errors.append("SECRET_KEY is required")

        # 验证持久化会话配置
        if self.max_remember_me_days < self.remember_me_days:
            errors.append(
                f"MAX_REMEMBER_ME_DAYS ({self.max_remember_me_days}) must be >= REMEMBER_ME_DAYS ({self.remember_me_days})"
            )

        if errors:
            raise ValueError("\n".join(errors))


# 全局配置实例
settings = Settings()
