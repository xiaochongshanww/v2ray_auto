"""V2Ray VMess configuration generation."""

from __future__ import annotations

import base64
import json
import random
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class VmessConfig:
    listen_port: int
    client_id: str
    server_config: dict
    client_config: dict
    vmess_url: str


def build_vmess_client_uri(host: str, port: int, client_id: str) -> str:
    """Build a VMess protocol link for client import."""
    payload = {
        "v": "2",
        "ps": f"v2ray-auto-{host}",
        "add": host,
        "port": str(port),
        "id": client_id,
        "aid": "0",
        "net": "tcp",
        "type": "none",
        "host": "",
        "path": "",
        "tls": "",
    }
    encoded = base64.b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("utf-8")
    return f"vmess://{encoded}"


def build_vmess_config(server_host: str, *, port: int | None = None, client_id: str | None = None) -> VmessConfig:
    listen_port = port or random.randint(10000, 65535)
    generated_id = client_id or str(uuid.uuid4())

    server_config = {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "port": listen_port,
                "listen": "0.0.0.0",
                "protocol": "vmess",
                "settings": {"clients": [{"id": generated_id, "alterId": 0}]},
                "streamSettings": {"network": "tcp"},
            }
        ],
        "outbounds": [{"protocol": "freedom", "settings": {}}],
    }

    client_config = {
        "outbounds": [
            {
                "protocol": "vmess",
                "settings": {
                    "vnext": [
                        {
                            "address": server_host,
                            "port": listen_port,
                            "users": [{"id": generated_id, "alterId": 0, "security": "auto"}],
                        }
                    ]
                },
                "streamSettings": {"network": "tcp"},
            }
        ]
    }

    return VmessConfig(
        listen_port=listen_port,
        client_id=generated_id,
        server_config=server_config,
        client_config=client_config,
        vmess_url=build_vmess_client_uri(server_host, listen_port, generated_id),
    )
