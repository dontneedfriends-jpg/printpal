# AGENTS.md — PrintPAL

## Android APK Build

```powershell
# Prerequisites
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
$env:GRADLE_HOME = "C:\Users\annenskei\.gradle\wrapper\dists\gradle-8.14.3-all\10utluxaxniiv4wxiphsi49nj\gradle-8.14.3"
$env:Path = "$env:JAVA_HOME\bin;$env:GRADLE_HOME\bin;$env:ANDROID_HOME\platform-tools;$env:ANDROID_HOME\build-tools\34.0.0;$env:Path"

# Build
cd printpal-android
gradle assembleDebug --no-daemon

# APK location:
# printpal-android/app/build/outputs/apk/debug/app-debug.apk
```

### Установка на телефон
1. Включить отладку по USB на телефоне
2. `adb install printpal-android/app/build/outputs/apk/debug/app-debug.apk`
3. Открыть PrintPAL → Settings → ввести IP компьютера с Flask сервером (http://192.168.x.x:5000)

### Структура Android проекта
- `printpal-android/` — корень Gradle проекта
- `app/src/main/java/com/printpal/app/MainActivity.java` — WebView, загружающий URL из SharedPreferences
- `app/src/main/java/com/printpal/app/SettingsActivity.java` — экран настройки URL сервера
- `res/xml/network_security_config.xml` — разрешает HTTP (cleartext)
- `res/drawable/ic_launcher_foreground.xml` — трофей (Lucide) на 108dp
- `res/mipmap-anydpi-v26/` — адаптивная иконка (API 26+)

### Важные нюансы
- APK подписан debug-ключом (не для публикации в Google Play)
- Для release нужно создать keystore и подписать
- Gradle 8.5 + AGP 8.3.2 (совместимость с JDK 21 из Android Studio)
- Приложение подключается к удалённому Flask серверу — Python на телефоне не нужен

## Что это такое

**PrintPAL** — десктопное приложение на Electron для расчета стоимости 3D-печати. Помогает калькулировать цену печати с учетом:
- стоимости филамента (по граммам)
- электроэнергии (по ваттам принтера и тарифу)
- амортизации принтера (по часам работы)
- базовой ставки и наценки

Приложение ориентировано на русскоязычных пользователей, но поддерживает i18n (ru/en/es).

## Архитектура

### Стек
- **Backend**: Python 3.11 + Flask
- **Frontend**: HTML + CSS + vanilla JS (Jinja2 templates)
- **Desktop shell**: Electron (Node.js)
- **Database**: SQLite (2 БД: `data.db` — основная, `shpoolken.db` — каталог филаментов)
- **Tests**: pytest

### Структура проекта

```
printpal/
├── electron-app/
│   ├── main.js                    # Entry point Electron, управление окном, запуск Flask
│   ├── preload.js                 # Electron preload (безопасный bridge)
│   ├── loading.html               # Splash screen (Fluent Acrylic)
│   ├── error.html                 # Экран ошибки запуска
│   ├── package.json
│   └── filament-calculator/       # Flask app
│       ├── app.py                 # Точка входа Flask, factory + routes
│       ├── config.py              # HOST, PORT, пути, дефолтные значения
│       ├── database.py            # SQLite helpers, init_db, get_db()
│       ├── themes.json            # 26 цветовых тем (light/dark)
│       ├── translations.py        # i18n словарь
│       ├── utils.py               # safe_float, safe_int
│       ├── requirements.txt
│       ├── static/
│       │   ├── style.css          # Основной CSS (~1700 строк, Acrylic)
│       │   ├── app.js             # Frontend logic (theme, cookies, toast)
│       │   └── bulk-actions.js    # Bulk delete/restore
│       ├── templates/
│       │   ├── base.html          # Layout: titlebar, navbar, scroll-area
│       │   ├── index.html         # Dashboard
│       │   ├── printers.html
│       │   ├── filaments.html     # Мои филаменты + вкладка Shpoolken
│       │   ├── calculator.html
│       │   ├── history.html
│       │   ├── settings.html
│       │   ├── clients.html       # Клиенты / Заказчики
│       │   └── about.html
│       ├── routes/                # Flask Blueprints
│       │   ├── printers.py
│       │   ├── filaments.py
│       │   ├── calculator.py
│       │   ├── settings.py
│       │   ├── history.py
│       │   ├── shpoolken.py
│       │   └── clients.py
│       └── tests/
│           ├── test_smoke.py
│           └── test_calculator.py
└── README.md
```

### Flask Blueprints

После рефакторинга весь routing разбит на Blueprints. Обратная совместимость `url_for` в шаблонах обеспечена через monkey-patch `Request.endpoint` (стрипит префикс blueprint) и `inject_url_for_alias` context processor.

| Blueprint | Prefix | Endpoints |
|-----------|--------|-----------|
| printers | /printers | index, add, edit, delete, restore, monitor |
| filaments | /filaments | index, add, edit, delete, restore, toggle_archived |
| calculator | /calculator | index, upload, calculate |
| settings | /settings | index, update |
| history | /history | index, delete |
| shpoolken | /shpoolken | index, search, sync, add |
| clients | /clients | index, add, edit, delete |

### Electron ↔ Flask взаимодействие

1. `main.js` создает `BrowserWindow` (frameless)
2. Показывает `loading.html`
3. Запускает Flask как child_process (`python app.py`)
4. Ждет `http://127.0.0.1:5000` через `waitForServer()`
5. Загружает `mainWindow.loadURL(url)`
6. `preload.js` экспонирует `window.electronAPI` для minimize/maximize/close

## Дизайн-система: Microsoft Acrylic Fluent

### Философия
- **In-app acrylic** для карточек, кнопок, навбара, модалок, тостов
- **Background acrylic** только для transient UI (modal overlay)
- **Не ставить acrylic на большие фоновые поверхности** (по документации MS)
- Плотный tint (opacity ~0.77–0.88), не прозрачный glass

### CSS-переменные

Ключевые переменные генерируются динамически роутом `/theme.css` из `themes.json`:

```css
:root {
  --glass-bg: rgba(255,255,255,0.77);        /* acrylic tint */
  --glass-bg-hover: rgba(255,255,255,0.83);
  --glass-border: rgba(255,255,255,0.64);    /* luminosity border */
  --glass-border-strong: rgba(255,255,255,0.88);
  --glass-shadow: 0 8px 32px rgba(0,0,0,0.08);
  --glass-shadow-lg: 0 16px 48px rgba(0,0,0,0.12);
  --glass-blur: 24px;                        /* light: 24px, dark: 32px */
  --glass-backdrop: blur(var(--glass-blur)) saturate(1.15);
  --bg-card: rgba(255,255,255,0.80);
  --bg-modal-overlay: rgba(0,0,0,0.35);      /* background acrylic */
  /* ... */
}
```

### Acrylic применение

```css
/* In-app acrylic — карточки, кнопки, тосты */
.card, .stat-card, .filament-card, .modal-box, .toast, .btn-secondary {
  backdrop-filter: var(--glass-backdrop);
  -webkit-backdrop-filter: var(--glass-backdrop);
}

/* Header acrylic */
.titlebar, .navbar {
  backdrop-filter: blur(20px) saturate(1.1);
}

/* Background acrylic — transient UI */
.modal-overlay {
  backdrop-filter: blur(8px) saturate(1.1);
}
```

### Noise texture

Добавлена через `::before` на основных поверхностях:
- `.card::before`, `.modal-box::before`, `.toast::before`, `.titlebar::after`, `.navbar::after`
- Inline SVG с `feTurbulence` (fractalNoise, baseFrequency=0.8)
- Opacity 0.02–0.025
- `pointer-events: none; z-index: 0`
- Дочерние элементы `position: relative; z-index: 1`

### Fallback

```css
@supports not (backdrop-filter: blur(1px)) {
  .card, .modal-box, .toast { background: var(--bg-card); }
}
```

### Темы

26 тем в `themes.json`. Каждая тема имеет `light` и `dark` наборы. Активная тема выбирается через cookie `preset` + `theme` + `glass`.

`app.py` генерирует `/theme.css` на лету. При `glass=0` выдает solid colors без blur.

### Иконки

Все иконки — inline SVG в стиле **Lucide** (stroke-based, 2px stroke, round caps/joins):
- Titlebar: `minus`, `maximize`, `maximize-2` (restore), `x`
- Theme toggle: `moon` / `sun` (автопереключение)
- App icon (loading.html): `trophy` (Lucide)
- Error page: `alert-circle`

Никаких emoji-иконок в навбаре. Навбар — чистый текст.

## Ключевые модули

### database.py
- `get_db()` — возвращает `sqlite3.Row` connection
- `init_db()` — создает таблицы printers, filaments, calculations, clients, settings
- `init_shpoolken_db()` — отдельная БД для каталога
- `get_shpoolken_filaments()` — поиск по каталогу

### calculator logic (app.py)

```python
def calculate_cost_details(printer, filaments_data, print_time, base_rate, markup_pct):
    # Возвращает dict с:
    # filament_costs[], total_weight, total_filament_cost,
    # electricity_cost, depreciation_cost, subtotal, markup_amount, total
```

### Shpoolken (каталог филаментов)

- Загружает JSON с GitHub репозитория при синхронизации
- Сохраняет в `shpoolken.db`
- Встроен в `filaments.html` как вкладка «Каталог Shpoolken»
- Карточный UI: цветная плашка, производитель, материал, температуры
- Фильтры по производителю/материалу, поиск, bulk add с выбором
- Sync overlay с shimmer progress bar и cycling status

### Upload

Поддерживает STL, OBJ, 3MF, GCODE, STEP, STP, AMF. Файлы сохраняются в `uploads/` с UUID-именами.

## Запуск и разработка

### Dev mode
```bash
cd electron-app/filament-calculator
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python app.py
```

### Electron
```bash
cd electron-app
npm install
npm start
```

### Tests
```bash
cd electron-app/filament-calculator
venv\Scripts\python -m pytest tests/ -v
```

17 тестов: smoke GET routes, 404 handler, static files, theme.css, calculator unit tests.

## Важные нюансы

### Monkey-patch Request.endpoint

Flask Blueprint добавляет префикс к endpoint (`printers.index`). Для backward-compatible `request.endpoint == 'index'` в шаблонах сделан monkey-patch:

```python
_FlaskRequest.endpoint = property(_aliased_endpoint)
# Стрипит все до точки: "printers.index" -> "index"
```

### url_for alias

Context processor `inject_url_for_alias` мапит короткие имена (`index`, `printers`) на полные blueprint endpoint'ы.

### Cache busting

Все статические файлы подключаются с `?v=2`:
```html
<link rel="stylesheet" href="style.css?v=2">
<script src="app.js?v=2">
```

Это критично, т.к. `SEND_FILE_MAX_AGE_DEFAULT = 31536000` (1 год).

### Glass mode toggle

```python
glass = bool(int(request.args.get("glass", 1)))
```
Строка `"0"` была truthy, поэтому нужно явное `int()` + `bool()`.

## Последние изменения

1. **Acrylic redesign** — весь UI переработан под Microsoft Acrylic Fluent
2. **Lucide icons** — все иконки заменены на stroke-based SVG
3. **Splash screen** — acrylic-карточка с shimmer progress bar
4. **Error screen** — acrylic с красным акцентом
5. **Navbar acrylic** — blur(20px) + noise
6. **Btn-secondary acrylic** — blur(12px) с усилением при hover
7. **Themes.json** — opacity tint увеличены до 0.77–0.88
8. **Blueprints** — god object разбит на 6 blueprint'ов
9. **Tests** — 17 pytest тестов
10. **Bulk actions** — массовое удаление/восстановление
11. **Shpoolken sync overlay** — glassmorphism overlay с анимацией
12. **Дерево филаментов** — кастомный dropdown с группировкой тип → производитель → стек → катушка в калькуляторе
13. **Статистика** — среднее время печати, топ клиентов, самый тяжёлый/дорогой заказ в настройках
14. **Лог обслуживания** — таблица `maintenance_logs`, модалка с историей для каждого принтера
15. **Объединение страниц** — Shpoolken встроен в `filaments.html` через вкладки
