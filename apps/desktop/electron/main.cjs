const { app, BrowserWindow, globalShortcut, Tray, Menu, nativeImage, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
const crypto = require('crypto');
const { spawn } = require('child_process');
const { detectPythonCommand } = require('./pythonVersion.cjs');

// Disable GPU hardware acceleration to avoid driver crashes (exit_code=-1073741819)
app.disableHardwareAcceleration();

// Autoplay policy for embedded media playback (MED-01)
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');

// Generate or read persistent session token
let sessionToken = process.env.PHENOM_SESSION_TOKEN;
const candidateTokenFiles = [
  path.join(app.getPath('userData'), '.session_token'),
  path.join(process.env.APPDATA || '', 'phenom-desktop', '.session_token'),
  path.join(process.env.APPDATA || '', 'Phenom', '.session_token')
];

if (!sessionToken) {
  for (const tf of candidateTokenFiles) {
    try {
      if (fs.existsSync(tf)) {
        const val = fs.readFileSync(tf, 'utf8').trim();
        if (val) {
          sessionToken = val;
          break;
        }
      }
    } catch (e) {}
  }
}

if (!sessionToken) {
  sessionToken = crypto.randomBytes(32).toString('hex');
}

for (const tf of candidateTokenFiles) {
  try {
    const dir = path.dirname(tf);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(tf, sessionToken, 'utf8');
  } catch (e) {}
}

process.env.PHENOM_SESSION_TOKEN = sessionToken;

// IPC handler to expose session token securely via contextBridge preload (Task 6E Hardening F11)
ipcMain.on('phenom:get-session-token', (event) => {
  const senderUrl = event.senderFrame?.url || event.sender?.getURL() || '';
  const isTrusted = senderUrl.startsWith('file://') || (!app.isPackaged && (senderUrl.startsWith('http://localhost:5173') || senderUrl.startsWith('http://127.0.0.1:5173')));
  if (!isTrusted) {
    console.warn('[Phenom Security] Blocked get-session-token request from untrusted origin:', senderUrl);
    event.returnValue = null;
    return;
  }
  event.returnValue = sessionToken;
});

function getSettingsFilePath() {
  try {
    return path.join(app.getPath('userData'), 'phenom-settings.json');
  } catch {
    return path.join(__dirname, 'phenom-settings.json');
  }
}

function isFirstRunDone() {
  try {
    const p = getSettingsFilePath();
    if (fs.existsSync(p)) {
      const data = JSON.parse(fs.readFileSync(p, 'utf8'));
      if (data.first_run_done !== undefined) return Boolean(data.first_run_done);
    }
  } catch (e) {}
  // Fix for Task 6E: Do not default to true; first-run wizard must be reachable
  return false;
}

function setFirstRunDone() {
  try {
    const p = getSettingsFilePath();
    let data = {};
    if (fs.existsSync(p)) {
      try { data = JSON.parse(fs.readFileSync(p, 'utf8')); } catch {}
    }
    data.first_run_done = true;
    fs.writeFileSync(p, JSON.stringify(data, null, 2), 'utf8');
  } catch (e) {}
}

ipcMain.on('phenom:is-first-run-done', (event) => {
  event.returnValue = isFirstRunDone();
});

ipcMain.on('phenom:set-first-run-done', (event) => {
  setFirstRunDone();
  event.returnValue = true;
});

let mainWindow;
let orbWindow = null;
let tray = null;
let isQuitting = false;
let isVoiceMuted = false;
let backendProcess = null;
let backendRestartAttempts = 0;
const MAX_BACKEND_RESTARTS = 5;

// Orb Window IPC Listeners (Task 6E)
ipcMain.on('orb:set-ignore-mouse-events', (event, ignore, options) => {
  if (orbWindow && !orbWindow.isDestroyed()) {
    orbWindow.setIgnoreMouseEvents(Boolean(ignore), options || { forward: true });
  }
});

ipcMain.on('orb:set-opacity', (event, opacity) => {
  if (orbWindow && !orbWindow.isDestroyed()) {
    orbWindow.setOpacity(Math.max(0.1, Math.min(1.0, Number(opacity))));
  }
});

ipcMain.on('orb:toggle-main-window', () => {
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (mainWindow.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow.show();
      mainWindow.focus();
    }
  }
});

ipcMain.on('orb:file-drop', (event, filePath) => {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('orb:file-dropped', filePath);
  }
});

function triggerGuardianHalt(reason = 'Electron Tray/Hotkey HALT') {
  // 1. Synchronously mute all active WebContents audio (< 1ms SLA)
  try {
    const { webContents } = require('electron');
    if (webContents) {
      webContents.getAllWebContents().forEach(wc => {
        try { wc.setAudioMuted(true); } catch (e) {}
      });
    }
  } catch (e) {}

  // 2. Notify renderer windows
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('guardian:hotkey', { reason });
    mainWindow.webContents.send('media:guardian-mute');
  }
  if (orbWindow && !orbWindow.isDestroyed()) {
    orbWindow.webContents.send('guardian:hotkey', { reason });
  }

  // 3. Directly call backend REST API to trigger Guardian Kill Switch (< 10ms)
  try {
    const http = require('http');
    const req = http.request({
      hostname: '127.0.0.1',
      port: 8000,
      path: '/api/killswitch/trigger',
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${sessionToken}`,
        'Content-Type': 'application/json'
      },
      timeout: 1000
    }, (res) => {});
    req.on('error', (err) => {
      console.warn('[Phenom] Could not post killswitch to backend:', err.message);
    });
    req.write(JSON.stringify({ reason }));
    req.end();
  } catch (err) {
    console.warn('[Phenom] Failed to dispatch killswitch HTTP request:', err);
  }
}

function updateTrayContextMenu() {
  if (!tray) return;
  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show Phenom',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      }
    },
    {
      label: 'Hide to Tray',
      click: () => {
        if (mainWindow) mainWindow.hide();
      }
    },
    { type: 'separator' },
    {
      label: isVoiceMuted ? 'Unmute Voice' : 'Mute Voice',
      click: () => {
        isVoiceMuted = !isVoiceMuted;
        updateTrayContextMenu();
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('voice:set-muted', isVoiceMuted);
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Guardian Kill Switch (HALT)',
      click: () => {
        triggerGuardianHalt('Tray HALT menu item clicked');
      }
    },
    { type: 'separator' },
    {
      label: 'Quit Phenom',
      click: () => {
        isQuitting = true;
        app.quit();
      }
    }
  ]);
  tray.setContextMenu(contextMenu);
}

ipcMain.on('phenom:get-voice-muted', (event) => {
  event.returnValue = isVoiceMuted;
});

ipcMain.on('phenom:set-voice-muted', (event, muted) => {
  isVoiceMuted = Boolean(muted);
  updateTrayContextMenu();
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('voice:set-muted', isVoiceMuted);
  }
  event.returnValue = isVoiceMuted;
});

function spawnBackendWithWatchdog(pythonTarget) {
  if (isQuitting) return;

  const repoRoot = path.resolve(__dirname, '../../..');
  const backendCwd = (fs.existsSync(path.join(repoRoot, 'services', 'backend', 'main.py')))
    ? repoRoot
    : (fs.existsSync(path.join(process.resourcesPath, 'services', 'backend', 'main.py'))
        ? process.resourcesPath
        : path.join(process.resourcesPath, 'backend'));

  const spawnTarget = (fs.existsSync(path.join(backendCwd, 'services', 'backend', 'main.py')))
    ? 'services.backend.main:app'
    : 'main:app';

  console.log(`[Phenom Watchdog] Starting backend service using ${pythonTarget.cmd} (${pythonTarget.version.raw})...`);
  console.log('[Phenom Watchdog] Target:', spawnTarget, 'in CWD:', backendCwd);

  const spawnArgs = [...pythonTarget.execArgs, '-m', 'uvicorn', spawnTarget, '--host', '127.0.0.1', '--port', '8000'];

  const pyPathList = [
    backendCwd,
    repoRoot,
    process.resourcesPath,
    path.join(process.resourcesPath, 'backend'),
    process.env.PYTHONPATH || ''
  ].filter(Boolean).join(path.delimiter);

  backendProcess = spawn(
    pythonTarget.cmd,
    spawnArgs,
    {
      cwd: backendCwd,
      env: { ...process.env, PYTHONUNBUFFERED: '1', PHENOM_SESSION_TOKEN: sessionToken, PYTHONPATH: pyPathList },
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: process.platform === 'win32'
    }
  );

  backendProcess.stdout.on('data', (d) => {
    console.log(`[Backend] ${d.toString().trim()}`);
  });
  backendProcess.stderr.on('data', (d) => {
    console.log(`[Backend] ${d.toString().trim()}`);
  });

  backendProcess.on('error', (err) => {
    console.error('[Phenom Watchdog] Failed to spawn backend process:', err);
  });

  backendProcess.on('exit', (code, signal) => {
    console.log(`[Phenom Watchdog] Backend process terminated (code: ${code}, signal: ${signal}).`);
    backendProcess = null;

    if (!isQuitting && backendRestartAttempts < MAX_BACKEND_RESTARTS) {
      backendRestartAttempts++;
      const delayMs = 1500; // Guarantees restart under 2000ms
      console.log(`[Phenom Watchdog] Relaunching backend in ${delayMs}ms (attempt ${backendRestartAttempts}/${MAX_BACKEND_RESTARTS})...`);
      setTimeout(() => {
        if (!isQuitting) {
          spawnBackendWithWatchdog(pythonTarget);
        }
      }, delayMs);
    }
  });
}

function startBackend() {
  const pythonTarget = detectPythonCommand();
  if (!pythonTarget) {
    dialog.showErrorBox(
      'Python 3.11+ Required',
      'Phenom requires Python 3.11 or newer to run the assistant backend.\n\n' +
      'Please install Python 3.11 or newer from https://www.python.org/downloads/ and ensure it is added to your system PATH.'
    );
    console.error('[Phenom] Aborting backend startup: Python 3.11+ not found on host.');
    return;
  }

  // If backend is already running (e.g. during dev), do not spawn duplicate
  let probed = false;
  const probe = http.get('http://127.0.0.1:8000/health', (res) => {
    probed = true;
    console.log('[Phenom] Backend already active (Status: ' + res.statusCode + ')');
  });
  probe.on('error', () => {
    if (!probed) {
      probed = true;
      spawnBackendWithWatchdog(pythonTarget);
    }
  });
  probe.setTimeout(1500, () => {
    if (!probed) {
      probed = true;
      try { probe.destroy(); } catch (e) {}
      spawnBackendWithWatchdog(pythonTarget);
    }
  });
}

// Check if quiet background start requested
const isHiddenStart = process.argv.includes('--hidden') || process.argv.includes('--quiet');

function createTray() {
  const iconCandidates = [
    path.join(__dirname, 'icon.png'),
    path.join(__dirname, 'icon.ico'),
    path.join(__dirname, '../public/icon.png'),
    path.join(__dirname, '../public/icon.ico'),
    path.join(__dirname, '../dist/icon.png'),
    path.join(__dirname, '../dist/icon.ico'),
    path.join(process.resourcesPath || '', 'icon.png'),
    path.join(process.resourcesPath || '', 'icon.ico')
  ];

  let icon = null;
  for (const c of iconCandidates) {
    if (fs.existsSync(c)) {
      try {
        const loaded = nativeImage.createFromPath(c);
        if (!loaded.isEmpty()) {
          icon = loaded;
          console.log('[Phenom] Tray icon loaded from:', c);
          break;
        }
      } catch (e) {
        console.warn('[Phenom] Failed to load icon from candidate:', c, e.message);
      }
    }
  }

  if (!icon || icon.isEmpty()) {
    console.warn('[Phenom] Warning: No valid icon found for tray. Skipping tray setup.');
    return;
  }

  try {
    tray = new Tray(icon);
    tray.setToolTip('Phenom 3.0 Cyber Assistant (Windows 11)');
  } catch (err) {
    console.warn('[Phenom] Tray initialization skipped:', err.message);
    return;
  }

  updateTrayContextMenu();

  // Single click restores/focuses window
  tray.on('click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.focus();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    }
  });

  tray.on('double-click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    }
  });
}

function checkPrerequisites() {
  const req = http.get('http://127.0.0.1:8000/health', (res) => {
    console.log('[Phenom Prerequisite Check] Backend connected (Status: ' + res.statusCode + ')');
  });
  req.on('error', () => {
    console.log('[Phenom Prerequisite Check] Backend not yet reachable; starting/retrying...');
  });
}

function getDistPath() {
  const candidates = [
    path.join(__dirname, '../dist/index.html'),
    path.join(app.getAppPath(), 'dist/index.html'),
    path.join(__dirname, 'dist/index.html')
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return candidates[0];
}

function createWindow() {
  const iconPath = path.join(__dirname, 'icon.png');
  mainWindow = new BrowserWindow({
    width: 1080,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    show: true,
    backgroundColor: '#080B10',
    title: 'Phenom',
    icon: fs.existsSync(iconPath) ? iconPath : undefined,
    frame: true,
    titleBarStyle: 'default',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      webviewTag: true,
      preload: path.join(__dirname, 'preload.cjs')
    }
  });

  const distPath = getDistPath();
  let loaded = false;
  const loadDist = () => {
    if (loaded) return;
    loaded = true;
    console.log('[Phenom] Loading frontend from local dist:', distPath);
    mainWindow.loadFile(distPath);
  };

  // Hardening guard (F11/H2): Never probe localhost:5173 when app is packaged
  if (app.isPackaged) {
    loadDist();
  } else {
    const req = http.get('http://localhost:5173', (res) => {
      if (!loaded) {
        loaded = true;
        console.log('[Phenom] Connected to Vite dev server on 5173');
        mainWindow.loadURL('http://localhost:5173');
      }
    });
    req.on('error', loadDist);
    req.setTimeout(400, () => {
      req.destroy();
      loadDist();
    });
  }

  // Security navigation & window opening guards (Task 6E Hardening)
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://') || url.startsWith('http://')) {
      require('electron').shell.openExternal(url);
    }
    return { action: 'deny' };
  });

  mainWindow.webContents.on('will-navigate', (event, url) => {
    const isLocal = url.startsWith('file://') || (!app.isPackaged && (url.startsWith('http://localhost:5173') || url.startsWith('http://127.0.0.1:5173')));
    if (!isLocal) {
      event.preventDefault();
      if (url.startsWith('https://') || url.startsWith('http://')) {
        require('electron').shell.openExternal(url);
      }
    }
  });

  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    console.log(`[Renderer Console] ${message}`);
  });

  mainWindow.once('ready-to-show', () => {
    console.log('[Phenom] Window ready-to-show event fired.');
    mainWindow.show();
    mainWindow.focus();
    mainWindow.moveTop();
  });

  // Fallback: force show after 1500ms
  setTimeout(() => {
    if (mainWindow && !mainWindow.isVisible()) {
      console.log('[Phenom] Fallback force-showing window.');
      mainWindow.show();
      mainWindow.focus();
    }
  }, 1500);

  // Minimize to tray on close
  mainWindow.on('close', (e) => {
    if (!isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });
}

function createOrbWindow() {
  const primaryDisplay = require('electron').screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;

  let orbX = screenWidth - 180;
  let orbY = screenHeight - 180;
  try {
    const p = getSettingsFilePath();
    if (fs.existsSync(p)) {
      const data = JSON.parse(fs.readFileSync(p, 'utf8'));
      if (data.orb_x !== undefined && data.orb_y !== undefined) {
        orbX = data.orb_x;
        orbY = data.orb_y;
      }
    }
  } catch (e) {}

  orbWindow = new BrowserWindow({
    width: 160,
    height: 160,
    x: orbX,
    y: orbY,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    hasShadow: false,
    backgroundColor: '#00000000',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.cjs')
    }
  });

  // Click-through when idle, forward events so hover can solid
  orbWindow.setIgnoreMouseEvents(true, { forward: true });

  const distPath = getDistPath();
  if (app.isPackaged) {
    orbWindow.loadFile(distPath, { hash: 'orb' });
  } else {
    orbWindow.loadURL('http://localhost:5173/#/orb').catch(() => {
      orbWindow.loadFile(distPath, { hash: 'orb' });
    });
  }

  // Snapping to screen edges & remembering coordinates (Task 6E.1)
  orbWindow.on('moved', () => {
    if (!orbWindow || orbWindow.isDestroyed()) return;
    const [x, y] = orbWindow.getPosition();
    const [w, h] = orbWindow.getSize();
    const disp = require('electron').screen.getDisplayNearestPoint({ x, y });
    const { x: dx, y: dy, width: dw, height: dh } = disp.workArea;

    let finalX = x;
    let finalY = y;
    const SNAP_MARGIN = 32;

    if (Math.abs(x - dx) < SNAP_MARGIN) finalX = dx + 12;
    else if (Math.abs(x + w - (dx + dw)) < SNAP_MARGIN) finalX = dx + dw - w - 12;

    if (Math.abs(y - dy) < SNAP_MARGIN) finalY = dy + 12;
    else if (Math.abs(y + h - (dy + dh)) < SNAP_MARGIN) finalY = dy + dh - h - 12;

    if (finalX !== x || finalY !== y) {
      orbWindow.setPosition(finalX, finalY);
    }

    try {
      const p = getSettingsFilePath();
      let data = {};
      if (fs.existsSync(p)) {
        try { data = JSON.parse(fs.readFileSync(p, 'utf8')); } catch {}
      }
      data.orb_x = finalX;
      data.orb_y = finalY;
      fs.writeFileSync(p, JSON.stringify(data, null, 2), 'utf8');
    } catch (e) {}
  });

  orbWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  orbWindow.webContents.on('will-navigate', (e) => e.preventDefault());
}

app.whenReady().then(() => {
  // Configure Windows Auto-Start
  app.setLoginItemSettings({
    openAtLogin: true,
    openAsHidden: true,
    name: 'Phenom Assistant'
  });

  createTray();
  startBackend();
  createWindow();
  createOrbWindow();
  checkPrerequisites();

  // Register IPC handler for webview media muting
  ipcMain.handle('media:mute-all', (event, muted) => {
    const { webContents } = require('electron');
    if (webContents) {
      webContents.getAllWebContents().forEach(wc => {
        try { wc.setAudioMuted(Boolean(muted)); } catch (e) {}
      });
    }
    return true;
  });

  // Register global Guardian Kill Switch hotkey (Ctrl+Alt+P and Ctrl+Alt+Escape)
  const registerKillHotkey = (shortcut) => {
    try {
      globalShortcut.register(shortcut, () => {
        triggerGuardianHalt(`Global hotkey ${shortcut}`);
      });
    } catch (err) {
      console.warn(`Could not register ${shortcut}:`, err);
    }
  };

  // Register OS Media Keys (MED-01)
  const registerMediaKey = (key, action) => {
    try {
      globalShortcut.register(key, () => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('media:transport-key', action);
        }
      });
    } catch (e) {}
  };
  registerMediaKey('MediaPlayPause', 'play_pause');
  registerMediaKey('MediaNextTrack', 'next');
  registerMediaKey('MediaPreviousTrack', 'prev');
  registerMediaKey('MediaStop', 'stop');

  registerKillHotkey('CommandOrControl+Alt+P');
  registerKillHotkey('CommandOrControl+Alt+Escape');

  try {
    globalShortcut.register('Alt+Space', () => {
      if (mainWindow) {
        if (mainWindow.isVisible() && mainWindow.isFocused()) {
          mainWindow.hide();
        } else {
          mainWindow.show();
          mainWindow.focus();
        }
      }
    });
    console.log('[Phenom] Registered Alt+Space global summon hotkey.');
  } catch (err) {
    console.warn('[Phenom] Could not register Alt+Space:', err);
  }

  app.on('activate', () => {
    if (mainWindow) {
      mainWindow.show();
    } else if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('before-quit', () => {
  isQuitting = true;
  if (backendProcess) {
    try {
      backendProcess.kill();
    } catch (e) {
      // ignore
    }
    backendProcess = null;
  }
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin' && isQuitting) {
    app.quit();
  }
});
