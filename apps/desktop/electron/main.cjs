const { app, BrowserWindow, globalShortcut, Tray, Menu, nativeImage, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
const crypto = require('crypto');
const { spawn } = require('child_process');
const { detectPythonCommand } = require('./pythonVersion.cjs');

// Generate fresh 32-byte session token at every launch
const sessionToken = process.env.PHENOM_SESSION_TOKEN || crypto.randomBytes(32).toString('hex');
process.env.PHENOM_SESSION_TOKEN = sessionToken;

// IPC handler to expose session token securely via contextBridge preload
ipcMain.on('phenom:get-session-token', (event) => {
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
  return true; // Already configured in config.toml
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
let tray = null;
let isQuitting = false;
let backendProcess = null;
let backendRestartAttempts = 0;
const MAX_BACKEND_RESTARTS = 5;

function spawnBackendWithWatchdog(pythonTarget) {
  if (isQuitting) return;

  console.log(`[Phenom Watchdog] Starting backend service using ${pythonTarget.cmd} (${pythonTarget.version.raw})...`);
  const spawnArgs = [...pythonTarget.execArgs, '-m', 'uvicorn', 'services.backend.main:app', '--host', '127.0.0.1', '--port', '8000'];
  const backendCwd = app.isPackaged
    ? path.join(process.resourcesPath, 'backend')
    : path.join(__dirname, '../../..');

  console.log('[Phenom Watchdog] Spawning backend from working directory:', backendCwd);

  backendProcess = spawn(
    pythonTarget.cmd,
    spawnArgs,
    {
      cwd: backendCwd,
      env: { ...process.env, PYTHONUNBUFFERED: '1', PHENOM_SESSION_TOKEN: sessionToken },
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
  const probe = http.get('http://127.0.0.1:8000/health', (res) => {
    console.log('[Phenom] Backend already active (Status: ' + res.statusCode + ')');
  });
  probe.on('error', () => {
    spawnBackendWithWatchdog(pythonTarget);
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
    tray.setToolTip('Phenom - Windows 11 Personal AI Assistant');
  } catch (err) {
    console.warn('[Phenom] Tray initialization skipped:', err.message);
    return;
  }

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
      label: 'Guardian Kill Switch (HALT)',
      click: () => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('guardian:hotkey');
        }
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

function createWindow() {
  const iconPath = path.join(__dirname, 'icon.png');
  mainWindow = new BrowserWindow({
    width: 1080,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    show: true,
    backgroundColor: '#0b0f19',
    title: 'Phenom',
    icon: fs.existsSync(iconPath) ? iconPath : undefined,
    frame: true,
    titleBarStyle: 'default',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.cjs')
    }
  });

  const candidates = [
    path.join(__dirname, '../dist/index.html'),
    path.join(app.getAppPath(), 'dist/index.html'),
    path.join(__dirname, 'dist/index.html')
  ];
  let distPath = candidates[0];
  for (const c of candidates) {
    if (fs.existsSync(c)) {
      distPath = c;
      break;
    }
  }

  let loaded = false;
  const loadDist = () => {
    if (loaded) return;
    loaded = true;
    console.log('[Phenom] Loading frontend from local dist:', distPath);
    mainWindow.loadFile(distPath);
  };

  const req = http.get('http://localhost:5173', (res) => {
    if (!loaded) {
      loaded = true;
      console.log('[Phenom] Connected to Vite dev server on 5173');
      mainWindow.loadURL('http://localhost:5173');
    }
  });
  req.on('error', loadDist);
  req.setTimeout(300, () => {
    req.destroy();
    loadDist();
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
  checkPrerequisites();

  // Register global Guardian Kill Switch hotkey (Ctrl+Alt+P and Ctrl+Alt+Escape)
  const registerKillHotkey = (shortcut) => {
    try {
      globalShortcut.register(shortcut, () => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('guardian:hotkey');
        }
      });
    } catch (err) {
      console.warn(`Could not register ${shortcut}:`, err);
    }
  };

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
