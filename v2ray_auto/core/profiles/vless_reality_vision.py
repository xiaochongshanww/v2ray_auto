"""Default Xray VLESS REALITY Vision profile."""

from __future__ import annotations

import secrets
import uuid
from urllib.parse import quote

from v2ray_auto.core.models import GeneratedConfig


def build_vless_reality_vision_config(
    *,
    server_host: str,
    listen_port: int,
    server_name: str,
    dest: str,
    private_key: str,
    public_key: str,
) -> GeneratedConfig:
    client_id = str(uuid.uuid4())
    short_id = secrets.token_hex(8)

    server_config = {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "tag": "vless-reality-vision-in",
                "listen": "0.0.0.0",
                "port": listen_port,
                "protocol": "vless",
                "settings": {
                    "clients": [
                        {
                            "id": client_id,
                            "flow": "xtls-rprx-vision",
                            "email": "v2ray-auto@local",
                        }
                    ],
                    "decryption": "none",
                },
                "streamSettings": {
                    "network": "raw",
                    "security": "reality",
                    "realitySettings": {
                        "show": False,
                        "dest": dest,
                        "xver": 0,
                        "serverNames": [server_name],
                        "privateKey": private_key,
                        "shortIds": [short_id],
                    },
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"],
                },
            }
        ],
        "outbounds": [
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "block"},
        ],
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": [
                {
                    "type": "field",
                    "ip": ["geoip:private"],
                    "outboundTag": "block",
                }
            ],
        },
    }

    query = "&".join(
        [
            "type=tcp",
            "security=reality",
            "flow=xtls-rprx-vision",
            f"sni={quote(server_name)}",
            "fp=chrome",
            f"pbk={quote(public_key)}",
            f"sid={short_id}",
        ]
    )
    client_uri = f"vless://{client_id}@{server_host}:{listen_port}?{query}#v2ray-auto-{server_host}"

    return GeneratedConfig(
        core="xray",
        profile="vless-reality-vision",
        service_name="xray.service",
        config_path="/usr/local/etc/xray/config.json",
        server_config=server_config,
        client_uri=client_uri,
        port=listen_port,
        client_id=client_id,
        metadata={
            "network": "raw",
            "security": "reality",
            "flow": "xtls-rprx-vision",
            "serverName": server_name,
            "dest": dest,
            "publicKey": public_key,
            "shortId": short_id,
            "mux": False,
        },
    )
