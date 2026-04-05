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
  const localAppData = process.env.LOCALAPPDATA || "";
  const progFiles = process.env.ProgramFiles || "C:\\Program Files";

  // Prefer known-good paths first
  const candidates = [
    path.join(localAppData, "Programs", "Python", "Python314", "python.exe"),
    path.join(localAppData, "Programs", "Python", "Python313", "python.exe"),
    path.join(localAppData, "Programs", "Python", "Python312", "python.exe"),
    path.join(localAppData, "Programs", "Python", "Python311", "python.exe"),
    path.join(localAppData, "Programs", "Python", "Python310", "python.exe"),
    path.join(progFiles, "Python314", "python.exe"),
    path.join(progFiles, "Python313", "python.exe"),
    path.join(progFiles, "Python312", "python.exe"),
    path.join(progFiles, "Python311", "python.exe"),
    path.join(progFiles, "Python310", "python.exe"),
    `C:\\Python314\\python.exe`,
    `C:\\Python313\\python.exe`,
    `C:\\Python312\\python.exe`,
    `C:\\Python311\\python.exe`,
    `C:\\Python310\\python.exe`,
    "py",
    "python3",
    "python",
  ];

  for (const cmd of candidates) {
    try {
      execSync(`"${cmd}" --version`, { stdio: "pipe", timeout: 2000 });
      // Check if Flask is available
      try {
        execSync(`"${cmd}" -c "import flask"`, { stdio: "pipe", timeout: 3000 });
        return cmd;
      } catch (e) {
        // No Flask yet, will install later — still return this Python
        return cmd;
      }
    } catch (e) {}
  }
  return null;
}

function checkFlask(pythonCmd) {
  try {
    execSync(`"${pythonCmd}" -c "import flask"`, { stdio: "pipe", timeout: 3000 });
    return true;
  } catch (e) {
    return false;
  }
}

function installFlask(pythonCmd, cwd) {
  return new Promise((resolve, reject) => {
    const proc = spawn(`"${pythonCmd}"`, ["-m", "pip", "install", "--quiet", "flask"], {
      cwd: cwd || process.cwd(),
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
      shell: true,
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
    ? path.join(__dirname, "filament-calculator")
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
  const cmd = pythonCmd.includes(" ") ? `"${pythonCmd}"` : pythonCmd;

  flaskProcess = spawn(cmd, [scriptPath], {
    cwd: basePath,
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
    stdio: ["pipe", "pipe", "pipe"],
    windowsHide: true,
    shell: true,
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
