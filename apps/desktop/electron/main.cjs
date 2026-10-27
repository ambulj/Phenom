const { app, BrowserWindow, globalShortcut } = require('electron');
const path = require('path');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1050,
    height: 780,
    minWidth: 800,
    minHeight: 600,
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
    // If dev server isn't up, load built dist
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  });
}

app.whenReady().then(() => {
  createWindow();

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
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
