"""Tests for deployment model validation."""

import pytest

from v2ray_auto.core.models import DeploymentRequest


def test_valid_minimal_request():
    request = DeploymentRequest(host="203.0.113.10", port=22, username="root", password="pw")
    request.validate()  # should not raise


def test_valid_with_private_key():
    request = DeploymentRequest(host="203.0.113.10", port=22, username="root", private_key_path="/tmp/key")
    request.validate()  # should not raise


def test_missing_host():
    with pytest.raises(ValueError):
        DeploymentRequest(host="", port=22, username="root", password="pw").validate()


def test_invalid_port():
    with pytest.raises(ValueError):
        DeploymentRequest(host="203.0.113.10", port=0, username="root", password="pw").validate()


def test_invalid_port_high():
    with pytest.raises(ValueError):
        DeploymentRequest(host="203.0.113.10", port=70000, username="root", password="pw").validate()


def test_missing_username():
    with pytest.raises(ValueError):
        DeploymentRequest(host="203.0.113.10", port=22, username="", password="pw").validate()


def test_missing_credentials():
    with pytest.raises(ValueError):
        DeploymentRequest(host="203.0.113.10", port=22, username="root").validate()


def test_listen_port_validation():
    with pytest.raises(ValueError):
        DeploymentRequest(host="203.0.113.10", port=22, username="root", password="pw", listen_port=99999).validate()


def test_valid_listen_port():
    request = DeploymentRequest(host="203.0.113.10", port=22, username="root", password="pw", listen_port=443)
    request.validate()  # should not raise


def test_default_profile():
    request = DeploymentRequest(host="203.0.113.10", port=22, username="root", password="pw")
    assert request.profile == "vless-reality-vision"
