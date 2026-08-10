"""Local sidecar launcher for the Electron desktop app.

Binds a Flask + Socket.IO server to 127.0.0.1 on a random port, prints a
single JSON line with the port to stdout so the Electron main process can
discover it, then serves until terminated.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import sys
import threading
from pathlib import Path

def _find_package_root() -> Path:
    here = Path(__file__).resolve()
    for cand in (here.parents[1], here.parents[2]):
        if (cand / "v2ray_auto").is_dir():
            return cand
    return here.parents[1]


PACKAGE_ROOT = _find_package_root()
sys.path.insert(0, str(PACKAGE_ROOT))


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main() -> int:
    port = int(os.environ.get("V2RAY_DESKTOP_PORT") or "0") or find_free_port()

    from v2ray_auto.api.app import create_app
    from v2ray_auto.core.settings import Settings

    settings = Settings(
        allowed_origins=("*",),
        default_remote_dir=os.environ.get("V2RAY_AUTO_DEFAULT_REMOTE_DIR", "/opt/v2ray_auto"),
        command_timeout=int(os.environ.get("V2RAY_AUTO_COMMAND_TIMEOUT", "900")),
    )
    app, socketio = create_app(settings)

    shutdown_event = threading.Event()

    def handle_signal(signum, _frame):
        print("shutting down", flush=True)
        shutdown_event.set()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    print(json.dumps({"ready": True, "port": port, "pid": os.getpid()}), flush=True)
    socketio.run(
        app,
        host="127.0.0.1",
        port=port,
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
        log_output=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
