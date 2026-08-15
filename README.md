# V2Ray Auto

一键部署 V2Ray/Xray 代理服务的桌面客户端。

连接一台（近乎）全新的 VPS，自动完成 bootstrap、安装核心服务、生成优化配置、网络调优、开放端口，并返回可直接导入客户端的 URI——全程无需手动登录服务器。

## 功能特性

- **一键部署**：SSH 连接 → 系统识别 → 基础软件安装 → 低内存自动建 swap → 安装 Xray → BBR/TCP 调优 → 生成配置 → 重启服务 → 开放防火墙端口 → 返回客户端 URI
- **两种配置模板**：
  - `vless-reality-vision`（默认）：Xray + VLESS + REALITY + Vision，端口 443
  - `vmess-tcp-legacy`：VMess TCP，旧版兼容
- **部署取消与回退**：部署中可随时取消，已实施的步骤（防火墙/服务/配置）自动逆序回退，服务器恢复部署前状态
- **一键卸载**：部署历史中对节点执行卸载，幂等可重复，支持崩溃后恢复
- **结构化错误提示**：连接超时 / 认证失败 / 端口占用等错误分类展示中文排查指引，不再只有裸异常
- **部署历史**：本地保存部署记录（成功/失败/已取消/已卸载），支持查看详情、二维码与 URI 复制
- **凭据安全**：SSH 密码经系统钥匙串加密存储（Electron safeStorage），下次部署自动回填
- **并发保护**：同一时间只允许一个部署/卸载任务
- **自动更新**：通过 GitHub Release 检查并下载新版本

## 架构

```
desktop/                  Electron 桌面客户端
  main.js                 主进程（后端生命周期、IPC、自动更新）
  preload.js              渲染进程安全桥接
  renderer/               前端构建产物
  backend/                 Python 后端子进程（launcher.py 启动）
vue_web/remote-server-config/   Vue3 + Vite + Tailwind 前端源码
v2ray_auto/               Python 后端（Flask + SocketIO）
  core/                    纯业务逻辑（无框架依赖，可单测）
    deployment.py          部署/卸载编排
    installer.py           远程安装引导
    ssh.py                 SSH 执行层（含错误分类）
    profiles/              配置模板生成
    errors.py              结构化异常体系
    network_tuning.py      BBR / TCP 调优
    state.py               远端状态持久化
  api/app.py               HTTP API（/api/deploy、/api/uninstall、/api/cancel）
tests/                    pytest 测试（77 用例）
```

后端作为独立进程由 Electron 启动，通过本地 HTTP + SocketIO（流式日志）通信，启动端口随机分配避免冲突。

## 桌面客户端开发

```bash
cd desktop
npm install
npm run setup            # 安装依赖 + 构建前端 + 安装后端 Python 依赖
npm run dev              # 启动开发（自动拉起 Python 后端子进程）
```

打包分发（electron-builder）：

```bash
npm run dist:mac         # .dmg / .zip
npm run dist:win         # NSIS 安装版 / 便携版 .exe
npm run dist:linux       # .AppImage / .deb
```

> macOS 安装指引见 [docs/INSTALL_GUIDE.md](docs/INSTALL_GUIDE.md)（未签名应用需解除 quarantine）。

## 仅运行后端 API

```bash
pip install -r requirements.txt
cp .env.example .env      # 按需编辑环境变量
python -m flask --app v2ray_auto.api.app run --host 127.0.0.1 --port 5000
```

健康检查：

```bash
curl http://127.0.0.1:5000/health
```

### API 端点

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/deploy` | POST | 一键部署 |
| `/api/uninstall` | POST | 卸载节点 |
| `/api/cancel` | POST | 取消进行中的部署/卸载 |
| `/health` | GET | 健康检查 |

部署请求示例：

```json
{
  "host": "203.0.113.10",
  "serverPort": 22,
  "username": "root",
  "password": "<ssh 密码>",
  "profile": "vless-reality-vision",
  "listenPort": 443,
  "realityServerName": "www.apple.com",
  "realityDest": "www.apple.com:443"
}
```

### 环境变量（`.env`）

| 变量 | 说明 | 默认 |
|---|---|---|
| `V2RAY_AUTO_API_KEY` | API 密钥，为空则跳过鉴权（桌面端默认） | 空 |
| `V2RAY_AUTO_ALLOWED_ORIGINS` | 允许的 CORS 来源 | `http://localhost:8080` |
| `V2RAY_AUTO_DEFAULT_REMOTE_DIR` | 远端工作目录 | `/opt/v2ray_auto` |
| `V2RAY_AUTO_COMMAND_TIMEOUT` | 远端命令超时（秒） | `900` |
| `V2RAY_AUTO_LOG_LEVEL` | 日志级别 | `INFO` |
| `V2RAY_AUTO_SMTP_*` | 部署结果邮件通知（可选） | 空 |

## 测试

```bash
python -m pip install -r requirements.txt pytest ruff
ruff check v2ray_auto/ tests/
ruff format --check v2ray_auto/ tests/
python -m pytest tests/
```

## 发布流程

推送 `v*` tag 触发 CI（`.github/workflows/build-desktop.yml`）：

1. `backend-tests`：ruff lint + 全量 pytest
2. `package`：macOS / Windows / Linux 三平台并行打包
3. `publish`：上传三平台安装包到 GitHub Release，自动附加变更日志与[安装指引](docs/INSTALL_GUIDE.md)

```bash
git tag v0.1.0 && git push origin v0.1.0
```

桌面端通过 electron-updater 检测 GitHub Release 实现自动更新（仅 NSIS 安装版支持静默更新）。

## 相关文档

- [docs/ROADMAP_IMPROVEMENTS.md](docs/ROADMAP_IMPROVEMENTS.md) — 改进路线图与决策记录
- [docs/INSTALL_GUIDE.md](docs/INSTALL_GUIDE.md) — 各平台安装指引
- [docs/ARCHITECTURE_ELECTRON.md](docs/ARCHITECTURE_ELECTRON.md) — Electron 架构决策记录
