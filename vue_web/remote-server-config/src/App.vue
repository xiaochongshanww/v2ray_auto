<template>
  <div id="app">
    <h1>V2Ray Auto - 一键部署</h1>

    <div v-if="!deployed" class="form-container">
      <!-- API Key -->
      <div class="form-group">
        <label for="apiKey">API Key:</label>
        <input type="password" id="apiKey" v-model="apiKey" placeholder="输入 API Key" />
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
  </div>
</template>

<script>
import io from "socket.io-client";

export default {
  data() {
    return {
      apiKey: "",
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
      socket: null,
    };
  },
  mounted() {
    this.socket = io("/", {
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
  methods: {
    deploy() {
      if (!this.apiKey) {
        alert("请输入 API Key");
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

      fetch("/api/deploy", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": this.apiKey,
        },
        body: JSON.stringify(payload),
      })
        .then((response) => {
          if (!response.ok) {
            return response.json().then((err) => {
              throw new Error(err.error || `HTTP ${response.status}`);
            });
          }
          return response.json();
        })
        .then((data) => {
          this.result = data;
          this.deployed = true;
        })
        .catch((error) => {
          this.processOutput += `\n[错误] ${error.message}`;
        })
        .finally(() => {
          this.deploying = false;
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
</style>
