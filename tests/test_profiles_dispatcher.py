import pytest

from v2ray_auto.core.errors import ConfigError
from v2ray_auto.core.models import DeploymentRequest
from v2ray_auto.core.profiles import build_config_for_request


def test_vless_profile_requires_reality_keys():
    request = DeploymentRequest(host="203.0.113.10", port=22, username="root", password="pw")
    with pytest.raises(ConfigError):
        build_config_for_request(request)


def test_vless_profile_dispatches_with_reality_keys():
    request = DeploymentRequest(host="203.0.113.10", port=22, username="root", password="pw")
    generated = build_config_for_request(request, reality_private_key="private", reality_public_key="public")
    assert generated.core == "xray"
    assert generated.profile == "vless-reality-vision"
    assert generated.port == 443


def test_legacy_profile_dispatches():
    request = DeploymentRequest(
        host="203.0.113.10",
        port=22,
        username="root",
        password="pw",
        profile="vmess-tcp-legacy",
        listen_port=23456,
    )
    generated = build_config_for_request(request)
    assert generated.core == "v2ray"
    assert generated.profile == "vmess-tcp-legacy"
    assert generated.port == 23456
    assert generated.client_uri.startswith("vmess://")
    # client_uri is a base64-encoded JSON; verify it decodes properly
    encoded = generated.client_uri.removeprefix("vmess://")
    import base64
    import json

    decoded = json.loads(base64.b64decode(encoded))
    assert decoded["add"] == "203.0.113.10"
    assert decoded["port"] == "23456"
