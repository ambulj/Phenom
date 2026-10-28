const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('phenom', {
  getSessionToken: () => {
    try {
      return ipcRenderer.sendSync('phenom:get-session-token');
    } catch {
      return '';
    }
  }
});
