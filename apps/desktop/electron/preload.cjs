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
  },
  isVoiceMuted: () => {
    try {
      return ipcRenderer.sendSync('phenom:get-voice-muted');
    } catch {
      return false;
    }
  },
  setVoiceMuted: (muted) => {
    try {
      return ipcRenderer.sendSync('phenom:set-voice-muted', muted);
    } catch {
      return false;
    }
  },
  onVoiceMutedChanged: (callback) => {
    ipcRenderer.on('voice:set-muted', (_, muted) => {
      if (typeof callback === 'function') callback(muted);
    });
  },
  triggerGuardianKill: () => {
    try {
      ipcRenderer.send('phenom:guardian-halt');
    } catch {}
  },
  onGuardianHotkey: (callback) => {
    ipcRenderer.on('guardian:hotkey', () => {
      if (typeof callback === 'function') callback();
    });
  }
});
