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

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_key)


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
    )
