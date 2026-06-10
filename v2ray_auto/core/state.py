"""Remote deployment state persistence."""

from __future__ import annotations

import json
import secrets
import uuid
from dataclasses import dataclass
from typing import Any

from .installer import Installer, RealityKeyPair
from .ssh import SSHExecutor

STATE_PATH = "/usr/local/etc/v2ray-auto/state.json"


@dataclass(frozen=True)
class RealityProfileState:
    private_key: str
    public_key: str
    client_id: str
    short_id: str


class RemoteStateStore:
    def __init__(self, ssh: SSHExecutor, *, path: str = STATE_PATH):
        self.ssh = ssh
        self.path = path

    def load(self) -> dict[str, Any]:
        result = self.ssh.run(f"test -f {self.path} && cat {self.path}", sudo=True, check=False)
        raw = result.stdout.strip()
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def save(self, state: dict[str, Any]) -> None:
        content = json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True)
        tmp_path = "/tmp/v2ray-auto-state.json"
        self.ssh.put_text(tmp_path, content)
        directory = self.path.rsplit("/", 1)[0]
        self.ssh.run(f"mkdir -p {directory}", sudo=True)
        self.ssh.run(f"mv {tmp_path} {self.path}", sudo=True)
        self.ssh.run(f"chmod 600 {self.path}", sudo=True)

    def get_or_create_reality_profile_state(self, installer: Installer) -> RealityProfileState:
        state = self.load()
        profile_state = state.get("vless-reality-vision") or {}
        required = ["private_key", "public_key", "client_id", "short_id"]
        if all(profile_state.get(key) for key in required):
            return RealityProfileState(
                private_key=profile_state["private_key"],
                public_key=profile_state["public_key"],
                client_id=profile_state["client_id"],
                short_id=profile_state["short_id"],
            )

        key_pair: RealityKeyPair = installer.generate_reality_key_pair()
        created = RealityProfileState(
            private_key=key_pair.private_key,
            public_key=key_pair.public_key,
            client_id=str(uuid.uuid4()),
            short_id=secrets.token_hex(8),
        )
        state["vless-reality-vision"] = {
            "private_key": created.private_key,
            "public_key": created.public_key,
            "client_id": created.client_id,
            "short_id": created.short_id,
        }
        self.save(state)
        return created
