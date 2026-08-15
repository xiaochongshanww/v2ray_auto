"""Tests for network tuning module."""

from v2ray_auto.core.network_tuning import SYSCTL_FILE


def test_sysctl_file_path():
    assert SYSCTL_FILE == "/etc/sysctl.d/99-v2ray-auto.conf"
