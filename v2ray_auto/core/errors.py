"""Structured error taxonomy for deployment operations.

Every failure raised during deploy / uninstall is a DeploymentError subclass
that carries:

* ``code``    - stable machine-readable identifier (surfaced to the client)
* ``message`` - user-facing, actionable Chinese message
* ``detail``  - diagnostic detail (stderr, host, command, ...) for the log

The API boundary converts DeploymentError into ``{code, message, detail}`` so
the frontend can map codes to guidance instead of showing raw tracebacks.
"""

from __future__ import annotations


class DeploymentError(Exception):
    """Base class for all structured deployment failures."""

    code = "deploy_failed"
    message = "部署失败"
    status_code = 400

    def __init__(self, message: str | None = None, *, detail: str | None = None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.detail = detail or str(self) or self.message


class ValidationError(DeploymentError):
    """Request payload failed validation."""

    code = "invalid_request"
    message = "请求参数无效"


class UnsupportedProfileError(ValidationError):
    """Unknown deployment profile."""

    code = "unsupported_profile"
    message = "不支持的配置模板"


class SSHConnectionError(DeploymentError):
    """Generic failure establishing the SSH transport."""

    code = "ssh_connection_failed"
    message = "无法连接服务器"


class SSHTimedOutError(SSHConnectionError):
    """Socket/banner/auth connect timeout. Usually network unreachable or
    firewall silently dropping packets."""

    code = "ssh_timeout"
    message = "连接服务器超时"


class SSHDnsError(SSHConnectionError):
    """Host could not be resolved."""

    code = "ssh_dns_failed"
    message = "无法解析服务器地址"


class SSHRefusedError(SSHConnectionError):
    """TCP connection refused. Likely wrong SSH port or no SSH daemon."""

    code = "ssh_refused"
    message = "服务器拒绝了 SSH 连接"


class SSHAuthenticationError(SSHConnectionError):
    """Wrong username / password / key."""

    code = "ssh_auth_failed"
    message = "SSH 认证失败"


class SSHHostKeyError(SSHConnectionError):
    """Host key verification issue."""

    code = "ssh_host_key"
    message = "SSH 主机密钥校验失败"


class SSHProtocolError(SSHConnectionError):
    """SSH banner / protocol-level failure."""

    code = "ssh_protocol_error"
    message = "SSH 握手失败"


class RemoteCommandError(DeploymentError):
    """A remote shell command exited non-zero."""

    code = "remote_command_failed"
    message = "服务器命令执行失败"

    def __init__(self, command: str, exit_code: int, stderr: str, *, detail: str | None = None):
        self.command = command
        self.exit_code = exit_code
        self.stderr = stderr
        message = f"命令执行失败：{command}（退出码 {exit_code}）"
        super().__init__(message, detail=detail or stderr.strip())


class CommandTimedOutError(DeploymentError):
    """A remote command exceeded the command timeout."""

    code = "command_timeout"
    message = "服务器命令执行超时"


class PortOccupiedError(DeploymentError):
    """The requested listen port is already in use."""

    code = "port_occupied"
    message = "监听端口已被占用"


class InstallFailedError(DeploymentError):
    """Core binary could not be installed / located after bootstrap."""

    code = "install_failed"
    message = "核心程序安装失败"


class ServiceStartError(DeploymentError):
    """The deployed service failed to start."""

    code = "service_failed_to_start"
    message = "服务启动失败"


class ConfigError(DeploymentError):
    """Remote configuration generation / validation failed."""

    code = "config_error"
    message = "配置生成或校验失败"


class LockedOperationError(DeploymentError):
    """Another deploy / uninstall is already in progress."""

    code = "operation_in_progress"
    message = "已有部署或卸载正在进行中，请稍后再试"
    status_code = 409


class OperationCancelledError(DeploymentError):
    """The running deploy / uninstall was cancelled by the user."""

    code = "operation_cancelled"
    message = "操作已取消"
    status_code = 499
