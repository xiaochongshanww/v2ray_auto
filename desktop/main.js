const { app, BrowserWindow, ipcMain, safeStorage, dialog, Tray, Menu } = require('electron')
const { autoUpdater } = require('electron-updater')
const { spawn } = require('node:child_process')
const path = require('node:path')
const crypto = require('node:crypto')
const fs = require('node:fs')

let backend = null
let mainWindow = null
let tray = null
let apiBase = null
let apiKey = null

function resourcesPath() {
  return app.isPackaged ? process.resourcesPath : __dirname
}

function backendDir() {
  return path.join(resourcesPath(), 'backend')
}

function launcherPath() {
  return path.join(backendDir(), 'launcher.py')
}

function userDataFile(name) {
  return path.join(app.getPath('userData'), name)
}

function readJsonFile(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'))
  } catch {
    return null
  }
}

function writeJsonFile(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true })
  fs.writeFileSync(file, JSON.stringify(data, null, 2))
}

function listHistory() {
  return readJsonFile(userDataFile('history.json')) || []
}

function addHistory(record) {
  const list = listHistory()
  list.unshift({ id: Date.now(), time: new Date().toISOString(), ...record })
  writeJsonFile(userDataFile('history.json'), list.slice(0, 200))
  return list
}

function clearHistory() {
  writeJsonFile(userDataFile('history.json'), [])
  return []
}

function saveCredential(key, value) {
  if (!safeStorage.isEncryptionAvailable()) return false
  const store = readJsonFile(userDataFile('credentials.json')) || {}
  store[key] = safeStorage.encryptString(value).toString('base64')
  writeJsonFile(userDataFile('credentials.json'), store)
  return true
}

function loadCredential(key) {
  if (!safeStorage.isEncryptionAvailable()) return null
  const store = readJsonFile(userDataFile('credentials.json')) || {}
  const encoded = store[key]
  if (!encoded) return null
  try {
    return safeStorage.decryptString(Buffer.from(encoded, 'base64'))
  } catch {
    return null
  }
}

function deleteCredential(key) {
  const store = readJsonFile(userDataFile('credentials.json')) || {}
  delete store[key]
  writeJsonFile(userDataFile('credentials.json'), store)
}

function listNodes() {
  return readJsonFile(userDataFile('nodes.json')) || []
}

function saveNodes(nodes) {
  writeJsonFile(userDataFile('nodes.json'), nodes)
  return nodes
}

function upsertNode(node) {
  const nodes = listNodes()
  const idx = nodes.findIndex((n) => n.id === node.id)
  if (idx >= 0) {
    nodes[idx] = { ...nodes[idx], ...node }
  } else {
    nodes.unshift({ ...node, id: crypto.randomUUID() })
  }
  return saveNodes(nodes)
}

function deleteNode(id) {
  return saveNodes(listNodes().filter((n) => n.id !== id))
}

function backendBinaryPath() {
  return path.join(backendDir(), process.platform === 'win32' ? 'v2ray-backend.exe' : 'v2ray-backend')
}

function resolvePython() {
  const configured = process.env.V2RAY_DESKTOP_PYTHON
  if (configured) return configured
  const runtimeDir = path.join(__dirname, 'runtime', 'python3.13')
  const candidates = process.platform === 'win32'
    ? [path.join(runtimeDir, 'python.exe'), path.join(runtimeDir, 'python3.13.exe')]
    : [path.join(runtimeDir, 'bin', 'python3')]
  for (const cand of candidates) {
    if (fs.existsSync(cand)) return cand
  }
  return 'python3'
}

function backendInvocation() {
  if (app.isPackaged) {
    const bin = backendBinaryPath()
    if (!fs.existsSync(bin)) throw new Error(`backend binary missing: ${bin}`)
    return { command: bin, args: [] }
  }
  return { command: resolvePython(), args: [launcherPath()] }
}

function startBackend() {
  let invocation
  try {
    invocation = backendInvocation()
  } catch (err) {
    process.stderr.write(`[backend] ${err.message}\n`)
    app.quit()
    return
  }
  apiKey = process.env.V2RAY_DESKTOP_API_KEY || crypto.randomBytes(24).toString('hex')

  backend = spawn(invocation.command, invocation.args, {
    env: {
      ...process.env,
      V2RAY_DESKTOP_API_KEY: apiKey,
      V2RAY_AUTO_LOG_DIR: path.join(app.getPath('userData'), 'logs'),
      PYTHONUNBUFFERED: '1',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  backend.stdout.on('data', (chunk) => {
    const text = chunk.toString()
    for (const line of text.split('\n')) {
      if (!line.trim()) continue
      let parsed
      try {
        parsed = JSON.parse(line)
      } catch {
        process.stdout.write(`[backend] ${line}\n`)
        continue
      }
      if (parsed.ready) {
        apiBase = `http://127.0.0.1:${parsed.port}`
        process.stdout.write(`[backend] ready on ${apiBase}\n`)
        if (mainWindow) mainWindow.webContents.send('backend-ready', apiBase)
      }
    }
  })

  backend.stderr.on('data', (chunk) => {
    process.stderr.write(`[backend] ${chunk.toString()}`)
  })

  backend.on('exit', (code, signal) => {
    process.stdout.write(`[backend] exited code=${code} signal=${signal}\n`)
    backend = null
    if (!app.isQuitting) {
      app.quit()
    }
  })

  backend.on('error', (err) => {
    process.stderr.write(`[backend] failed to spawn: ${err.message}\n`)
    if (!app.isQuitting) app.quit()
  })
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 960,
    height: 720,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  if (process.env.V2RAY_DESKTOP_DEV_URL) {
    mainWindow.loadURL(process.env.V2RAY_DESKTOP_DEV_URL)
  } else {
    mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'))
  }

  mainWindow.webContents.on('console-message', (event) => {
    if (event.level === 'error') {
      process.stderr.write(`[renderer] ${event.message}\n`)
    }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  mainWindow.on('close', (event) => {
    if (!app.isQuitting) {
      event.preventDefault()
      mainWindow.hide()
    }
  })
}

function toggleWindow() {
  if (!mainWindow) return
  if (mainWindow.isVisible()) {
    mainWindow.hide()
  } else {
    mainWindow.show()
    mainWindow.focus()
  }
}

function checkForUpdates() {
  if (!app.isPackaged || process.env.V2RAY_DESKTOP_DISABLE_AUTOUPDATE) return
  autoUpdater.checkForUpdates().catch((err) => {
    process.stderr.write(`[updater] check failed: ${err.message}\n`)
  })
}

function createTray() {
  const iconPath = path.join(__dirname, 'assets', 'trayTemplate.png')
  tray = new Tray(iconPath)
  tray.setToolTip('V2Ray Auto')
  const menu = Menu.buildFromTemplate([
    { label: '显示 / 隐藏', click: () => toggleWindow() },
    { label: '检查更新', click: () => checkForUpdates() },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        app.isQuitting = true
        app.quit()
      },
    },
  ])
  tray.setContextMenu(menu)
  tray.on('click', () => toggleWindow())
}

function sendUpdateStatus(status) {
  if (mainWindow) mainWindow.webContents.send('update-status', status)
}

app.on('before-quit', () => {
  app.isQuitting = true
  if (backend) {
    backend.kill('SIGTERM')
  }
})

function setupAutoUpdater() {
  if (!app.isPackaged || process.env.V2RAY_DESKTOP_DISABLE_AUTOUPDATE) return
  autoUpdater.autoDownload = true
  autoUpdater.on('checking-for-update', () => {
    sendUpdateStatus({ state: 'checking' })
  })
  autoUpdater.on('update-available', (info) => {
    process.stdout.write(`[updater] update available: v${info.version}\n`)
    sendUpdateStatus({ state: 'available', version: info.version })
  })
  autoUpdater.on('update-not-available', () => {
    sendUpdateStatus({ state: 'not-available' })
  })
  autoUpdater.on('update-downloaded', async (info) => {
    process.stdout.write(`[updater] update downloaded: v${info.version}\n`)
    sendUpdateStatus({ state: 'downloaded', version: info.version })
    const options = {
      type: 'info',
      title: '更新已就绪',
      message: `新版本 v${info.version} 已下载完成`,
      detail: '重启应用以完成安装更新。',
      buttons: ['立即重启', '稍后'],
      defaultId: 0,
      cancelId: 1,
    }
    const { response } = mainWindow
      ? await dialog.showMessageBox(mainWindow, options)
      : await dialog.showMessageBox(options)
    if (response === 0) autoUpdater.quitAndInstall()
  })
  autoUpdater.on('error', (err) => {
    process.stderr.write(`[updater] error: ${err.message}\n`)
    sendUpdateStatus({ state: 'error', error: err.message })
  })
  autoUpdater.checkForUpdatesAndNotify().catch((err) => {
    process.stderr.write(`[updater] check failed: ${err.message}\n`)
  })
}

app.whenReady().then(() => {
  ipcMain.handle('get-api-base', () => apiBase)
  ipcMain.handle('get-api-key', () => apiKey)
  ipcMain.handle('get-backend-path', () => {
    try {
      return backendInvocation().command
    } catch (err) {
      return err.message
    }
  })
  ipcMain.handle('history-list', () => listHistory())
  ipcMain.handle('history-add', (_event, record) => addHistory(record))
  ipcMain.handle('history-clear', () => clearHistory())
  ipcMain.handle('credential-save', (_event, key, value) => saveCredential(key, value))
  ipcMain.handle('credential-load', (_event, key) => loadCredential(key))
  ipcMain.handle('credential-delete', (_event, key) => deleteCredential(key))
  ipcMain.handle('nodes-list', () => listNodes())
  ipcMain.handle('nodes-upsert', (_event, node) => upsertNode(node))
  ipcMain.handle('nodes-delete', (_event, id) => deleteNode(id))
  ipcMain.handle('updater-check', () => checkForUpdates())

  createWindow()
  startBackend()
  createTray()
  setupAutoUpdater()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    } else if (mainWindow) {
      mainWindow.show()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
