"""Tests for Installer bootstrap flow branches with a fake SSH executor."""

import pytest

from v2ray_auto.core.errors import ConfigError, InstallFailedError, RemoteCommandError
from v2ray_auto.core.installer import DEFAULT_XRAY_VERSION, Installer


class _Result:
    def __init__(self, exit_code, stdout="", stderr=""):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr

    @property
    def ok(self):
        return self.exit_code == 0


class _FakeSSH:
    def __init__(self, *, has_service=False, mem_mb=1024, swap_lines=0, mark_installed=True):
        self.commands = []
        self.has_service = has_service
        self.mem_mb = mem_mb
        self.swap_lines = swap_lines
        self.mark_installed = mark_installed
        self.logged = []

    def log(self, message):
        self.logged.append(message)

    def run(self, command, *, sudo=False, check=True, redact=(), ignore_cancel=False):
        self.commands.append(command)
        if "systemctl list-unit-files" in command:
            return _Result(0, "xray.service enabled\n" if self.has_service else "")
        if "free -m" in command:
            return _Result(0, str(self.mem_mb) + "\n")
        if "swapon --show" in command:
            return _Result(0, "1\n" if self.swap_lines else "0\n")
        if "bash " in command:
            if self.mark_installed:
                self.has_service = True
            return _Result(0)
        if "apt-get" in command or "yum install" in command or "curl" in command:
            return _Result(0)
        if any(token in command for token in ("fallocate", "chmod 600", "mkswap", "swapon", "/etc/fstab")):
            return _Result(0)
        if not check:
            return _Result(1, "", f"failed: {command}")
        raise RemoteCommandError(command, 1, f"failed: {command}")


def test_ensure_installed_skips_when_service_exists():
    ssh = _FakeSSH(has_service=True)
    installer = Installer(ssh, log=ssh.log)
    installer.ensure_installed("debian")
    assert any("already exists; skip bootstrap install" in line for line in ssh.logged)
    assert not any("bootstrap install will run" in line for line in ssh.logged)


def test_ensure_installed_fresh_bootstraps():
    ssh = _FakeSSH(has_service=False)
    installer = Installer(ssh, log=ssh.log)
    installer.ensure_installed("debian")
    assert any("bootstrap install will run" in line for line in ssh.logged)
    assert any("curl" in cmd and "install-release.sh" in cmd for cmd in ssh.commands)


def test_ensure_installed_raises_when_binary_missing_after_install():
    ssh = _FakeSSH(has_service=False, mark_installed=False)
    installer = Installer(ssh, log=ssh.log)
    with pytest.raises(InstallFailedError):
        installer.ensure_installed("debian")


def test_ensure_installed_redhat_bootstrap_command_used():
    ssh = _FakeSSH(has_service=False)
    installer = Installer(ssh, log=ssh.log)
    installer.ensure_installed("redhat")
    assert any("yum install -y curl" in cmd for cmd in ssh.commands)


def test_swap_created_for_small_memory():
    ssh = _FakeSSH(has_service=True, mem_mb=512, swap_lines=0)
    installer = Installer(ssh, log=ssh.log)
    installer.ensure_swap_for_small_server()
    assert any("fallocate -l 1G /swapfile" in cmd for cmd in ssh.commands)
    assert any("mkswap /swapfile" in cmd for cmd in ssh.commands)
    assert any("swapon /swapfile" in cmd for cmd in ssh.commands)
    assert any("/swapfile swap swap defaults" in cmd for cmd in ssh.commands)


def test_swap_skipped_when_enough_memory():
    ssh = _FakeSSH(has_service=True, mem_mb=4096, swap_lines=0)
    installer = Installer(ssh, log=ssh.log)
    installer.ensure_swap_for_small_server()
    assert any("swap bootstrap skipped" in line for line in ssh.logged)
    assert not any("mkswap" in cmd for cmd in ssh.commands)


def test_swap_skipped_when_swap_already_present():
    ssh = _FakeSSH(has_service=True, mem_mb=512, swap_lines=1)
    installer = Installer(ssh, log=ssh.log)
    installer.ensure_swap_for_small_server()
    assert any("swap bootstrap skipped" in line for line in ssh.logged)
    assert not any("mkswap" in cmd for cmd in ssh.commands)


def test_install_core_uses_configured_script_url():
    ssh = _FakeSSH(has_service=False)
    installer = Installer(ssh, log=ssh.log, xray_install_script_url="https://example.test/xray.sh")
    installer.ensure_installed("debian")
    assert any("https://example.test/xray.sh" in cmd for cmd in ssh.commands)


def test_pinned_version_defaults_to_compat_release():
    installer = Installer(None)  # type: ignore[arg-type]
    assert installer.pinned_version == DEFAULT_XRAY_VERSION


def test_install_command_passes_version_flag():
    installer = Installer(None)  # type: ignore[arg-type]
    command = installer._install_command("/tmp/x.sh")
    assert command == f"bash /tmp/x.sh install --version {DEFAULT_XRAY_VERSION}"


def test_latest_version_disables_pin():
    installer = Installer(None, core_version="latest")  # type: ignore[arg-type]
    assert installer.pinned_version is None
    assert installer._install_command("/tmp/x.sh") == "bash /tmp/x.sh"


def test_version_without_prefix_is_normalised():
    installer = Installer(None, core="xray", core_version="25.3.6")  # type: ignore[arg-type]
    assert installer.pinned_version == "v25.3.6"


def test_invalid_version_is_rejected():
    installer = Installer(None, core_version="v1.0.0; rm -rf /")  # type: ignore[arg-type]
    with pytest.raises(ConfigError):
        _ = installer.pinned_version


def test_v2ray_core_is_never_pinned():
    installer = Installer(None, core="v2ray")  # type: ignore[arg-type]
    assert installer.pinned_version is None


def test_bootstrap_install_uses_pinned_version():
    ssh = _FakeSSH(has_service=False)
    installer = Installer(ssh, log=ssh.log)
    installer.ensure_installed("debian")
    assert any(f"install --version {DEFAULT_XRAY_VERSION}" in cmd for cmd in ssh.commands)
    assert any("pinned" in line for line in ssh.logged)
