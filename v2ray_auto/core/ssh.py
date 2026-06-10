"""SSH execution layer.

The old code mixed Paramiko calls, logging, sudo handling and business logic in
multiple places. This module is the single low-level remote execution boundary.
"""

from __future__ import annotations

import shlex
import socket
import time
from dataclasses import dataclass
from typing import Iterable

import paramiko

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


class RemoteCommandError(RuntimeError):
    def __init__(self, result: CommandResult):
        super().__init__(f"remote command failed ({result.exit_code}): {result.command}\n{result.stderr}")
        self.result = result


class SSHExecutor:
    def __init__(self, request: DeploymentRequest, log: LogSink | None = None, timeout: int = 900):
        self.request = request
        self.log = log or (lambda message: None)
        self.timeout = timeout
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def __enter__(self) -> "SSHExecutor":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def connect(self) -> None:
        self.log(f"connecting to {self.request.host}:{self.request.port} as {self.request.username}")
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
        self.client.connect(**kwargs)
        self.log("ssh connected")

    def close(self) -> None:
        self.client.close()
        self.log("ssh closed")

    def run(self, command: str, *, sudo: bool = False, check: bool = True, redact: Iterable[str] = ()) -> CommandResult:
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
        stdin, stdout, stderr = self.client.exec_command(sent_command, get_pty=use_stdin_password, timeout=self.timeout)
        if use_stdin_password:
            stdin.write(self.request.password + "\n")
            stdin.flush()

        out_chunks: list[str] = []
        err_chunks: list[str] = []
        start = time.monotonic()
        channel = stdout.channel

        while not channel.exit_status_ready():
            if time.monotonic() - start > self.timeout:
                channel.close()
                raise TimeoutError(f"command timed out after {self.timeout}s: {display_command}")
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
            raise RemoteCommandError(result)
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
