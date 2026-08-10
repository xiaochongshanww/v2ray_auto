<template>
  <div id="app">
    <h1>V2Ray Auto - 一键部署</h1>

    <!-- 更新状态 -->
    <div v-if="isDesktop && updateStatus" class="update-banner" :class="'update-' + updateStatus.state">
      <template v-if="updateStatus.state === 'checking'">正在检查更新...</template>
      <template v-else-if="updateStatus.state === 'available'">发现新版本 v{{ updateStatus.version }}，正在下载...</template>
      <template v-else-if="updateStatus.state === 'downloaded'">新版本 v{{ updateStatus.version }} 已下载，重启应用完成更新</template>
      <template v-else-if="updateStatus.state === 'not-available'">已是最新版本</template>
      <template v-else-if="updateStatus.state === 'error'">检查更新失败：{{ updateStatus.error }}</template>
    </div>

    <div v-if="!deployed" class="form-container">
      <!-- 节点管理（桌面端） -->
      <div v-if="isDesktop" class="node-bar">
        <label for="nodeSelect">节点:</label>
        <select id="nodeSelect" :value="selectedNodeId" @change="onNodeSelect">
          <option value="">未选择</option>
          <option v-for="n in nodes" :key="n.id" :value="n.id">{{ n.name }}</option>
        </select>
        <button type="button" class="btn btn-secondary" @click="saveCurrentNode">保存当前为节点</button>
        <button type="button" class="btn btn-secondary" @click="showNodeManager = !showNodeManager">
          {{ showNodeManager ? '收起节点管理' : '节点管理' }}
        </button>
      </div>

      <!-- 节点管理列表 -->
      <div v-if="isDesktop && showNodeManager" class="node-manager">
        <table class="history-table">
          <thead>
            <tr>
              <th>名称</th>
              <th>服务器</th>
              <th>用户名</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="n in nodes" :key="n.id">
              <td>{{ n.name }}</td>
              <td>{{ n.serverIp }}:{{ n.serverPort }}</td>
              <td>{{ n.username }}</td>
              <td>
                <button type="button" class="btn btn-secondary" @click="selectNode(n.id)">载入</button>
                <button type="button" class="btn btn-secondary" @click="deleteNode(n.id)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="!nodes.length" class="node-empty">暂无节点。填写下方表单后点击「保存当前为节点」。</p>
      </div>

      <!-- 服务器配置 -->
      <fieldset>
        <legend>服务器连接</legend>
        <div class="form-group">
          <label for="ip">服务器 IP:</label>
          <input type="text" id="ip" v-model="serverIp" required />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label for="port">SSH 端口:</label>
            <input type="number" id="port" v-model="serverPort" required />
          </div>
          <div class="form-group">
            <label for="listenPort">监听端口:</label>
            <input type="number" id="listenPort" v-model="listenPort" placeholder="默认 443" />
          </div>
        </div>
        <div class="form-group">
          <label for="username">用户名:</label>
          <input type="text" id="username" v-model="username" required />
        </div>
        <div class="form-group">
          <label for="password">密码:</label>
          <input type="password" id="password" v-model="password" />
        </div>
        <div v-if="isDesktop" class="form-group">
          <label>
            <input type="checkbox" v-model="rememberPassword" />
            记住密码（本机加密保存）
          </label>
        </div>
      </fieldset>

      <!-- 部署配置 -->
      <fieldset>
        <legend>部署配置</legend>
        <div class="form-group">
          <label for="profile">配置模板:</label>
          <select id="profile" v-model="profile">
            <option value="vless-reality-vision">VLESS + REALITY + Vision（默认）</option>
            <option value="vmess-tcp-legacy">VMess TCP（旧版兼容）</option>
          </select>
        </div>

        <template v-if="profile === 'vless-reality-vision'">
          <div class="form-group">
            <label for="realityServerName">REALITY ServerName:</label>
            <input type="text" id="realityServerName" v-model="realityServerName" />
          </div>
          <div class="form-group">
            <label for="realityDest">REALITY Dest:</label>
            <input type="text" id="realityDest" v-model="realityDest" />
          </div>
        </template>

        <div class="form-group">
          <label for="email">通知邮箱（可选）:</label>
          <input type="email" id="email" v-model="email" />
        </div>
      </fieldset>

      <button type="button" class="btn" @click="deploy" :disabled="deploying">
        {{ deploying ? '部署中...' : '开始部署' }}
      </button>
    </div>

    <!-- 配置过程输出 -->
    <div v-if="processOutput.length" class="output-container">
      <h2>部署日志</h2>
      <div class="output-box" ref="processOutputBox">
        <pre class="output-pre">{{ processOutput }}</pre>
      </div>
    </div>

    <!-- 部署结果 -->
    <div v-if="result" class="output-container">
      <h2>部署成功</h2>
      <div class="result-card">
        <div class="result-row">
          <span class="result-label">服务器:</span>
          <span class="result-value">{{ result.server }}</span>
        </div>
        <div class="result-row">
          <span class="result-label">端口:</span>
          <span class="result-value">{{ result.port }}</span>
        </div>
        <div class="result-row">
          <span class="result-label">核心:</span>
          <span class="result-value">{{ result.core }}</span>
        </div>
        <div class="result-row">
          <span class="result-label">模板:</span>
          <span class="result-value">{{ result.profile }}</span>
        </div>
        <div class="result-row">
          <span class="result-label">UUID:</span>
          <span class="result-value result-uuid">{{ result.uuid }}</span>
        </div>
        <div class="result-row">
          <span class="result-label">客户端 URI:</span>
          <span class="result-value result-uri">{{ result.clientUri }}</span>
        </div>
      </div>
      <div class="center">
        <button @click="copyResult" class="btn">复制 URI</button>
        <button @click="reset" class="btn btn-secondary">重新部署</button>
      </div>
    </div>

    <!-- 部署历史 -->
    <div v-if="isDesktop && history.length" class="output-container">
      <h2>部署历史</h2>
      <table class="history-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>服务器</th>
            <th>模板</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in history" :key="item.id">
            <td>{{ item.time }}</td>
            <td>{{ item.server }}</td>
            <td>{{ item.profile }}</td>
            <td>
              <span :class="item.status === 'ok' ? 'status-ok' : 'status-error'">
                {{ item.status === 'ok' ? '成功' : '失败' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="center">
        <button @click="clearHistory" class="btn btn-secondary">清空历史</button>
      </div>
    </div>
  </div>
</template>

<script>
import io from "socket.io-client";

export default {
  data() {
    return {
      apiBase: "",
      isDesktop: false,
      rememberPassword: false,
      serverIp: "",
      serverPort: "22",
      listenPort: "",
      username: "",
      password: "",
      email: "",
      profile: "vless-reality-vision",
      realityServerName: "www.microsoft.com",
      realityDest: "www.microsoft.com:443",
      deploying: false,
      deployed: false,
      processOutput: "",
      result: null,
      history: [],
      nodes: [],
      selectedNodeId: "",
      showNodeManager: false,
      updateStatus: null,
      socket: null,
    };
  },
  async mounted() {
      if (window.v2rayDesktop) {
        this.isDesktop = true;
        try {
          const base = await window.v2rayDesktop.getApiBase();
          if (base) this.connectSocket(base);
          window.v2rayDesktop.onBackendReady((base) => this.connectSocket(base));
        } catch (e) {
          this.processOutput += `\n[错误] 桌面端初始化失败: ${e.message}`;
        }
      this.loadHistory();
      this.restoreLastServer();
      this.loadNodes();
      this.listenUpdater();
    } else {
      this.connectSocket("");
    }
  },
  methods: {
    connectSocket(base) {
      if (this.socket) return;
      this.apiBase = base || "";
      this.socket = io(this.apiBase || "/", {
        transports: ["websocket"],
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
      });
      this.socket.on("process_update", (data) => {
        this.processOutput += `\n${data.message}`;
        this.$nextTick(() => {
          const box = this.$refs.processOutputBox;
          if (box) box.scrollTop = box.scrollHeight;
        });
      });
    },
    async deploy() {
      if (this.isDesktop && !this.apiBase) {
        alert("后端尚未就绪");
        return;
      }
      if (!this.serverIp || !this.username) {
        alert("请填写服务器 IP 和用户名");
        return;
      }
      this.deploying = true;
      this.processOutput = "";
      this.result = null;
      this.deployed = false;

      const payload = {
        host: this.serverIp,
        serverPort: parseInt(this.serverPort),
        username: this.username,
        password: this.password || undefined,
        email: this.email || undefined,
        profile: this.profile,
      };

      if (this.listenPort) {
        payload.listenPort = parseInt(this.listenPort);
      }
      if (this.profile === "vless-reality-vision") {
        payload.realityServerName = this.realityServerName;
        payload.realityDest = this.realityDest;
      }

      try {
        const response = await fetch(`${this.apiBase}/api/deploy`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error || `HTTP ${response.status}`);
        }
        this.result = data;
        this.deployed = true;
        this.addHistory({
          server: data.server || this.serverIp,
          port: data.port,
          profile: data.profile,
          clientUri: data.clientUri,
          status: "ok",
        });
        this.persistIfRemembered();
      } catch (error) {
        this.processOutput += `\n[错误] ${error.message}`;
        this.addHistory({
          server: this.serverIp,
          profile: this.profile,
          status: "error",
          error: error.message,
        });
      } finally {
        this.deploying = false;
      }
    },
    async persistIfRemembered() {
      if (!this.rememberPassword || !this.isDesktop || !this.password) return;
      const key = `${this.serverIp}@${this.username}`;
      await window.v2rayDesktop.credential.save(key, this.password);
      await window.v2rayDesktop.credential.save("last-key", key);
    },
    async restoreLastServer() {
      if (!this.isDesktop) return;
      const key = await window.v2rayDesktop.credential.load("last-key");
      if (!key) return;
      const pw = await window.v2rayDesktop.credential.load(key);
      if (pw === null) return;
      const [host, username] = key.split("@");
      this.serverIp = host || this.serverIp;
      this.username = username || this.username;
      this.password = pw;
      this.rememberPassword = true;
    },
    async loadHistory() {
      if (!this.isDesktop) return;
      try {
        this.history = await window.v2rayDesktop.history.list();
      } catch (e) {
        this.processOutput += `\n[错误] 读取历史失败: ${e.message}`;
      }
    },
    async addHistory(record) {
      if (!this.isDesktop) return;
      this.history = await window.v2rayDesktop.history.add(record);
    },
    async clearHistory() {
      if (!this.isDesktop) return;
      if (!confirm("确定清空部署历史？")) return;
      this.history = await window.v2rayDesktop.history.clear();
    },
    async loadNodes() {
      if (!this.isDesktop) return;
      try {
        this.nodes = await window.v2rayDesktop.nodes.list();
      } catch (e) {
        this.processOutput += `\n[错误] 读取节点失败: ${e.message}`;
        return;
      }
      const active = localStorage.getItem("activeNodeId");
      const node = this.nodes.find((n) => n.id === active);
      if (node) {
        this.applyNodeToForm(node);
        this.selectedNodeId = node.id;
        const pw = await window.v2rayDesktop.credential.load(
          `${node.serverIp}@${node.username}`
        );
        if (pw !== null) {
          this.password = pw;
          this.rememberPassword = true;
        }
      }
    },
    onNodeSelect(event) {
      if (event.target.value) this.selectNode(event.target.value);
    },
    async selectNode(id) {
      const node = this.nodes.find((n) => n.id === id);
      if (!node) return;
      this.applyNodeToForm(node);
      this.selectedNodeId = id;
      localStorage.setItem("activeNodeId", id);
      const pw = await window.v2rayDesktop.credential.load(
        `${node.serverIp}@${node.username}`
      );
      if (pw !== null) {
        this.password = pw;
        this.rememberPassword = true;
      }
    },
    applyNodeToForm(node) {
      this.serverIp = node.serverIp || "";
      this.serverPort = node.serverPort || "22";
      this.listenPort = node.listenPort || "";
      this.username = node.username || "";
      this.profile = node.profile || "vless-reality-vision";
      this.realityServerName = node.realityServerName || "www.microsoft.com";
      this.realityDest = node.realityDest || "www.microsoft.com:443";
      this.email = node.email || "";
    },
    async saveCurrentNode() {
      if (!this.serverIp || !this.username) {
        alert("请先填写服务器 IP 和用户名");
        return;
      }
      const node = {
        name: `${this.serverIp}（${this.username}）`,
        serverIp: this.serverIp,
        serverPort: this.serverPort,
        listenPort: this.listenPort,
        username: this.username,
        profile: this.profile,
        realityServerName: this.realityServerName,
        realityDest: this.realityDest,
        email: this.email,
      };
      const existing = this.nodes.find(
        (n) => n.serverIp === this.serverIp && n.username === this.username
      );
      if (existing) node.id = existing.id;
      await window.v2rayDesktop.nodes.upsert(node);
      await this.loadNodes();
      const saved = this.nodes.find(
        (n) => n.serverIp === this.serverIp && n.username === this.username
      );
      if (saved) {
        this.selectedNodeId = saved.id;
        localStorage.setItem("activeNodeId", saved.id);
      }
    },
    async deleteNode(id) {
      if (!confirm("确定删除该节点？")) return;
      await window.v2rayDesktop.nodes.delete(id);
      await this.loadNodes();
      if (this.selectedNodeId === id) {
        this.selectedNodeId = "";
        localStorage.removeItem("activeNodeId");
      }
    },
    listenUpdater() {
      if (!this.isDesktop) return;
      window.v2rayDesktop.updater.onStatus((status) => {
        this.updateStatus = status;
        clearTimeout(this._updateTimer);
        this._updateTimer = setTimeout(() => {
          this.updateStatus = null;
        }, 8000);
      });
    },
    copyResult() {
      if (this.result) {
        navigator.clipboard.writeText(this.result.clientUri).then(() => {
          alert("客户端 URI 已复制到剪贴板");
        });
      }
    },
    reset() {
      this.deployed = false;
      this.result = null;
      this.processOutput = "";
    },
  },
};
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  color: #333;
  padding: 20px;
  max-width: 720px;
  margin: 0 auto;
}

h1 {
  font-size: 24px;
  text-align: center;
  margin-bottom: 24px;
}

fieldset {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

legend {
  font-weight: bold;
  font-size: 14px;
  padding: 0 8px;
}

.form-group {
  margin-bottom: 12px;
}

.form-row {
  display: flex;
  gap: 12px;
}

.form-row .form-group {
  flex: 1;
}

label {
  display: block;
  margin-bottom: 4px;
  font-size: 13px;
  font-weight: 600;
  color: #555;
}

input,
select {
  width: 100%;
  padding: 10px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 6px;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

input:focus,
select:focus {
  border-color: #007aff;
  outline: none;
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.15);
}

.btn {
  display: inline-block;
  padding: 12px 32px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  background-color: #007aff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
  width: 100%;
}

.btn:hover {
  background-color: #005bb5;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #6c757d;
  margin-top: 8px;
}

.btn-secondary:hover {
  background-color: #5a6268;
}

.output-container {
  margin-top: 20px;
}

.output-box {
  max-height: 300px;
  overflow-y: auto;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 8px;
  font-family: "SF Mono", "Fira Code", monospace;
  font-size: 12px;
  line-height: 1.5;
}

.output-pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.result-card {
  background: #f0f9f0;
  border: 1px solid #b8e6b8;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.result-row {
  display: flex;
  padding: 8px 0;
  border-bottom: 1px solid #e0e0e0;
}

.result-row:last-child {
  border-bottom: none;
}

.result-label {
  font-weight: 600;
  width: 120px;
  flex-shrink: 0;
  color: #555;
}

.result-value {
  word-break: break-all;
}

.result-uuid {
  font-family: "SF Mono", "Fira Code", monospace;
  font-size: 13px;
}

.result-uri {
  font-family: "SF Mono", "Fira Code", monospace;
  font-size: 13px;
  color: #1a7a1a;
}

.center {
  text-align: center;
}

.history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.history-table th,
.history-table td {
  border: 1px solid #d0d0d0;
  padding: 6px 10px;
  text-align: left;
}

.history-table th {
  background: #f5f5f5;
}

.status-ok {
  color: #1a7a1a;
  font-weight: 600;
}

.status-error {
  color: #c0392b;
  font-weight: 600;
}

.node-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.node-bar label {
  font-weight: 600;
}

.node-manager {
  margin-bottom: 16px;
}

.node-empty {
  color: #888;
  font-size: 13px;
}

.update-banner {
  padding: 8px 12px;
  margin-bottom: 16px;
  border-radius: 6px;
  font-size: 13px;
  background: #eaf4fe;
  border: 1px solid #b8d9f5;
  color: #1a5276;
}

.update-available,
.update-downloaded {
  background: #fef9e7;
  border-color: #f0d8a0;
  color: #7d6608;
}

.update-error {
  background: #fdecea;
  border-color: #f0b8b8;
  color: #7b241c;
}
</style>
