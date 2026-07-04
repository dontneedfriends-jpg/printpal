from flask import Blueprint, request, render_template, redirect, url_for, flash, Response, jsonify
from database import get_db, get_settings
from config import DEFAULT_ELECTRICITY_RATE, DEFAULT_BASE_RATE, DEFAULT_MARKUP_PERCENT
from utils import safe_float
from translations import t as _t
import json
import os
from datetime import datetime

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings")
def settings():
    from app import PRESETS, get_setting
    s = get_settings()
    db = get_db()
    calc_count = db.execute("SELECT COUNT(*) as cnt FROM calculations").fetchone()["cnt"]
    total_used = db.execute("SELECT COALESCE(SUM(weight_g), 0) as total FROM calculations").fetchone()["total"]
    avg_time = db.execute("SELECT AVG(print_time_hours) as avg FROM calculations").fetchone()["avg"]
    top_clients = db.execute("""
        SELECT c.name, COALESCE(SUM(cal.total_cost), 0) as total
        FROM calculations cal
        LEFT JOIN clients c ON cal.client_id = c.id
        GROUP BY cal.client_id
        ORDER BY total DESC
        LIMIT 5
    """).fetchall()
    heaviest = db.execute("SELECT model_name, weight_g FROM calculations ORDER BY weight_g DESC LIMIT 1").fetchone()
    most_expensive = db.execute("SELECT model_name, total_cost as total FROM calculations ORDER BY total_cost DESC LIMIT 1").fetchone()
    printers = db.execute("SELECT * FROM printers ORDER BY name").fetchall()
    db.close()

    current_preset = s.get("theme_preset", "modern")
    current_theme = "light"
    glass_mode = bool(s.get("glass_mode", 1))
    tab_order = s.get("tab_order", "")
    current_lang = s.get("language", "ru")

    preview_colors = {}
    for pid, pdata in PRESETS.items():
        colors = pdata["light"]
        preview_colors[pid] = {
            "bg": colors["bg"],
            "border": colors["border"],
            "accent": colors["accent"],
            "secondary": colors["secondary"],
            "danger": colors["danger"],
            "muted": colors["text-muted"],
        }

    return render_template(
        "settings.html",
        settings={
            "electricity_rate": s.get("electricity_rate", DEFAULT_ELECTRICITY_RATE),
            "base_rate": s.get("base_rate", DEFAULT_BASE_RATE),
            "markup_percent": s.get("markup_percent", DEFAULT_MARKUP_PERCENT),
        },
        calc_count=calc_count,
        total_filament_used=total_used,
        avg_time=avg_time,
        top_clients=top_clients,
        heaviest=heaviest,
        most_expensive=most_expensive,
        current_theme=current_theme,
        current_preset=current_preset,
        glass_mode=glass_mode,
        tab_order=tab_order,
        current_lang=current_lang,
        printers=printers,
        presets=PRESETS,
        preview_colors=preview_colors,
        lang=request.lang,
    )


@settings_bp.route("/settings/lang", methods=["POST"])
def save_lang():
    db = get_db()
    lang = request.form.get("lang", "ru")
    if lang in ("ru", "en", "es"):
        db.execute("UPDATE settings SET value = ? WHERE key = 'language'", (lang,))
        db.commit()
    db.close()
    resp = Response("ok")
    resp.set_cookie("lang", lang, max_age=31536000)
    return resp


@settings_bp.route("/settings/theme", methods=["POST"])
def save_theme():
    db = get_db()
    db.execute("UPDATE settings SET value = ? WHERE key = 'theme'", (request.form["theme"],))
    db.commit()
    db.close()
    return "ok"


@settings_bp.route("/settings/preset", methods=["POST"])
def save_preset():
    from app import PRESETS
    db = get_db()
    preset = request.form["preset"]
    if preset in PRESETS:
        db.execute("UPDATE settings SET value = ? WHERE key = 'theme_preset'", (preset,))
        db.commit()
    db.close()
    return "ok"


@settings_bp.route("/settings/glass", methods=["POST"])
def save_glass():
    db = get_db()
    db.execute("UPDATE settings SET value = ? WHERE key = 'glass_mode'", (safe_float(request.form["glass"], 1),))
    db.commit()
    db.close()
    return "ok"


@settings_bp.route("/settings/save", methods=["POST"])
def save_settings():
    db = get_db()
    db.execute("UPDATE settings SET value = ? WHERE key = 'electricity_rate'", (safe_float(request.form["electricity_rate"], DEFAULT_ELECTRICITY_RATE),))
    db.execute("UPDATE settings SET value = ? WHERE key = 'base_rate'", (safe_float(request.form["base_rate"], DEFAULT_BASE_RATE),))
    db.execute("UPDATE settings SET value = ? WHERE key = 'markup_percent'", (safe_float(request.form["markup_percent"], DEFAULT_MARKUP_PERCENT),))
    db.commit()
    db.close()
    flash(_t(request.lang, "settings_saved"), "success")
    return redirect(url_for(".settings"))


@settings_bp.route("/settings/clear_history", methods=["POST"])
def clear_history():
    from config import UPLOAD_DIR
    db = get_db()
    for row in db.execute("SELECT model_file FROM calculations").fetchall():
        if row["model_file"]:
            fpath = os.path.join(UPLOAD_DIR, row["model_file"])
            if os.path.exists(fpath):
                os.remove(fpath)
    db.execute("DELETE FROM calculations")
    db.commit()
    db.close()
    flash(_t(request.lang, "history_cleared"), "success")
    return redirect(url_for(".settings"))


@settings_bp.route("/settings/tab_order", methods=["POST"])
def save_tab_order():
    db = get_db()
    db.execute("UPDATE settings SET value = ? WHERE key = 'tab_order'", (request.form["tab_order"],))
    db.commit()
    db.close()
    return "ok"


@settings_bp.route("/settings/maintenance", methods=["POST"])
def save_maintenance():
    db = get_db()
    for key, val in request.form.items():
        if key.startswith("maint_"):
            printer_id = key.replace("maint_", "")
            db.execute("UPDATE printers SET maintenance_hours = ? WHERE id = ?", (safe_float(val, 0), printer_id))
    db.commit()
    db.close()
    flash(_t(request.lang, "maintenance_saved"), "success")
    return redirect(url_for(".settings"))


@settings_bp.route("/settings/monitor_mode", methods=["POST"])
def save_monitor_mode():
    db = get_db()
    checked = set()
    for key, val in request.form.items():
        if key.startswith("webui_mode_"):
            pid = key.replace("webui_mode_", "")
            db.execute("UPDATE printers SET webui_mode = ? WHERE id = ?", (int(val), pid))
        if key.startswith("auto_deduct_"):
            pid = key.replace("auto_deduct_", "")
            checked.add(pid)
            db.execute("UPDATE printers SET auto_deduct = 1 WHERE id = ?", (pid,))
    for key, val in request.form.items():
        if key.startswith("webui_mode_"):
            pid = key.replace("webui_mode_", "")
            if pid not in checked:
                db.execute("UPDATE printers SET auto_deduct = 0 WHERE id = ?", (pid,))
    db.commit()
    db.close()
    flash("Режим монитора сохранён", "success")
    return redirect(url_for(".settings"))


@settings_bp.route("/settings/backup")
def backup_json():
    db = get_db()
    backup = {
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "settings": [dict(r) for r in db.execute("SELECT key, value FROM settings").fetchall()],
        "printers": [dict(r) for r in db.execute("SELECT * FROM printers").fetchall()],
        "filaments": [dict(r) for r in db.execute("SELECT * FROM filaments").fetchall()],
        "calculations": [dict(r) for r in db.execute("SELECT * FROM calculations").fetchall()],
        "clients": [dict(r) for r in db.execute("SELECT * FROM clients").fetchall()],
        "maintenance_logs": [dict(r) for r in db.execute("SELECT * FROM maintenance_logs").fetchall()],
    }
    db.close()
    resp = jsonify(backup)
    ts = backup["timestamp"].replace(":", "-").split(".")[0]
    resp.headers["Content-Disposition"] = f"attachment; filename=printpal-backup-{ts}.json"
    return resp


@settings_bp.route("/settings/restore", methods=["POST"])
def restore_json():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        flash("Файл бэкапа повреждён или пуст", "error")
        return redirect(url_for(".settings"))
    db = get_db()
    counts = {"settings": 0, "printers": 0, "filaments": 0, "calculations": 0, "clients": 0, "maintenance_logs": 0}
    try:
        # FK-safe delete order: children first
        db.execute("DELETE FROM maintenance_logs")
        db.execute("DELETE FROM calculations")
        db.execute("DELETE FROM filaments")
        db.execute("DELETE FROM printers")
        db.execute("DELETE FROM clients")
        db.execute("DELETE FROM settings")
        db.commit()

        for row in data.get("settings") or []:
            db.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (row.get("key"), row.get("value")))
            counts["settings"] += 1
        for row in data.get("clients") or []:
            r = {k: row.get(k) for k in ("id", "name", "contact", "notes", "created_at")}
            db.execute("INSERT INTO clients (id, name, contact, notes, created_at) VALUES (?, ?, ?, ?, ?)",
                       (r["id"], r["name"], r["contact"], r["notes"], r["created_at"]))
            counts["clients"] += 1
        for row in data.get("printers") or []:
            cols = [k for k in row.keys() if k != "rowid"]
            placeholders = ",".join(["?"] * len(cols))
            values = [row.get(c) for c in cols]
            col_list = ",".join(cols)
            db.execute(f"INSERT INTO printers ({col_list}) VALUES ({placeholders})", values)
            counts["printers"] += 1
        for row in data.get("filaments") or []:
            cols = [k for k in row.keys() if k != "rowid"]
            placeholders = ",".join(["?"] * len(cols))
            values = [row.get(c) for c in cols]
            col_list = ",".join(cols)
            db.execute(f"INSERT INTO filaments ({col_list}) VALUES ({placeholders})", values)
            counts["filaments"] += 1
        for row in data.get("calculations") or []:
            cols = [k for k in row.keys() if k != "rowid"]
            placeholders = ",".join(["?"] * len(cols))
            values = [row.get(c) for c in cols]
            col_list = ",".join(cols)
            db.execute(f"INSERT INTO calculations ({col_list}) VALUES ({placeholders})", values)
            counts["calculations"] += 1
        for row in data.get("maintenance_logs") or []:
            cols = [k for k in row.keys() if k != "rowid"]
            placeholders = ",".join(["?"] * len(cols))
            values = [row.get(c) for c in cols]
            col_list = ",".join(cols)
            db.execute(f"INSERT INTO maintenance_logs ({col_list}) VALUES ({placeholders})", values)
            counts["maintenance_logs"] += 1
        db.commit()
        flash(f"Бэкап восстановлен: {sum(counts.values())} записей", "success")
        return redirect(url_for(".settings"))
    except Exception as e:
        db.rollback()
        flash(f"Ошибка восстановления: {e}", "error")
        return redirect(url_for(".settings"))


