# PrintPAL Changelog

## v1.3.0 — 2026-04-10

### Features

- **Embedded Python 3.12.8** — Больше не надо просить друзей установить Python, чтобы запустить программу. Всё внутри, включая интерпретатор. Просто скачай, распакуй и работай. Никаких "pip install", никаких "а какой версии у тебя Python?", никакой головной боли с зависимостями!

- **17 новых тем** — Добавлены: Game Boy, CRT, Neon, Windows 98, Solarized, Gruvbox, Synthwave, Monochrome, Catppuccin, Tokyo Night, One Dark, Monokai, GitHub, Ayu, Night Owl, Cobalt2, Horizon. Всего 26 тем (light + dark) — для перфекционистов, любителей ретро-игр, ценителей киберпанка и просто всех, кому надоели стандартные цвета. Найди свою идеальную тему или перебирай их все — кто спешит?

- **Undo удаление** — Ударил не то? Ударил, но передумал? Не беда! 5 секунд на раздумье, кнопка ↺ спасёт мир. Только не забудь нажать вовремя — время не резиновое

- **Bulk operations** — Надо удалить сразу 15 филаментов, 3 принтера и историю за месяц? Один клик — и никакой рутины. Выделил, нажал, забыл. Правда, Undo работает только 5 секунд, так что выделяй аккуратно

- **AJAX сохранение** — Калькулятор теперь сохраняет без перезагрузки страницы. Плюс модное toast-уведомление, чтобы ты точно знал, что всё сохранилось. Никакого моргания экрана, никаких "подождите, идёт загрузка"

- **Контекстное меню** — Забыл, где кнопка редактирования? Не помнишь, как удалить? Правый клик — и редактируй или удаляй. Не надо искать кнопки, не надо листать страницу — всё под рукой

- **Расширенное модальное окно Shpoolken** — 600px ширина, индивидуальные поля для цены каждого филамента. Теперь можно не только смотреть, но и вносить свои данные. Или просто смотреть на цены и плакать — каждому своё

- **Огонь на логотипе** — При клике на логотип страницы "О приложении" появляется огонь. Просто так, без причины, без последствий. Потому что можем

### Bug Fixes

- **Jinja from_json filter** — Исправлена ошибка 500 на странице истории. Оказывается, filter нужно регистрировать через `@app.template_filter`, а не через context_processor. Кто бы мог подумать! Теперь история показывается правильно, без ошибок и ругательств

- **Select mode header** — Исправлено смещение заголовка в режиме выбора. Теперь всё ровно, как должно быть. Никаких кривых заголовков, никаких сдвинутых кнопок — чистота и порядок

### Technical

- Python 3.12.8 интегрирован через `electron-app/python/` папку — без системного Python, без конфликтов версий, без танцев с бубном
- runner.py добавляет filament-calculator в sys.path — маленький костыль для большого удобства, но работает
- Build output: `dist6/win-unpacked/PrintPAL.exe` (~180 MB portable) — просто распаковать и запустить. Никакой установки, никакой регистрации, никаких скрытых майнеров

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
