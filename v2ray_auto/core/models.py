"""Typed request and result models for deployment orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

LogSink = Callable[[str], None]

LinuxFamily = Literal["debian", "redhat", "unknown"]


@dataclass(frozen=True)
class DeploymentRequest:
    host: str
    port: int
    username: str
    password: str | None = None
    private_key_path: str | None = None
    email: str | None = None
    remote_dir: str = "/opt/v2ray_auto"
    install_warp: bool = False

    def validate(self) -> None:
        if not self.host:
            raise ValueError("host is required")
        if not 1 <= int(self.port) <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if not self.username:
            raise ValueError("username is required")
        if not self.password and not self.private_key_path:
            raise ValueError("password or private_key_path is required")


@dataclass(frozen=True)
class DeploymentResult:
    server: str
    port: int
    uuid: str
    vmess_url: str
    remote_config_path: str
    logs: list[str] = field(default_factory=list)
