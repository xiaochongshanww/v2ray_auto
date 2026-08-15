"""Flask API entrypoint for the refactored service."""

from __future__ import annotations

import logging
import os
import threading
from logging.handlers import TimedRotatingFileHandler

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO

from v2ray_auto.core.deployment import DeploymentService
from v2ray_auto.core.errors import DeploymentError, LockedOperationError
from v2ray_auto.core.models import DeploymentRequest, UninstallRequest
from v2ray_auto.core.settings import Settings, load_settings

_LOG_DIR = os.environ.get(
    "V2RAY_AUTO_LOG_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "logs"),
)

# Guards remote operations (deploy / uninstall). Only one may run at a time
# because they all SSH into a target server and mutate it; concurrent
# invocations would race on services, config files and firewall rules.
_remote_op_lock = threading.Lock()

# Cooperative cancellation signal for the in-flight remote operation. Set by
# POST /api/cancel; checked by the SSH executor's command loop.
_op_cancel_event = threading.Event()


def _setup_file_logger(name: str) -> logging.Logger:
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    os.makedirs(_LOG_DIR, exist_ok=True)
    handler = TimedRotatingFileHandler(
        os.path.join(_LOG_DIR, "deploy.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
    return log


_file_log = _setup_file_logger("v2ray_auto.api")


def _optional_int(value):
    if value in (None, ""):
        return None
    return int(value)


def _error_response(exc: Exception) -> tuple[dict, int]:
    """Convert an exception into a structured JSON error.

    DeploymentError subclasses carry a stable code, a user-facing message and a
    diagnostic detail. Unknown exceptions are collapsed into a generic response
    so raw tracebacks never leak to the client.
    """
    if isinstance(exc, DeploymentError):
        return {"code": exc.code, "message": exc.message, "detail": exc.detail}, exc.status_code
    return {
        "code": "internal_error",
        "message": "服务器内部错误，请查看日志了解详情",
        "detail": str(exc),
    }, 500


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
        return jsonify(
            {
                "service": "v2ray_auto",
                "version": "0.2.0-refactor",
                "endpoints": {
                    "health": "GET /health",
                    "deploy": "POST /api/deploy",
                    "uninstall": "POST /api/uninstall",
                },
            }
        )

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/api/cancel")
    def cancel():
        """Request cancellation of the in-flight deploy / uninstall."""
        if not has_valid_key():
            return jsonify({"error": "unauthorized"}), 401
        _op_cancel_event.set()
        _file_log.info("cancel requested")
        return jsonify({"status": "cancelling"})

    @app.post("/api/deploy")
    def deploy():
        if not has_valid_key():
            return jsonify({"error": "unauthorized"}), 401

        payload = request.get_json(silent=True) or {}
        target = payload.get("host") or payload.get("serverIp", "?")
        _file_log.info("deploy request: host=%s profile=%s", target, payload.get("profile", "?"))
        if not _remote_op_lock.acquire(blocking=False):
            _file_log.warning("deploy rejected: another remote operation is running")
            return jsonify(
                {
                    "code": LockedOperationError.code,
                    "message": LockedOperationError.message,
                    "detail": "another deploy or uninstall is already in progress",
                }
            ), 409
        _op_cancel_event.clear()
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
                reality_server_name=payload.get("realityServerName")
                or payload.get("reality_server_name")
                or "www.apple.com",
                reality_dest=payload.get("realityDest") or payload.get("reality_dest") or "www.apple.com:443",
            )
            result = DeploymentService(settings, log=emit_log, cancel_event=_op_cancel_event).deploy(deploy_request)
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
                    "warning": result.warning,
                }
            )
        except DeploymentError as exc:
            _file_log.error("deploy failed [%s]: %s", exc.code, exc.detail or exc.message)
            return _error_response(exc)
        except Exception as exc:
            _file_log.error("deploy failed (unexpected): %s", exc)
            return _error_response(exc)
        finally:
            _remote_op_lock.release()

    @app.post("/api/uninstall")
    def uninstall():
        if not has_valid_key():
            return jsonify({"error": "unauthorized"}), 401

        payload = request.get_json(silent=True) or {}
        target = payload.get("host") or payload.get("serverIp", "?")
        _file_log.info("uninstall request: host=%s profile=%s", target, payload.get("profile", "?"))
        if not _remote_op_lock.acquire(blocking=False):
            _file_log.warning("uninstall rejected: another remote operation is running")
            return jsonify(
                {
                    "code": LockedOperationError.code,
                    "message": LockedOperationError.message,
                    "detail": "another deploy or uninstall is already in progress",
                }
            ), 409
        _op_cancel_event.clear()
        try:
            uninstall_request = UninstallRequest(
                host=payload.get("host") or payload.get("serverIp"),
                port=int(payload.get("port") or payload.get("serverPort") or 22),
                username=payload.get("username"),
                password=payload.get("password"),
                private_key_path=payload.get("privateKeyPath") or payload.get("private_key_path"),
                profile=payload.get("profile") or "vless-reality-vision",
                listen_port=_optional_int(payload.get("listenPort") or payload.get("listen_port")),
            )
            result = DeploymentService(settings, log=emit_log, cancel_event=_op_cancel_event).uninstall(
                uninstall_request
            )
            return jsonify(
                {
                    "server": result.server,
                    "profile": result.profile,
                    "removedConfig": result.removed_config,
                    "removedState": result.removed_state,
                    "stoppedService": result.stopped_service,
                    "closedFirewall": result.closed_firewall,
                }
            )
        except DeploymentError as exc:
            _file_log.error("uninstall failed [%s]: %s", exc.code, exc.detail or exc.message)
            return _error_response(exc)
        except Exception as exc:
            _file_log.error("uninstall failed (unexpected): %s", exc)
            return _error_response(exc)
        finally:
            _remote_op_lock.release()

    return app, socketio


app, socketio = create_app()
