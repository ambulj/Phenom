const { app, BrowserWindow, globalShortcut, Tray, Menu, nativeImage } = require('electron');
const path = require('path');
const http = require('http');

let mainWindow;
let tray = null;
let isQuitting = false;

// Check if quiet background start requested
const isHiddenStart = process.argv.includes('--hidden') || process.argv.includes('--quiet');

function createTray() {
  const icon = nativeImage.createEmpty();
  tray = new Tray(icon);
  tray.setToolTip('Phenom - Windows 11 Personal AI Assistant');

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
  const req = http.get('http://localhost:8000/api/health', (res) => {
    console.log('[Phenom Prerequisite Check] Backend connected (Status: ' + res.statusCode + ')');
  });
  req.on('error', () => {
    console.log('[Phenom Prerequisite Check] Backend not yet reachable; will retry on launch.');
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1080,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    show: !isHiddenStart,
    backgroundColor: '#0b0f19',
    title: 'Phenom',
    frame: true,
    titleBarStyle: 'default',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  const devUrl = 'http://localhost:5173';
  mainWindow.loadURL(devUrl).catch(() => {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  });

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
  createWindow();
  checkPrerequisites();

  // Register global Guardian Kill Switch hotkey (Ctrl+Alt+Pause)
  try {
    globalShortcut.register('Ctrl+Alt+Pause', () => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('guardian:hotkey');
      }
    });
  } catch (err) {
    console.error('Failed to register global hotkey:', err);
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
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin' && isQuitting) {
    app.quit();
  }
});
