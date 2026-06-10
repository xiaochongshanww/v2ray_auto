"""Flask API entrypoint for the refactored service."""

from __future__ import annotations

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO

from v2ray_auto.core.deployment import DeploymentService
from v2ray_auto.core.models import DeploymentRequest
from v2ray_auto.core.settings import Settings, load_settings


def create_app(settings: Settings | None = None) -> tuple[Flask, SocketIO]:
    settings = settings or load_settings()
    app = Flask(__name__)
    CORS(app, origins=list(settings.allowed_origins))
    socketio = SocketIO(app, cors_allowed_origins=list(settings.allowed_origins), async_mode="threading")

    def emit_log(message: str) -> None:
        socketio.emit("process_update", {"message": message})

    def has_valid_key() -> bool:
        return request.headers.get("X-API-Key", "") == settings.api_key

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/api/deploy")
    def deploy():
        if not has_valid_key():
            return jsonify({"error": "unauthorized"}), 401

        payload = request.get_json(silent=True) or {}
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
                listen_port=payload.get("listenPort") or payload.get("listen_port"),
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
            emit_log(str(exc))
            return jsonify({"error": str(exc)}), 400

    return app, socketio


app, socketio = create_app()
