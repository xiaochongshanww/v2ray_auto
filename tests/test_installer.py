import pytest

from v2ray_auto.core.installer import Installer, package_bootstrap_command


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


def test_extract_reality_key_pair_values():
    output = "Private key: abc_private\nPublic key: xyz_public\n"
    assert Installer._extract_key(output, "Private key") == "abc_private"
    assert Installer._extract_key(output, "Public key") == "xyz_public"


def test_extract_key_raises_when_missing():
    with pytest.raises(RuntimeError):
        Installer._extract_key("invalid output", "Private key")
