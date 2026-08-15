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


def bind_listener(preferred: int = 0) -> tuple[socket.socket, int]:
    """Bind a listening socket, preferring ``preferred`` port.

    If the preferred port is unavailable (e.g. already in use) a random
    free port is chosen instead. The socket is returned already listening
    so there is no race between picking a port and serving on it.
    """
    for port in (preferred, 0):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
            sock.listen(128)
            return sock, sock.getsockname()[1]
        except OSError:
            sock.close()
    raise RuntimeError("unable to bind any local port")


def main() -> int:
    preferred = int(os.environ.get("V2RAY_DESKTOP_PORT") or "0")

    from v2ray_auto.api.app import create_app
    from v2ray_auto.core.settings import Settings

    settings = Settings(
        allowed_origins=("*",),
        default_remote_dir=os.environ.get("V2RAY_AUTO_DEFAULT_REMOTE_DIR", "/opt/v2ray_auto"),
        command_timeout=int(os.environ.get("V2RAY_AUTO_COMMAND_TIMEOUT", "900")),
    )
    app, socketio = create_app(settings)

    listener, port = bind_listener(preferred)

    shutdown_event = threading.Event()

    def handle_signal(signum, _frame):
        print("shutting down", flush=True)
        shutdown_event.set()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    print(json.dumps({"ready": True, "port": port, "pid": os.getpid()}), flush=True)

    from werkzeug.serving import make_server

    server = make_server("127.0.0.1", port, app, threaded=True, fd=listener.fileno())
    try:
        server.serve_forever()
    finally:
        listener.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
