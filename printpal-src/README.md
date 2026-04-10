# PrintPAL

**RU** — Программа для учёта филамента и расчёта стоимости 3D-печати.

**EN** — Filament tracker and 3D print cost calculator.

> **Version 1.3.0** — см. [Changelog](CHANGELOG.md)

<img width="1280" height="1032" alt="dash" src="https://github.com/user-attachments/assets/7c37d0d5-5c94-441d-86ca-4ccbd872c8c2" />

---

## Что умеет / Features

**RU:**

- Считает стоимость печати. Учитывает филамент, электричество, износ принтера, наценку
- Следит за остатками филамента. Остаток уменьшается сам после каждого расчёта
- Хранит историю расчётов. Прикреплённый файл модели скачивается из истории
- Показывает веб-интерфейс принтера. Вводишь IP — видишь морду принтера прямо в программе
- Поддерживает камеру. Отдельный IP для видеопотока
- Отслеживает часы до техобслуживания. Прогресс-бар на дашборде
- Экспорт и импорт филаментов через JSON-файл
- **26 цветовых тем**. Каждая со светлой и тёмной версией ( Dracula, Nord, Catppuccin, Tokyo Night, One Dark, Monokai, GitHub, и др.)
- Три языка интерфейса: русский, английский, испанский
- Настраиваемый порядок вкладок. Перетащи как удобно
- Экспорт истории в CSV
- **Групповые операции** с отменой (удаление нескольких филаментов/принтеров с undo за 5 секунд)
- **Интеграция с ShpoolkenDB**. Загружай филаменты из онлайн-базы или добавляй свои
- **Не требует Python**. Python встроен в приложение — просто скачай и запусти
- **Работает офлайн**. Всё хранится локально — никаких облаков и Docker

**EN:**

- Calculates print cost. Counts filament, electricity, printer wear, markup
- Tracks filament remaining. Decreases automatically after each calculation
- Saves calculation history. Attached model files downloadable from history
- Shows printer web UI. Enter IP — see printer interface right in the app
- Supports camera. Separate IP for video stream
- Tracks maintenance hours. Progress bar on dashboard
- Export and import filaments via JSON file
- **26 color themes**. Each with light and dark mode (Dracula, Nord, Catppuccin, Tokyo Night, One Dark, Monokai, GitHub, etc.)
- Three languages. Russian, English, Spanish
- Customizable tab order. Drag to reorder
- Export history to CSV
- **Bulk operations with undo** (delete multiple filaments/printers with 5-second undo)
- **ShpoolkenDB integration**. Load filaments from online DB or add your own
- **No Python required**. Python is embedded — just download and run
- **Works offline**. Everything stored locally — no clouds and no Docker


<img width="1280" height="1032" alt="calc" src="https://github.com/user-attachments/assets/9597388a-35ed-4301-9bd3-2572cf5127c4" />
<img width="1280" height="833" alt="web" src="https://github.com/user-attachments/assets/65d0bf9a-7027-4373-a662-b90e0d914911" />
<img width="1280" height="1032" alt="settings" src="https://github.com/user-attachments/assets/8f74881f-b013-4f98-98f0-c17832fafad5" />
<img width="1280" height="833" alt="print" src="https://github.com/user-attachments/assets/aa4db95d-1c5d-45d9-8d98-77a69f3c0a95" />
<img width="1280" height="1032" alt="history" src="https://github.com/user-attachments/assets/bc2dee4e-b222-457d-878e-eac15426a14e" />
<img width="1280" height="833" alt="filaments" src="https://github.com/user-attachments/assets/167021a1-6a67-4714-b0ed-37f1b800f18b" />

---

## Как запустить / Quick Start

**Windows (portable):**

Просто запусти `PrintPAL.exe` из папки `dist6/win-unpacked/`. Ничего не требуется — Python уже внутри.

Just run `PrintPAL.exe` from `dist6/win-unpacked/`. Nothing required — Python is already inside.

**Dev-режим / Dev mode:**

Нужен Python и Node.js.

```bash
# Установить зависимости Python
cd electron-app/filament-calculator
pip install flask

# Установить зависимости Node.js
cd ..
npm install

# Запустить
npm start
```

**EN:**

Requires Python and Node.js.

```bash
# Install Python dependencies
cd electron-app/filament-calculator
pip install flask

# Install Node.js dependencies
cd ..
npm install

# Run
npm start
```

---

## Сборка / Build

### Windows

```bash
cd electron-app
npm run build
```

Result: `dist6/win-unpacked/PrintPAL.exe` — portable file, ~180 MB.

### Linux

```bash
cd electron-app
npm install
npx electron-builder --linux
```

Result: `dist/printpal-1.3.0.tar.gz` — archive, ~98 MB.

Run:
```bash
tar -xzf printpal-1.3.0.tar.gz
cd PrintPAL
./PrintPAL
```

### macOS

macOS build only possible on Mac.

```bash
cd electron-app
npm install
npx electron-builder --mac
```

Result: `dist/PrintPAL-1.3.0.dmg`

---

## Техническая часть / Technical Details

### Архитектура

Electron запускает встроенный Python 3.12.8 как дочерний процесс. Flask слушает `127.0.0.1:5000`. Electron открывает это URL в окне. При закрытии окна Flask процесс убивается.

Embedded Python runs as a child process. Flask listens on `127.0.0.1:5000`. Electron opens this URL in the window. When window closes, Flask process is killed.

### Стек / Stack

| Компонент / Component | Технология / Technology |
|-----------------------|------------------------|
| Desktop | Electron 33 |
| Backend | Python 3.12.8 (embedded) / Flask |
| База данных / DB | SQLite (WAL mode, indexes) |
| Frontend | HTML + CSS + JS, Jinja2 templates |

### Почему без Docker? / Why no Docker?

Потому что нормальный софт не должен требовать докера для простой задачи учёта филаментов.

Because normal software shouldn't require Docker for a simple filament tracking task.

### Структура проекта / Project Structure

```
electron-app/
├── main.js                 # Electron main process
├── preload.js              # Secure bridge
├── runner.py               # Flask runner (adds filament-calculator to path)
├── loading.html            # Loading screen
├── error.html              # Error screen
├── package.json            # Dependencies + electron-builder config
├── python/                 # Embedded Python 3.12.8
│   └── python.exe
└── filament-calculator/
    ├── app.py              # Flask: routes, calculation logic, i18n, 26 themes
    ├── database.py         # DB schema, migrations, PRAGMA optimizations
    ├── config.py           # Constants, paths to DB and uploads
    ├── translations.py     # Translation dictionaries (RU/EN/ES)
    ├── requirements.txt    # flask
    ├── templates/          # Jinja2 templates (9 pages)
    └── static/
        └── style.css       # CSS variables, 26 themes, responsive
```

### База данных / Database

4 tables: `printers`, `filaments`, `calculations`, `settings`.

SQLite optimizations:
- `journal_mode = WAL` — parallel read/write
- `synchronous = NORMAL` — speed vs safety balance
- `cache_size = -2000` — 2MB cache in memory
- Indexes on `created_at`, `printer_id`, `filament_id`, `name`

### Формула расчёта / Calculation formula

```
price_per_gram = spool_price / spool_weight_g
filament_cost  = weight_g × price_per_gram
electricity    = hours × (watts / 1000) × rate_per_kwh
depreciation   = hours × depreciation_per_hour
subtotal       = base_rate + filament_cost + electricity + depreciation
markup         = subtotal × (markup_percent / 100)
total          = subtotal + markup
```

### i18n

Translations via `translations.py` (RU/EN/ES dictionaries). Jinja2 gets `_()` function via `@app.context_processor`. Navigation translated server-side, JS elements — via `T` object in `base.html`. Language stored in cookie + localStorage + DB.

### Темы / Themes

26 themes, each with light and dark mode:

`modern`, `retro`, `terminal`, `material`, `pastel`, `nord`, `dracula`, `ocean`, `sunset`, `gameboy`, `crt`, `neon`, `windows98`, `solarized`, `gruvbox`, `synthwave`, `monochrome`, `catppuccin`, `tokyonight`, `onedark`, `monokai`, `github`, `ayu`, `nightowl`, `cobalt2`, `horizon`

### Хранение данных / Data storage

- **Dev mode:** DB in project folder (`filament-calculator/filament.db`)
- **Packaged mode:** `%APPDATA%\PrintPAL\data\filament.db` (Windows), `~/Library/Application Support/PrintPAL/data/` (macOS), `~/.local/share/PrintPAL/data/` (Linux)
- Uploaded model files: next to DB in `uploads/` folder

---

## ShpoolkenDB

База филаментов ShpoolkenDB поддерживается и развивается тем же автором. Добавляй свои филаменты в общее хранилище!

The ShpoolkenDB filament database is also maintained and developed by the same author. Add your filaments to the shared pool!

🔗 https://dontneedfriends-jpg.github.io/ShpoolkenDB/

---

## Лицензия / License

MIT