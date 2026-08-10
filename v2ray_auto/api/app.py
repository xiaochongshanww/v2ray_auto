"""Flask API entrypoint for the refactored service."""

from __future__ import annotations

import logging
import os

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO

from v2ray_auto.core.deployment import DeploymentService
from v2ray_auto.core.models import DeploymentRequest
from v2ray_auto.core.settings import Settings, load_settings

_LOG_DIR = os.environ.get(
    "V2RAY_AUTO_LOG_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "logs"),
)


def _setup_file_logger(name: str) -> logging.Logger:
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    os.makedirs(_LOG_DIR, exist_ok=True)
    handler = logging.FileHandler(os.path.join(_LOG_DIR, "deploy.log"), encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
    return log


_file_log = _setup_file_logger("v2ray_auto.api")


def _optional_int(value):
    if value in (None, ""):
        return None
    return int(value)


def create_app(settings: Settings | None = None) -> tuple[Flask, SocketIO]:
    settings = settings or load_settings()
    app = Flask(__name__)
    CORS(app, origins=list(settings.allowed_origins))
    socketio = SocketIO(app, cors_allowed_origins=list(settings.allowed_origins), async_mode="threading")

    def emit_log(message: str) -> None:
        _file_log.info("%s", message)
        socketio.emit("process_update", {"message": message})

    def has_valid_key() -> bool:
        if not settings.auth_enabled:
            return True
        return request.headers.get("X-API-Key", "") == settings.api_key

    @app.get("/")
    def index():
        return jsonify({
            "service": "v2ray_auto",
            "version": "0.2.0-refactor",
            "endpoints": {
                "health": "GET /health",
                "deploy": "POST /api/deploy",
            },
        })

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/api/deploy")
    def deploy():
        if not has_valid_key():
            return jsonify({"error": "unauthorized"}), 401

        payload = request.get_json(silent=True) or {}
        target = payload.get("host") or payload.get("serverIp", "?")
        _file_log.info("deploy request: host=%s profile=%s", target, payload.get("profile", "?"))
        try:
            deploy_request = DeploymentRequest(
                host=payload.get("host") or payload.get("serverIp"),
                port=int(payload.get("port") or payload.get("serverPort") or 22),
                username=payload.get("username"),
                password=payload.get("password"),
                private_key_path=payload.get("privateKeyPath") or payload.get("private_key_path"),
                email=payload.get("email"),
                remote_dir=payload.get("remoteDir") or settings.default_remote_dir,
                install_warp=bool(payload.get("installWarp", False)),
                profile=payload.get("profile") or "vless-reality-vision",
                listen_port=_optional_int(payload.get("listenPort") or payload.get("listen_port")),
                reality_server_name=payload.get("realityServerName") or payload.get("reality_server_name") or "www.microsoft.com",
                reality_dest=payload.get("realityDest") or payload.get("reality_dest") or "www.microsoft.com:443",
            )
            result = DeploymentService(settings, log=emit_log).deploy(deploy_request)
            socketio.emit("configuration_complete", {"result": result.client_uri})
            return jsonify(
                {
                    "server": result.server,
                    "port": result.port,
                    "uuid": result.uuid,
                    "clientUri": result.client_uri,
                    "vmessUrl": result.vmess_url,
                    "remoteConfigPath": result.remote_config_path,
                    "core": result.core,
                    "profile": result.profile,
                    "serviceName": result.service_name,
                }
            )
        except Exception as exc:
            _file_log.error("deploy failed: %s", exc)
            emit_log(str(exc))
            return jsonify({"error": str(exc)}), 400

    return app, socketio


app, socketio = create_app()
