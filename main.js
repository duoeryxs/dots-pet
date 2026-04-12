const { app, BrowserWindow, ipcMain, screen, Tray, Menu, nativeImage } = require('electron');
const path = require('path');

let mainWindow;
let tray;

function createWindow() {
  const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize;

  mainWindow = new BrowserWindow({
    width: 200,
    height: 280,
    x: screenWidth - 250,
    y: screenHeight - 320,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    hasShadow: false,
    resizable: false,
    skipTaskbar: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });

  mainWindow.loadFile('index.html');
  mainWindow.setIgnoreMouseEvents(false);
  mainWindow.setVisibleOnAllWorkspaces(true);

  // Allow click-through on transparent areas
  ipcMain.on('set-ignore-mouse', (event, ignore) => {
    mainWindow.setIgnoreMouseEvents(ignore, { forward: true });
  });

  ipcMain.on('window-move', (event, { dx, dy }) => {
    const [x, y] = mainWindow.getPosition();
    mainWindow.setPosition(x + dx, y + dy);
  });

  ipcMain.on('resize-window', (event, { width, height }) => {
    mainWindow.setSize(width, height);
  });
}

function createTray() {
  // Create a simple tray icon
  const icon = nativeImage.createFromDataURL(
    'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAAbwAAAG8B8aLcQwAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAEKSURBVDiNpZMxTsNAEEX/rDeOEkFBgUQHHIAzcAJuwBW4AA0VLQ0dJ6DnBpyAI9BQIKEIKYhxvLtDsXZsxzHiS6Od+fP/zO4uMDMqABF5BG6ANIA9MyuAqnNuK0lLgDXQAFdABlyb2V5ExBhIgVtgMDNbF5E4A+4aZluATMBELoFroAcugQzYAwfAkZktJL0HfgBvgG8zO2sKWNfMA68AR+PfAq8iMnXXdCSiTyIS+OM8BYaiemRmt5IOgZeqn6vqUkQpIj8iCRHJJZ1L+hORE0mJpK6kHUkdSX1JR+W5gaQkCIIsSZLTMAy/wjD8UhAE8xsbZ8BQUt/MRmY2lJSb2RhYNLP/AL8BCeJYTFwAAAAASUVORK5CYII='
  );
  tray = new Tray(icon);
  const contextMenu = Menu.buildFromTemplate([
    { label: 'Show Claude', click: () => mainWindow.show() },
    { label: 'Quit', click: () => app.quit() },
  ]);
  tray.setToolTip('Claude Pet');
  tray.setContextMenu(contextMenu);
}

app.whenReady().then(() => {
  createWindow();
  createTray();
});

app.on('window-all-closed', () => {
  app.quit();
});
