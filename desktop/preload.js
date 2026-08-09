const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('v2rayDesktop', {
  getApiBase: () => ipcRenderer.invoke('get-api-base'),
  getApiKey: () => ipcRenderer.invoke('get-api-key'),
  onBackendReady: (callback) => {
    ipcRenderer.on('backend-ready', (_event, apiBase) => callback(apiBase))
  },
  history: {
    list: () => ipcRenderer.invoke('history-list'),
    add: (record) => ipcRenderer.invoke('history-add', record),
    clear: () => ipcRenderer.invoke('history-clear'),
  },
  credential: {
    save: (key, value) => ipcRenderer.invoke('credential-save', key, value),
    load: (key) => ipcRenderer.invoke('credential-load', key),
    delete: (key) => ipcRenderer.invoke('credential-delete', key),
  },
  nodes: {
    list: () => ipcRenderer.invoke('nodes-list'),
    upsert: (node) => ipcRenderer.invoke('nodes-upsert', node),
    delete: (id) => ipcRenderer.invoke('nodes-delete', id),
  },
  updater: {
    check: () => ipcRenderer.invoke('updater-check'),
    onStatus: (callback) => {
      ipcRenderer.on('update-status', (_event, status) => callback(status))
    },
  },
})
