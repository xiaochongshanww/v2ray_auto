import pytest

from v2ray_auto.core.installer import package_bootstrap_command


def test_debian_bootstrap_command():
    command = package_bootstrap_command("debian")
    assert "apt-get update" in command
    assert "curl" in command


def test_redhat_bootstrap_command():
    command = package_bootstrap_command("redhat")
    assert "yum install" in command
    assert "curl" in command


def test_unknown_bootstrap_command():
    with pytest.raises(RuntimeError):
        package_bootstrap_command("unknown")
