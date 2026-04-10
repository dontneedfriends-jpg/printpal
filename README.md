# PrintPAL

**RU** — Программа для учёта филамента и расчёта стоимости 3D-печати.

**EN** — Filament tracker and 3D print cost calculator.


<img width="1280" height="800" alt="Capture" src="https://github.com/user-attachments/assets/e282ba5a-f9fc-4399-97ea-96a4d66656fc" />



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

<img width="1920" height="1032" alt="ddd" src="https://github.com/user-attachments/assets/0f643044-bb3e-4a39-abf0-745e1f00244e" />
<img width="1280" height="1032" alt="ыещ" src="https://github.com/user-attachments/assets/dc605626-aa86-4ef1-953d-1d6b9c4445a3" />
<img width="1280" height="1032" alt="фы" src="https://github.com/user-attachments/assets/4c4f3fc1-4d44-4e3f-ab2e-7064fbb0acde" />
<img width="1280" height="1032" alt="зшг" src="https://github.com/user-attachments/assets/3eb13b48-9259-41b1-a8da-33b80139bb77" />
<img width="1920" height="1032" alt="base" src="https://github.com/user-attachments/assets/fa07fbdb-d582-477a-bb68-5de757b97808" />





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
