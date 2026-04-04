# PrintPAL Changelog

## v1.0.0 — 2026-04-04

### Features

- **Cost calculator** — filament + electricity + depreciation + markup
- **Filament tracking** — remaining weight auto-decreases after each calculation
- **Print history** — with attached model files (STL, OBJ, 3MF, GCODE, STEP)
- **Printer monitoring** — embedded web UI via IP address
- **Camera support** — separate IP for video stream
- **Maintenance tracking** — hours-to-service counter with progress bar on dashboard
- **Filament export/import** — JSON file format for backup and sharing
- **9 color themes** — Modern, Retro, Terminal, Material, Pastel, Nord, Dracula, Ocean, Sunset (each light + dark)
- **3 languages** — Russian, English, Spanish
- **Custom tab order** — drag & drop to reorder navigation
- **CSV export** — full calculation history
- **Custom titlebar** — frameless window with minimize/maximize/close buttons
- **Loading screen** — branded loading state with error handling
- **Auto Flask install** — first launch installs Flask automatically

### Technical

- Electron 33 + Flask + SQLite
- WAL mode, indexed queries
- i18n via `translations.py` + Jinja2 context processor
- CSS variables for theming (60+ variables per preset)
- Data stored in `%APPDATA%\PrintPAL\data` (packaged) or project folder (dev)

### Platforms

- **Windows**: `dist5/PrintPAL.exe` — portable, ~71 MB
- **Linux**: `dist5/printpal-1.0.0.tar.gz` — archive, ~98 MB
