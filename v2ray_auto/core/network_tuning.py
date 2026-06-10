"""Network tuning helpers."""

from __future__ import annotations

from .models import LogSink
from .ssh import SSHExecutor

SYSCTL_FILE = "/etc/sysctl.d/99-v2ray-auto.conf"


class NetworkTuning:
    def __init__(self, ssh: SSHExecutor, log: LogSink | None = None):
        self.ssh = ssh
        self.log = log or (lambda message: None)

    def enable_bbr_if_available(self) -> None:
        available = self.ssh.run("sysctl -n net.ipv4.tcp_available_congestion_control", check=False)
        if "bbr" not in available.stdout.split():
            self.log("BBR not available; skip TCP tuning")
            return

        current = self.ssh.run("sysctl -n net.ipv4.tcp_congestion_control", check=False)
        if current.stdout.strip() == "bbr":
            self.log("BBR already enabled; skip TCP tuning")
            return

        self.log("BBR available; enabling fq + bbr")
        content = "net.core.default_qdisc=fq\nnet.ipv4.tcp_congestion_control=bbr\n"
        remote_tmp = "/tmp/v2ray-auto-sysctl.conf"
        self.ssh.put_text(remote_tmp, content)
        self.ssh.run(f"mv {remote_tmp} {SYSCTL_FILE}", sudo=True)
        self.ssh.run(f"sysctl -p {SYSCTL_FILE}", sudo=True, check=False)
