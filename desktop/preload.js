const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('v2rayDesktop', {
  getApiBase: () => ipcRenderer.invoke('get-api-base'),
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  onBackendReady: (callback) => {
    ipcRenderer.on('backend-ready', (_event, apiBase) => callback(apiBase))
  },
  history: {
    list: () => ipcRenderer.invoke('history-list'),
    add: (record) => ipcRenderer.invoke('history-add', record),
    clear: () => ipcRenderer.invoke('history-clear'),
    markUninstalled: (id) => ipcRenderer.invoke('history-mark-uninstalled', id),
  },
  credential: {
    save: (key, value) => ipcRenderer.invoke('credential-save', key, value),
    load: (key) => ipcRenderer.invoke('credential-load', key),
    delete: (key) => ipcRenderer.invoke('credential-delete', key),
  },
  updater: {
    check: () => ipcRenderer.invoke('updater-check'),
    onStatus: (callback) => {
      ipcRenderer.on('update-status', (_event, status) => callback(status))
    },
  },
  logs: {
    read: () => ipcRenderer.invoke('logs-read'),
    openFolder: () => ipcRenderer.invoke('logs-open-folder'),
  },
})
