import sqlite3
import os
from config import DATABASE

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = -2000")
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS printers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            power_watts REAL NOT NULL DEFAULT 200,
            purchase_price REAL NOT NULL DEFAULT 0,
            depreciation_per_hour REAL NOT NULL DEFAULT 0,
            ip_address TEXT DEFAULT '',
            maintenance_hours REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS filaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            filament_type TEXT NOT NULL,
            color TEXT NOT NULL,
            spool_weight_g REAL NOT NULL,
            spool_price REAL NOT NULL,
            remaining_g REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            printer_id INTEGER NOT NULL,
            filament_id INTEGER NOT NULL,
            model_name TEXT NOT NULL,
            weight_g REAL NOT NULL,
            print_time_hours REAL NOT NULL,
            base_rate REAL NOT NULL,
            filament_cost REAL NOT NULL,
            electricity_cost REAL NOT NULL,
            depreciation_cost REAL NOT NULL,
            markup_percent REAL NOT NULL,
            markup_amount REAL NOT NULL,
            total_cost REAL NOT NULL,
            model_file TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (printer_id) REFERENCES printers(id),
            FOREIGN KEY (filament_id) REFERENCES filaments(id)
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_calculations_created ON calculations(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_calculations_printer ON calculations(printer_id);
        CREATE INDEX IF NOT EXISTS idx_calculations_filament ON calculations(filament_id);
        CREATE INDEX IF NOT EXISTS idx_filaments_name ON filaments(name);
        CREATE INDEX IF NOT EXISTS idx_printers_name ON printers(name);
    """)
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('electricity_rate', 5.0)")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('base_rate', 50.0)")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('markup_percent', 20.0)")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('theme_preset', 'modern')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('glass_mode', 1.0)")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('tab_order', '')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('language', 'ru')")

    try:
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(printers)").fetchall()]
        if "ip_address" not in columns:
            conn.execute("ALTER TABLE printers ADD COLUMN ip_address TEXT DEFAULT ''")
        if "maintenance_hours" not in columns:
            conn.execute("ALTER TABLE printers ADD COLUMN maintenance_hours REAL DEFAULT 0")
        if "camera_ip" not in columns:
            conn.execute("ALTER TABLE printers ADD COLUMN camera_ip TEXT DEFAULT ''")
    except Exception:
        pass

    try:
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(calculations)").fetchall()]
        if "model_file" not in columns:
            conn.execute("ALTER TABLE calculations ADD COLUMN model_file TEXT")
        if "model_orig_name" not in columns:
            conn.execute("ALTER TABLE calculations ADD COLUMN model_orig_name TEXT DEFAULT ''")
    except Exception:
        pass

    conn.commit()
    conn.close()


def get_settings():
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    settings = {row["key"]: row["value"] for row in rows}
    db.close()
    return settings
