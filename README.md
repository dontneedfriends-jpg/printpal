# PrintPAL

**RU** — Программа для учёта филамента и расчёта стоимости 3D-печати.
**EN** — Filament tracker and 3D print cost calculator.

---

## Что умеет / Features

**RU:**

- Считает стоимость печати. Учитывает филамент, электричество, износ принтера, наценку
- Следит за остатками филамента. Остаток уменьшается сам после каждого расчёта
- Хранит историю расчётов. Можно прикрепить файл модели (STL, OBJ, GCODE)
- Показывает веб-интерфейс принтера. Вводишь IP — видишь морду принтера прямо в программе
- Поддерживает камеру. Отдельный IP для видеопотока
- 9 цветовых тем. Каждая со светлой и тёмной версией
- Три языка. Русский, английский, испанский
- Настраиваемый порядок вкладок. Перетащи как удобно
- Экспорт истории в CSV

**EN:**

- Calculates print cost. Counts filament, electricity, printer wear, markup
- Tracks filament remaining. Decreases automatically after each calculation
- Saves calculation history. Attach model files (STL, OBJ, GCODE)
- Shows printer web UI. Enter IP — see printer interface right in the app
- Supports camera. Separate IP for video stream
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

**RU:**

```bash
npm run build:win
```

Результат: `dist/PrintPAL.exe` — портативный файл, ~75 МБ. Не требует установки.

**EN:**

```bash
npm run build:win
```

Output: `dist/PrintPAL.exe` — portable executable, ~75 MB. No installation needed.

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
    ├── templates/          # Jinja2 шаблоны (7 страниц)
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

---

## Лицензия / License

MIT
