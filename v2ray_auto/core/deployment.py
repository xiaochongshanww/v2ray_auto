"""Deployment orchestration for one-click setup on empty servers."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections.abc import Callable

from .errors import (
    DeploymentError,
    OperationCancelledError,
    PortOccupiedError,
    ServiceStartError,
    UnsupportedProfileError,
)
from .installer import Installer
from .models import (
    CoreName,
    DeploymentRequest,
    DeploymentResult,
    GeneratedConfig,
    LogSink,
    UninstallRequest,
    UninstallResult,
)
from .network_tuning import NetworkTuning
from .os_release import parse_os_release
from .profiles import build_config_for_request
from .settings import Settings
from .ssh import SSHExecutor
from .state import STATE_PATH, RemoteStateStore

# Per-profile paths and service names for cleanup. Kept in sync with the
# config builders in core/profiles.
PROFILE_CLEANUP = {
    "vless-reality-vision": {
        "core": "xray",
        "service_name": "xray.service",
        "config_dir": "/usr/local/etc/xray",
    },
    "vmess-tcp-legacy": {
        "core": "v2ray",
        "service_name": "v2ray.service",
        "config_dir": "/usr/local/etc/v2ray",
    },
}


class DeploymentService:
    def __init__(
        self,
        settings: Settings,
        log: LogSink | None = None,
        cancel_event: threading.Event | None = None,
    ):
        self.settings = settings
        self.log = log or (lambda message: None)
        self.cancel_event = cancel_event

    def uninstall(
        self,
        request: UninstallRequest,
        *,
        ssh_factory: Callable[[UninstallRequest, LogSink, int], SSHExecutor] | None = None,
    ) -> UninstallResult:
        """Tear down a previously deployed instance.

        Idempotent: missing services / files / rules are treated as already
        removed rather than errors. The core binary (xray/v2ray) itself is
        intentionally kept, since it may be shared with other uses.
        """
        request.validate()
        cleanup = PROFILE_CLEANUP.get(request.profile)
        if not cleanup:
            raise UnsupportedProfileError(detail=f"unsupported profile: {request.profile}")

        service_name = cleanup["service_name"]
        service_unit = service_name.removesuffix(".service")
        config_dir = cleanup["config_dir"]
        port = request.listen_port or self._default_port_for(request.profile)

        logs: list[str] = []

        def capture(message: str) -> None:
            if message:
                logs.append(message)
                self.log(message)

        stopped_service = False
        removed_config = False
        removed_state = False
        closed_firewall = False

        factory = ssh_factory or (
            lambda req, log, timeout: SSHExecutor(req, log=log, timeout=timeout, cancel_event=self.cancel_event)
        )
        with factory(request, capture, self.settings.command_timeout) as ssh:
            # 1. Stop and disable the service. Each step is idempotent and
            # independent so a crash part-way through is fully recoverable:
            # if the service was stopped but the unit never disabled, a retry
            # still disables it.
            active = ssh.run(f"systemctl is-active {service_unit}", sudo=True, check=False)
            if active.ok:
                ssh.run(f"systemctl stop {service_unit}", sudo=True, check=False)
                stopped_service = True
                capture(f"stopped {service_name}")
            else:
                capture(f"{service_name} not active; skip service stop")

            enabled = ssh.run(f"systemctl is-enabled {service_unit}", sudo=True, check=False)
            if enabled.ok:
                ssh.run(f"systemctl disable {service_unit}", sudo=True, check=False)
                ssh.run("systemctl daemon-reload", sudo=True, check=False)
                capture(f"disabled {service_name}")
            else:
                capture(f"{service_name} not enabled; skip service disable")

            # 2. Remove the config directory.
            exists = ssh.run(f"test -d {config_dir} && echo yes || echo no", sudo=True, check=False)
            if "yes" in exists.stdout.lower():
                ssh.run(f"rm -rf {config_dir}", sudo=True, check=False)
                removed_config = True
                capture(f"removed config directory {config_dir}")
            else:
                capture(f"config directory {config_dir} not found; skip")

            # 3. Remove the v2ray-auto state file.
            state_dir = STATE_PATH.rsplit("/", 1)[0]
            state_exists = ssh.run(f"test -d {state_dir} && echo yes || echo no", sudo=True, check=False)
            if "yes" in state_exists.stdout.lower():
                ssh.run(f"rm -rf {state_dir}", sudo=True, check=False)
                removed_state = True
                capture(f"removed state directory {state_dir}")
            else:
                capture(f"state directory {state_dir} not found; skip")

            # 4. Close the firewall rule for the deployed port (idempotent).
            closed_firewall = self._close_firewall(ssh, port, capture)

        return UninstallResult(
            server=request.host,
            profile=request.profile,
            removed_config=removed_config,
            removed_state=removed_state,
            stopped_service=stopped_service,
            closed_firewall=closed_firewall,
            logs=logs,
        )

    @staticmethod
    def _default_port_for(profile: str) -> int:
        return 443 if profile == "vless-reality-vision" else 10086

    def _close_firewall(self, ssh: SSHExecutor, port: int, capture: LogSink, *, ignore_cancel: bool = False) -> bool:
        """Remove the inbound firewall rule added by _open_firewall.

        Returns True if any rule was found and removed.
        """
        changed = False
        capture(f"closing port {port}/tcp in firewall")

        ufw_active = ssh.run("ufw status 2>/dev/null | head -1", sudo=True, check=False, ignore_cancel=ignore_cancel)
        if "active" in ufw_active.stdout.lower():
            result = ssh.run(f"ufw status | grep -q {port}/tcp", sudo=True, check=False, ignore_cancel=ignore_cancel)
            if result.ok:
                ssh.run(f"ufw delete allow {port}/tcp", sudo=True, check=False, ignore_cancel=ignore_cancel)
                capture("ufw rule removed")
                changed = True

        iptables_check = ssh.run(
            f"iptables -C INPUT -p tcp --dport {port} -j ACCEPT 2>/dev/null",
            sudo=True,
            check=False,
            ignore_cancel=ignore_cancel,
        )
        if iptables_check.ok:
            ssh.run(
                f"iptables -D INPUT -p tcp --dport {port} -j ACCEPT",
                sudo=True,
                check=False,
                ignore_cancel=ignore_cancel,
            )
            capture("iptables rule removed")
            changed = True

        has_firewalld = ssh.run(
            "command -v firewall-cmd >/dev/null 2>&1", sudo=True, check=False, ignore_cancel=ignore_cancel
        )
        if has_firewalld.ok:
            result = ssh.run(
                f"firewall-cmd --permanent --query-port={port}/tcp", sudo=True, check=False, ignore_cancel=ignore_cancel
            )
            if result.ok:
                ssh.run(
                    f"firewall-cmd --permanent --remove-port={port}/tcp",
                    sudo=True,
                    check=False,
                    ignore_cancel=ignore_cancel,
                )
                ssh.run("firewall-cmd --reload", sudo=True, check=False, ignore_cancel=ignore_cancel)
                capture("firewalld rule removed")
                changed = True

        if not changed:
            capture("no matching firewall rule found; skip")
        return changed

    def _rollback(
        self,
        ssh: SSHExecutor,
        profile: str,
        generated: GeneratedConfig | None,
        completed_steps: list[str],
        capture: LogSink,
    ) -> None:
        """Undo completed deploy steps after a cancellation, in reverse order.

        Only steps that were explicitly completed are reverted. The core binary
        and sysctl tuning are kept (matching uninstall semantics: they are
        additive changes that are cheap to keep and expensive to safely undo).
        """
        cleanup = PROFILE_CLEANUP.get(profile)
        if not cleanup:
            capture("WARNING: cannot roll back unknown profile")
            return

        service_name = cleanup["service_name"]
        service_unit = service_name.removesuffix(".service")
        config_dir = cleanup["config_dir"]
        port = generated.port if generated else self._default_port_for(profile)

        if "firewall" in completed_steps:
            self._close_firewall(ssh, port, capture, ignore_cancel=True)

        if "service" in completed_steps:
            active = ssh.run(f"systemctl is-active {service_unit}", sudo=True, check=False, ignore_cancel=True)
            if active.ok:
                ssh.run(f"systemctl stop {service_unit}", sudo=True, check=False, ignore_cancel=True)
                capture(f"stopped {service_name}")
            enabled = ssh.run(f"systemctl is-enabled {service_unit}", sudo=True, check=False, ignore_cancel=True)
            if enabled.ok:
                ssh.run(f"systemctl disable {service_unit}", sudo=True, check=False, ignore_cancel=True)
                ssh.run("systemctl daemon-reload", sudo=True, check=False, ignore_cancel=True)
                capture(f"disabled {service_name}")

        if "config" in completed_steps:
            exists = ssh.run(f"test -d {config_dir} && echo yes || echo no", sudo=True, check=False, ignore_cancel=True)
            if "yes" in exists.stdout.lower():
                ssh.run(f"rm -rf {config_dir}", sudo=True, check=False, ignore_cancel=True)
                capture(f"removed config directory {config_dir}")

        capture("rollback complete")

    def deploy(
        self,
        request: DeploymentRequest,
        *,
        ssh_factory: Callable[[DeploymentRequest, LogSink, int], SSHExecutor] | None = None,
    ) -> DeploymentResult:
        request.validate()
        self._validate_profile(request.profile)

        logs: list[str] = []

        def capture(message: str) -> None:
            if message:
                logs.append(message)
                self.log(message)

        # Steps that have completed and can be rolled back, in execution order.
        # On cancellation we undo them in reverse so the server returns to its
        # pre-deploy state (binary and sysctl tuning are intentionally kept).
        completed_steps: list[str] = []

        factory = ssh_factory or (
            lambda req, log, timeout: SSHExecutor(req, log=log, timeout=timeout, cancel_event=self.cancel_event)
        )
        with factory(request, capture, self.settings.command_timeout) as ssh:
            generated = None
            try:
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
                    completed_steps.append("config")
                    self._validate_remote_config(ssh, generated)
                    self._restart_service(ssh, generated)
                    completed_steps.append("service")
                else:
                    capture("config unchanged; skip service restart")
                self._open_firewall(ssh, generated.port)
                completed_steps.append("firewall")
                self._assert_port_listening(ssh, generated.port, generated.service_name)

                warning = None
                if request.profile == "vless-reality-vision":
                    warning = self._verify_reality_connectivity(ssh, generated)
            except OperationCancelledError:
                capture("cancelled by user; rolling back completed steps...")
                self._rollback(ssh, request.profile, generated, completed_steps, capture)
                raise

        return DeploymentResult(
            server=request.host,
            port=generated.port,
            uuid=generated.client_id,
            client_uri=generated.client_uri,
            remote_config_path=generated.config_path,
            core=generated.core,
            profile=generated.profile,
            service_name=generated.service_name,
            warning=warning,
            logs=logs,
        )

    def _verify_reality_connectivity(self, ssh: SSHExecutor, generated: GeneratedConfig) -> str | None:
        """Loopback self-test after deploy.

        Runs a temporary xray client on the server that dials the freshly
        installed inbound over loopback. If the REALITY handshake fails (e.g.
        the fronting target `dest` rejects the server's TLS handshake), the
        deployed configuration is unusable and a warning is returned so the
        user can change REALITY Dest / ServerName and redeploy.
        """
        capture = self.log
        client_id = generated.client_id
        server_name = generated.metadata.get("serverName")
        public_key = generated.metadata.get("publicKey")
        short_id = generated.metadata.get("shortId")
        if not (client_id and server_name and public_key and short_id):
            capture("SKIP REALITY self-test: missing metadata")
            return None

        socks_port = self._pick_socks_port(ssh)
        client_config = {
            "log": {"loglevel": "warning"},
            "inbounds": [
                {
                    "listen": "127.0.0.1",
                    "port": socks_port,
                    "protocol": "socks",
                    "settings": {"udp": True},
                }
            ],
            "outbounds": [
                {
                    "protocol": "vless",
                    "settings": {
                        "vnext": [
                            {
                                "address": "127.0.0.1",
                                "port": generated.port,
                                "users": [
                                    {
                                        "id": client_id,
                                        "encryption": "none",
                                        "flow": "xtls-rprx-vision",
                                    }
                                ],
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "tcp",
                        "security": "reality",
                        "realitySettings": {
                            "serverName": server_name,
                            "fingerprint": "chrome",
                            "publicKey": public_key,
                            "shortId": short_id,
                        },
                    },
                }
            ],
        }

        client_path = "/tmp/v2ray-auto-selfcheck-client.json"
        log_path = "/tmp/v2ray-auto-selfcheck-client.log"
        capture("running REALITY connectivity self-test on the server...")
        try:
            ssh.put_text(client_path, json.dumps(client_config, indent=2))
            ssh.run(
                f"nohup xray run -c {client_path} > {log_path} 2>&1 < /dev/null &",
                sudo=True,
                check=False,
            )
            time.sleep(3)
            probe = ssh.run(
                f"curl -s -o /dev/null -w '%{{http_code}}' "
                f"--socks5-hostname 127.0.0.1:{socks_port} --max-time 10 "
                f"https://www.gstatic.com/generate_204",
                sudo=True,
                check=False,
            )
            code = probe.stdout.strip()
            if code in ("204", "200", "301", "302"):
                capture(f"REALITY self-test OK (HTTP {code})")
                return None
            capture(f"WARNING: REALITY self-test failed (HTTP {code or 'no response'})")
            capture(
                "The server could not complete a REALITY handshake to itself with the current "
                "configuration. The most likely cause is that the fronting target (REALITY Dest) "
                "rejects the server's TLS handshake."
            )
            return (
                "REALITY 自检未通过：服务器无法完成 REALITY 握手，通常是因为 REALITY Dest / "
                f"ServerName（{server_name}）拒绝来自该服务器的握手。请更换 REALITY Dest 和 "
                "ServerName（例如 www.apple.com / www.google.com）后重新部署。"
            )
        finally:
            ssh.run(f"pkill -f {client_path} >/dev/null 2>&1 || true", sudo=True, check=False)
            ssh.run(f"rm -f {client_path} {log_path} >/dev/null 2>&1 || true", sudo=True, check=False)

    def _pick_socks_port(self, ssh: SSHExecutor) -> int:
        capture = self.log
        for port in range(18080, 18100):
            result = ssh.run(f"ss -ltn '( sport = :{port} )' 2>/dev/null | tail -n +2", sudo=True, check=False)
            if not result.stdout.strip():
                capture(f"self-test socks port: {port}")
                return port
        raise DeploymentError("REALITY 自检失败：服务器上无可用端口", detail="no free port for REALITY self-test")

    def _core_for_profile(self, profile: str) -> CoreName:
        return "v2ray" if profile == "vmess-tcp-legacy" else "xray"

    def _validate_profile(self, profile: str) -> None:
        valid = {"vless-reality-vision", "vmess-tcp-legacy"}
        if profile not in valid:
            raise UnsupportedProfileError(detail=f"unsupported profile: {profile}")

    def _detect_os(self, ssh: SSHExecutor) -> tuple[str, str]:
        result = ssh.run("cat /etc/os-release", check=True)
        return parse_os_release(result.stdout)

    def _assert_port_available(self, ssh: SSHExecutor, port: int, service_name: str) -> None:
        service_unit = service_name.removesuffix(".service")
        command = f"ss -ltnp '( sport = :{port} )' 2>/dev/null | grep -v {service_unit} | tail -n +2"
        result = ssh.run(command, sudo=True, check=False)
        if result.stdout.strip():
            raise PortOccupiedError(detail=f"port {port} is already occupied by another process")

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
        result = ssh.run(
            f"test -f {config_path} && sha256sum {config_path} | awk '{{print $1}}'", sudo=True, check=False
        )
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
            raise ServiceStartError(detail=f"{generated.service_name} was not found after bootstrap install")
        service_unit = generated.service_name.removesuffix(".service")
        ssh.run(f"systemctl enable {service_unit}", sudo=True)
        ssh.run(f"systemctl restart {service_unit}", sudo=True)
        result = ssh.run(f"systemctl is-active {service_unit}", sudo=True, check=False)
        if not result.ok:
            journal = ssh.run(f"journalctl -u {service_unit} --no-pager -n 20", sudo=True, check=False)
            capture(f"service is {result.stdout.strip()}")
            capture(f"journalctl ({service_unit}):\n{journal.stdout.strip()}")
            raise ServiceStartError(detail=f"{generated.service_name} failed to start")

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
        iptables_check = ssh.run(
            f"iptables -C INPUT -p tcp --dport {port} -j ACCEPT 2>/dev/null", sudo=True, check=False
        )
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
