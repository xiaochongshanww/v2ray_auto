"""Tests for the REALITY connectivity self-test logic."""

from v2ray_auto.core.deployment import DeploymentService
from v2ray_auto.core.models import GeneratedConfig
from v2ray_auto.core.settings import Settings


class _FakeSSH:
    def __init__(self):
        self.logged = []
        self.commands = []
        self.stdout_by_substring = {}
        self.uploads = []

    def run(self, command, *, sudo=False, check=True, redact=()):
        self.commands.append(command)
        if "ss -ltn '( sport = :18080 )'" in command:
            return _Result(0, "")
        if "socks5-hostname 127.0.0.1:18080" in command:
            return _Result(0, self.stdout_by_substring.get("probe", "204"))
        return _Result(0, "")

    def put_text(self, remote_path, content, *, mode=0o600):
        self.uploads.append((remote_path, content))

    def log(self, message):
        self.logged.append(message)


class _Result:
    def __init__(self, exit_code, stdout, stderr=""):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr

    @property
    def ok(self):
        return self.exit_code == 0


def _generated(**overrides):
    kwargs = {
        "core": "xray",
        "profile": "vless-reality-vision",
        "service_name": "xray.service",
        "config_path": "/usr/local/etc/xray/config.json",
        "server_config": {},
        "client_uri": "vless://test",
        "port": 443,
        "client_id": "33f54a1b-4ff7-41be-8e9d-24f4369e71cb",
        "metadata": {
            "serverName": "www.apple.com",
            "publicKey": "public-key",
            "shortId": "e764a52c64a1f9b9",
        },
    }
    kwargs.update(overrides)
    return GeneratedConfig(**kwargs)


def _service():
    return DeploymentService(Settings())


def _service_with_log(log_list):
    return DeploymentService(Settings(), log=log_list.append)


def test_self_test_ok_returns_none():
    ssh = _FakeSSH()
    logs = []
    service = _service_with_log(logs)
    warning = service._verify_reality_connectivity(ssh, _generated())
    assert warning is None
    assert any("REALITY self-test OK" in line for line in logs)


def test_self_test_failure_returns_warning():
    ssh = _FakeSSH()
    ssh.stdout_by_substring["probe"] = "000"
    logs = []
    service = _service_with_log(logs)
    warning = service._verify_reality_connectivity(ssh, _generated())
    assert warning is not None
    assert "REALITY Dest" in warning
    assert any("self-test failed" in line for line in logs)


def test_self_test_missing_metadata_skipped():
    ssh = _FakeSSH()
    logs = []
    service = _service_with_log(logs)
    warning = service._verify_reality_connectivity(ssh, _generated(metadata={}))
    assert warning is None
    assert any("missing metadata" in line for line in logs)


def test_self_test_cleanup_runs():
    ssh = _FakeSSH()
    service = _service()
    service._verify_reality_connectivity(ssh, _generated())
    cleanup = [c for c in ssh.commands if "pkill" in c and "selfcheck" in c]
    assert cleanup, "expected pkill cleanup command"
    assert "selfcheck-client.json" in cleanup[0]
