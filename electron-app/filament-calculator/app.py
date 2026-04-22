import os
import sys
import re
import uuid
import csv
import io
import json
import secrets
import logging
import urllib.request

# Add current directory to path for local imports
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, Response, make_response, abort, jsonify
from database import get_db, init_db, get_settings, init_shpoolken_db, is_shpoolken_loaded, get_shpoolken_filaments, get_shpoolken_manufacturers, get_shpoolken_materials, get_shpoolken_stats, insert_shpoolken_filaments
from config import DEFAULT_ELECTRICITY_RATE, DEFAULT_BASE_RATE, DEFAULT_MARKUP_PERCENT, UPLOAD_DIR, LOG_FILE, HOST, PORT
from translations import t as _t
from utils import safe_float, safe_int

# Monkey-patch Request.endpoint to strip blueprint prefix for template compatibility
from flask import Request as _FlaskRequest
_original_endpoint_fget = _FlaskRequest.endpoint.fget

def _aliased_endpoint(self):
    ep = _original_endpoint_fget(self)
    if ep and "." in ep:
        return ep.split(".", 1)[1]
    return ep

_FlaskRequest.endpoint = property(_aliased_endpoint)

logger = logging.getLogger(__name__)

if os.path.exists(os.path.dirname(LOG_FILE)):
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.ERROR)
    logger.addHandler(file_handler)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 31536000

ALLOWED_EXTENSIONS = {"stl", "obj", "3mf", "gcode", "step", "stp", "amf"}


def safe_filename(filename):
    filename = os.path.basename(filename)
    filename = re.sub(r"[^\w\-.]", "_", filename)
    return filename


def validate_filament_id(fid):
    try:
        fid_int = int(fid)
        if fid_int < 1:
            return None
        return fid_int
    except (TypeError, ValueError):
        return None


@app.template_filter('from_json')
def from_json_filter(s):
    try:
        return json.loads(s) if s else []
    except (ValueError, TypeError, json.JSONDecodeError):
        return []


from translations import T as TRANSLATIONS

@app.context_processor
def inject_translations():
    def _(key):
        return _t(request.cookies.get("lang", "ru"), key)
    return {"_": _, "translations": TRANSLATIONS}


@app.context_processor
def inject_url_for_alias():
    from flask import url_for as _flask_url_for
    def url_for(endpoint, **values):
        aliased = _endpoint_aliases.get(endpoint)
        if aliased:
            endpoint = aliased
        return _flask_url_for(endpoint, **values)
    return {"url_for": url_for}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_setting(key):
    settings = get_settings()
    return settings.get(key, {
        "electricity_rate": DEFAULT_ELECTRICITY_RATE,
        "base_rate": DEFAULT_BASE_RATE,
        "markup_percent": DEFAULT_MARKUP_PERCENT,
        "language": "ru",
    }.get(key, 0))


@app.before_request
def before_request():
    init_db()
    lang = request.cookies.get("lang", "ru")
    if lang not in ("ru", "en", "es"):
        lang = "ru"
    request.lang = lang


def calculate_cost_details(printer, filaments_data, print_time, base_rate, markup_pct):
    """
    Central function for calculating print cost details.
    filaments_data: list of dicts with keys: filament (db row), weight (grams)
    Returns: dict with all cost components
    """
    electricity_rate = get_setting("electricity_rate")
    
    total_filament_cost = 0
    total_weight = 0
    filament_costs_list = []
    
    for item in filaments_data:
        filament = dict(item["filament"])
        weight = item["weight"]
        
        spool_weight = filament.get("spool_weight_g") or 1.0
        if spool_weight <= 0:
            spool_weight = 1.0
        
        price_per_gram = filament.get("spool_price", 0) / spool_weight
        cost = weight * price_per_gram
        
        total_filament_cost += cost
        total_weight += weight
        filament_costs_list.append({
            "id": filament.get("id"),
            "name": filament.get("name"),
            "color": filament.get("color"),
            "weight": weight,
            "cost": cost,
        })
    
    printer_dict = dict(printer)
    electricity_cost = print_time * (printer_dict.get("power_watts", 200) / 1000) * electricity_rate
    depreciation_cost = print_time * printer_dict.get("depreciation_per_hour", 0)
    subtotal = base_rate + total_filament_cost + electricity_cost + depreciation_cost
    markup_amount = subtotal * (markup_pct / 100)
    total = subtotal + markup_amount
    
    return {
        "filament_costs": filament_costs_list,
        "total_weight": total_weight,
        "total_filament_cost": total_filament_cost,
        "electricity_cost": electricity_cost,
        "depreciation_cost": depreciation_cost,
        "subtotal": subtotal,
        "markup_amount": markup_amount,
        "total": total,
    }


def calc_cost(printer, filament, weight_g, print_time, base_rate, markup_pct):
    details = calculate_cost_details(printer, [{"filament": filament, "weight": weight_g}], print_time, base_rate, markup_pct)
    filament_cost = details["filament_costs"][0]["cost"] if details["filament_costs"] else 0
    price_per_gram = filament["spool_price"] / max(filament["spool_weight_g"], 1)
    return {
        "price_per_gram": price_per_gram,
        "filament_cost": filament_cost,
        "electricity_cost": details["electricity_cost"],
        "depreciation_cost": details["depreciation_cost"],
        "subtotal": details["subtotal"],
        "markup_amount": details["markup_amount"],
        "total": details["total"],
    }


def save_uploaded_file(file):
    if file and file.filename and allowed_file(file.filename):
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = file.filename.rsplit(".", 1)[1].lower()
        safe_name = f"{uuid.uuid4().hex}.{ext}"
        orig_name = file.filename.rsplit(".", 1)[0]
        file.save(os.path.join(UPLOAD_DIR, safe_name))
        return safe_name, orig_name
    return None, None


@app.route("/")
def index():
    db = get_db()
    filaments = db.execute("SELECT *, CASE WHEN spool_weight_g > 0 THEN (spool_price / spool_weight_g) ELSE 0 END as price_per_g FROM filaments ORDER BY name").fetchall()
    printers = db.execute("SELECT * FROM printers ORDER BY name").fetchall()
    today_count = db.execute("SELECT COUNT(*) as cnt FROM calculations WHERE date(created_at) = date('now')").fetchone()["cnt"]

    maintenance_info = []
    for p in printers:
        maint_hrs = dict(p).get("maintenance_hours") or 0
        if maint_hrs > 0:
            used = db.execute(
                "SELECT COALESCE(SUM(print_time_hours), 0) as total FROM calculations WHERE printer_id = ?",
                (p["id"],)
            ).fetchone()["total"]
            remaining = max(0, maint_hrs - used)
            maintenance_info.append({
                "name": p["name"],
                "total": maint_hrs,
                "used": round(used, 1),
                "remaining": round(remaining, 1),
                "pct": min(100, (used / maint_hrs) * 100),
            })

    db.close()
    return render_template("index.html", filaments=filaments, printers=printers, today_count=today_count, maintenance=maintenance_info, lang=request.lang)


@app.route("/theme.css")
def theme_css():
    s = get_settings()
    preset_name = request.args.get("preset", s.get("theme_preset", "modern"))
    theme = request.args.get("theme", "light")
    try:
        glass = bool(int(request.args.get("glass", s.get("glass_mode", 1))))
    except (ValueError, TypeError):
        glass = True

    if preset_name not in PRESETS:
        preset_name = "modern"

    colors = PRESETS[preset_name].get(theme, PRESETS[preset_name]["light"])

    lines = [":root {"]
    for key, val in colors.items():
        lines.append(f"    --{key}: {val};")

    if not glass:
        lines.append("    --glass-bg: var(--bg-card);")
        lines.append("    --glass-bg-hover: var(--bg-card);")
        lines.append("    --glass-border: var(--border);")
        lines.append("    --glass-border-strong: var(--border);")
        lines.append("    --glass-shadow: none;")
        lines.append("    --glass-shadow-lg: none;")
        lines.append("    --glass-blur: 0px;")
        lines.append("    --glass-backdrop: none;")
    else:
        lines.append("    --glass-backdrop: blur(var(--glass-blur)) saturate(1.15);")

    lines.append("}")
    return Response("\n".join(lines), mimetype="text/css")


@app.route("/uploads/<filename>")
def download_file(filename):
    safe_name = safe_filename(filename)
    if not safe_name or safe_name.startswith("."):
        logger.warning(f"Blocked invalid filename: {filename}")
        abort(400)
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    if not os.path.isfile(filepath):
        logger.warning(f"File not found: {filepath}")
        abort(404)
    return send_from_directory(UPLOAD_DIR, safe_name, as_attachment=True)


_PRESETS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "themes.json")
with open(_PRESETS_PATH, "r", encoding="utf-8") as f:
    PRESETS = json.load(f)


@app.route("/about")
def about():
    return render_template("about.html", lang=request.lang)


# Register blueprints
from routes.printers import printers_bp
from routes.filaments import filaments_bp
from routes.calculator import calculator_bp
from routes.settings import settings_bp
from routes.history import history_bp
from routes.shpoolken import shpoolken_bp

app.register_blueprint(printers_bp)
app.register_blueprint(filaments_bp)
app.register_blueprint(calculator_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(history_bp)
app.register_blueprint(shpoolken_bp)

# Build endpoint alias map for backward-compatible url_for in templates
_endpoint_aliases = {}
for rule in app.url_map.iter_rules():
    endpoint = rule.endpoint
    if "." in endpoint:
        bp_name, ep_name = endpoint.split(".", 1)
        if ep_name == bp_name:
            _endpoint_aliases[ep_name] = endpoint
        elif ep_name not in _endpoint_aliases:
            _endpoint_aliases[ep_name] = endpoint


@app.errorhandler(404)
def not_found(e):
    lang = getattr(request, "lang", "ru")
    message = (
        "Страница не найдена" if lang == "ru"
        else "Página no encontrada" if lang == "es"
        else "Page not found"
    )
    return render_template("error.html", code=404, message=message, lang=lang), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    lang = getattr(request, "lang", "ru")
    message = (
        "Внутренняя ошибка сервера" if lang == "ru"
        else "Error interno del servidor" if lang == "es"
        else "Internal server error"
    )
    return render_template("error.html", code=500, message=message, lang=lang), 500


if __name__ == "__main__":
    init_db()
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    app.run(debug=False, host=HOST, port=PORT, threaded=True)
