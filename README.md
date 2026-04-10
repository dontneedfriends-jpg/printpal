# PrintPAL

Программа для учёта филамента и расчёта стоимости 3D-печати. Потому что считать на калькуляторе — это прошлый век.

Filament tracker and 3D print cost calculator. Because calculators are so 1990s.

> **Version 1.3.0**

<img width="1280" height="1032" alt="dash" src="https://github.com/user-attachments/assets/7c37d0d5-5c94-441d-86ca-4ccbd872c8c2" />

---

## Возможности

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

---

## Запуск

### Готовый exe (рекомендуется)

```
dist6/win-unpacked/PrintPAL.exe
```

### Из исходников

```bash
# Python
cd electron-app/filament-calculator
pip install flask

# Node.js
cd ..
npm install

# Запуск
npm start
```

---

## Сборка

### Windows

```bash
npm run build:win
```

Результат: `dist6/win-unpacked/PrintPAL.exe` (~180 MB)

### Linux

```bash
cd electron-app
npm install
npx electron-builder --linux
```

### macOS

```bash
cd electron-app
npm install
npx electron-builder --mac
```

---

## Технические детали

### Стек

- Backend: Python 3.12 / Flask
- База данных: SQLite
- Desktop: Electron 33
- Frontend: HTML + CSS + Jinja2

### База данных

4 таблицы: `printers`, `filaments`, `calculations`, `settings`.

### Формула расчёта

```
total = base_rate + filament_cost + electricity + depreciation + markup
```

### Темы

26 тем: modern, retro, terminal, material, pastel, nord, dracula, ocean, sunset, gameboy, crt, neon, windows98, solarized, gruvbox, synthwave, monochrome, catppuccin, tokyonight, onedark, monokai, github, ayu, nightowl, cobalt2, horizon.

### Хранение данных

- Dev: `filament-calculator/filament.db`
- Windows packaged: `%APPDATA%\PrintPAL\data\filament.db`

---

## Лицензия

MIT

---

## Авторы

Сделано с ❤️ и ☕

База филаментов: [ShpoolkenDB](https://dontneedfriends-jpg.github.io/ShpoolkenDB/)