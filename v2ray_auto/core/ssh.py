"""SSH execution layer.

The old code mixed Paramiko calls, logging, sudo handling and business logic in
multiple places. This module is the single low-level remote execution boundary.
"""

from __future__ import annotations

import shlex
import socket
import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Self

import paramiko

from .errors import (
    CommandTimedOutError,
    DeploymentError,
    OperationCancelledError,
    RemoteCommandError,
    SSHAuthenticationError,
    SSHDnsError,
    SSHHostKeyError,
    SSHProtocolError,
    SSHRefusedError,
    SSHTimedOutError,
)
from .models import DeploymentRequest, LogSink


@dataclass(frozen=True)
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


class SSHExecutor:
    def __init__(
        self,
        request: DeploymentRequest,
        log: LogSink | None = None,
        timeout: int = 900,
        cancel_event: threading.Event | None = None,
    ):
        self.request = request
        self.log = log or (lambda message: None)
        self.timeout = timeout
        self.cancel_event = cancel_event
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._closed = False

    def _raise_if_cancelled(self) -> None:
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise OperationCancelledError(detail="operation cancelled by user")

    def _fast_tcp_probe(self) -> None:
        """Fail fast on unreachable / refused hosts before the slow banner
        connect, so wrong-IP cases surface in seconds instead of 20s."""
        try:
            with socket.create_connection((self.request.host, int(self.request.port)), timeout=3.0):
                return
        except TimeoutError:
            raise SSHTimedOutError(
                "连接服务器超时，请检查服务器 IP、SSH 端口是否正确，以及服务器是否在线",
                detail=f"tcp connect to {self.request.host}:{self.request.port} timed out",
            ) from None
        except OSError as exc:
            raise SSHRefusedError(
                "服务器拒绝了 SSH 连接，请检查 SSH 端口是否正确，以及服务器防火墙是否放行",
                detail=f"tcp connect to {self.request.host}:{self.request.port} refused: {exc}",
            ) from None

    def __enter__(self) -> Self:
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def connect(self) -> None:
        self.log(f"connecting to {self.request.host}:{self.request.port} as {self.request.username}")
        self._raise_if_cancelled()
        self._fast_tcp_probe()
        kwargs = {
            "hostname": self.request.host,
            "port": int(self.request.port),
            "username": self.request.username,
            "timeout": 20,
            "banner_timeout": 20,
            "auth_timeout": 20,
        }
        if self.request.private_key_path:
            kwargs["key_filename"] = self.request.private_key_path
        else:
            kwargs["password"] = self.request.password
        try:
            self.client.connect(**kwargs)
        except Exception as exc:
            raise self._classify_connect_error(exc) from exc
        self._raise_if_cancelled()
        self.log("ssh connected")

    @staticmethod
    def _classify_connect_error(exc: Exception) -> Exception:
        import paramiko

        if isinstance(exc, TimeoutError):
            return SSHTimedOutError(
                "连接服务器超时，请检查服务器 IP、SSH 端口是否正确，以及服务器是否在线",
                detail=f"connect to {exc}",
            )
        if isinstance(exc, paramiko.AuthenticationException):
            return SSHAuthenticationError(
                "SSH 认证失败，请检查用户名和密码是否正确",
                detail=str(exc),
            )
        if isinstance(exc, paramiko.BadHostKeyException):
            return SSHHostKeyError("SSH 主机密钥校验失败", detail=str(exc))
        if isinstance(exc, paramiko.SSHException):
            return SSHProtocolError("SSH 握手失败，请确认服务器开启了 SSH 服务", detail=str(exc))
        if isinstance(exc, socket.gaierror):
            return SSHDnsError("无法解析服务器地址，请检查 IP 或域名是否正确", detail=str(exc))
        if isinstance(exc, OSError):
            return SSHRefusedError(
                "服务器拒绝了 SSH 连接，请检查 SSH 端口是否正确，以及服务器防火墙是否放行",
                detail=str(exc),
            )
        return DeploymentError("连接服务器失败", detail=str(exc))

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.client.close()
        self.log("ssh closed")

    def run(
        self,
        command: str,
        *,
        sudo: bool = False,
        check: bool = True,
        redact: Iterable[str] = (),
        ignore_cancel: bool = False,
    ) -> CommandResult:
        sent_command = command
        display_command = self._redact(command, redact)
        use_stdin_password = False
        if sudo:
            if self.request.username == "root":
                sent_command = f"sh -lc {shlex.quote(command)}"
                display_command = f"sh -lc {shlex.quote(display_command)}"
            elif self.request.password:
                sent_command = f"sudo -S -p '' sh -lc {shlex.quote(command)}"
                display_command = f"sudo sh -lc {shlex.quote(display_command)}"
                use_stdin_password = True
            else:
                sent_command = f"sudo -n sh -lc {shlex.quote(command)}"
                display_command = f"sudo -n sh -lc {shlex.quote(display_command)}"

        self.log(f"$ {display_command}")
        if not ignore_cancel:
            self._raise_if_cancelled()
        stdin, stdout, stderr = self.client.exec_command(sent_command, get_pty=use_stdin_password, timeout=self.timeout)
        if use_stdin_password:
            stdin.write(self.request.password + "\n")
            stdin.flush()

        out_chunks: list[str] = []
        err_chunks: list[str] = []
        start = time.monotonic()
        channel = stdout.channel

        while not channel.exit_status_ready():
            if not ignore_cancel:
                self._raise_if_cancelled()
            if time.monotonic() - start > self.timeout:
                channel.close()
                raise CommandTimedOutError(
                    "服务器命令执行超时",
                    detail=f"command timed out after {self.timeout}s: {display_command}",
                )
            self._drain(stdout, stderr, out_chunks, err_chunks, redact)
            time.sleep(0.1)

        self._drain(stdout, stderr, out_chunks, err_chunks, redact)
        exit_code = channel.recv_exit_status()
        result = CommandResult(
            command=display_command,
            exit_code=exit_code,
            stdout="".join(out_chunks),
            stderr="".join(err_chunks),
        )
        if check and not result.ok:
            raise RemoteCommandError(result.command, result.exit_code, result.stderr)
        return result

    def put_text(self, remote_path: str, content: str, *, mode: int = 0o600) -> None:
        self.log(f"upload {remote_path}")
        sftp = self.client.open_sftp()
        try:
            with sftp.file(remote_path, "w") as file_obj:
                file_obj.write(content)
            sftp.chmod(remote_path, mode)
        finally:
            sftp.close()

    def _drain(self, stdout, stderr, out_chunks: list[str], err_chunks: list[str], redact: Iterable[str]) -> None:
        while stdout.channel.recv_ready():
            text = stdout.channel.recv(4096).decode("utf-8", errors="replace")
            text = self._redact(text, redact)
            out_chunks.append(text)
            self.log(text.rstrip())
        while stderr.channel.recv_stderr_ready():
            text = stderr.channel.recv_stderr(4096).decode("utf-8", errors="replace")
            text = self._redact(text, redact)
            err_chunks.append(text)
            self.log(text.rstrip())

    @staticmethod
    def _redact(text: str, values: Iterable[str]) -> str:
        redacted = text
        for value in values:
            if value:
                redacted = redacted.replace(value, "***")
        return redacted


def is_tcp_open(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False
