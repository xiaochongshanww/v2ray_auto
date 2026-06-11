"""Legacy VMess TCP profile.

Kept for old clients only. This profile is not the recommended default.
"""

from __future__ import annotations

import random
import uuid

from v2ray_auto.core.models import GeneratedConfig
from v2ray_auto.core.vmess import build_vmess_client_uri


def build_vmess_tcp_legacy_config(server_host: str, *, listen_port: int | None = None) -> GeneratedConfig:
    port = listen_port or random.randint(10000, 65535)
    client_id = str(uuid.uuid4())

    server_config = {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "port": port,
                "listen": "0.0.0.0",
                "protocol": "vmess",
                "settings": {"clients": [{"id": client_id, "alterId": 0}]},
                "streamSettings": {"network": "tcp"},
            }
        ],
        "outbounds": [{"protocol": "freedom", "settings": {}}],
    }

    return GeneratedConfig(
        core="v2ray",
        profile="vmess-tcp-legacy",
        service_name="v2ray.service",
        config_path="/usr/local/etc/v2ray/config.json",
        server_config=server_config,
        client_uri=build_vmess_client_uri(server_host, port, client_id),
        port=port,
        client_id=client_id,
        metadata={"network": "tcp", "security": "none", "server": server_host},
    )
