"""Deployment orchestration for one-click setup on empty servers."""

from __future__ import annotations

import hashlib
import json
import time

from .installer import Installer
from .models import CoreName, DeploymentRequest, DeploymentResult, GeneratedConfig, LogSink
from .network_tuning import NetworkTuning
from .os_release import parse_os_release
from .profiles import build_config_for_request
from .settings import Settings
from .ssh import SSHExecutor
from .state import RemoteStateStore


class DeploymentService:
    def __init__(self, settings: Settings, log: LogSink | None = None):
        self.settings = settings
        self.log = log or (lambda message: None)

    def deploy(self, request: DeploymentRequest) -> DeploymentResult:
        request.validate()
        self._validate_profile(request.profile)

        logs: list[str] = []

        def capture(message: str) -> None:
            if message:
                logs.append(message)
                self.log(message)

        with SSHExecutor(request, log=capture, timeout=self.settings.command_timeout) as ssh:
            distro_id, family = self._detect_os(ssh)
            capture(f"detected linux distribution: {distro_id} ({family})")

            core = self._core_for_profile(request.profile)
            installer = Installer(ssh, core=core, log=capture)
            installer.ensure_installed(family)
            tuning = NetworkTuning(ssh, log=capture)
            tuning.enable_bbr_if_available()
            tuning.tune_tcp_buffers()
            tuning.enable_pmtu_discovery()

            if request.profile == "vless-reality-vision":
                profile_state = RemoteStateStore(ssh).get_or_create_reality_profile_state(installer)
                generated = build_config_for_request(
                    request,
                    reality_private_key=profile_state.private_key,
                    reality_public_key=profile_state.public_key,
                    client_id=profile_state.client_id,
                    short_id=profile_state.short_id,
                )
            else:
                generated = build_config_for_request(request)

            self._assert_port_available(ssh, generated.port, generated.service_name)
            self._prepare_config_dir(ssh, generated.config_path)
            config_changed = self._upload_config_if_changed(ssh, generated.config_path, generated.server_config)
            if config_changed:
                self._validate_remote_config(ssh, generated)
                self._restart_service(ssh, generated)
            else:
                capture("config unchanged; skip service restart")
            self._open_firewall(ssh, generated.port)
            self._assert_port_listening(ssh, generated.port, generated.service_name)

        return DeploymentResult(
            server=request.host,
            port=generated.port,
            uuid=generated.client_id,
            client_uri=generated.client_uri,
            remote_config_path=generated.config_path,
            core=generated.core,
            profile=generated.profile,
            service_name=generated.service_name,
            logs=logs,
        )

    def _core_for_profile(self, profile: str) -> CoreName:
        return "v2ray" if profile == "vmess-tcp-legacy" else "xray"

    def _validate_profile(self, profile: str) -> None:
        valid = {"vless-reality-vision", "vmess-tcp-legacy"}
        if profile not in valid:
            raise ValueError(f"unsupported profile: {profile}")

    def _detect_os(self, ssh: SSHExecutor) -> tuple[str, str]:
        result = ssh.run("cat /etc/os-release", check=True)
        return parse_os_release(result.stdout)

    def _assert_port_available(self, ssh: SSHExecutor, port: int, service_name: str) -> None:
        service_unit = service_name.removesuffix(".service")
        command = (
            f"ss -ltnp '( sport = :{port} )' 2>/dev/null | "
            f"grep -v {service_unit} | tail -n +2"
        )
        result = ssh.run(command, sudo=True, check=False)
        if result.stdout.strip():
            raise RuntimeError(f"port {port} is already occupied by another process")

    def _assert_port_listening(self, ssh: SSHExecutor, port: int, service_name: str) -> None:
        capture = self.log
        service_unit = service_name.removesuffix(".service")
        time.sleep(1)

        command = f"ss -ltnp '( sport = :{port} )' 2>/dev/null"
        result = ssh.run(command, sudo=True, check=False)
        if service_unit not in result.stdout.lower():
            active = ssh.run(f"systemctl is-active {service_unit}", sudo=True, check=False)
            if active.ok:
                capture(f"WARNING: {service_unit} is active but not listening on port {port}")
                if port < 1024:
                    unit_file = ssh.run(f"cat /etc/systemd/system/{service_name}", sudo=True, check=False)
                    if unit_file.ok and "CAP_NET_BIND_SERVICE" not in unit_file.stdout:
                        capture(f"NOTE: {service_name} lacks CAP_NET_BIND_SERVICE for port {port}")
                        capture("Try a port above 1024, or fix the systemd unit")
            else:
                journal = ssh.run(f"journalctl -u {service_unit} --no-pager -n 10", sudo=True, check=False)
                capture(f"SERVICE CRASHED: {active.stdout.strip()}")
                capture(f"journalctl:\n{journal.stdout.strip()}")
            capture(f"current listeners on {port}: {result.stdout.strip() or 'none'}")

    def _prepare_config_dir(self, ssh: SSHExecutor, config_path: str) -> None:
        directory = config_path.rsplit("/", 1)[0]
        ssh.run(f"mkdir -p {directory}", sudo=True)
        ssh.run(f"test -f {config_path} && cp {config_path} {config_path}.bak.$(date +%Y%m%d%H%M%S) || true", sudo=True)

    def _upload_config_if_changed(self, ssh: SSHExecutor, config_path: str, config_data: dict) -> bool:
        content = json.dumps(config_data, indent=2, ensure_ascii=False, sort_keys=True)
        local_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        remote_hash = self._remote_file_sha256(ssh, config_path)
        if remote_hash == local_hash:
            return False

        tmp_path = f"/tmp/v2ray-auto-config-{id(config_data)}.json"
        ssh.put_text(tmp_path, content)
        ssh.run(f"mv {tmp_path} {config_path}", sudo=True)
        ssh.run(f"chmod 644 {config_path}", sudo=True)
        return True

    def _remote_file_sha256(self, ssh: SSHExecutor, config_path: str) -> str | None:
        result = ssh.run(f"test -f {config_path} && sha256sum {config_path} | awk '{{print $1}}'", sudo=True, check=False)
        value = result.stdout.strip()
        return value or None

    def _validate_remote_config(self, ssh: SSHExecutor, generated: GeneratedConfig) -> None:
        capture = self.log
        if generated.core == "xray":
            result = ssh.run(f"xray run -test -c {generated.config_path}", sudo=True, check=False)
            if not result.ok:
                lines = result.stderr.strip().rsplit("\n", 5)
                capture(f"config validation error: {lines}")
        else:
            result = ssh.run(f"v2ray test -c {generated.config_path}", sudo=True, check=False)
            if not result.ok:
                lines = result.stderr.strip().rsplit("\n", 5)
                capture(f"config validation error: {lines}")

    def _restart_service(self, ssh: SSHExecutor, generated: GeneratedConfig) -> None:
        capture = self.log
        ssh.run("systemctl daemon-reload", sudo=True)
        service_pattern = generated.service_name.replace(".", "\\.")
        result = ssh.run(f"systemctl list-unit-files | grep -E '^{service_pattern}'", sudo=True, check=False)
        if not result.stdout.strip():
            raise RuntimeError(f"{generated.service_name} was not found after bootstrap install")
        service_unit = generated.service_name.removesuffix(".service")
        ssh.run(f"systemctl enable {service_unit}", sudo=True)
        ssh.run(f"systemctl restart {service_unit}", sudo=True)
        result = ssh.run(f"systemctl is-active {service_unit}", sudo=True, check=False)
        if not result.ok:
            journal = ssh.run(f"journalctl -u {service_unit} --no-pager -n 20", sudo=True, check=False)
            capture(f"service is {result.stdout.strip()}")
            capture(f"journalctl ({service_unit}):\n{journal.stdout.strip()}")
            raise RuntimeError(f"{generated.service_name} failed to start")

    def _open_firewall(self, ssh: SSHExecutor, port: int) -> None:
        capture = self.log
        capture(f"opening port {port}/tcp in firewall")

        # Check ufw
        ufw_active = ssh.run("ufw status 2>/dev/null | head -1", sudo=True, check=False)
        if "active" in ufw_active.stdout.lower():
            ssh.run(f"ufw allow {port}/tcp", sudo=True, check=False)
            ssh.run(f"ufw status | grep {port}", sudo=True, check=False)
            capture("ufw rule added")

        # Check iptables
        iptables_check = ssh.run(f"iptables -C INPUT -p tcp --dport {port} -j ACCEPT 2>/dev/null", sudo=True, check=False)
        if not iptables_check.ok:
            ssh.run(f"iptables -A INPUT -p tcp --dport {port} -j ACCEPT", sudo=True, check=False)
            capture("iptables rule added")

        # Check firewall-cmd
        has_firewalld = ssh.run("command -v firewall-cmd >/dev/null 2>&1", sudo=True, check=False)
        if has_firewalld.ok:
            ssh.run(f"firewall-cmd --permanent --add-port={port}/tcp", sudo=True, check=False)
            ssh.run("firewall-cmd --reload", sudo=True, check=False)
            capture("firewalld rule added")

        # Verify no cloud-level firewall is blocking
        capture("local firewall configuration complete")
