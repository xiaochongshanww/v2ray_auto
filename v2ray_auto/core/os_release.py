"""Remote Linux distribution detection."""

from __future__ import annotations

from .models import LinuxFamily


def parse_os_release(content: str) -> tuple[str, LinuxFamily]:
    values: dict[str, str] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')

    distro_id = values.get("ID", "unknown").lower()
    like = values.get("ID_LIKE", "").lower()
    haystack = f"{distro_id} {like}"

    if any(item in haystack for item in ("debian", "ubuntu")):
        return distro_id, "debian"
    if any(item in haystack for item in ("rhel", "centos", "fedora", "rocky", "almalinux")):
        return distro_id, "redhat"
    return distro_id, "unknown"
