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
  },
  muteAllAudio: (muted) => {
    try {
      return ipcRenderer.invoke('media:mute-all', Boolean(muted));
    } catch {
      return Promise.resolve(false);
    }
  },
  onMediaTransportKey: (callback) => {
    ipcRenderer.on('media:transport-key', (_, action) => {
      if (typeof callback === 'function') callback(action);
    });
  },
  onMediaGuardianMute: (callback) => {
    ipcRenderer.on('media:guardian-mute', () => {
      if (typeof callback === 'function') callback();
    });
  },
  // Orb Floating Window & HUD Controls (Task 6E)
  setIgnoreMouseEvents: (ignore, options) => {
    try {
      ipcRenderer.send('orb:set-ignore-mouse-events', ignore, options);
    } catch {}
  },
  setOrbOpacity: (opacity) => {
    try {
      ipcRenderer.send('orb:set-opacity', opacity);
    } catch {}
  },
  toggleMainWindow: () => {
    try {
      ipcRenderer.send('orb:toggle-main-window');
    } catch {}
  },
  sendOrbFileDrop: (filePath) => {
    try {
      ipcRenderer.send('orb:file-drop', filePath);
    } catch {}
  }
});
