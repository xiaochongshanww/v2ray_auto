"""Profile dispatcher."""

from __future__ import annotations

from v2ray_auto.core.models import DeploymentRequest, GeneratedConfig

from .vless_reality_vision import build_vless_reality_vision_config
from .vmess_tcp_legacy import build_vmess_tcp_legacy_config


def build_config_for_request(
    request: DeploymentRequest,
    *,
    reality_private_key: str | None = None,
    reality_public_key: str | None = None,
    client_id: str | None = None,
    short_id: str | None = None,
) -> GeneratedConfig:
    if request.profile == "vless-reality-vision":
        if not reality_private_key or not reality_public_key:
            raise ValueError("REALITY key pair is required for vless-reality-vision profile")
        return build_vless_reality_vision_config(
            server_host=request.host,
            listen_port=request.listen_port or 443,
            server_name=request.reality_server_name,
            dest=request.reality_dest,
            private_key=reality_private_key,
            public_key=reality_public_key,
            client_id=client_id,
            short_id=short_id,
        )
    if request.profile == "vmess-tcp-legacy":
        return build_vmess_tcp_legacy_config(server_host=request.host, listen_port=request.listen_port)
    raise ValueError(f"unsupported profile: {request.profile}")
