const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { spawn, execSync } = require("child_process");
const http = require("http");
const fs = require("fs");

let mainWindow;
let flaskProcess;

function waitForServer(url, retries, interval, cb, failCb) {
  http
    .get(url, (res) => {
      if (res.statusCode === 200) cb();
      else if (retries > 0) setTimeout(() => waitForServer(url, retries - 1, interval, cb, failCb), interval);
      else failCb(`Server returned ${res.statusCode}`);
    })
    .on("error", () => {
      if (retries > 0) setTimeout(() => waitForServer(url, retries - 1, interval, cb, failCb), interval);
      else failCb("Connection refused");
    });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: "PrintPAL",
    frame: false,
    show: false,
    backgroundColor: "#1a1a2e",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
      nodeEnv: "production",
    },
  });

  mainWindow.setMenuBarVisibility(false);
  mainWindow.on("closed", () => { mainWindow = null; });
  return mainWindow;
}

function showLoadingScreen() {
  mainWindow.loadFile(path.join(__dirname, "loading.html"));
  mainWindow.show();
}

ipcMain.on("win-minimize", () => mainWindow && mainWindow.minimize());
ipcMain.on("win-maximize", () => {
  if (mainWindow) mainWindow.isMaximized() ? mainWindow.unmaximize() : mainWindow.maximize();
});
ipcMain.on("win-close", () => mainWindow && mainWindow.close());

function findPython() {
  if (app.isPackaged) {
    const embeddedPython = path.join(path.dirname(process.execPath), "python", "python.exe");
    if (fs.existsSync(embeddedPython)) {
      return embeddedPython;
    }
    const resourcesPython = path.join(process.resourcesPath, "python", "python.exe");
    if (fs.existsSync(resourcesPython)) {
      return resourcesPython;
    }
  } else {
    const devPython = path.join(__dirname, "electron-app", "python", "python.exe");
    if (fs.existsSync(devPython)) {
      return devPython;
    }
  }
  return null;
}

function checkFlask(pythonCmd) {
  try {
    const result = require("child_process").spawnSync(pythonCmd, ["-c", "import flask"], { stdio: "pipe", timeout: 3000 });
    return result.status === 0;
  } catch (e) {
    return false;
  }
}

function installFlask(pythonCmd, cwd) {
  return new Promise((resolve, reject) => {
    const proc = spawn(pythonCmd, ["-m", "pip", "install", "--quiet", "flask"], {
      cwd: cwd || process.cwd(),
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
    });
    let output = "";
    proc.stdout.on("data", (d) => { output += d.toString(); });
    proc.stderr.on("data", (d) => { output += d.toString(); });
    proc.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(output || `Exit code ${code}`));
    });
    proc.on("error", reject);
  });
}

function killFlask() {
  if (!flaskProcess) return;

  if (process.platform === "win32") {
    try {
      require("child_process").execSync(`taskkill /F /T /PID ${flaskProcess.pid}`, { stdio: "pipe", timeout: 5000 });
    } catch (e) {}
  } else {
    if (!flaskProcess.killed) {
      flaskProcess.kill("SIGTERM");
      setTimeout(() => {
        if (!flaskProcess.killed) flaskProcess.kill("SIGKILL");
      }, 2000);
    }
  }
  flaskProcess = null;
}

async function setupAndStart() {
  const isDev = !app.isPackaged;
  const basePath = isDev
    ? path.join(__dirname, "electron-app", "filament-calculator")
    : path.join(process.resourcesPath, "filament-calculator");

  const pythonCmd = findPython();
  if (!pythonCmd) {
    mainWindow.loadFile(path.join(__dirname, "error.html"));
    return;
  }

  if (!checkFlask(pythonCmd)) {
    const flagFile = path.join(app.getPath("userData"), ".flask_installed");
    if (fs.existsSync(flagFile)) {
      mainWindow.loadFile(path.join(__dirname, "error.html"));
      return;
    }
    try {
      await installFlask(pythonCmd, basePath);
      fs.writeFileSync(flagFile, "");
    } catch (e) {
      mainWindow.loadFile(path.join(__dirname, "error.html"));
      return;
    }
  }

  const scriptPath = path.join(basePath, "app.py");

  let pythonPath = path.dirname(pythonCmd);
  let env = { ...process.env, PYTHONUNBUFFERED: "1" };
  
  if (app.isPackaged && pythonCmd.includes("python.exe")) {
    const pythonDir = path.dirname(pythonCmd);
    const sitePackages = path.join(pythonDir, "Lib", "site-packages");
    env.PYTHONPATH = sitePackages + path.delimiter + pythonDir;
  }

  flaskProcess = spawn(pythonCmd, [scriptPath], {
    cwd: basePath,
    env: env,
    stdio: ["pipe", "pipe", "pipe"],
    windowsHide: true,
  });

  flaskProcess.stderr.on("data", (d) => {
    const msg = d.toString().trim();
    if (msg.includes("No module named") || msg.includes("ModuleNotFoundError")) {
      mainWindow.loadFile(path.join(__dirname, "error.html"));
    }
  });

  flaskProcess.on("close", () => { flaskProcess = null; });
  flaskProcess.on("error", () => { flaskProcess = null; });

  const url = "http://127.0.0.1:5000";

  waitForServer(url, 30, 500, () => {
    mainWindow.loadURL(url);
  }, () => {
    mainWindow.loadFile(path.join(__dirname, "error.html"));
  });
}

app.whenReady().then(() => {
  mainWindow = createWindow();
  showLoadingScreen();
  setupAndStart().catch(() => {
    mainWindow.loadFile(path.join(__dirname, "error.html"));
  });
  app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});

app.on("window-all-closed", () => {
  killFlask();
  setTimeout(() => {
    app.exit(0);
  }, 500);
});

app.on("before-quit", () => {
  killFlask();
});

app.on("will-quit", () => {
  killFlask();
});
