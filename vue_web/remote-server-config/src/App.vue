<template>
  <div id="app">
    <h1>服务器配置</h1>
    <form @submit.prevent="configureServer">
      <div class="form-group">
        <label for="ip">服务器 IP:</label>
        <input type="text" id="ip" v-model="serverIp" required />
      </div>
      <div class="form-group">
        <label for="port">服务器端口:</label>
        <input type="number" id="port" v-model="serverPort" required />
      </div>
      <div class="form-group">
        <label for="username">用户名:</label>
        <input type="text" id="username" v-model="username" required />
      </div>
      <div class="form-group">
        <label for="password">密码:</label>
        <input type="password" id="password" v-model="password" required />
      </div>
      <div class="form-group">
        <label for="email">接收邮箱:</label>
        <input type="email" id="email" v-model="email" required />
      </div>
      <div class="form-group">
        <label for="os">操作系统类型:</label>
        <select id="os" v-model="osType" required>
          <option value="centos">Centos</option>
          <option value="ubuntu">Ubuntu</option>
          <option value="azure ubuntu">Azure Ubuntu</option>
          <option value="debian">Debian</option>
          <option value="fedora">Fedora</option>
          <option value="redhat">Redhat</option>
        </select>
      </div>
      <button type="submit" class="btn">配置服务器</button>
    </form>

    <!-- 配置过程输出框部分 -->
    <div v-if="processOutput" class="output-container">
      <h2>配置过程</h2>
      <div class="output-box" ref="processOutputBox">
        <pre class="config-process-pre">{{ processOutput }}</pre>
      </div>
    </div>

    <!-- 配置结果输出框部分 -->
    <div v-if="resultOutput" class="output-container">
      <h2>配置结果</h2>
      <div class="output-box" ref="resultOutputBox">
        <pre class="config-result-pre">{{ resultOutput }}</pre>
      </div>
      <div class="center-config-button">
        <button @click="copyToClipboard" class="btn">复制配置</button>
      </div>
    </div>
  </div>
</template>

<script>
import io from "socket.io-client";

export default {
  data() {
    return {
      serverIp: "",
      serverPort: "22",
      username: "",
      password: "",
      osType: "centos",
      email: "",
      processOutput: "",
      resultOutput: "",
      socket: null,
    };
  },
  mounted() {
    this.socket = io("http://127.0.0.1:5000/", {
    // path: '/socket.io/',
    transports: ['websocket'],
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    timeout: 20000,
    autoConnect: true,
    debug: true
    });
  },
  methods: {
    configureServer() {
      this.processOutput = `正在配置服务器...\n服务器 IP: ${this.serverIp}\n服务器端口: ${this.serverPort}\n用户名: ${this.username}\n操作系统类型: ${this.osType}`;
      this.resultOutput = "";

      // Use fetch to send a POST request to the server
      fetch("http://127.0.0.1:5000/api/configure", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          serverIp: this.serverIp,
          serverPort: this.serverPort,
          username: this.username,
          password: this.password,
          email: this.email,
          os: this.osType,
        }),
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
        })
        .then((data) => {
          if (data.processOutput) {
            this.processOutput += `\n${data.processOutput}`;
          }
          if (data.resultOutput) {
            this.resultOutput = data.resultOutput;
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          this.processOutput += `\n配置接口返回错误: ${error.message}`;
        });

      // Listen for process updates from the server
      this.socket.on("process_update", (data) => {
        this.processOutput += `\n${data.message}`;
        this.$nextTick(() => {
          const outputBox = this.$refs.processOutputBox;
          outputBox.scrollTop = outputBox.scrollHeight;
        });
      });

      // Listen for the final result from the server
      this.socket.on("configuration_complete", (data) => {
        this.resultOutput = data.result;
        this.$nextTick(() => {
          const outputBox = this.$refs.resultOutputBox;
          outputBox.scrollTop = outputBox.scrollHeight;

          // 页面滚动到最底部
          window.scrollTo({
            top: document.body.scrollHeight,
            behavior: "smooth",  // 平滑滚动
          });
        });
        this.socket.disconnect();
      });
    },
    copyToClipboard() {
      navigator.clipboard
        .writeText(this.resultOutput)
        .then(() => {
          alert("配置已复制到剪贴板");
        })
        .catch((err) => {
          console.error("Failed to copy text: ", err);
        });
    },
  },
};
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #333;
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
  background: #f9f9f9;
  border-radius: 10px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

h1 {
  font-size: 24px;
  margin-bottom: 20px;
}

form {
  margin: 20px 0;
}

.form-group {
  margin-bottom: 15px;
  text-align: left;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

input,
select {
  width: 100%;
  padding: 10px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 5px;
  box-sizing: border-box;
}

input:focus,
select:focus {
  border-color: #007aff;
  outline: none;
  box-shadow: 0 0 5px rgba(0, 122, 255, 0.5);
}

.btn {
  display: inline-block;
  padding: 10px 20px;
  font-size: 16px;
  color: #fff;
  background-color: #007aff;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.btn:hover {
  background-color: #005bb5;
}

.output-container {
  margin-top: 20px;
  text-align: left;
}

.output-box {
  max-height: 200px; /* 设置最大高度 */
  overflow-y: auto; /* 设置垂直滚动条 */
  background: #fff;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 5px;
}

pre {
  background: #fff;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 5px;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.config-process-pre {
  background: #fff;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 5px;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
}

.config-result-pre {
  background: #fff;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 5px;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
}

.center {
  text-align: center;
}

.center-config-button {
  text-align: center;
  margin-top: 20px;
}

/* 响应式设计 */
@media (max-width: 600px) {
  #app {
    padding: 10px;
    max-width: 100%;
    margin: 0 10px;
  }

  h1 {
    font-size: 20px;
  }

  .btn {
    width: 100%;
    padding: 15px;
    font-size: 18px;
  }

  input,
  select {
    padding: 15px;
    font-size: 16px;
  }
}
</style>