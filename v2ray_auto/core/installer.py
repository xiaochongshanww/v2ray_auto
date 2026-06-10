"""Remote bootstrap installers for empty servers."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import CoreName, LinuxFamily, LogSink
from .ssh import SSHExecutor

DEFAULT_XRAY_INSTALL_SCRIPT_URL = "https://github.com/XTLS/Xray-install/raw/main/install-release.sh"
DEFAULT_V2RAY_INSTALL_SCRIPT_URL = "https://raw.githubusercontent.com/v2fly/fhs-install-v2ray/master/install-release.sh"


@dataclass(frozen=True)
class RealityKeyPair:
    private_key: str
    public_key: str


def package_bootstrap_command(family: LinuxFamily) -> str:
    if family == "debian":
        return "apt-get update && apt-get install -y curl ca-certificates unzip"
    if family == "redhat":
        return "yum install -y curl ca-certificates unzip"
    raise RuntimeError("unsupported linux family for automatic bootstrap")


class Installer:
    def __init__(
        self,
        ssh: SSHExecutor,
        *,
        core: CoreName = "xray",
        xray_install_script_url: str = DEFAULT_XRAY_INSTALL_SCRIPT_URL,
        v2ray_install_script_url: str = DEFAULT_V2RAY_INSTALL_SCRIPT_URL,
        log: LogSink | None = None,
    ):
        self.ssh = ssh
        self.core = core
        self.xray_install_script_url = xray_install_script_url
        self.v2ray_install_script_url = v2ray_install_script_url
        self.log = log or (lambda message: None)

    @property
    def service_name(self) -> str:
        return "xray.service" if self.core == "xray" else "v2ray.service"

    @property
    def binary_name(self) -> str:
        return "xray" if self.core == "xray" else "v2ray"

    def ensure_installed(self, family: LinuxFamily) -> None:
        if self.has_service():
            self.log(f"{self.service_name} already exists; skip bootstrap install")
            return

        self.log(f"{self.service_name} not found; bootstrap install will run")
        self.ensure_basic_packages(family)
        self.ensure_swap_for_small_server()
        self.install_core()

        if not self.has_service():
            raise RuntimeError(f"{self.service_name} still not found after bootstrap install")

    def has_service(self) -> bool:
        service = re.escape(self.service_name)
        result = self.ssh.run(f"systemctl list-unit-files | grep -E '^{service}'", sudo=True, check=False)
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

    def install_core(self) -> None:
        script_url = self.xray_install_script_url if self.core == "xray" else self.v2ray_install_script_url
        remote_script = f"/tmp/v2ray-auto-install-{self.binary_name}.sh"
        self.ssh.run(f"curl --connect-timeout 10 --retry 3 --retry-delay 2 -fsSL {script_url} -o {remote_script}", sudo=True)
        self.ssh.run(f"bash {remote_script}", sudo=True)

    def generate_reality_key_pair(self) -> RealityKeyPair:
        if self.core != "xray":
            raise RuntimeError("REALITY key pair generation requires xray core")
        result = self.ssh.run("xray x25519", sudo=True)
        private_key = self._extract_key(result.stdout, "Private key")
        public_key = self._extract_key(result.stdout, "Public key")
        return RealityKeyPair(private_key=private_key, public_key=public_key)

    @staticmethod
    def _extract_key(output: str, label: str) -> str:
        pattern = rf"{re.escape(label)}:\s*([A-Za-z0-9_-]+)"
        match = re.search(pattern, output)
        if not match:
            raise RuntimeError(f"failed to parse {label} from xray output")
        return match.group(1)
