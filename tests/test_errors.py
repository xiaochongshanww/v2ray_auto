"""Tests for the structured error taxonomy and its API serialization."""

from v2ray_auto.api.app import _error_response, create_app
from v2ray_auto.core.errors import (
    LockedOperationError,
    OperationCancelledError,
    PortOccupiedError,
    SSHAuthenticationError,
    SSHDnsError,
    SSHRefusedError,
    SSHTimedOutError,
)
from v2ray_auto.core.settings import Settings
from v2ray_auto.core.ssh import CommandResult, RemoteCommandError, SSHExecutor


def test_operation_cancelled_error_taxonomy():
    exc = OperationCancelledError(detail="cancelled by user")
    assert exc.code == "operation_cancelled"
    assert exc.message == "操作已取消"


def test_error_response_for_cancelled():
    body, status = _error_response(OperationCancelledError())
    assert body["code"] == "operation_cancelled"
    assert status == 499


def test_ssh_run_raises_cancelled_when_event_set(monkeypatch):
    import threading

    request = type("R", (), {"host": "x", "port": 22, "username": "u", "password": "p"})()
    event = threading.Event()
    executor = SSHExecutor(request, cancel_event=event)
    event.set()
    import pytest

    with pytest.raises(OperationCancelledError):
        executor._raise_if_cancelled()


def test_api_cancel_endpoint(monkeypatch):
    settings = Settings(api_key="", allowed_origins=())
    app, _sio = create_app(settings)
    resp = app.test_client().post("/api/cancel")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "cancelling"


def test_deployment_error_carries_code_message_detail():
    exc = SSHTimedOutError("连接服务器超时", detail="timed out")
    assert exc.code == "ssh_timeout"
    assert exc.message == "连接服务器超时"
    assert exc.detail == "timed out"


def test_error_response_serializes_structured_error():
    exc = PortOccupiedError(detail="port 443 is occupied")
    body, status = _error_response(exc)
    assert body == {
        "code": "port_occupied",
        "message": "监听端口已被占用",
        "detail": "port 443 is occupied",
    }
    assert status == 400


def test_error_response_409_status():
    body, status = _error_response(LockedOperationError())
    assert body["code"] == "operation_in_progress"
    assert status == 409


def test_error_response_collapses_unknown_exceptions():
    body, status = _error_response(RuntimeError("boom"))
    assert body["code"] == "internal_error"
    assert status == 500
    assert "boom" in body["detail"]


def test_remote_command_error_builds_actionable_message():
    result = CommandResult(command="systemctl restart xray", exit_code=1, stdout="", stderr="Unit failed")
    exc = RemoteCommandError(result.command, result.exit_code, result.stderr)
    assert exc.code == "remote_command_failed"
    assert "退出码 1" in exc.message
    assert "Unit failed" in exc.detail


def test_api_returns_structured_error_body(monkeypatch):
    settings = Settings(api_key="", allowed_origins=())

    class _AuthFail:
        def deploy(self, request):
            raise SSHAuthenticationError("SSH 认证失败", detail="Authentication failed.")

    monkeypatch.setattr(
        "v2ray_auto.api.app.DeploymentService", lambda settings, log=None, cancel_event=None: _AuthFail()
    )
    app, _sio = create_app(settings)
    resp = app.test_client().post(
        "/api/deploy",
        json={"host": "203.0.113.10", "serverPort": 22, "username": "root", "password": "pw"},
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["code"] == "ssh_auth_failed"
    assert body["message"] == "SSH 认证失败"
    assert body["detail"] == "Authentication failed."


def test_api_returns_internal_error_for_unknown_exception(monkeypatch):
    settings = Settings(api_key="", allowed_origins=())

    class _Boom:
        def deploy(self, request):
            raise RuntimeError("something weird")

    monkeypatch.setattr("v2ray_auto.api.app.DeploymentService", lambda settings, log=None, cancel_event=None: _Boom())
    app, _sio = create_app(settings)
    resp = app.test_client().post(
        "/api/deploy",
        json={"host": "203.0.113.10", "serverPort": 22, "username": "root", "password": "pw"},
    )
    assert resp.status_code == 500
    body = resp.get_json()
    assert body["code"] == "internal_error"
    assert "something weird" in body["detail"]


def test_ssh_classifies_connect_exceptions():
    import socket

    assert isinstance(SSHExecutor._classify_connect_error(TimeoutError("timed out")), SSHTimedOutError)
    assert isinstance(SSHExecutor._classify_connect_error(socket.gaierror("nodename nor servname")), SSHDnsError)
    assert isinstance(SSHExecutor._classify_connect_error(OSError("connection refused")), SSHRefusedError)
