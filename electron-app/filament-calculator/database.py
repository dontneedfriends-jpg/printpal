import sqlite3
import os
import logging
from config import DATABASE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    except Exception as e:
        logger.warning(f"Migration printers columns: {e}")

    try:
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(calculations)").fetchall()]
        if "model_file" not in columns:
            conn.execute("ALTER TABLE calculations ADD COLUMN model_file TEXT")
        if "model_orig_name" not in columns:
            conn.execute("ALTER TABLE calculations ADD COLUMN model_orig_name TEXT DEFAULT ''")
        if "filament_data" not in columns:
            conn.execute("ALTER TABLE calculations ADD COLUMN filament_data TEXT DEFAULT ''")
    except Exception as e:
        logger.warning(f"Migration calculations columns: {e}")

    try:
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(filaments)").fetchall()]
        if "density" not in columns:
            conn.execute("ALTER TABLE filaments ADD COLUMN density REAL DEFAULT 0")
        if "diameter" not in columns:
            conn.execute("ALTER TABLE filaments ADD COLUMN diameter REAL DEFAULT 1.75")
        if "color_hex" not in columns:
            conn.execute("ALTER TABLE filaments ADD COLUMN color_hex TEXT DEFAULT ''")
    except Exception as e:
        logger.warning(f"Migration filaments columns: {e}")

    conn.commit()
    conn.close()


def get_settings():
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    settings = {row["key"]: row["value"] for row in rows}
    db.close()
    return settings


def get_shpoolken_db():
    db_path = os.path.join(os.path.dirname(DATABASE), "shpoolken.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_shpoolken_db():
    conn = get_shpoolken_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS filaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manufacturer TEXT NOT NULL,
            name TEXT NOT NULL,
            material TEXT NOT NULL,
            color_name TEXT,
            color_hex TEXT,
            density REAL,
            diameter REAL,
            weight INTEGER,
            spool_weight INTEGER,
            extruder_temp INTEGER,
            bed_temp INTEGER,
            finish TEXT,
            pattern TEXT,
            glow INTEGER DEFAULT 0,
            translucent INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_info (
            id INTEGER PRIMARY KEY,
            last_sync TEXT,
            file_count INTEGER
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_spoolken_manufacturer ON filaments(manufacturer)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_spoolken_material ON filaments(material)")
    conn.commit()
    conn.close()


def is_shpoolken_loaded():
    conn = get_shpoolken_db()
    count = conn.execute("SELECT COUNT(*) as c FROM filaments").fetchone()
    conn.close()
    return count and count["c"] > 0


def clear_shpoolken_db():
    conn = get_shpoolken_db()
    conn.execute("DELETE FROM filaments")
    conn.execute("DELETE FROM sync_info")
    conn.commit()
    conn.close()


def insert_shpoolken_filaments(filaments_data):
    conn = get_shpoolken_db()
    clear_shpoolken_db()
    
    for item in filaments_data:
        manufacturer = item.get("manufacturer", "")
        for filament in item.get("filaments", []):
            name = filament.get("name", "") or ""
            if name == "{color_name}":
                name = ""
            material = filament.get("material", "")
            density = filament.get("density")
            extruder_temp = filament.get("extruder_temp")
            bed_temp = filament.get("bed_temp")
            finish = filament.get("finish")
            pattern = filament.get("pattern")
            glow = 1 if filament.get("glow") else 0
            translucent = 1 if filament.get("translucent") else 0
            
            diameters = filament.get("diameters", [1.75])
            weights = filament.get("weights", [{"weight": 1000, "spool_weight": 250}])
            colors = filament.get("colors", [])
            
            if not colors:
                colors = [{"name": None, "hex": None}]
            
            for weight_info in weights:
                weight = weight_info.get("weight")
                spool_weight = weight_info.get("spool_weight", 250)
                
                for color in colors:
                    color_name = color.get("name") or ""
                    if color_name == "{color_name}":
                        color_name = ""
                    color_hex = color.get("hex")
                    
                    for diameter in diameters:
                        conn.execute("""
                            INSERT INTO filaments 
                            (manufacturer, name, material, color_name, color_hex, density, diameter, weight, spool_weight, extruder_temp, bed_temp, finish, pattern, glow, translucent)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (manufacturer, name, material, color_name, color_hex, density, diameter, weight, spool_weight, extruder_temp, bed_temp, finish, pattern, glow, translucent))
    
    conn.execute("DELETE FROM sync_info")
    conn.execute("INSERT INTO sync_info (id, last_sync, file_count) VALUES (1, datetime('now'), ?)", (len(filaments_data),))
    conn.commit()
    conn.close()


def get_shpoolken_filaments(manufacturer=None, material=None, search=None, limit=500):
    conn = get_shpoolken_db()
    
    sql = "SELECT * FROM filaments WHERE 1=1"
    params = []
    
    if manufacturer:
        sql += " AND manufacturer = ?"
        params.append(manufacturer)
    
    if material:
        sql += " AND material = ?"
        params.append(material)
    
    if search:
        sql += " AND (manufacturer LIKE ? OR name LIKE ? OR material LIKE ? OR color_name LIKE ?)"
        pattern = f"%{search}%"
        params.extend([pattern, pattern, pattern, pattern])
    
    sql += " ORDER BY manufacturer, material, color_name LIMIT ?"
    params.append(limit)
    
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def get_shpoolken_manufacturers():
    conn = get_shpoolken_db()
    rows = conn.execute("""
        SELECT manufacturer, COUNT(*) as count 
        FROM filaments 
        GROUP BY manufacturer 
        ORDER BY manufacturer
    """).fetchall()
    conn.close()
    return rows


def get_shpoolken_materials():
    conn = get_shpoolken_db()
    rows = conn.execute("""
        SELECT DISTINCT material 
        FROM filaments 
        ORDER BY material
    """).fetchall()
    conn.close()
    return [r["material"] for r in rows]


def get_shpoolken_stats():
    conn = get_shpoolken_db()
    stats = conn.execute("""
        SELECT 
            COUNT(DISTINCT manufacturer) as manufacturer_count,
            COUNT(*) as filament_count,
            COUNT(DISTINCT color_name) as color_count
        FROM filaments
    """).fetchone()
    sync = conn.execute("SELECT last_sync, file_count FROM sync_info ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return {
        "manufacturer_count": stats["manufacturer_count"] if stats else 0,
        "filament_count": stats["filament_count"] if stats else 0,
        "color_count": stats["color_count"] if stats else 0,
        "last_sync": sync["last_sync"] if sync else None,
        "file_count": sync["file_count"] if sync else 0
    }
