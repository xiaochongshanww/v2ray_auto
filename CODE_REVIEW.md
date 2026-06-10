# V2Ray Auto 重构审查记录

## 当前分支

`refactor/destructive-core-rewrite`

## 关键结论

1. 旧项目存在多套入口：根目录脚本、PyQt 客户端、Vue + Flask Web 后端。
2. 旧实现中部署逻辑重复，SSH 执行、日志、配置生成和 Web 入口耦合严重。
3. 当前重构分支已经将 `config.py` 去敏，并改为环境变量加载。
4. 旧 Web API 缺少认证、CORS 过宽、返回链路不完整；新 API 增加 API Key 校验和来源白名单。
5. 旧测试依赖固定公网 IP，已经移除，改为纯函数测试。

## 重构策略

- 删除会与新包冲突的旧 `v2ray_auto.py`。
- 将核心逻辑迁移到 `v2ray_auto/core/`。
- 将 HTTP 入口迁移到 `v2ray_auto/api/app.py`。
- 将 `auto_install_v2ray.py` 改为废弃提示。
- 将 `vue_web/Python_api/config_server_api.py` 改为兼容包装。

## 仍需处理

- 清理 Git 历史中的历史敏感数据。
- 为目标机安装器设计独立插件。
- 重写 Vue 前端请求地址、API Key 配置和结果展示。
- 重新设计 PyQt 客户端是否继续保留。
