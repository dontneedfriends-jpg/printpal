# PrintPAL

**RU** — Программа для учёта филамента и расчёта стоимости 3D-печати. Потому что считать в уме — это для математиков, а мы тут печатаем.

**EN** — Filament tracker and 3D print cost calculator. Because doing math in your head is for mathematicians, and we're here to print stuff.

> **Version 1.3.0** — см. [Changelog](CHANGELOG.md)

<img width="1280" height="1032" alt="dash" src="https://github.com/user-attachments/assets/7c37d0d5-5c94-441d-86ca-4ccbd872c8c2" />

---

## Что умеет / Features

**RU:**

- Считает стоимость печати. Учитывает филамент, электричество, износ принтера, наценку — всё как взрослые
- Следит за остатками филамента. Остаток уменьшается сам после каждого расчёта, потому что лень обновлять
- Хранит историю расчётов. Прикреплённый файл модели скачивается из истории — вдруг передумаешь
- Показывает веб-интерфейс принтера. Вводишь IP — видишь морду принтера прямо в программе. Зачем вставать?
- Поддерживает камеру. Отдельный IP для видеопотока — следить за печатью с дивана
- Отслеживает часы до техобслуживания. Прогресс-бар на дашборде — чтобы не сломалось в самый неподходящий момент
- Экспорт и импорт филаментов через JSON. Делись своим богатством
- 26 цветовых тем. Каждая со светлой и тёмной версией — для перфекционистов
- Три языка интерфейса: русский, английский, испанский. Глобализация во всей красе
- Настраиваемый порядок вкладок. Перетащи как удобно
- Экспорт истории в CSV. Для бухгалтеров и их странных запросов
- База филаментов из ShpoolkenDB. Поддерживается автором проекта
- Страница "О приложении". Где ещё узнать, кто виноват в этом?

**EN:**

- Calculates print cost. Counts filament, electricity, printer wear, markup — adulting edition
- Tracks filament remaining. Decreases automatically after each calculation, because updating is for chumps
- Saves calculation history. Attached model files downloadable from history — in case you reconsider
- Shows printer web UI. Enter IP — see printer interface right in the app. Why get up?
- Supports camera. Separate IP for video stream — watching prints from the couch
- Tracks maintenance hours. Progress bar on dashboard — so it doesn't break at the worst moment
- Export and import filaments via JSON. Share your wealth
- 26 color themes. Each with light and dark mode — for perfectionists
- Three languages. Russian, English, Spanish. Globalization at its finest
- Customizable tab order. Drag to reorder
- Export history to CSV. For accountants and their weird requests
- Filament database from ShpoolkenDB. Maintained by project author
- About page. Where else will you learn who's to blame?

<img width="1280" height="1032" alt="calc" src="https://github.com/user-attachments/assets/9597388a-35ed-4301-9bd3-2572cf5127c4" />
<img width="1280" height="833" alt="web" src="https://github.com/user-attachments/assets/65d0bf9a-7027-4373-a662-b90e0d914911" />
<img width="1280" height="1032" alt="settings" src="https://github.com/user-attachments/assets/8f74881f-b013-4f98-98f0-c17832fafad5" />
<img width="1280" height="833" alt="print" src="https://github.com/user-attachments/assets/aa4db95d-1c5d-45d9-8d98-77a69f3c0a95" />
<img width="1280" height="1032" alt="history" src="https://github.com/user-attachments/assets/bc2dee4e-b222-457d-878e-eac15426a14e" />
<img width="1280" height="833" alt="filaments" src="https://github.com/user-attachments/assets/167021a1-6a67-4714-b0ed-37f1b800f18b" />

---

## Как запустить / Quick Start

**RU:**

В теории нужен Python и Node.js. На практике есть портативный exe — просто запусти и не парься.

Вариант 1 (portable, рекомендуется):
```
dist6/win-unpacked/PrintPAL.exe
```

Вариант 2 (из исходников, для гиков):
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

In theory you need Python and Node.js. In practice there's a portable exe — just run it and don't sweat it.

Option 1 (portable, recommended):
```
dist6/win-unpacked/PrintPAL.exe
```

Option 2 (from source, for geeks):
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

Результат: `dist6/win-unpacked/PrintPAL.exe` — портативный файл, ~180 МБ. Готов к использованию, не благодари.

### Linux

```bash
cd electron-app
npm install
npx electron-builder --linux
```

Результат: `dist/printpal-1.3.0.tar.gz` — архив, ~98 МБ.

Запуск:
```bash
tar -xzf printpal-1.3.0.tar.gz
cd PrintPAL
./PrintPAL
```

### macOS

Сборка macOS возможна только на Mac. Это не дискриминация — это Apple.

```bash
cd electron-app
npm install
npx electron-builder --mac
```

Результат: `dist/PrintPAL-1.3.0.dmg`

---

## Техническая часть / Technical Details

### Архитектура

Electron запускает Flask как дочерний процесс. Flask слушает `127.0.0.1:5000`. Electron открывает это URL в окне с кастомным тайтбаром. При закрытии окна Flask процесс убивается через `taskkill /F /T`. Всё просто, как в библиотеке.

### Стек

| Компонент | Технология |
|-----------|------------|
| Backend | Python 3.12 / Flask |
| База данных | SQLite (WAL mode, индексы) |
| Desktop | Electron 33 |
| Frontend | HTML + CSS + JS, Jinja2 шаблоны |

### Структура проекта

```
electron-app/
├── main.js                 # Electron main process, запуск Flask
├── preload.js              # Безопасный мост Electron ↔ renderer
├── loading.html            # Экран загрузки — пока ждёшь
├── error.html              # Экран ошибки — когда всё сломалось
├── package.json            # Зависимости + конфиг electron-builder
├── python/                  # Embedded Python 3.12 — да, без системного Python
├── runner.py               # Flask runner — костыль для запуска из Electron
└── filament-calculator/
    ├── app.py              # Flask: маршруты, логика расчёта, i18n, 26 тем
    ├── database.py         # Схема БД, миграции, PRAGMA оптимизации
    ├── config.py           # Константы, пути к БД и uploads
    ├── translations.py     # Словари переводов (RU/EN/ES)
    ├── requirements.txt    # flask
    ├── templates/          # Jinja2 шаблоны (12 страниц)
    │   ├── base.html       # База с темами
    │   ├── index.html     # Дашборд
    │   ├── filaments.html  # Управление филаментами
    │   ├── printers.html   # Управление принтерами
    │   ├── calculator.html # Калькулятор стоимости
    │   ├── history.html   # История расчётов
    │   ├── settings.html # Настройки
    │   ├── about.html    # О приложении
    │   ├── shpoolken.html # База из ShpoolkenDB
    │   └── ...
    └── static/
        └── style.css       # CSS переменные, 26 тем, адаптив
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

Просто математика, никакой магии.

### i18n

Переводы через `translations.py` (словари RU/EN/ES). Jinja2 получает функцию `_()` через `@app.context_processor`. Навигация переводится на сервере, JS-элементы — через объект `T` в `base.html`. Язык хранится в cookie + localStorage + БД.

### Темы

CSS переменные в `:root` и `[data-theme="dark"]`. 26 пресетов через `[data-preset="..."]` — каждый определяет ~60 переменных. Переключение через cookie, сервер генерирует `/theme.css` с актуальными значениями.

Список тем: modern, retro, terminal, material, pastel, nord, dracula, ocean, sunset, gameboy, crt, neon, windows98, solarized, gruvbox, synthwave, monochrome, catppuccin, tokyonight, onedark, monokai, github, ayu, nightowl, cobalt2, horizon.



### Хранение данных

- **Dev-режим:** БД в папке проекта (`filament-calculator/filament.db`)
- **Packaged режим:** `%APPDATA%\PrintPAL\data\filament.db` (Windows), `~/Library/Application Support/PrintPAL/data/` (macOS), `~/.local/share/PrintPAL/data/` (Linux)
- Загруженные файлы моделей: рядом с БД в папке `uploads/`

---

## Лицензия / License

MIT — делай что хочешь, только не ной.

---

## Авторы / Credits

Сделано с ❤️, ☕ и немного с 🧠.

База филаментов: [ShpoolkenDB](https://dontneedfriends-jpg.github.io/ShpoolkenDB/) — источник данных о филаментах, который сэкономил нам кучу времени.