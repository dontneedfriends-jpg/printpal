# PrintPAL Changelog

## v1.3.0 — 2026-04-10

### Features

- **Embedded Python 3.12.8** — Приложение не требует установленного Python. Всё внутри!
- **17 новых тем** — Добавлены: Game Boy, CRT, Neon, Windows 98, Solarized, Gruvbox, Synthwave, Monochrome, Catppuccin, Tokyo Night, One Dark, Monokai, GitHub, Ayu, Night Owl, Cobalt2, Horizon. Всего 26 тем (light + dark)
- **Undo удаление** — Удалённые элементы можно восстановить за 5 секунд (кнопка ↺)
- **Bulk operations** — Групповое удаление филаментов, принтеров, истории расчётов
- **AJAX сохранение** — Калькулятор сохраняет без перезагрузки страницы (toast уведомление)
- **Контекстное меню** — Удаление и редактирование по клику правой кнопкой
- **Расширенное модальное окно Shpoolken** — 600px ширина, индивидуальные поля для цены каждого филамента
- **Easter eggs** — Konami code (↑↑↓↓←→←→BA) и огонь на логотипе при клике (страница "О приложении")

### Bug Fixes

- **Jinja from_json filter** — Исправлена ошибка 500 на странице истории (filter должен быть зарегистрирован через `@app.template_filter`, не context_processor)
- **Select mode header** — Исправлено смещение заголовка в режиме выбора

### Technical

- Python интегрирован через `electron-app/python/` папку
- runner.py добавляет filament-calculator в sys.path
- Build output: `dist6/win-unpacked/PrintPAL.exe` (~180 MB portable)

---

## v1.1.1 — 2026-04-07

### Features

- **ShpoolkenDB Integration** — Online filament catalog with card-based UI and large color blocks
  - Sync from GitHub repository
  - Filter by manufacturer and material
  - One-click add to local filaments
  - `{color_name}` placeholder filtered at insert time
- **Color Picker** — HTML5 color picker in filament add/edit modal
- **Color Circles** — Color dots shown on Dashboard, filaments page, and history
- **About Page** — New navbar tab with donate links (CloudTips, Boosty)
- **Multi-filament History** — All filaments shown in history (not just first one)

### Bug Fixes

- **History Delete** — Deleting calculation now restores filament weights back
- **ShpoolkenDB Display** — `{color_name}` filtered from names and colors
- **Calculator Error** — Added fallback for old databases without `filament_data` column
- **History Display** — Fixed showing only first filament

### Technical

- `calculations` table now has `filament_data` JSON column storing all filaments used
- `from_json()` Jinja filter added to context processor
- `filament_data` migration with fallback for old databases

---

## v1.1.0 — 2026-04-06

### Bug Fixes

- **History delete** — fixed deletion not working; now uses modal confirmation dialog (like filaments)
- **Calculator persistence** — filament selection and weights now preserved after preview
- **CSS typo** — fixed `--text-muted: #6868888` → `#686888`

### Security Improvements

- Secret key generated dynamically via `secrets.token_hex(32)` (no hardcoded key)
- Path traversal protection in file downloads via `safe_filename()`
- Input validation helpers (`safe_float()`, `safe_int()`) with sensible defaults
- Division by zero protection in cost calculations
- Database migration errors now logged instead of silently ignored

---

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

- **Windows**: portable exe, ~71 MB
- **Linux**: archive, ~98 MB
