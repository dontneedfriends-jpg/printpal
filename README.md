# PrintPAL

**RU** — Программа для учёта филамента и расчёта стоимости 3D-печати.

**EN** — Filament tracker and 3D print cost calculator.


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
- 9 цветовых тем. Каждая со светлой и тёмной версией
- Три языка интерфейса: русский, английский, испанский
- Настраиваемый порядок вкладок. Перетащи как удобно
- Экспорт истории в CSV


<img width="1280" height="1032" alt="calc" src="https://github.com/user-attachments/assets/9597388a-35ed-4301-9bd3-2572cf5127c4" />
<img width="1280" height="833" alt="web" src="https://github.com/user-attachments/assets/65d0bf9a-7027-4373-a662-b90e0d914911" />
<img width="1280" height="1032" alt="settings" src="https://github.com/user-attachments/assets/8f74881f-b013-4f98-98f0-c17832fafad5" />
<img width="1280" height="833" alt="print" src="https://github.com/user-attachments/assets/aa4db95d-1c5d-45d9-8d98-77a69f3c0a95" />
<img width="1280" height="1032" alt="history" src="https://github.com/user-attachments/assets/bc2dee4e-b222-457d-878e-eac15426a14e" />
<img width="1280" height="833" alt="filaments" src="https://github.com/user-attachments/assets/167021a1-6a67-4714-b0ed-37f1b800f18b" />



**EN:**

- Calculates print cost. Counts filament, electricity, printer wear, markup
- Tracks filament remaining. Decreases automatically after each calculation
- Saves calculation history. Attached model files downloadable from history
- Shows printer web UI. Enter IP — see printer interface right in the app
- Supports camera. Separate IP for video stream
- Tracks maintenance hours. Progress bar on dashboard
- Export and import filaments via JSON file
- 9 color themes. Each with light and dark mode
- Three languages. Russian, English, Spanish
- Customizable tab order. Drag to reorder
- Export history to CSV

---

## Как запустить / Quick Start

**RU:**

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
npm run build:win
```

Результат: `dist5/PrintPAL.exe` — портативный файл, ~180 МБ.

### Linux

```bash
cd electron-app
npm install
npx electron-builder --linux
```

Результат: `dist/printpal-1.1.0.tar.gz` — архив, ~98 МБ.

Запуск:
```bash
tar -xzf printpal-1.1.0.tar.gz
cd PrintPAL
./PrintPAL
```

### macOS

Сборка macOS возможна только на Mac.

```bash
cd electron-app
npm install
npx electron-builder --mac
```

Результат: `dist/PrintPAL-1.1.0.dmg`

---

## Техническая часть / Technical Details

### Архитектура

Electron запускает Flask как дочерний процесс. Flask слушает `127.0.0.1:5000`. Electron открывает это URL в окне с кастомным тайтлбаром. При закрытии окна Flask процесс убивается через `taskkill /F /T`.

### Стек

| Компонент | Технология |
|-----------|------------|
| Backend | Python 3.10+ / Flask |
| База данных | SQLite (WAL mode, индексы) |
| Desktop | Electron 33 |
| Frontend | HTML + CSS + JS, Jinja2 шаблоны |

### Структура проекта

```
electron-app/
├── main.js                 # Electron main process, запуск Flask
├── preload.js              # Безопасный мост Electron ↔ renderer
├── loading.html            # Экран загрузки
├── error.html              # Экран ошибки
├── package.json            # Зависимости + конфиг electron-builder
└── filament-calculator/
    ├── app.py              # Flask: маршруты, логика расчёта, i18n
    ├── database.py         # Схема БД, миграции, PRAGMA оптимизации
    ├── config.py           # Константы, пути к БД и uploads
    ├── translations.py     # Словари переводов (RU/EN/ES)
    ├── requirements.txt    # flask
    ├── templates/          # Jinja2 шаблоны (8 страниц)
    └── static/
        └── style.css       # CSS переменные, 9 тем, адаптив
```

### База данных

4 таблицы: `printers`, `filaments`, `calculations`, `settings`.

Оптимизации SQLite:
- `journal_mode = WAL` — параллельное чтение/запись
- `synchronous = NORMAL` — баланс скорости и безопасности
- `cache_size = -2000` — 2 МБ кэш в памяти
- Индексы на `created_at`, `printer_id`, `filament_id`, `name`

### Формула расчёта

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

Переводы через `translations.py` (словари RU/EN/ES). Jinja2 получает функцию `_()` через `@app.context_processor`. Навигация переводится на сервере, JS-элементы — через объект `T` в `base.html`. Язык хранится в cookie + localStorage + БД.

### Темы

CSS переменные в `:root` и `[data-theme="dark"]`. 9 пресетов через `[data-preset="..."]` — каждый определяет ~60 переменных. Переключение через cookie, сервер генерирует `/theme.css` с актуальными значениями.

### Хранение данных

- **Dev-режим:** БД в папке проекта (`filament-calculator/filament.db`)
- **Packaged режим:** `%APPDATA%\PrintPAL\data\filament.db` (Windows), `~/Library/Application Support/PrintPAL/data/` (macOS), `~/.local/share/PrintPAL/data/` (Linux)
- Загруженные файлы моделей: рядом с БД в папке `uploads/`

---

## Лицензия / License

MIT
