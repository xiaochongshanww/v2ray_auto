from v2ray_auto.core.profiles.vless_reality_vision import build_vless_reality_vision_config


def test_build_vless_reality_vision_config():
    generated = build_vless_reality_vision_config(
        server_host="203.0.113.10",
        listen_port=443,
        server_name="www.microsoft.com",
        dest="www.microsoft.com:443",
        private_key="private-key",
        public_key="public-key",
    )

    assert generated.core == "xray"
    assert generated.profile == "vless-reality-vision"
    assert generated.service_name == "xray.service"
    assert generated.config_path == "/usr/local/etc/xray/config.json"
    assert generated.port == 443
    assert generated.client_uri.startswith("vless://")
    inbound = generated.server_config["inbounds"][0]
    assert inbound["protocol"] == "vless"
    assert inbound["streamSettings"]["security"] == "reality"
    assert inbound["streamSettings"]["network"] == "tcp"
    assert inbound["settings"]["clients"][0]["flow"] == "xtls-rprx-vision"
