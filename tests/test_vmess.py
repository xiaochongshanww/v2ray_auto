from v2ray_auto.core.vmess import build_vmess_config


def test_build_vmess_config_contains_expected_values():
    config = build_vmess_config("203.0.113.10", port=23456, client_id="00000000-0000-0000-0000-000000000000")

    assert config.listen_port == 23456
    assert config.client_id == "00000000-0000-0000-0000-000000000000"
    assert config.server_config["inbounds"][0]["port"] == 23456
    assert config.server_config["inbounds"][0]["settings"]["clients"][0]["id"] == config.client_id
    assert config.client_config["outbounds"][0]["settings"]["vnext"][0]["address"] == "203.0.113.10"
    assert config.vmess_url.startswith("vmess://")
