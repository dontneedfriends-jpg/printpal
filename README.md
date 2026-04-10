# PrintPAL

**RU** — Программа для учёта филамента и расчёта стоимости 3D-печати. Потому что считать на калькуляторе — это прошлый век.

**EN** — Filament tracker and 3D print cost calculator. Because calculators are so 1990s.

> **Version 1.3.0**

<img width="1280" height="1032" alt="dash" src="https://github.com/user-attachments/assets/7c37d0d5-5c94-441d-86ca-4ccbd872c8c2" />

---

## Возможности / Features

**RU:**

- Расчёт стоимости печати (филамент, электричество, износ, наценка)
- Учёт остатков филамента с автоматическим списанием — меньше ручной работы
- История расчётов с возможностью скачать файл модели
- Встроенный веб-интерфейс принтера по IP — не надо переключаться между окнами
- Поддержка IP-камеры
- Отслеживание часов до техобслуживания
- Экспорт/импорт филаментов через JSON
- 26 цветовых тем (light/dark) — для перфекционистов
- Три языка: русский, английский, испанский
- Настраиваемый порядок вкладок
- Экспорт истории в CSV — для бухгалтеров
- Встроенная база филаментов из ShpoolkenDB

**EN:**

- Print cost calculation (filament, electricity, depreciation, markup)
- Filament tracking with automatic write-off — less manual work
- Calculation history with downloadable model files
- Built-in printer web interface by IP — no need to switch windows
- IP camera support
- Maintenance hours tracking
- Export/import filaments via JSON
- 26 color themes (light/dark) — for perfectionists
- Three languages: Russian, English, Spanish
- Customizable tab order
- History export to CSV — for accountants
- Built-in filament database from ShpoolkenDB

---

## Запуск / Quick Start

```bash
# Python
cd electron-app/filament-calculator
pip install flask

# Node.js
cd ..
npm install

# Run
npm start
```

---

## Сборка / Build

```bash
npm run build:win
```

**RU:** Результат: `dist6/win-unpacked/PrintPAL.exe` (~180 MB)

**EN:** Result: `dist6/win-unpacked/PrintPAL.exe` (~180 MB)

---

## Технические детали / Technical Details

### Stack / Стек

| Component | Technology |
|-----------|------------|
| Backend | Python 3.12 / Flask |
| Database | SQLite |
| Desktop | Electron 33 |
| Frontend | HTML + CSS + Jinja2 |

### Database / База данных

4 таблицы / tables: `printers`, `filaments`, `calculations`, `settings`.

### Calculation formula / Формула расчёта

```
total = base_rate + filament_cost + electricity + depreciation + markup
```

### Themes / Темы

26 тем / themes: modern, retro, terminal, material, pastel, nord, dracula, ocean, sunset, gameboy, crt, neon, windows98, solarized, gruvbox, synthwave, monochrome, catppuccin, tokyonight, onedark, monokai, github, ayu, nightowl, cobalt2, horizon.

### Data storage / Хранение данных

- Dev: `filament-calculator/filament.db`
- Windows: `%APPDATA%\PrintPAL\data\filament.db`

---

## Лицензия / License

MIT

---

## Авторы / Authors

Сделано с ❤️ и ☕ / Made with ❤️ and ☕

База филаментов / Filament database: [ShpoolkenDB](https://dontneedfriends-jpg.github.io/ShpoolkenDB/)