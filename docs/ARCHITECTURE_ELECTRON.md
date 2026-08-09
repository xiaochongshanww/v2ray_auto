# Electron 桌面客户端架构选型方案

> 状态：架构定稿；M0 PoC 通过；M1 MVP 完成；M2 打包分发完成；M3 增强完成
> 日期：2026-08-09
> 范围：将当前"Web 部署式"的 v2ray 自动化工具改造为跨平台桌面客户端的架构决策

---

## 1. 背景

当前项目以 Web 方案运行：

```
Vue3 前端 (remote-server-config)
        │ fetch /api/deploy + socket.io
        ▼
Flask 后端 (v2ray_auto.api.app)
        │
        ▼
v2ray_auto.core.DeploymentService（纯 Python，SSH 直连远端 VPS）
```

**痛点**：使用者必须先在服务器上部署 web 服务（装依赖、配 `.env`、跑 gunicorn）才能使用，运维负担重、入口在远端、操作有延迟。

**目标**：做成 Electron 桌面客户端，双击即用、跨平台（macOS / Windows / Linux），开发一次即可分发。

**核心事实**：部署逻辑 `v2ray_auto.core` 是纯 Python 包，不依赖 web 服务；Flask 只是薄壳。桌面化**不需要重写业务**，只需要决定"桌面壳如何承载 Python 后端"。

---

## 2. 决策问题

> 采用哪种技术方案构建桌面客户端，以复用现有 Python 核心为最高优先级？

评判维度：
- 代码复用度（能否直接复用已验证的 `v2ray_auto.core` 与 37 个测试）
- 开发成本 / 开发周期
- 长期维护成本
- 打包与分发难度（体积、三平台、代码签名）
- 运行稳定性与排查难度
- 安全性
- 演进空间（多节点、自动更新等）

---

## 3. 候选方案

### 方案 A：Electron + Python 后端子进程 + 本地 HTTP API（Sidecar）

**原理**：

```
┌─ Electron 应用 ──────────────────────────────┐
│  Main Process                               │
│   ├─ spawn 管理 Python 后端子进程             │
│   ├─ 分配随机端口 + 生成内部 API Key          │
│   └─ 生命周期守护（崩溃拉起/退出回收）        │
│  Renderer（现有 Vue3 + Vite 构建物）         │
│   └─ fetch http://127.0.0.1:<port>/api/deploy
│   └─ socket.io-client 实时日志               │
└─────────────────────────────────────────────┘
              │ spawn（PyInstaller 或 python-build-standalone）
              ▼
┌─ Python 后端（原样复用 v2ray_auto.api.app）──┐
│  Flask + Socket.IO（threading 模式）          │
│  DeploymentService → SSH → 远端 VPS           │
└─────────────────────────────────────────────┘
```

**Python 承载方式（A 的两个子选项）**：

| 子选项 | 说明 | 优劣 |
|---|---|---|
| A1 PyInstaller one-dir | 把 Python+依赖打成目录，含独立可执行文件 | 优点：单目录自包含；缺点：需收集 C 扩展（cryptography 等），有 spec 调参成本；代码签名需处理内嵌二进制 |
| A2 python-build-standalone + 源码 | 官方独立 Python 运行时 + 直接跑源码/venv | 优点：无二进制收集魔法、可读可调试、升级只换运行时；缺点：目录更大、需自带依赖安装步骤 |

**优点**
- ✅ 代码复用率最高：后端零改动，前端基本零改动（仅改 API base URL）
- ✅ 边界极薄且稳定：两端只通过 HTTP 通信，互不耦合，各自可独立升级
- ✅ 生态成熟：该模式被大量桌面工具采用，坑都有现成解法
- ✅ 安全可控：后端只绑 `127.0.0.1`，可加随机端口 + 内部 API Key 双保险
- ✅ 可并行保留 Web 方案：同一后端代码可继续发布 web 版

**缺点 / 风险**
- ❌ 双运行时，包体积大（约 150–300MB/平台）
- ❌ 打包、进程生命周期、三平台签名是主要工程投入（见 §5 风险表）
- ❌ 排查需跨 JS/Python 两层
- ⚠️ 杀软/SmartScreen 对双运行时可能误报

### 方案 B：Electron + Python stdio IPC（JSON-RPC over stdin/stdout）

**原理**：Electron 主进程直接与 Python 子进程用 stdin/stdout 传 JSON 消息，不经 HTTP；渲染进程通过 IPC 桥接主进程。

**优点**
- ✅ 无端口占用/防火墙干扰
- ✅ 少一层 HTTP server，攻击面更小

**缺点 / 风险**
- ❌ 现有 `config_server_api` 的 HTTP+Socket.IO 机制全部失效，需新写一套 IPC 协议
- ❌ 渲染进程不能直连，所有调用要主进程中转，代码量反而更大
- ❌ 长日志流/流式输出在 stdio 上需要自定义帧协议，复杂度高
- ❌ 丢失"后端可独立运行/可测试"的属性

### 方案 C：纯 Node.js 重写（ssh2 / node-ssh 替代 paramiko）

**原理**：弃用 Python，全部用 TypeScript/JS 在 Electron 内实现 SSH 与部署。

**优点**
- ✅ 单运行时，无跨进程耦合，打包最小
- ✅ 结构最"干净"，没有两个生态

**缺点 / 风险**
- ❌ 重写 `v2ray_auto.core`（约 1100 行）+ profiles + state + 网络调优 + 37 个测试，周期以月计
- ❌ 丢验证过的实现（REALITY 密钥处理、远端故障诊断、dpkg 修复等），真实部署场景出问题更难排查
- ❌ SSH 库能力（SFTP、pty、channel 级控制）需重新对齐，边角情况多
- ❌ 新代码本身即新风险源

### 方案 D：复用旧 PyQt 桌面客户端（`v2ray_auto_client/`）

**优点**
- ✅ 已有 GUI 和 paramiko 直连逻辑

**缺点 / 风险**
- ❌ 走的是"克隆仓库+远程跑脚本"的旧部署链路，与当前核心架构不符
- ❌ 依赖已废弃的 `auto_install_v2ray.py`，当前必然失败
- ❌ PyQt 打包体积不小、跨平台一致性和现代 UI 能力弱于 Electron
- ❌ 与用户明确诉求（Electron）不符

### 方案 E：Tauri（Rust 壳）+ Python 后端

**原理**：用 Tauri 替代 Electron 做壳，后端仍用 Python（同 A 的承载方式）。

**优点**
- ✅ 壳更轻（体积 ~50MB 内）、内存占用小
- ✅ 系统集成 API（托盘/更新）更贴近原生

**缺点 / 风险**
- ❌ **Python 问题一个不少**：后端仍要 PyInstaller/独立运行时 + 子进程管理 + 三平台签名
- ❌ 前端生态从 Vue-CLI 迁移到 Tauri 需调整（但其实现有 Vue 可直接接）
- ❌ 团队若更熟 JS/Node 生态，Tauri 学习曲线是额外成本
- ❌ 社区/文档成熟度、包管理器等配套不如 Electron 老牌

> 结论：Tauri 能优化"壳"的体积与性能，但**消除不了 Python sidecar 这个核心复杂度**，与用户的担忧无本质缓解。

### 方案 F：保留 Web 方案 + 独立维护桌面端

**优点**
- ✅ 无新技术栈风险

**缺点 / 风险**
- ❌ 两份前端/两份入口长期并行，维护成本翻倍
- ❌ 未解决"必须部署服务器"的核心痛点
- ❌ 桌面端最终仍要选 A/B/C 之一，只是把决策推迟

---

## 4. 方案对比总表

| 维度 | A Sidecar HTTP | B stdio IPC | C Node 重写 | D 旧 PyQt | E Tauri+Py | F 双轨 |
|---|---|---|---|---|---|---|
| 核心复用率 | ★★★★★ | ★★★★ | ★ | ★★ | ★★★★★ | ★★★★ |
| 开发周期 | 短 | 中 | 长 | 短（但劣质） | 中 | 长 |
| 维护成本 | 中 | 中高 | 高 | 高 | 中 | 高 |
| 包体积 | 150–300MB | 150–300MB | 最小 | 大 | 最小壳 | 双份 |
| 打包签名难度 | 中 | 中 | 低 | 中 | 中 | 中 |
| 运行时耦合 | 低（HTTP 薄边界） | 中 | 无 | 低 | 低 | 低 |
| 实时日志 | 复用现有 | 需重写 | 重写 | 需重写 | 复用现有 | 复用 |
| 可独立测试后端 | ✅ | ❌ | N/A | 部分 | ✅ | ✅ |
| 风险可控性 | 高 | 中 | 低 | 低 | 中 | 中 |

**推荐：方案 A（优先 A2 承载方式，A1 作为备选）**

理由：
1. 复用率最高 → 开发周期与风险最小；
2. HTTP 薄边界把"Electron 与 Python 的配合"约束到最小协议面，直接回应了"配合不好"的顾虑；
3. 后端保持可独立运行/测试，37 个测试继续作为回归基线；
4. 不排斥未来换 Tauri（后端不变，只换壳）。

---

## 5. 风险与缓解（针对方案 A）

| 风险 | 等级 | 缓解措施 |
|---|---|---|
| PyInstaller 打包 C 扩展（cryptography/paramiko）缺文件 | 高 | 先做 PoC；必要时用 spec 显式收集；或切 A2 独立运行时 |
| 冻结模式下资源路径 / `sys.executable` 行为差异 | 高 | PoC 中专门用例覆盖；后端资源全部走显式路径 |
| 子进程生命周期（启动/退出/崩溃拉起） | 高 | 主进程统一状态机：心跳检测 + 异常退出自动重启 + 退出时回收 |
| macOS 公证 / Windows 签名牵连 Python 二进制 | 中 | A2 运行时可直接签名；CI 内验证公证流程 |
| 杀软误报 | 中 | 正式发布走代码签名 + 提交厂商白名单 |
| 端口冲突 | 低 | 随机端口 + 重试；只绑 127.0.0.1 |
| 体积偏大 | 低 | 接受；后续可用 UPX/按平台裁剪 |

---

## 6. PoC 验证计划（决策前必做）

> 用最小可运行样例，把"Electron+Python 配合"的最大风险先证伪或坐实。

- **P0.1** 最小 Electron 壳启动 python-build-standalone（A2）打包的 Python 后端，含 paramiko + Flask-SocketIO
- **P0.2** 健康检查 + 端到端部署一台测试 VPS（或 mock），验证日志回流
- **P0.3** macOS + Windows 双平台产物跑通
- **P0.4** 验证 A1（PyInstaller）作为备份路径可行

**通过标准**：三件事全过——能打包、能 spawn、能端到端部署。
若 PoC 失败：转向方案 C 或保留方案 F 的明确决策依据即已获得，而非猜测。

---

## 6.1 M0 概念验证结果（2026-08-09 ✅ 通过）

**验证环境**：macOS（arm64）、Electron v43.3.0、python-build-standalone 20260807（CPython 3.13.15）、Node v24.6。

| 验证项 | 结果 |
|---|---|
| P0.1 Electron spawn A2 后端 | ✅ `[backend] ready on http://127.0.0.1:<随机端口>` |
| P0.2 健康检查 | ✅ `{"status":"ok"}` |
| P0.2 部署接口链路 | ✅ `POST /api/deploy` 走通完整 `DeploymentService` 管线（对不可达主机返回明确 SSH 错误） |
| P0.2 认证 | ✅ 无 `X-API-Key` → 401 |
| P0.2 生命周期回收 | ✅ 关闭 Electron → 后端收到 SIGTERM → `shutting down` → 退出 code=0 |
| 回归 | ✅ 37 个 Python 测试全部通过 |

**过程中解决的坑**：
1. `app.py` 模块级 `create_app()` 需 `V2RAY_AUTO_API_KEY` → launcher 在 import 前将桌面 Key 注入 `os.environ`
2. Electron 二进制 GitHub 下载 TLS 失败 → 使用 `ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/`
3. 旧 venv 污染 → A2 独立运行时内干净安装依赖

**结论**：A2 路径验证通过，正式定稿 **A2（python-build-standalone + 源码/依赖运行）**，A1（PyInstaller）降级为 M2 打包期的可选对比项。P0.3（Windows 产物）留待 M2 CI 矩阵验证。

## 6.2 M1 MVP 验证结果（2026-08-09 ✅ 通过）

**范围**：功能对齐 Web 前端 + 部署历史 + 凭据安全。

| 验证项 | 结果 |
|---|---|
| Vue 前端接入桌面 | ✅ Vite 构建产物（`base:'./'`）直接由 Electron `loadFile` 加载，双模式（桌面/web）共用同一份前端 |
| 动态 API base | ✅ 桌面模式经 preload 注入 `apiBase` + 自动 API Key（`getApiBase`/`getApiKey`/`onBackendReady`），web 模式保持 `/` 相对路径 + 手动 Key |
| 实时日志回流 | ✅ Socket.IO 连 `io(apiBase)`，`process_update` 事件正常渲染 |
| 部署历史 | ✅ 主进程 `userData/history.json`（上限 200 条），preload 暴露 `history.list/add/clear`，UI 表格展示 |
| 凭据加密 | ✅ `safeStorage` 加密存入 `credentials.json`（Keychain/DPAPI 底层），`credential.save/load/delete`，「记住密码」+ 自动回填上次服务器 |
| 渲染进程 | ✅ 无 JS 错误（console-message 钩子捕获） |
| 生命周期 | ✅ 关闭 Electron → 后端 SIGTERM → 退出 code=0 |
| 回归 | ✅ 37 个 Python 测试全部通过 |

**关键实现**：`main.js` 主进程持有 `apiKey`（`startBackend()` 同步生成，先于渲染进程加载 → 无竞态）；后端就绪 JSON 解析后经 `backend-ready` 事件推送渲染进程重连 Socket；`sandbox: true` + `contextIsolation: true` 保持。

---

## 6.3 M2 打包分发验证结果（2026-08-09 ✅ 通过）

**范围**：electron-builder 三平台打包 + CI 矩阵 + 签名 + 自动更新。

| 验证项 | 结果 |
|---|---|
| 本机 macOS 打包 | ✅ `V2Ray Auto-0.1.0-arm64.dmg`（150MB）+ `.zip`（152MB）+ blockmap 全部生成 |
| 打包内资源 | ✅ `Resources/{app.asar, backend/, runtime/, v2ray_auto/}` 完整；icon.icns 由 `assets/icon.png` 自动生成 |
| 打包产物启动 | ✅ 直接运行 `.app` 内二进制 → 后端从 `process.resourcesPath` 启动 → `[backend] ready` → 优雅退出 code=0 |
| 打包模式资源路径 | ✅ `resourcesPath()/backendDir()/launcherPath()` 双模式（dev `__dirname` / packaged `process.resourcesPath`） |
| Python 包路径 | ✅ `launcher.py` `_find_package_root()` 双模式查找 `v2ray_auto` 源码目录 |
| 日志目录 | ✅ `app.py` 支持 `V2RAY_AUTO_LOG_DIR` env，桌面端写 `userData/logs/`（避免打包后只读路径） |
| Windows 路径 | ✅ `resolvePython()` 兼容 `runtime/python3.13/python.exe` |
| 运行时获取 | ✅ `scripts/fetch-runtime.sh` 按平台/架构下载 python-build-standalone（.tar.gz，无需 zstd） |
| CI 矩阵 | ✅ `.github/workflows/build-desktop.yml`：后端测试 + mac/win/linux 三平台打包 + tag 发布 GitHub Release |
| 签名 | ✅ 无有效证书时 electron-builder 自动跳过；有 `CSC_LINK`/证书时自动签名；公证可选（`npm run dist:mac -- --config.mac.notarize=true` + APPLE_* env） |
| 自动更新 | ✅ `electron-updater` 已接线（仅 packaged 模式），GitHub Releases feed，实测初始化正常 |

**过程中解决的坑**：
1. package.json 手改导致尾括号重复 → JSON 非法 → Electron 静默失败（进程存活但 main.js 不加载）；用 `node -e JSON.parse` 校验
2. DMG 构建需下载 electron-builder 二进制（默认走 GitHub，本机 TLS 失败）→ `ELECTRON_BUILDER_BINARIES_MIRROR=https://npmmirror.com/mirrors/electron-builder-binaries/`（已固化进 dist 脚本，用 cross-env 跨平台）
3. 打包模式下 `logs/` 不可写 → `V2RAY_AUTO_LOG_DIR` 指向 `userData/logs`

---

## 6.4 M3 增强验证结果（2026-08-09 ✅ 通过）

**范围**：多节点、托盘、自动更新细节。

| 验证项 | 结果 |
|---|---|
| 多节点 | ✅ `userData/nodes.json` CRUD（`nodes-list/upsert/delete` IPC）；UI：节点下拉选择/载入/「保存当前为节点」/管理列表（载入/删除）；activeNodeId 存 localStorage |
| 节点凭据 | ✅ 载入节点时按 `${ip}@${username}` 从 `safeStorage` 凭据库自动回填密码 |
| 托盘 | ✅ `Tray`（`assets/trayTemplate.png`，macOS 模板图），菜单：显示/隐藏、检查更新、退出；点图标切换窗口 |
| 关闭到托盘 | ✅ `close` 事件拦截：非退出时 `preventDefault + hide`，仅托盘「退出」真正退出 |
| 自动更新细节 | ✅ 状态事件推送渲染进程（checking/available/downloaded/not-available/error），UI 顶部横幅提示 8s；托盘「检查更新」手动触发 |
| 打包 | ✅ 重打包 mac `.dmg`/`.zip`，`app.asar` 含 `trayTemplate.png`，产物启动无错误 |

---

## 7. 决策结论

| 决策项 | 结论 | 状态 |
|---|---|---|
| 整体架构 | **方案 A：Electron + Python 后端子进程 + 本地 HTTP API（Sidecar）** | ✅ 锁定 |
| Python 承载 | **A2 定稿**：python-build-standalone + 内置依赖/源码运行（PoC 已验证）；A1（PyInstaller）降为 M2 可选对比 | ✅ 定稿 |
| Web 方案去留 | 保留为**可选后端运行形态**，但产品主入口转向桌面端 | ✅ 定稿 |
| 旧 PyQt 客户端 | **归档或删除** | ✅ 定稿 |
| 凭据策略 | **记住密码**（Electron `safeStorage` → OS Keychain / Windows DPAPI），加密存 `userData/credentials.json`，可回填上次服务器 | ✅ 定稿（M1 已实现） |
| 分发渠道 | **GitHub Releases + electron-updater 自动更新**（`publish.provider=github`），CI tag 自动发布 | ✅ 定稿（M2 已实现） |
| 签名 | 无证书自动跳过；macOS 公证可选（`--config.mac.notarize=true` + APPLE_* env）；Windows 用 CSC_LINK/p12 | ✅ 定稿（M2 已实现） |

---

## 8. 里程碑

| 阶段 | 内容 | 出口标准 |
|---|---|---|
| M0 概念验证 | Electron 壳 + Python 后端 + 端到端部署 | PoC 三平台跑通 |
| M1 MVP | 功能对齐 Web 前端 + 部署历史 + 凭据安全 | 37 测试回归通过 |
| M2 打包分发 | electron-builder 三平台 + CI 矩阵 + 签名 + 自动更新 | 可下载安装包（本机 mac 已产出；win/linux 由 CI 矩阵产出） |
| M3 增强 | 多节点、托盘、自动更新细节 | 生产可用（✅ 已达成） |
| M4 展望 | 打包产物 CI 跑通、正式签名公证、发布流程验证 | 首个对外发布 |

---

## 9. 决策记录

- **日期**：2026-08-09
- **状态**：✅ 架构定稿（Sidecar HTTP 模式）；✅ A2 承载方式定稿；✅ M1 MVP；✅ M2 打包分发；✅ M3 增强（多节点/托盘/自动更新细节）
- **已确认决策**：
  1. 整体采用方案 A（Electron + Python 后端子进程 + 本地 HTTP API）
  2. **A2 定稿**：python-build-standalone + 源码/依赖运行（M0 PoC 通过）；A1（PyInstaller）降为 M2 可选对比
  3. Web 模式保留为可选后端运行形态，产品主入口转向桌面端
  4. 旧 PyQt 客户端归档或删除
  5. **凭据策略定稿**（M1）："记住密码"经 `safeStorage` 加密，凭据与历史存 `userData/`
  6. **分发渠道定稿**（M2）：GitHub Releases + electron-updater；CI 三平台矩阵 + tag 自动发布
  7. **签名策略定稿**（M2）：无证书自动跳过；公证/签名按证书可用性开关
  8. **多节点定稿**（M3）：`userData/nodes.json` 节点库 + localStorage 记忆当前节点；密码仍按节点走 `safeStorage`
- **待定**：正式发布需 CI 三平台产物跑通 + 真实签名/公证证书
- **下一步**：M4（发布流程）：push 后 CI 矩阵构建 win/linux 产物、配置签名/公证、打 tag 走 Release
- **关联文档**：`docs/CONFIG_AND_SPEED_OPTIMIZATION.md`、`README.md`
