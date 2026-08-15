"""Tests for deploy cancellation and rollback of completed steps."""

import pytest

from v2ray_auto.core.deployment import DeploymentService
from v2ray_auto.core.errors import OperationCancelledError
from v2ray_auto.core.models import DeploymentRequest
from v2ray_auto.core.settings import Settings


class _Result:
    def __init__(self, exit_code, stdout, stderr=""):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr

    @property
    def ok(self):
        return self.exit_code == 0


class _FakeSSH:
    """Records commands; simulates a cancel event mid-deploy and then lets the
    rollback commands through (ignore_cancel)."""

    def __init__(self, cancel_after_commands=0, *, service_active=True, service_enabled=True, config_exists=True):
        self.commands = []
        self.logged = []
        self.cancel_after_commands = cancel_after_commands
        self.ran = 0
        self.service_active = service_active
        self.service_enabled = service_enabled
        self.config_exists = config_exists

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def connect(self):
        pass

    def close(self):
        pass

    def run(self, command, *, sudo=False, check=True, redact=(), ignore_cancel=False):
        self.commands.append(command)
        self.ran += 1
        if not ignore_cancel and self.cancel_after_commands and self.ran > self.cancel_after_commands:
            raise OperationCancelledError(detail="cancelled by user")
        if "cat /etc/os-release" in command:
            return _Result(0, 'ID="debian"\n')
        if "systemctl list-unit-files" in command:
            return _Result(0, "xray.service  enabled\n")
        if "xray x25519" in command:
            return _Result(0, "Private key: aaaa\nPublic key: bbbb\n")
        if "sha256sum" in command:
            return _Result(1, "")
        if "ss -ltnp" in command:
            return _Result(0, "")
        if "xray run -test" in command:
            return _Result(0, "")
        if "systemctl is-active" in command:
            return _Result(0 if self.service_active else 3, "active\n" if self.service_active else "inactive\n")
        if "systemctl is-enabled" in command:
            return _Result(0 if self.service_enabled else 1, "enabled\n" if self.service_enabled else "disabled\n")
        if "test -d" in command and "echo yes" in command:
            has = "/usr/local/etc/xray" in command and self.config_exists
            return _Result(0, "yes\n" if has else "no\n")
        if "ufw status" in command and "head -1" in command:
            return _Result(0, "Status: active\n")
        if "ufw status" in command and "grep -q" in command:
            return _Result(0, "")
        if "iptables -C" in command:
            return _Result(0, "")
        if "command -v firewall-cmd" in command:
            return _Result(1, "")
        return _Result(0, "")

    def log(self, message):
        self.logged.append(message)

    def put_text(self, remote_path, content, *, mode=0o600):
        pass


def _request():
    return DeploymentRequest(
        host="203.0.113.10",
        port=22,
        username="root",
        password="secret",
        profile="vless-reality-vision",
    )


def _factory(ssh):
    return lambda req, log, timeout: ssh


def test_deploy_cancel_rolls_back_completed_steps():
    """Cancel after config/service/firewall complete -> all are rolled back."""
    ssh = _FakeSSH(cancel_after_commands=37)
    logs = []
    service = DeploymentService(Settings(), log=logs.append)
    with pytest.raises(OperationCancelledError):
        service.deploy(_request(), ssh_factory=_factory(ssh))

    assert any("rolling back completed steps" in line for line in logs)
    assert any("stopped xray.service" in line for line in logs)
    assert any("disabled xray.service" in line for line in logs)
    assert any("removed config directory /usr/local/etc/xray" in line for line in logs)
    assert any("ufw rule removed" in line for line in logs)
    assert any("rollback complete" in line for line in logs)


def test_deploy_cancel_before_steps_no_rollback():
    """Cancel during install -> no config/service/firewall to roll back."""
    ssh = _FakeSSH(cancel_after_commands=2)
    logs = []
    service = DeploymentService(Settings(), log=logs.append)
    with pytest.raises(OperationCancelledError):
        service.deploy(_request(), ssh_factory=_factory(ssh))

    assert any("rolling back completed steps" in line for line in logs)
    assert not any("stopped xray.service" in line for line in logs)
    assert not any("removed config directory" in line for line in logs)


def test_rollback_is_idempotent():
    """Rollback with nothing actually present does not crash."""
    service = DeploymentService(Settings())
    ssh = _FakeSSH(service_active=False, service_enabled=False, config_exists=False)
    logs = []
    service._rollback(ssh, "vless-reality-vision", None, ["firewall", "service", "config"], logs.append)
    assert any("rollback complete" in line for line in logs)
    assert not any("stopped" in line for line in logs)
    assert not any("disabled" in line for line in logs)


def test_rollback_unknown_profile_is_safe():
    service = DeploymentService(Settings())
    ssh = _FakeSSH()
    logs = []
    service._rollback(ssh, "trojan", None, ["config"], logs.append)
    assert any("cannot roll back" in line for line in logs)
