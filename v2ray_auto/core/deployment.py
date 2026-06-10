"""Deployment orchestration for one-click setup on empty servers."""

from __future__ import annotations

import hashlib
import json

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
            NetworkTuning(ssh, log=capture).enable_bbr_if_available()

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
                self._restart_service(ssh, generated)
            else:
                capture("config unchanged; skip service restart")
            self._open_firewall(ssh, generated.port)

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
        ssh.run(f"chmod 600 {config_path}", sudo=True)
        return True

    def _remote_file_sha256(self, ssh: SSHExecutor, config_path: str) -> str | None:
        result = ssh.run(f"test -f {config_path} && sha256sum {config_path} | awk '{{print $1}}'", sudo=True, check=False)
        value = result.stdout.strip()
        return value or None

    def _restart_service(self, ssh: SSHExecutor, generated: GeneratedConfig) -> None:
        ssh.run("systemctl daemon-reload", sudo=True)
        service_pattern = generated.service_name.replace(".", "\\.")
        result = ssh.run(f"systemctl list-unit-files | grep -E '^{service_pattern}'", sudo=True, check=False)
        if not result.stdout.strip():
            raise RuntimeError(f"{generated.service_name} was not found after bootstrap install")
        service_unit = generated.service_name.removesuffix(".service")
        ssh.run(f"systemctl enable {service_unit}", sudo=True)
        ssh.run(f"systemctl restart {service_unit}", sudo=True)
        ssh.run(f"systemctl is-active {service_unit}", sudo=True)

    def _open_firewall(self, ssh: SSHExecutor, port: int) -> None:
        commands = [
            f"command -v ufw >/dev/null 2>&1 && ufw allow {port}/tcp || true",
            f"command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --permanent --add-port={port}/tcp && firewall-cmd --reload || true",
            f"command -v iptables >/dev/null 2>&1 && iptables -C INPUT -p tcp --dport {port} -j ACCEPT 2>/dev/null || iptables -A INPUT -p tcp --dport {port} -j ACCEPT || true",
        ]
        for command in commands:
            ssh.run(command, sudo=True, check=False)
