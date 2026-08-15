<template>
  <div id="app">
    <div class="flex h-full">
      <aside class="w-60 shrink-0 bg-white border-r border-slate-200 flex flex-col" style="min-height:100%">
        <div class="flex items-center gap-3 px-5 py-5">
          <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white text-lg font-bold shadow">V</div>
          <div>
            <div class="font-bold text-slate-800 leading-tight">V2Ray Auto</div>
            <div class="text-[11px] text-slate-400 leading-tight">一键部署客户端</div>
          </div>
        </div>
        <nav class="flex-1 px-3 space-y-1">
          <div v-for="item in navItems" :key="item.key"
               class="nav-item px-3 py-2.5 text-sm text-slate-600 cursor-pointer flex items-center gap-3"
               :class="{ active: currentView === item.key }"
               @click="currentView = item.key">
            <el-icon :size="18"><component :is="item.icon" /></el-icon>
            <span>{{ item.label }}</span>
          </div>
        </nav>
        <div class="px-5 py-4 border-t border-slate-100">
          <div class="text-[11px] text-slate-400">v{{ appVersion }}</div>
        </div>
      </aside>

      <main class="flex-1 overflow-y-auto">
        <div class="max-w-6xl mx-auto px-8 py-8">

          <!-- ================= 部署 ================= -->
          <div v-if="currentView === 'deploy'">
            <div class="flex items-center justify-between mb-6">
              <div>
                <h1 class="text-2xl font-bold text-slate-800">一键部署</h1>
                <p class="text-sm text-slate-400 mt-1">连接服务器，自动安装 Xray 并生成客户端配置</p>
              </div>
            </div>

            <div class="grid grid-cols-12 gap-6">
              <!-- 服务器连接 -->
              <div class="card p-6 col-span-12 xl:col-span-4 xl:row-span-2">
                <div class="flex items-center gap-2 mb-5">
                  <el-icon :size="16" color="#4f46e5"><Monitor /></el-icon>
                  <h2 class="font-semibold text-slate-700">服务器连接</h2>
                </div>
                <el-form label-position="top" size="large">
                  <el-form-item label="服务器 IP">
                    <el-input v-model="serverIp" placeholder="例如 1.2.3.4" />
                  </el-form-item>
                  <div class="grid grid-cols-2 gap-3">
                    <el-form-item label="SSH 端口">
                      <el-input-number v-model="serverPort" :min="1" :max="65535" style="width:100%" />
                    </el-form-item>
                    <el-form-item label="监听端口">
                      <el-input v-model="listenPort" placeholder="默认 443" />
                    </el-form-item>
                  </div>
                  <el-form-item label="用户名">
                    <el-input v-model="username" placeholder="root" />
                  </el-form-item>
                  <el-form-item label="密码">
                    <el-input v-model="password" type="password" show-password placeholder="或使用已保存凭据" />
                  </el-form-item>
                  <el-checkbox v-model="rememberPassword" class="text-sm">本机加密保存密码</el-checkbox>
                </el-form>
              </div>

              <!-- 目标摘要 -->
              <div class="card p-6 flex items-center justify-between col-span-12 xl:col-span-8">
                <div>
                  <div class="text-sm text-slate-500 mb-1">目标：{{ serverIp || '未填写' }}</div>
                  <div class="text-xs text-slate-400">SSH {{ username || 'root' }}@{{ serverIp || '?' }}:{{ serverPort }} · {{ profileLabel }}</div>
                </div>
                <el-button type="primary" size="large" :loading="deploying" @click="startDeploy" class="!px-10 !py-6 !text-base">
                  {{ deploying ? '部署中…' : '开始部署' }}
                </el-button>
                <el-button v-if="deploying" size="large" class="!py-6" @click="cancelDeploy">取消部署</el-button>
              </div>

              <!-- 部署日志 -->
              <div class="card col-span-12 xl:col-span-8">
                <div class="flex items-center gap-2 px-6 pt-5 pb-4">
                  <el-icon :size="16" color="#4f46e5"><Document /></el-icon>
                  <h2 class="font-semibold text-slate-700">部署日志</h2>
                  <span v-if="deploying" class="text-xs text-brand-600 ml-auto">进行中…</span>
                  <span v-else-if="deployed" class="text-xs text-emerald-600 ml-auto">已完成</span>
                  <span v-else-if="deployFailed" class="text-xs text-rose-600 ml-auto font-semibold">部署失败</span>
                </div>
                <div class="px-6 pb-6">
                  <div class="terminal" ref="terminalBox">
                    <div v-for="(line, i) in logLines" :key="i">
                      <span class="dim">$</span> {{ line }}
                    </div>
                    <div v-if="deploying" class="dim">…</div>
                  </div>
                </div>
              </div>

              <!-- 部署配置 -->
              <div class="card p-6 col-span-12 xl:col-span-4">
                <div class="flex items-center gap-2 mb-5">
                  <el-icon :size="16" color="#4f46e5"><Setting /></el-icon>
                  <h2 class="font-semibold text-slate-700">部署配置</h2>
                </div>
                <el-form label-position="top" size="large">
                  <el-form-item label="配置模板">
                    <el-select v-model="profile" style="width:100%">
                      <el-option value="vless-reality-vision" label="VLESS + REALITY + Vision（默认）" />
                      <el-option value="vmess-tcp-legacy" label="VMess TCP（旧版兼容）" />
                    </el-select>
                  </el-form-item>
                  <template v-if="profile === 'vless-reality-vision'">
                    <el-form-item label="REALITY ServerName">
                      <el-input v-model="realityServerName" placeholder="www.apple.com" />
                    </el-form-item>
                    <el-form-item label="REALITY Dest">
                      <el-input v-model="realityDest" placeholder="www.apple.com:443" />
                    </el-form-item>
                  </template>
                  <el-form-item label="通知邮箱（可选）">
                    <el-input v-model="email" placeholder="部署结果发送到此邮箱" />
                  </el-form-item>
                  <div class="flex items-center justify-between pt-1">
                    <span class="form-label !mb-0">安装 Warp 加速</span>
                    <el-switch v-model="installWarp" />
                  </div>
                </el-form>
              </div>

              <!-- 部署结果 -->
              <div v-if="result" ref="resultCard" class="card p-6 col-span-12 xl:col-span-8">
                <div class="flex items-center gap-2 mb-4">
                  <el-icon :size="18" color="#10b981"><SuccessFilled /></el-icon>
                  <h2 class="font-semibold text-slate-700 text-lg">部署成功</h2>
                </div>
                <div v-if="result.warning" class="flex items-start gap-2 mb-4 rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-700">
                  <el-icon :size="18" class="mt-0.5 shrink-0"><WarningFilled /></el-icon>
                  <div>
                    <div class="font-semibold mb-1">配置可能无法使用</div>
                    <div>{{ result.warning }}</div>
                  </div>
                </div>
                <div class="flex gap-6">
                  <div class="flex-1 space-y-2.5 text-sm">
                    <div class="flex justify-between border-b border-slate-50 pb-2"><span class="text-slate-400">服务器</span><span class="font-medium text-slate-700">{{ result.server }}</span></div>
                    <div class="flex justify-between border-b border-slate-50 pb-2"><span class="text-slate-400">端口</span><span class="font-medium text-slate-700">{{ result.port }}</span></div>
                    <div class="flex justify-between border-b border-slate-50 pb-2"><span class="text-slate-400">核心</span><span class="font-medium text-slate-700">{{ result.core }}</span></div>
                    <div class="flex justify-between border-b border-slate-50 pb-2"><span class="text-slate-400">UUID</span><span class="font-mono text-xs text-slate-700 break-all">{{ result.uuid }}</span></div>
                    <div class="pt-2">
                      <div class="text-xs text-slate-400 mb-1.5">客户端 URI</div>
                      <div class="bg-slate-50 rounded-lg px-3 py-2 font-mono text-xs text-slate-600 break-all border border-slate-200">{{ result.clientUri }}</div>
                      <div class="flex gap-2 mt-3">
                        <el-button type="primary" size="small" @click="copyUri">复制 URI</el-button>
                        <el-button size="small" @click="resetDeploy">重新部署</el-button>
                      </div>
                    </div>
                  </div>
                  <div class="flex flex-col items-center justify-center shrink-0">
                    <div class="qrcode">
                      <canvas ref="qrCanvas" width="128" height="128"></canvas>
                    </div>
                    <div class="text-[11px] text-slate-400 mt-2">扫码连接</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- ================= 部署历史 ================= -->
          <div v-if="currentView === 'history'">
            <div class="flex items-center justify-between mb-6">
              <div>
                <h1 class="text-2xl font-bold text-slate-800">部署历史</h1>
                <p class="text-sm text-slate-400 mt-1">最近 {{ history.length }} 次部署记录</p>
              </div>
              <el-popconfirm title="确认清空全部历史？" @confirm="clearHistory">
                <template #reference><el-button type="danger" plain>清空历史</el-button></template>
              </el-popconfirm>
            </div>
            <div class="card">
              <el-table :data="history" style="width:100%">
                <el-table-column label="时间" min-width="170">
                  <template #default="{ row }">{{ formatTime(row.time) }}</template>
                </el-table-column>
                <el-table-column prop="server" label="服务器" min-width="150" />
                <el-table-column label="模板" min-width="160">
                  <template #default="{ row }">{{ profileName(row.profile) }}</template>
                </el-table-column>
                <el-table-column label="状态" width="110" align="center">
                  <template #default="{ row }">
                    <el-tag v-if="row.status === 'ok'" type="success" effect="light" round>成功</el-tag>
                    <el-tag v-else-if="row.status === 'uninstalled'" type="info" effect="plain" round>已卸载</el-tag>
                    <el-tag v-else-if="row.status === 'cancelled'" type="warning" effect="light" round>已取消</el-tag>
                    <el-tag v-else type="danger" effect="light" round>失败</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="客户端 URI" min-width="260">
                  <template #default="{ row }">
                    <div v-if="row.clientUri" class="font-mono text-xs text-slate-500 truncate max-w-56">{{ row.clientUri }}</div>
                    <span v-else class="text-slate-300">—</span>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="140" align="center">
                  <template #default="{ row }">
                    <el-button size="small" link type="primary" @click="viewHistory(row)">查看</el-button>
                    <el-button v-if="row.status === 'ok'" size="small" link type="danger" @click="openUninstallDialog(row)">卸载</el-button>                  </template>
                </el-table-column>
              </el-table>

              <el-dialog v-model="historyDialogVisible" title="部署详情" width="560">
                <div v-if="historyDetail" class="space-y-2.5 text-sm">
                  <div class="flex justify-between border-b border-slate-100 pb-2"><span class="text-slate-400">时间</span><span class="font-medium text-slate-700">{{ formatTime(historyDetail.time) }}</span></div>
                  <div class="flex justify-between border-b border-slate-100 pb-2"><span class="text-slate-400">服务器</span><span class="font-medium text-slate-700">{{ historyDetail.server }}{{ historyDetail.port ? ':' + historyDetail.port : '' }}</span></div>
                  <div v-if="historyDetail.username" class="flex justify-between border-b border-slate-100 pb-2"><span class="text-slate-400">用户名</span><span class="font-medium text-slate-700">{{ historyDetail.username }}</span></div>
                  <div class="flex justify-between border-b border-slate-100 pb-2"><span class="text-slate-400">模板</span><span class="font-medium text-slate-700">{{ profileName(historyDetail.profile) }}</span></div>
                  <div class="flex justify-between border-b border-slate-100 pb-2"><span class="text-slate-400">状态</span>
                    <el-tag v-if="historyDetail.status === 'ok'" type="success" effect="light" round>成功</el-tag>
                    <el-tag v-else-if="historyDetail.status === 'uninstalled'" type="info" effect="plain" round>已卸载</el-tag>
                    <el-tag v-else-if="historyDetail.status === 'cancelled'" type="warning" effect="light" round>已取消</el-tag>
                    <el-tag v-else type="danger" effect="light" round>失败</el-tag>
                  </div>
                  <div v-if="historyDetail.profile === 'vless-reality-vision'" class="flex justify-between border-b border-slate-100 pb-2">
                    <span class="text-slate-400">REALITY ServerName</span><span class="font-medium text-slate-700">{{ historyDetail.realityServerName || '—' }}</span>
                  </div>
                  <div v-if="historyDetail.profile === 'vless-reality-vision'" class="flex justify-between border-b border-slate-100 pb-2">
                    <span class="text-slate-400">REALITY Dest</span><span class="font-medium text-slate-700">{{ historyDetail.realityDest || '—' }}</span>
                  </div>
                  <div v-if="historyDetail.uuid" class="flex justify-between border-b border-slate-100 pb-2">
                    <span class="text-slate-400 shrink-0 mr-4">UUID</span><span class="font-mono text-xs text-slate-700 break-all text-right">{{ historyDetail.uuid }}</span>
                  </div>
                  <div>
                    <div class="text-xs text-slate-400 mb-1.5">客户端 URI</div>
                    <div class="bg-slate-50 rounded-lg px-3 py-2 font-mono text-xs text-slate-600 break-all border border-slate-200">{{ historyDetail.clientUri || '—' }}</div>
                    <div v-if="historyDetail.clientUri" class="flex flex-col items-center mt-4">
                      <div class="border border-slate-100 rounded-lg p-3 bg-white">
                        <canvas ref="historyQrCanvas" width="160" height="160"></canvas>
                      </div>
                      <div class="text-[11px] text-slate-400 mt-2">扫码连接</div>
                    </div>
                  </div>
                  <div v-if="historyDetail.error">
                    <div class="text-xs text-slate-400 mb-1.5">错误信息</div>
                    <div class="bg-rose-50 rounded-lg px-3 py-2 font-mono text-xs text-rose-600 break-all border border-rose-200">{{ historyDetail.error }}</div>
                  </div>
                </div>
                <template #footer>
                  <el-button v-if="historyDetail && historyDetail.clientUri" type="primary" size="small" @click="copyHistoryUri">复制 URI</el-button>
                  <el-button size="small" @click="historyDialogVisible = false">关闭</el-button>
                </template>
              </el-dialog>
            </div>
          </div>

          <el-dialog v-model="uninstallDialogVisible" title="卸载部署" width="520">
            <div v-if="uninstallTarget" class="space-y-4 text-sm">
              <div class="bg-rose-50 border border-rose-200 rounded-lg px-4 py-3 text-rose-700">
                将停止并禁用 <span class="font-mono">{{ profileName(uninstallTarget.profile) }}</span> 服务，删除远端配置与状态文件，并关闭已开放的端口。此操作不可撤销。
              </div>
              <div class="flex justify-between border-b border-slate-100 pb-2"><span class="text-slate-400">服务器</span><span class="font-medium text-slate-700">{{ uninstallTarget.server }}{{ uninstallTarget.port ? ':' + uninstallTarget.port : '' }}</span></div>
              <el-form label-position="top" @submit.prevent>
                <el-form-item label="SSH 密码" :required="!savedCredentialAvailable">
                  <el-input v-model="uninstallPassword" type="password" show-password
                            :placeholder="savedCredentialAvailable ? '已使用本机保存的密码（可覆盖）' : '请输入服务器 SSH 密码'" />
                </el-form-item>
              </el-form>
              <div v-if="uninstalling" class="terminal !h-40 !text-[12px]" ref="uninstallTerminal">
                <div v-for="(line, i) in uninstallLogs" :key="i"><span class="dim">$</span> {{ line }}</div>
              </div>
              <div v-if="uninstallResult" class="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-emerald-700">
                <div class="font-semibold mb-1">卸载完成</div>
                <div class="space-y-1 text-xs">
                  <div>服务停止：{{ uninstallResult.stoppedService ? '是' : '无需停止' }}</div>
                  <div>配置删除：{{ uninstallResult.removedConfig ? '是' : '未找到' }}</div>
                  <div>状态删除：{{ uninstallResult.removedState ? '是' : '未找到' }}</div>
                  <div>防火墙关闭：{{ uninstallResult.closedFirewall ? '是' : '无规则' }}</div>
                </div>
              </div>
            </div>
            <template #footer>
              <el-button v-if="!uninstallResult" size="small" :disabled="uninstalling" @click="uninstallDialogVisible = false">取消</el-button>
              <el-button v-if="!uninstallResult" size="small" type="danger" :loading="uninstalling" @click="confirmUninstall">确认卸载</el-button>
              <el-button v-else size="small" type="primary" @click="uninstallDialogVisible = false">完成</el-button>
            </template>
          </el-dialog>

          <!-- ================= 设置 ================= -->
          <div v-if="currentView === 'settings'">
            <h1 class="text-2xl font-bold text-slate-800 mb-6">设置</h1>
            <div class="max-w-2xl space-y-6">
              <div class="card p-6">
                <h2 class="font-semibold text-slate-700 mb-4">更新</h2>
                <div class="flex items-center justify-between">
                  <div class="text-sm text-slate-500">检查 GitHub Release 更新</div>
                  <el-button size="small" :loading="updateStatus && updateStatus.state === 'checking'" @click="checkUpdate">检查更新</el-button>
                </div>
                <div class="text-xs text-slate-400 mt-3">v{{ appVersion }}（当前）</div>
              </div>
              <div class="card p-6">
                <h2 class="font-semibold text-slate-700 mb-4">日志</h2>
                <div class="flex items-center justify-between">
                  <div class="text-sm text-slate-500">查看部署日志文件，用于排查问题</div>
                  <el-button size="small" @click="openLogDialog">查看日志</el-button>
                </div>
              </div>
              <div class="card p-6">
                <h2 class="font-semibold text-slate-700 mb-4">关于</h2>
                <div class="space-y-2 text-sm text-slate-500">
                  <div class="flex justify-between"><span class="text-slate-400">应用</span><span class="font-medium text-slate-700">V2Ray Auto</span></div>
                  <div class="flex justify-between"><span class="text-slate-400">版本</span><span class="font-mono text-xs">v{{ appVersion }}</span></div>
                  <div class="flex justify-between"><span class="text-slate-400">说明</span><span class="text-slate-600">一键部署 Xray 并生成客户端配置</span></div>
                </div>
              </div>
            </div>
          </div>

          <el-dialog v-model="logDialogVisible" title="部署日志" width="680">
            <div class="flex items-center justify-between mb-3">
              <span v-if="logFileName" class="text-xs text-slate-400 font-mono">{{ logFileName }}</span>
              <span v-else></span>
              <el-button size="small" @click="openLogsFolder">在文件夹中显示</el-button>
            </div>
            <pre class="log-viewer">{{ logContent }}</pre>
            <template #footer>
              <el-button size="small" @click="logDialogVisible = false">关闭</el-button>
            </template>
          </el-dialog>

        </div>
      </main>
    </div>
  </div>
</template>

<script>
import io from 'socket.io-client'
import QRCode from 'qrcode'
import { ElMessage, ElNotification } from 'element-plus'

export default {
  data() {
    return {
      currentView: 'deploy',
      navItems: [
        { key: 'deploy', label: '一键部署', icon: 'Promotion' },
        { key: 'history', label: '部署历史', icon: 'Clock' },
        { key: 'settings', label: '设置', icon: 'Setting' },
      ],
      apiBase: '',
      isDesktop: false,
      appVersion: '0.1.0',
      backendOnline: false,
      backendAddr: '',
      rememberPassword: false,
      serverIp: '',
      serverPort: 22,
      listenPort: '',
      username: '',
      password: '',
      email: '',
      profile: 'vless-reality-vision',
      realityServerName: 'www.apple.com',
      realityDest: 'www.apple.com:443',
      installWarp: false,
      deploying: false,
      deployed: false,
      deployFailed: false,
      deployCancelled: false,
      deployErrorMsg: '',
      logLines: [],
      result: null,
      history: [],
      historyDetail: null,
      historyDialogVisible: false,
      logDialogVisible: false,
      logFileName: '',
      logContent: '',
      uninstallDialogVisible: false,
      uninstallTarget: null,
      uninstallPassword: '',
      savedCredentialAvailable: false,
      uninstalling: false,
      uninstallLogs: [],
      uninstallResult: null,
      updateStatus: null,
      socket: null,
    }
  },
  computed: {
    profileLabel() {
      return this.profile === 'vless-reality-vision' ? 'VLESS + REALITY + Vision' : 'VMess TCP'
    },
  },
  watch: {
    currentView(newView) {
      if (newView === 'deploy' && this.result && this.result.clientUri) {
        this.$nextTick(() => this.drawQR(this.result.clientUri))
      }
    },
  },
  async mounted() {
    if (window.v2rayDesktop) {
      this.isDesktop = true
      try {
        this.appVersion = await window.v2rayDesktop.getAppVersion()
        const base = await window.v2rayDesktop.getApiBase()
        if (base) this.connectSocket(base)
        window.v2rayDesktop.onBackendReady((base) => this.connectSocket(base))
      } catch (e) {
        this.logLines.push(`[错误] 桌面端初始化失败: ${e.message}`)
      }
      this.loadHistory()
      this.restoreLastServer()
      this.listenUpdater()
    } else {
      this.connectSocket('')
    }
  },
  methods: {
    profileName(key) {
      return key === 'vless-reality-vision' ? 'VLESS + REALITY + Vision' : 'VMess TCP'
    },
    formatTime(value) {
      if (!value) return '—'
      const d = new Date(value)
      if (Number.isNaN(d.getTime())) return value
      const pad = (n) => String(n).padStart(2, '0')
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
    },
    connectSocket(base) {
      if (this.socket) return
      this.apiBase = base || ''
      this.socket = io(this.apiBase || '/', {
        transports: ['websocket'],
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
      })
      this.socket.on('connect', () => {
        this.backendOnline = true
        this.backendAddr = (this.apiBase || '').replace(/^https?:\/\//, '')
      })
      this.socket.on('disconnect', (reason) => {
        this.backendOnline = false
        if (reason === 'io server disconnect') return
        ElMessage.error('后端服务连接中断')
      })
      this.socket.on('connect_error', () => {
        this.backendOnline = false
        ElMessage.error('无法连接后端服务')
      })
      this.socket.on('reconnect_failed', () => {
        this.backendOnline = false
        ElMessage.error('后端服务连接失败，请检查应用状态后重试')
      })
      this.socket.on('process_update', (data) => {
        if (!data || !data.message) return
        const lines = String(data.message).split('\n').filter((l) => l.length)
        if (this.uninstalling) {
          this.uninstallLogs.push(...lines)
        } else {
          this.logLines.push(...lines)
        }
        this.scrollTerminal()
      })
    },
    scrollTerminal() {
      this.$nextTick(() => {
        const box = this.$refs.terminalBox
        if (box) box.scrollTop = box.scrollHeight
        const uninstallBox = this.$refs.uninstallTerminal
        if (uninstallBox) uninstallBox.scrollTop = uninstallBox.scrollHeight
      })
    },
    scrollToResult() {
      this.$nextTick(() => {
        const card = this.$refs.resultCard
        if (card) card.scrollIntoView({ behavior: 'smooth', block: 'start' })
      })
    },
    parseError(data, status) {
      if (data && data.code && data.message) {
        return { code: data.code, message: data.message, detail: data.detail || '' }
      }
      if (data && data.error) {
        return { message: data.error, detail: '' }
      }
      return { message: `请求失败（HTTP ${status}）`, detail: '' }
    },
    async startDeploy() {
      if (this.isDesktop && !this.apiBase) {
        ElMessage.warning('后端尚未就绪')
        return
      }
      if (!this.serverIp || !this.username) {
        ElMessage.warning('请先填写服务器 IP 和用户名')
        return
      }
      ElNotification.closeAll()
      this.deploying = true
      this.deployed = false
      this.deployFailed = false
      this.deployCancelled = false
      this.deployErrorMsg = ''
      this.result = null
      this.logLines = []

      const payload = {
        host: this.serverIp,
        serverPort: parseInt(this.serverPort),
        username: this.username,
        password: this.password || undefined,
        email: this.email || undefined,
        profile: this.profile,
        installWarp: this.installWarp,
      }
      if (this.listenPort) payload.listenPort = parseInt(this.listenPort)
      if (this.profile === 'vless-reality-vision') {
        payload.realityServerName = this.realityServerName
        payload.realityDest = this.realityDest
      }

      try {
        const response = await fetch(`${this.apiBase}/api/deploy`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        const data = await response.json()
        if (!response.ok) {
          const err = this.parseError(data, response.status)
          throw new Error(err.message, { cause: err })
        }
        this.result = data
        this.deployed = true
        this.addHistory({
          server: data.server || this.serverIp,
          port: data.port,
          username: this.username,
          profile: data.profile,
          clientUri: data.clientUri,
          uuid: data.uuid,
          realityServerName: this.realityServerName,
          realityDest: this.realityDest,
          status: 'ok',
        })
        this.persistIfRemembered()
        this.$nextTick(() => this.drawQR(data.clientUri))
        this.$nextTick(() => this.scrollToResult())
        ElMessage.success('部署成功')
      } catch (error) {
        const err = error.cause || { message: error.message, detail: '' }
        const friendly = err.message
        const detail = err.detail || ''
        const cancelled = err.code === 'operation_cancelled'
        this.logLines.push(cancelled ? `[已取消] ${friendly}` : `[错误] ${friendly}`)
        if (detail && detail !== friendly) this.logLines.push(detail)
        this.addHistory({
          server: this.serverIp,
          username: this.username,
          profile: this.profile,
          realityServerName: this.realityServerName,
          realityDest: this.realityDest,
          status: cancelled ? 'cancelled' : 'error',
          error: err.code ? `${err.code}: ${friendly}` : friendly,
        })
        if (cancelled) {
          this.deployCancelled = true
          ElMessage.info('部署已取消')
        } else {
          ElMessage.error(`部署失败：${friendly}`)
          ElNotification({
            type: 'error',
            title: '部署失败',
            message: friendly,
            duration: 0,
            position: 'bottom-right',
            onClick: () => {
              ElNotification.closeAll()
              const box = this.$refs.terminalBox
              if (box) box.scrollIntoView({ behavior: 'smooth', block: 'start' })
            },
          })
          this.deployFailed = true
          this.deployErrorMsg = friendly
        }
      } finally {
        this.deploying = false
      }
    },
    async cancelDeploy() {
      if (!this.deploying) return
      try {
        await fetch(`${this.apiBase}/api/cancel`, { method: 'POST' })
        this.logLines.push('[取消] 正在请求取消部署…')
      } catch (e) {
        ElMessage.error('发送取消请求失败')
      }
    },
    async persistIfRemembered() {
      if (!this.rememberPassword || !this.isDesktop || !this.password) return
      const key = `${this.serverIp}@${this.username}`
      await window.v2rayDesktop.credential.save(key, this.password)
      await window.v2rayDesktop.credential.save('last-key', key)
    },
    async restoreLastServer() {
      if (!this.isDesktop) return
      const key = await window.v2rayDesktop.credential.load('last-key')
      if (!key) return
      const pw = await window.v2rayDesktop.credential.load(key)
      if (pw === null) return
      const [host, username] = key.split('@')
      this.serverIp = host || this.serverIp
      this.username = username || this.username
      this.password = pw
      this.rememberPassword = true
    },
    async loadHistory() {
      if (!this.isDesktop) return
      try {
        this.history = await window.v2rayDesktop.history.list()
      } catch (e) {
        this.logLines.push(`[错误] 读取历史失败: ${e.message}`)
      }
    },
    async addHistory(record) {
      if (!this.isDesktop) return
      this.history = await window.v2rayDesktop.history.add(record)
    },
    async viewHistory(row) {
      this.historyDetail = row
      this.historyDialogVisible = true
      this.$nextTick(async () => {
        const canvas = this.$refs.historyQrCanvas
        if (canvas && row.clientUri) {
          try {
            await QRCode.toCanvas(canvas, row.clientUri, { width: 160, margin: 1 })
          } catch (e) {
            // ignore QR rendering failures
          }
        }
      })
    },
    async copyHistoryUri() {
      if (this.historyDetail && this.historyDetail.clientUri && navigator.clipboard) {
        await navigator.clipboard.writeText(this.historyDetail.clientUri)
        ElMessage.success('客户端 URI 已复制到剪贴板')
      }
    },
    async clearHistory() {
      if (!this.isDesktop) return
      this.history = await window.v2rayDesktop.history.clear()
      ElMessage.success('历史已清空')
    },
    async openUninstallDialog(row) {
      this.uninstallTarget = row
      this.uninstallPassword = ''
      this.uninstallLogs = []
      this.uninstallResult = null
      this.uninstalling = false
      this.savedCredentialAvailable = false
      if (this.isDesktop) {
        try {
          const key = `${row.server}@${row.username || 'root'}`
          const pw = await window.v2rayDesktop.credential.load(key)
          if (pw !== null) {
            this.savedCredentialAvailable = true
            this.uninstallPassword = pw
          }
        } catch (e) {
          // ignore credential load errors; user can type the password
        }
      }
      this.uninstallDialogVisible = true
    },
    async confirmUninstall() {
      if (!this.isDesktop) return
      const row = this.uninstallTarget
      if (!row) return
      if (!this.uninstallPassword) {
        ElMessage.warning('请填写 SSH 密码')
        return
      }
      this.uninstalling = true
      this.uninstallLogs = []
      const payload = {
        host: row.server,
        serverPort: 22,
        username: row.username || 'root',
        password: this.uninstallPassword,
        profile: row.profile || 'vless-reality-vision',
        listenPort: row.port,
      }
      try {
        const response = await fetch(`${this.apiBase}/api/uninstall`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        const data = await response.json()
        if (!response.ok) {
          const err = this.parseError(data, response.status)
          throw new Error(err.message, { cause: err })
        }
        if (row.id) {
          this.history = await window.v2rayDesktop.history.markUninstalled(row.id)
        }
        this.uninstallResult = data
        this.uninstallLogs.push('卸载完成')
      } catch (error) {
        const err = error.cause || { message: error.message, detail: '' }
        const friendly = err.message
        const detail = err.detail || ''
        this.uninstallLogs.push(`[错误] ${friendly}`)
        if (detail && detail !== friendly) this.uninstallLogs.push(detail)
        ElMessage.error(`卸载失败：${friendly}`)
      } finally {
        this.uninstalling = false
      }
    },
    listenUpdater() {
      if (!this.isDesktop) return
      window.v2rayDesktop.updater.onStatus((status) => {
        this.updateStatus = status
        if (status.state === 'checking') return
        if (status.state === 'not-available') {
          ElMessage.info('已是最新版本')
        } else if (status.state === 'available') {
          ElMessage.info(`发现新版本 v${status.version}，正在下载...`)
        } else if (status.state === 'downloaded') {
          ElMessage.success(`新版本 v${status.version} 已下载，重启应用完成更新`)
        } else if (status.state === 'error') {
          ElMessage.error(`检查更新失败：${status.error || ''}`)
        }
      })
    },
    async checkUpdate() {
      if (!this.isDesktop) {
        ElMessage.info('仅桌面端支持自动更新')
        return
      }
      await window.v2rayDesktop.updater.check()
    },
    async openLogDialog() {
      if (!this.isDesktop) {
        ElMessage.info('仅桌面端支持查看日志')
        return
      }
      try {
        const { file, content } = await window.v2rayDesktop.logs.read()
        this.logFileName = file || '暂无日志'
        this.logContent = content || '暂无日志记录'
        this.logDialogVisible = true
      } catch (e) {
        console.error('[logs] openLogDialog error:', e)
        ElMessage.error(`读取日志失败：${e.message}`)
      }
    },
    async openLogsFolder() {
      if (!this.isDesktop) return
      await window.v2rayDesktop.logs.openFolder()
    },
    async drawQR(text) {
      const canvas = this.$refs.qrCanvas
      if (!canvas) return
      try {
        await QRCode.toCanvas(canvas, text, { width: 128, margin: 1 })
      } catch (e) {
        // ignore QR rendering failures
      }
    },
    copyUri() {
      if (this.result && navigator.clipboard) {
        navigator.clipboard.writeText(this.result.clientUri).then(() => {
          ElMessage.success('客户端 URI 已复制到剪贴板')
        })
      }
    },
    resetDeploy() {
      this.deployed = false
      this.deployFailed = false
      this.deployCancelled = false
      this.deployErrorMsg = ''
      this.result = null
      this.logLines = []
    },
  },
}
</script>
