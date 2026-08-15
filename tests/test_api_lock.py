"""Tests for the concurrent remote-operation lock in the Flask API."""

import threading

from v2ray_auto.api.app import create_app
from v2ray_auto.core.settings import Settings


class _BlockingDeploy:
    """Mimics a slow deploy: holds the lock and blocks until released."""

    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()

    def deploy(self, request):
        self.started.set()
        self.release.wait(timeout=5)
        from v2ray_auto.core.models import DeploymentResult

        return DeploymentResult(
            server=request.host,
            port=443,
            uuid="uuid",
            client_uri="vless://test",
            remote_config_path="/etc/xray/config.json",
            core="xray",
            profile=request.profile,
            service_name="xray.service",
        )

    def uninstall(self, request):
        self.started.set()
        self.release.wait(timeout=5)
        from v2ray_auto.core.models import UninstallResult

        return UninstallResult(
            server=request.host,
            profile=request.profile,
            removed_config=False,
            removed_state=False,
            stopped_service=False,
            closed_firewall=False,
        )


def test_concurrent_deploy_rejected(monkeypatch):
    settings = Settings(api_key="", allowed_origins=())
    app, _sio = create_app(settings)
    blocker = _BlockingDeploy()
    monkeypatch.setattr("v2ray_auto.api.app.DeploymentService", lambda settings, log=None, cancel_event=None: blocker)

    client = app.test_client()
    payload = {
        "host": "203.0.113.10",
        "serverPort": 22,
        "username": "root",
        "password": "secret",
        "profile": "vless-reality-vision",
    }

    # First request acquires the lock and blocks.
    first = threading.Thread(target=lambda: client.post("/api/deploy", json=payload))
    first.start()
    assert blocker.started.wait(timeout=3), "first deploy should start"

    # Second request must be rejected with 409 while the first holds the lock.
    resp = client.post("/api/deploy", json=payload)
    assert resp.status_code == 409
    assert resp.get_json()["code"] == "operation_in_progress"
    assert "进行中" in resp.get_json()["message"]

    # Release the first, it should complete.
    blocker.release.set()
    first.join(timeout=5)


def test_concurrent_uninstall_rejected(monkeypatch):
    settings = Settings(api_key="", allowed_origins=())
    app, _sio = create_app(settings)
    blocker = _BlockingDeploy()
    monkeypatch.setattr("v2ray_auto.api.app.DeploymentService", lambda settings, log=None, cancel_event=None: blocker)

    client = app.test_client()
    payload = {
        "host": "203.0.113.10",
        "serverPort": 22,
        "username": "root",
        "password": "secret",
        "profile": "vless-reality-vision",
    }

    first = threading.Thread(target=lambda: client.post("/api/deploy", json=payload))
    first.start()
    assert blocker.started.wait(timeout=3)

    resp = client.post("/api/uninstall", json=payload)
    assert resp.status_code == 409

    blocker.release.set()
    first.join(timeout=5)


def test_lock_released_after_success(monkeypatch):
    settings = Settings(api_key="", allowed_origins=())
    app, _sio = create_app(settings)

    class _Fast:
        def deploy(self, request):
            from v2ray_auto.core.models import DeploymentResult

            return DeploymentResult(
                server=request.host,
                port=443,
                uuid="uuid",
                client_uri="vless://test",
                remote_config_path="/etc/xray/config.json",
                core="xray",
                profile=request.profile,
                service_name="xray.service",
            )

        def uninstall(self, request):
            from v2ray_auto.core.models import UninstallResult

            return UninstallResult(
                server=request.host,
                profile=request.profile,
                removed_config=False,
                removed_state=False,
                stopped_service=False,
                closed_firewall=False,
            )

    monkeypatch.setattr("v2ray_auto.api.app.DeploymentService", lambda settings, log=None, cancel_event=None: _Fast())

    client = app.test_client()
    payload = {
        "host": "203.0.113.10",
        "serverPort": 22,
        "username": "root",
        "password": "secret",
        "profile": "vless-reality-vision",
    }

    # First deploy completes and releases the lock.
    resp1 = client.post("/api/deploy", json=payload)
    assert resp1.status_code == 200

    # A second deploy is then allowed (lock was released).
    resp2 = client.post("/api/deploy", json=payload)
    assert resp2.status_code == 200
