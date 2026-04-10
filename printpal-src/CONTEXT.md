# PrintPAL - Контекст разработки

## Общее описание

PrintPAL - десктопное приложение (Electron + Flask + SQLite) для учёта филаментов и расчёта стоимости 3D-печати. Версия 1.3.0.

## Структура проекта

```
printpal-src/
├── electron-app/
│   ├── main.js              # Electron main process
│   ├── preload.js           # Preload script
│   ├── runner.py            # Flask runner (запускает filament-calculator)
│   ├── package.json         # Build config (electron-builder)
│   ├── python/              # Embedded Python 3.12.8
│   │   └── python.exe
│   ├── filament-calculator/  # Flask приложение
│   │   ├── app.py           # Основное приложение (PRESETS, routes, DB)
│   │   ├── database.py      # SQLite DB operations
│   │   ├── config.py        # Конфигурация
│   │   ├── translations.py # Переводы (ru/en/es)
│   │   ├── templates/       # Jinja2 templates
│   │   │   ├── base.html   # Base template (theme CSS, konami code)
│   │   │   ├── about.html  # About page
│   │   │   ├── filaments.html
│   │   │   ├── printers.html
│   │   │   ├── calculator.html
│   │   │   ├── history.html
│   │   │   ├── shpoolken.html
│   │   │   └── ...
│   │   └── static/
│   └── dist6/               # Build output
│       └── win-unpacked/
│           └── PrintPAL.exe # 180 MB portable exe
```

## Основные компоненты

### main.js
- Запускает embedded Python из `electron-app/python/` папки
- Запускает Flask через runner.py
- Обрабатывает окно приложения

### runner.py
- Добавляет filament-calculator в sys.path
- Запускает Flask приложение

### app.py
- **PRESETS** - словарь тем (26 тем, light/dark варианты)
- **from_json** filter - зарегистрирован как template_filter
- Routes: /, /printers, /filaments, /calculator, /history, /settings, /shpoolken, /about

### translations.py
- T словарь с переводами на ru/en/es
- Ключи для всех UI элементов

### templates/base.html
- CSS variables для тем (через preset_colors)
- Konami code easter egg (↑↑↓↓←→←→BA)
- Toast notifications для feedback

## Темы (26 штук)

1. modern
2. retro
3. terminal
4. material
5. pastel
6. nord
7. dracula
8. ocean
9. sunset
10. gameboy
11. crt
12. neon
13. windows98
14. solarized
15. gruvbox
16. synthwave
17. monochrome
18. catppuccin
19. tokyonight
20. onedark
21. monokai
22. github
23. ayu
24. nightowl
25. cobalt2
26. horizon

Каждая тема имеет light и dark варианты.

## Особенности реализации

- **Embedded Python**: Python 3.12.8 встроен в Electron app, не требует системного Python
- **Bulk operations**: Удаление с undo (5 секунд, ↺ кнопка)
- **AJAX save**: Калькулятор сохраняет без redirect (toast notification)
- **Shpoolken integration**: База филаментов из https://dontneedfriends-jpg.github.io/ShpoolkenDB/
- **Jinja filter**: `from_json` должен быть зарегистрирован через `@app.template_filter`, не через context_processor

## Известные нюансы

- Build ошибка с winCodeSign (symlink для darwin) - не влияет на результат, exe создаётся
- При повторном build нужно удалить dist6 папку (файл лочится)
- Для запуска build: `npm run build` в папке electron-app
- Output: `dist6/win-unpacked/PrintPAL.exe` (portable, ~180 MB)

## О странице "О приложении"

- Ироничный tone
- Акцент на локальную БД без Docker
- Стек: Python + Flask + SQLite + Electron
- Поддержка ShpoolkenDB указана
- Переводы на ru/en/es
- Огонь на лого при клике (CSS animation)
- Footer с "Сделано с ❤️, ☕ и немного с 🧠"

## Ключевые файлы для редактирования

- `app.py` - темы, routes, логика
- `translations.py` - все тексты UI
- `templates/about.html` - страница "О приложении"
- `templates/base.html` - CSS variables, konami code

## Версия

1.3.0