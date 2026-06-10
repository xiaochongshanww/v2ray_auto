"""Deployment orchestration for one-click setup on empty servers."""

from __future__ import annotations

import json

from .installer import Installer
from .models import CoreName, DeploymentRequest, DeploymentResult, GeneratedConfig, LogSink
from .network_tuning import NetworkTuning
from .os_release import parse_os_release
from .profiles import build_config_for_request
from .settings import Settings
from .ssh import SSHExecutor


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
                key_pair = installer.generate_reality_key_pair()
                generated = build_config_for_request(
                    request,
                    reality_private_key=key_pair.private_key,
                    reality_public_key=key_pair.public_key,
                )
            else:
                generated = build_config_for_request(request)

            self._prepare_config_dir(ssh, generated.config_path)
            self._upload_config(ssh, generated.config_path, generated.server_config)
            self._restart_service(ssh, generated)
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

    def _prepare_config_dir(self, ssh: SSHExecutor, config_path: str) -> None:
        directory = config_path.rsplit("/", 1)[0]
        ssh.run(f"mkdir -p {directory}", sudo=True)
        ssh.run(f"test -f {config_path} && cp {config_path} {config_path}.bak.$(date +%Y%m%d%H%M%S) || true", sudo=True)

    def _upload_config(self, ssh: SSHExecutor, config_path: str, config_data: dict) -> None:
        tmp_path = f"/tmp/v2ray-auto-config-{id(config_data)}.json"
        content = json.dumps(config_data, indent=2, ensure_ascii=False)
        ssh.put_text(tmp_path, content)
        ssh.run(f"mv {tmp_path} {config_path}", sudo=True)
        ssh.run(f"chmod 600 {config_path}", sudo=True)

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
