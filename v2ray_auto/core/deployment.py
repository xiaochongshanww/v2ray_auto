"""Deployment orchestration for one-click setup on empty servers."""

from __future__ import annotations

import json

from .installer import Installer
from .models import DeploymentRequest, DeploymentResult, LogSink
from .os_release import parse_os_release
from .settings import Settings
from .ssh import SSHExecutor
from .vmess import build_vmess_config


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

            Installer(ssh, log=capture).ensure_installed(family)

            vmess = build_vmess_config(request.host)
            remote_config_path = self._resolve_config_path(ssh)
            self._prepare_config_dir(ssh, remote_config_path)
            self._upload_config(ssh, remote_config_path, vmess.server_config)
            self._restart_service(ssh)
            self._open_firewall(ssh, vmess.listen_port)

        return DeploymentResult(
            server=request.host,
            port=vmess.listen_port,
            uuid=vmess.client_id,
            vmess_url=vmess.vmess_url,
            remote_config_path=remote_config_path,
            logs=logs,
        )

    def _detect_os(self, ssh: SSHExecutor) -> tuple[str, str]:
        result = ssh.run("cat /etc/os-release", check=True)
        return parse_os_release(result.stdout)

    def _resolve_config_path(self, ssh: SSHExecutor) -> str:
        candidates = [
            "/usr/local/etc/v2ray/config.json",
            "/etc/v2ray/config.json",
        ]
        for path in candidates:
            result = ssh.run(f"test -e {path} && echo {path}", check=False)
            if result.stdout.strip():
                return path
        return candidates[0]

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

    def _restart_service(self, ssh: SSHExecutor) -> None:
        ssh.run("systemctl daemon-reload", sudo=True)
        result = ssh.run("systemctl list-unit-files | grep -E '^v2ray\\.service'", sudo=True, check=False)
        if not result.stdout.strip():
            raise RuntimeError("v2ray.service was not found after bootstrap install")
        ssh.run("systemctl enable v2ray", sudo=True)
        ssh.run("systemctl restart v2ray", sudo=True)
        ssh.run("systemctl is-active v2ray", sudo=True)

    def _open_firewall(self, ssh: SSHExecutor, port: int) -> None:
        commands = [
            f"command -v ufw >/dev/null 2>&1 && ufw allow {port}/tcp || true",
            f"command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --permanent --add-port={port}/tcp && firewall-cmd --reload || true",
            f"command -v iptables >/dev/null 2>&1 && iptables -C INPUT -p tcp --dport {port} -j ACCEPT 2>/dev/null || iptables -A INPUT -p tcp --dport {port} -j ACCEPT || true",
        ]
        for command in commands:
            ssh.run(command, sudo=True, check=False)
