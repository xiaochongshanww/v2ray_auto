"""Tests for DeploymentService (pure logic only, no SSH)."""

from v2ray_auto.core.deployment import DeploymentService
from v2ray_auto.core.models import DeploymentResult
from v2ray_auto.core.settings import Settings


def _settings() -> Settings:
    return Settings(api_key="test", allowed_origins=())


def test_core_for_profile_vless():
    service = DeploymentService(_settings())
    assert service._core_for_profile("vless-reality-vision") == "xray"


def test_core_for_profile_vmess():
    service = DeploymentService(_settings())
    assert service._core_for_profile("vmess-tcp-legacy") == "v2ray"


def test_validate_profile_valid():
    service = DeploymentService(_settings())
    service._validate_profile("vless-reality-vision")
    service._validate_profile("vmess-tcp-legacy")


def test_validate_profile_invalid():
    import pytest

    from v2ray_auto.core.errors import UnsupportedProfileError

    service = DeploymentService(_settings())
    with pytest.raises(UnsupportedProfileError, match="不支持的配置模板"):
        service._validate_profile("unknown-profile")


def test_deployment_result_vmess_url_alias():
    result = DeploymentResult(
        server="203.0.113.10",
        port=443,
        uuid="abc",
        client_uri="vmess://test",
        remote_config_path="/etc/config.json",
        core="xray",
        profile="vless-reality-vision",
        service_name="xray.service",
    )
    assert result.vmess_url == result.client_uri


def test_deployment_result_default_logs():
    result = DeploymentResult(
        server="203.0.113.10",
        port=443,
        uuid="abc",
        client_uri="vmess://test",
        remote_config_path="/etc/config.json",
        core="xray",
        profile="vless-reality-vision",
        service_name="xray.service",
    )
    assert result.logs == []
