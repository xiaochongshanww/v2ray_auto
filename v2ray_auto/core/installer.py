"""Remote bootstrap installer for empty servers."""

from __future__ import annotations

from .models import LinuxFamily, LogSink
from .ssh import SSHExecutor

DEFAULT_V2RAY_INSTALL_SCRIPT_URL = "https://raw.githubusercontent.com/v2fly/fhs-install-v2ray/master/install-release.sh"


def package_bootstrap_command(family: LinuxFamily) -> str:
    if family == "debian":
        return "apt-get update && apt-get install -y curl ca-certificates unzip"
    if family == "redhat":
        return "yum install -y curl ca-certificates unzip"
    raise RuntimeError("unsupported linux family for automatic bootstrap")


class Installer:
    def __init__(self, ssh: SSHExecutor, *, install_script_url: str = DEFAULT_V2RAY_INSTALL_SCRIPT_URL, log: LogSink | None = None):
        self.ssh = ssh
        self.install_script_url = install_script_url
        self.log = log or (lambda message: None)

    def ensure_installed(self, family: LinuxFamily) -> None:
        if self.has_v2ray_service():
            self.log("v2ray.service already exists; skip bootstrap install")
            return

        self.log("v2ray.service not found; bootstrap install will run")
        self.ensure_basic_packages(family)
        self.ensure_swap_for_small_server()
        self.install_v2ray()

        if not self.has_v2ray_service():
            raise RuntimeError("v2ray.service still not found after bootstrap install")

    def has_v2ray_service(self) -> bool:
        result = self.ssh.run("systemctl list-unit-files | grep -E '^v2ray\\.service'", sudo=True, check=False)
        return bool(result.stdout.strip())

    def ensure_basic_packages(self, family: LinuxFamily) -> None:
        self.ssh.run(package_bootstrap_command(family), sudo=True)

    def ensure_swap_for_small_server(self) -> None:
        memory_result = self.ssh.run("free -m | awk '/Mem:/ {print $7}'", check=False)
        try:
            available_mb = int(memory_result.stdout.strip() or "0")
        except ValueError:
            available_mb = 0

        swap_result = self.ssh.run("swapon --show | wc -l", check=False)
        try:
            swap_lines = int(swap_result.stdout.strip() or "0")
        except ValueError:
            swap_lines = 0

        if available_mb >= 128 or swap_lines > 0:
            self.log("swap bootstrap skipped")
            return

        self.log("low memory detected; creating 1G swapfile")
        self.ssh.run("fallocate -l 1G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=1024", sudo=True)
        self.ssh.run("chmod 600 /swapfile", sudo=True)
        self.ssh.run("mkswap /swapfile", sudo=True)
        self.ssh.run("swapon /swapfile", sudo=True)
        self.ssh.run("grep -q '^/swapfile ' /etc/fstab || echo '/swapfile swap swap defaults 0 0' >> /etc/fstab", sudo=True)

    def install_v2ray(self) -> None:
        remote_script = "/tmp/v2ray-auto-install-release.sh"
        self.ssh.run(f"curl -fsSL {self.install_script_url} -o {remote_script}", sudo=True)
        self.ssh.run(f"bash {remote_script}", sudo=True)
