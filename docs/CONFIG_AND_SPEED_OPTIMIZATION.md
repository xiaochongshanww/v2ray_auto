# 配置与提速优化方案

## 目标

本项目的核心目标是面向近乎空配置的 VPS 实现一键部署。配置优化不能只追求能连通，还要同时考虑连接质量、部署耗时、可维护性和失败恢复。

## 当前问题

旧方案以 VMess + TCP + 随机高端口为默认配置，存在几个问题：

1. 默认配置过于基础，不适合作为长期使用配置。
2. 随机高端口不符合常见 HTTPS 服务外观。
3. VMess TCP legacy 配置应保留兼容，但不应作为默认方案。
4. 部署步骤中安装、配置、调优没有清晰分层。
5. 重复部署时缺少幂等判断，容易浪费时间。

## 默认配置方向

默认 profile 调整为：

```text
Xray-core + VLESS + REALITY + Vision + 443
```

推荐默认参数：

```text
core = xray
protocol = vless
network = raw
security = reality
flow = xtls-rprx-vision
port = 443
mux = false
fingerprint = chrome
```

## Profile 分层

新增配置 profile 层：

```text
v2ray_auto/core/profiles/
  base.py
  vless_reality_vision.py
  vmess_tcp_legacy.py
```

默认 profile：

```text
vless-reality-vision
```

兼容 profile：

```text
vmess-tcp-legacy
```

## 安装器优化

默认安装器应从 V2Ray 切换到 Xray。

目标路径：

```text
service = xray.service
config = /usr/local/etc/xray/config.json
binary = /usr/local/bin/xray
```

安装阶段要求：

1. 检测 `xray.service` 是否已经存在。
2. 不存在时安装基础依赖。
3. 低内存机器补充 swap。
4. 下载安装脚本时启用连接超时和重试。
5. 安装后再次检查服务是否存在。

## 网络提速优化

### BBR

部署时自动检测 BBR 是否可用：

```bash
sysctl net.ipv4.tcp_available_congestion_control
```

可用时写入：

```text
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr
```

要求：

1. 已开启时跳过。
2. 不支持时跳过，不强制换内核。
3. 写入 `/etc/sysctl.d/99-v2ray-auto.conf`，不要直接污染主配置文件。

### Mux

默认禁用：

```text
mux = false
```

Mux 不作为吞吐提速手段，只允许后续作为客户端高级选项。

### 端口

默认端口：

```text
443
```

如果 443 被占用，后续再引入候选端口策略。第一阶段不做随机高端口默认值。

## 部署提速优化

第一阶段实现：

1. 服务存在则跳过安装。
2. swap 存在则跳过创建。
3. BBR 已开启则跳过配置。
4. 下载命令增加 retry。

后续阶段实现：

1. 合并 bootstrap shell，减少 SSH 往返。
2. 配置 hash 比对，配置未变时不重启。
3. 支持镜像源策略：`default` / `china`。
4. 失败恢复：安装失败、配置失败、服务启动失败分别输出明确阶段。

## 实施顺序

### P0

- 新增 Xray 安装器。
- 新增 VLESS REALITY Vision profile。
- 部署主流程默认切到 Xray profile。
- 增加 BBR 自动调优。
- README 更新默认架构。

### P1

- VMess TCP legacy profile 保留兼容。
- API 增加 profile 参数。
- 前端支持 profile 选择。
- 安装阶段合并脚本执行。

### P2

- 有域名模式：WebSocket/gRPC + TLS。
- 证书申请与 Nginx/Caddy 自动配置。
- 配置 hash 与无变更跳过重启。
