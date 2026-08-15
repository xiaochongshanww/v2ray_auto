"""Tests for the uninstall teardown logic."""

from v2ray_auto.core.deployment import PROFILE_CLEANUP, DeploymentService
from v2ray_auto.core.models import UninstallRequest
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
    def __init__(
        self,
        *,
        service_active=True,
        service_enabled=True,
        config_exists=True,
        state_exists=True,
        ufw_active=True,
        iptables_rule=True,
        firewalld=True,
    ):
        self.commands = []
        self.logged = []
        self.uploads = []
        self.service_active = service_active
        self.service_enabled = service_enabled
        self.config_exists = config_exists
        self.state_exists = state_exists
        self.ufw_active = ufw_active
        self.iptables_rule = iptables_rule
        self.firewalld = firewalld

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
        if "systemctl is-active" in command:
            return _Result(0 if self.service_active else 3, "active\n" if self.service_active else "inactive\n")
        if "systemctl is-enabled" in command:
            return _Result(0 if self.service_enabled else 1, "enabled\n" if self.service_enabled else "disabled\n")
        if "test -d" in command and "echo yes" in command:
            has = ("/usr/local/etc/xray" in command and self.config_exists) or (
                "/usr/local/etc/v2ray-auto" in command and self.state_exists
            )
            return _Result(0, "yes\n" if has else "no\n")
        if "ufw status" in command and "head -1" in command:
            return _Result(0, "Status: active\n" if self.ufw_active else "Status: inactive\n")
        if "ufw status" in command and "grep -q" in command:
            return _Result(0 if self.ufw_active else 1, "")
        if "iptables -C" in command:
            return _Result(0 if self.iptables_rule else 1, "")
        if "command -v firewall-cmd" in command:
            return _Result(0 if self.firewalld else 1, "")
        if "firewall-cmd --permanent --query-port" in command:
            return _Result(0 if self.firewalld else 1, "")
        return _Result(0, "")

    def put_text(self, remote_path, content, *, mode=0o600):
        self.uploads.append((remote_path, content))

    def log(self, message):
        self.logged.append(message)


def _service():
    return DeploymentService(Settings())


def _factory(ssh):
    return lambda req, log, timeout: ssh


def _request(**overrides):
    kwargs = {
        "host": "203.0.113.10",
        "port": 22,
        "username": "root",
        "profile": "vless-reality-vision",
        "password": "secret",
    }
    kwargs.update(overrides)
    return UninstallRequest(**kwargs)


def test_cleanup_paths_defined():
    assert set(PROFILE_CLEANUP) == {"vless-reality-vision", "vmess-tcp-legacy"}
    assert PROFILE_CLEANUP["vless-reality-vision"]["service_name"] == "xray.service"
    assert PROFILE_CLEANUP["vmess-tcp-legacy"]["service_name"] == "v2ray.service"


def test_uninstall_full_teardown():
    ssh = _FakeSSH()
    logs = []
    service = DeploymentService(Settings(), log=logs.append)
    result = service.uninstall(_request(), ssh_factory=_factory(ssh))

    assert result.stopped_service is True
    assert result.removed_config is True
    assert result.removed_state is True
    assert result.closed_firewall is True
    assert any("stopped xray.service" in line for line in logs)
    assert any("disabled xray.service" in line for line in logs)
    assert any("removed config directory /usr/local/etc/xray" in line for line in logs)
    assert any("removed state directory" in line for line in logs)
    assert any("ufw rule removed" in line for line in logs)
    assert any("iptables rule removed" in line for line in logs)
    assert any("firewalld rule removed" in line for line in logs)


def test_uninstall_idempotent_when_nothing_present():
    ssh = _FakeSSH(
        service_active=False,
        service_enabled=False,
        config_exists=False,
        state_exists=False,
        ufw_active=False,
        iptables_rule=False,
        firewalld=False,
    )
    logs = []
    service = DeploymentService(Settings(), log=logs.append)
    result = service.uninstall(_request(), ssh_factory=_factory(ssh))

    assert result.stopped_service is False
    assert result.removed_config is False
    assert result.removed_state is False
    assert result.closed_firewall is False
    assert any("not active; skip service stop" in line for line in logs)
    assert any("not enabled; skip service disable" in line for line in logs)
    assert any("config directory" in line and "not found" in line for line in logs)
    assert any("no matching firewall rule found" in line for line in logs)


def test_uninstall_recovers_after_crash_after_stop():
    """If a previous uninstall crashed right after `systemctl stop` (service
    is now inactive but the unit is still enabled), a retry must still
    disable the unit and remove files."""
    ssh = _FakeSSH(
        service_active=False,
        service_enabled=True,
        config_exists=True,
        state_exists=True,
        ufw_active=False,
        iptables_rule=False,
        firewalld=False,
    )
    logs = []
    service = DeploymentService(Settings(), log=logs.append)
    result = service.uninstall(_request(), ssh_factory=_factory(ssh))

    # service not active, but unit still enabled -> retry disables it
    assert any("systemctl disable xray" in c for c in ssh.commands)
    assert any("disabled xray.service" in line for line in logs)
    # remaining cleanup still runs
    assert result.removed_config is True
    assert result.removed_state is True
    # stopped_service stays False because it was already inactive
    assert result.stopped_service is False


def test_uninstall_recovers_after_crash_after_stop_but_already_disabled():
    """Crash after both stop and disable: retry is a clean no-op."""
    ssh = _FakeSSH(
        service_active=False,
        service_enabled=False,
        config_exists=False,
        state_exists=False,
        ufw_active=False,
        iptables_rule=False,
        firewalld=False,
    )
    logs = []
    service = DeploymentService(Settings(), log=logs.append)
    result = service.uninstall(_request(), ssh_factory=_factory(ssh))
    assert result.stopped_service is False
    assert result.removed_config is False
    assert result.removed_state is False


def test_uninstall_validates_request():
    import pytest

    service = _service()
    with pytest.raises(ValueError, match="host is required"):
        service.uninstall(_request(host=""))


def test_uninstall_invalid_profile():
    import pytest

    from v2ray_auto.core.errors import UnsupportedProfileError

    service = _service()
    with pytest.raises(UnsupportedProfileError, match="不支持的配置模板"):
        service.uninstall(_request(profile="trojan"))


def test_uninstall_default_port_mapping():
    service = _service()
    assert service._default_port_for("vless-reality-vision") == 443
    assert service._default_port_for("vmess-tcp-legacy") == 10086


def test_uninstall_vmess_profile_uses_v2ray_service():
    ssh = _FakeSSH()
    service = _service()
    result = service.uninstall(_request(profile="vmess-tcp-legacy"), ssh_factory=_factory(ssh))

    assert result.profile == "vmess-tcp-legacy"
    stop_cmds = [c for c in ssh.commands if "systemctl stop" in c]
    assert any("v2ray" in c for c in stop_cmds)
