from flask import Blueprint, request, render_template, redirect, url_for, flash, Response
from database import get_db, get_settings
from config import DEFAULT_ELECTRICITY_RATE, DEFAULT_BASE_RATE, DEFAULT_MARKUP_PERCENT
from utils import safe_float
from translations import t as _t
import json
import os

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings")
def settings():
    from app import PRESETS, get_setting
    s = get_settings()
    db = get_db()
    calc_count = db.execute("SELECT COUNT(*) as cnt FROM calculations").fetchone()["cnt"]
    total_used = db.execute("SELECT COALESCE(SUM(weight_g), 0) as total FROM calculations").fetchone()["total"]
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


