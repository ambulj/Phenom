const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('phenom', {
  getSessionToken: () => {
    try {
      return ipcRenderer.sendSync('phenom:get-session-token');
    } catch {
      return '';
    }
  },
  isFirstRunDone: () => {
    try {
      return ipcRenderer.sendSync('phenom:is-first-run-done');
    } catch {
      return true;
    }
  },
  setFirstRunDone: () => {
    try {
      return ipcRenderer.sendSync('phenom:set-first-run-done');
    } catch {
      return true;
    }
  }
});
