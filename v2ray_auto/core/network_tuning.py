"""Network tuning helpers."""

from __future__ import annotations

from .models import LogSink
from .ssh import SSHExecutor

SYSCTL_FILE = "/etc/sysctl.d/99-v2ray-auto.conf"


class NetworkTuning:
    def __init__(self, ssh: SSHExecutor, log: LogSink | None = None):
        self.ssh = ssh
        self.log = log or (lambda message: None)

    def _bbr_available(self) -> bool:
        self.ssh.run("modprobe tcp_bbr", sudo=True, check=False)
        available = self.ssh.run("sysctl -n net.ipv4.tcp_available_congestion_control", check=False)
        return "bbr" in available.stdout.split()

    def enable_bbr_if_available(self) -> None:
        if not self._bbr_available():
            self.log("BBR not available; skip TCP tuning")
            return

        current = self.ssh.run("sysctl -n net.ipv4.tcp_congestion_control", check=False)
        if current.stdout.strip() == "bbr":
            self.log("BBR already enabled; skip TCP tuning")
            return

        self.log("BBR available; enabling fq + bbr")
        content = (
            "net.core.default_qdisc=fq\n"
            "net.ipv4.tcp_congestion_control=bbr\n"
        )
        remote_tmp = "/tmp/v2ray-auto-sysctl.conf"
        self.ssh.put_text(remote_tmp, content)
        self.ssh.run(f"mv {remote_tmp} {SYSCTL_FILE}", sudo=True)
        self.ssh.run(f"sysctl -p {SYSCTL_FILE}", sudo=True, check=False)

    def tune_tcp_buffers(self) -> None:
        self.log("tuning TCP buffer sizes for long-distance links")
        current_content = self.ssh.run(f"test -f {SYSCTL_FILE} && cat {SYSCTL_FILE} || true", check=False)
        has_tcp_tuning = "tcp_rmem" in (current_content.stdout or "")
        if has_tcp_tuning:
            self.log("TCP buffers already tuned; skip")
            return

        content = (
            "\n# TCP buffer tuning for high-latency links\n"
            "net.core.rmem_max = 134217728\n"
            "net.core.wmem_max = 134217728\n"
            "net.ipv4.tcp_rmem = 4096 87380 134217728\n"
            "net.ipv4.tcp_wmem = 4096 65536 134217728\n"
        )
        remote_tmp = "/tmp/v2ray-auto-tcp.conf"
        self.ssh.put_text(remote_tmp, content)
        self.ssh.run(f"cat {remote_tmp} >> {SYSCTL_FILE}", sudo=True)
        self.ssh.run(f"rm {remote_tmp}", sudo=True)
        self.ssh.run(f"sysctl -p {SYSCTL_FILE}", sudo=True, check=False)
        self.log("TCP buffers tuned")
