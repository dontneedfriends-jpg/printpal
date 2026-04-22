const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { spawn, execSync } = require("child_process");
const http = require("http");
const fs = require("fs");

const CONFIG = {
  window: {
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
  },
  flask: {
    host: process.env.FLASK_HOST || "127.0.0.1",
    port: parseInt(process.env.FLASK_PORT, 10) || 5000,
    maxRetries: 30,
    retryInterval: 500,
  },
  timeouts: {
    kill: 5000,
    sigkillDelay: 2000,
    appExit: 500,
    startupDelay: 2000,
  },
};

let logFile;

function log(...args) {
  const line = new Date().toISOString() + " " + args.join(" ") + "\n";
  console.log(...args);
  if (logFile) {
    try { fs.appendFileSync(logFile, line); } catch(e) {}
  }
}

function getAppBasePath() {
  if (app.isPackaged) {
    return path.dirname(app.getAppPath());
  }
  return __dirname;
}

let mainWindow;
let flaskProcess;

function waitForServer(url, retries, interval, cb, failCb) {
  log("waitForServer:", url);
  http
    .get(url, (res) => {
      log("Server response:", res.statusCode);
      if (res.statusCode === 200) cb();
      else if (retries > 0) setTimeout(() => waitForServer(url, retries - 1, interval, cb, failCb), interval);
      else failCb(`Server returned ${res.statusCode}`);
    })
    .on("error", (e) => {
      log("Server error:", e.code);
      if (retries > 0) setTimeout(() => waitForServer(url, retries - 1, interval, cb, failCb), interval);
      else failCb("Connection refused");
    });
}

log("Creating window function...");

function createWindow() {
  mainWindow = new BrowserWindow({
    width: CONFIG.window.width,
    height: CONFIG.window.height,
    minWidth: CONFIG.window.minWidth,
    minHeight: CONFIG.window.minHeight,
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

function findEmbeddedPython() {
  const candidates = [
    path.join(__dirname, "python", "python.exe"),
    path.join(__dirname, "python", "python3.exe"),
  ];
  
  for (const cmd of candidates) {
    if (fs.existsSync(cmd)) {
      return cmd;
    }
  }
  return null;
}

function killFlask() {
  try {
    if (!flaskProcess) return;
    log("Killing Flask process...");
    if (process.platform === "win32") {
      try {
        execSync(`taskkill /F /T /PID ${flaskProcess.pid}`, { stdio: "pipe", timeout: CONFIG.timeouts.kill });
      } catch (e) { 
        log("kill error:", e.message); 
      }
      flaskProcess = null;
      return;
    } else {
      if (!flaskProcess.killed) {
        flaskProcess.kill("SIGTERM");
        setTimeout(() => {
          if (flaskProcess && !flaskProcess.killed) flaskProcess.kill("SIGKILL");
        }, CONFIG.timeouts.sigkillDelay);
      }
    }
    flaskProcess = null;
  } catch(e) {
    log("killFlask error:", e.message);
  }
}

async function setupAndStart() {
  const appBase = getAppBasePath();
  log("App base path:", appBase);
  log("App is packaged:", app.isPackaged);
  
  const isDev = !app.isPackaged;
  
  let basePath, pythonCmd, scriptPath;
  
  if (isDev) {
    log("Dev mode branch");
    basePath = path.join(__dirname, "filament-calculator");
    pythonCmd = findEmbeddedPython();
    if (!pythonCmd) {
      pythonCmd = "python";
    }
    scriptPath = path.join(basePath, "app.py");
  } else {
    log("Packaged mode branch");
    basePath = path.join(process.resourcesPath, "app.asar.unpacked", "filament-calculator");
    pythonCmd = path.join(process.resourcesPath, "python", "python.exe");
    scriptPath = path.join(basePath, "app.py");
    log("Using unpacked path:", basePath);
    log("Resources path:", process.resourcesPath);
    log("Python cmd:", pythonCmd);
  }
  
  log("Python exists:", fs.existsSync(pythonCmd), pythonCmd);
  log("Script exists:", fs.existsSync(scriptPath), scriptPath);
  
  if (!fs.existsSync(pythonCmd)) {
    console.error("Python not found:", pythonCmd);
    mainWindow.loadFile(path.join(__dirname, "error.html"));
    return;
  }
  
  if (!fs.existsSync(scriptPath)) {
    console.error("Script not found:", scriptPath);
    mainWindow.loadFile(path.join(__dirname, "error.html"));
    return;
  }
  
  const pythonDir = path.dirname(pythonCmd);
  const pythonPath = path.join(pythonDir, "Lib", "site-packages");
  const newPath = pythonDir + path.delimiter + (process.env.PATH || "");
  
  log("Python dir:", pythonDir);
  log("Python path:", pythonPath);
  
  const newEnv = { 
    ...process.env, 
    PYTHONUNBUFFERED: "1", 
    PATH: newPath,
    PYTHONPATH: pythonDir + path.delimiter + pythonPath + path.delimiter + basePath,
    FLASK_HOST: CONFIG.flask.host,
    FLASK_PORT: String(CONFIG.flask.port),
  };

  // Test python first
  const testPy = spawn(pythonCmd, ["-c", "import sys; print('PYTHON:', sys.path)"], {
    cwd: basePath,
    env: newEnv,
    stdio: ["pipe", "pipe", "pipe"],
    windowsHide: true,
  });
  
  testPy.stdout.on("data", (d) => { log("PYTHON TEST OUT:", d.toString().trim()); });
  testPy.stderr.on("data", (d) => { log("PYTHON TEST ERR:", d.toString().trim()); });
  testPy.on("close", (code) => {
    log("Python test exit code:", code);
    runFlask();
  });

  function runFlask() {
    log("PYTHONPATH:", pythonDir + path.delimiter + pythonPath + path.delimiter + basePath);
    log("Full command:", `"${pythonCmd}" "${scriptPath}"`);
    log("CWD:", basePath);

    flaskProcess = spawn(pythonCmd, [scriptPath], {
      cwd: basePath,
      env: newEnv,
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
      shell: true,
    });

    flaskProcess.stdout.on("data", (d) => { log("[FLASK]", d.toString().trim()); });
    flaskProcess.stderr.on("data", (d) => { log("[FLASK]", d.toString().trim()); });
    flaskProcess.on("close", () => { flaskProcess = null; });
    flaskProcess.on("error", (e) => { log("[SPAWN ERR]", e); flaskProcess = null; });

    const url = `http://${CONFIG.flask.host}:${CONFIG.flask.port}`;
    log("Will wait for Flask at:", url);
    waitForServer(url, CONFIG.flask.maxRetries, CONFIG.flask.retryInterval, () => {
      log("Flask server is up, loading URL...");
      mainWindow.loadURL(url);
    }, () => {
      log("Flask failed to start, loading error page");
      mainWindow.loadFile(path.join(__dirname, "error.html"));
    });
  }
}

app.whenReady().then(() => {
  const logDir = app.isPackaged ? process.resourcesPath : __dirname;
  logFile = path.join(logDir, "debug.log");
  try { fs.writeFileSync(logFile, "=== main.js started ===\n"); } catch(e) {}
  
  log("=== APP READY ===");
  log("App path:", app.getAppPath());
  log("Resources path:", process.resourcesPath);
  log("isPackaged:", app.isPackaged);
  log("__dirname:", __dirname);
  
  mainWindow = createWindow();
  
  mainWindow.loadFile(path.join(__dirname, "loading.html"));
  mainWindow.show();
  
  setTimeout(() => {
    setupAndStart().catch((e) => {
      console.error("Error:", e);
    });
  }, CONFIG.timeouts.startupDelay);
  
  app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});

app.on("window-all-closed", () => {
  try { killFlask(); } catch(e) { log("window-all-closed error:", e.message); }
  setTimeout(() => app.exit(0), CONFIG.timeouts.appExit);
});

app.on("before-quit", () => { 
  try { killFlask(); } catch(e) { log("before-quit error:", e.message); } 
});

app.on("will-quit", () => { 
  try { killFlask(); } catch(e) { log("will-quit error:", e.message); } 
});