"""Typed request and result models for deployment orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

LogSink = Callable[[str], None]

LinuxFamily = Literal["debian", "redhat", "unknown"]
CoreName = Literal["xray", "v2ray"]
ProfileName = Literal["vless-reality-vision", "vmess-tcp-legacy"]


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
    profile: ProfileName = "vless-reality-vision"
    listen_port: int | None = None
    reality_server_name: str = "www.microsoft.com"
    reality_dest: str = "www.microsoft.com:443"

    def validate(self) -> None:
        if not self.host:
            raise ValueError("host is required")
        if not 1 <= int(self.port) <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if self.listen_port is not None and not 1 <= int(self.listen_port) <= 65535:
            raise ValueError("listen_port must be between 1 and 65535")
        if not self.username:
            raise ValueError("username is required")
        if not self.password and not self.private_key_path:
            raise ValueError("password or private_key_path is required")


@dataclass(frozen=True)
class GeneratedConfig:
    core: CoreName
    profile: ProfileName
    service_name: str
    config_path: str
    server_config: dict
    client_uri: str
    port: int
    client_id: str
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class DeploymentResult:
    server: str
    port: int
    uuid: str
    client_uri: str
    remote_config_path: str
    core: CoreName
    profile: ProfileName
    service_name: str
    logs: list[str] = field(default_factory=list)

    @property
    def vmess_url(self) -> str:
        """Backward-compatible alias for old callers."""
        return self.client_uri
