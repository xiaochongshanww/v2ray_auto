"""Runtime settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional during bootstrap
    load_dotenv = None


@dataclass(frozen=True)
class Settings:
    api_key: str = ""
    allowed_origins: tuple[str, ...] = ()
    default_remote_dir: str = "/opt/v2ray_auto"
    command_timeout: int = 900
    log_level: str = "INFO"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_sender: str | None = None

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_key)

    @property
    def email_enabled(self) -> bool:
        return all([self.smtp_host, self.smtp_username, self.smtp_password, self.smtp_sender])


def _split_origins(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def load_settings() -> Settings:
    if load_dotenv:
        load_dotenv()

    api_key = os.getenv("V2RAY_AUTO_API_KEY", "").strip()

    origins = _split_origins(os.getenv("V2RAY_AUTO_ALLOWED_ORIGINS", "http://localhost:8080"))

    return Settings(
        api_key=api_key,
        allowed_origins=origins,
        default_remote_dir=os.getenv("V2RAY_AUTO_DEFAULT_REMOTE_DIR", "/opt/v2ray_auto"),
        command_timeout=int(os.getenv("V2RAY_AUTO_COMMAND_TIMEOUT", "900")),
        log_level=os.getenv("V2RAY_AUTO_LOG_LEVEL", "INFO"),
        smtp_host=os.getenv("V2RAY_AUTO_SMTP_HOST") or None,
        smtp_port=int(os.getenv("V2RAY_AUTO_SMTP_PORT", "587")),
        smtp_username=os.getenv("V2RAY_AUTO_SMTP_USERNAME") or None,
        smtp_password=os.getenv("V2RAY_AUTO_SMTP_PASSWORD") or None,
        smtp_sender=os.getenv("V2RAY_AUTO_SMTP_SENDER") or None,
    )
