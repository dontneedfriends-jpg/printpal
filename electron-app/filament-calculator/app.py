import os
import re
import uuid
import csv
import io
import json
import secrets
import logging
import urllib.request
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, Response, make_response, abort, jsonify
from database import get_db, init_db, get_settings, init_shpoolken_db, is_shpoolken_loaded, get_shpoolken_filaments, get_shpoolken_manufacturers, get_shpoolken_materials, get_shpoolken_stats, insert_shpoolken_filaments
from config import DEFAULT_ELECTRICITY_RATE, DEFAULT_BASE_RATE, DEFAULT_MARKUP_PERCENT, UPLOAD_DIR, LOG_FILE
from translations import t as _t

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


def safe_float(value, default=0.0, min_val=None, max_val=None):
    try:
        result = float(value)
        if result < 0:
            return default
        if min_val is not None and result < min_val:
            return default
        if max_val is not None and result > max_val:
            return max_val
        return result
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0, min_val=None, max_val=None):
    try:
        result = int(value)
        if result < 0:
            return default
        if min_val is not None and result < min_val:
            return default
        if max_val is not None and result > max_val:
            return max_val
        return result
    except (TypeError, ValueError):
        return default


def validate_filament_id(fid):
    try:
        fid_int = int(fid)
        if fid_int < 1:
            return None
        return fid_int
    except (TypeError, ValueError):
        return None


@app.context_processor
def inject_translations():
    def _(key):
        return _t(request.cookies.get("lang", "ru"), key)
    def from_json(s):
        try:
            return json.loads(s) if s else []
        except:
            return []
    return {"_": _, "from_json": from_json}


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


def calc_cost(printer, filament, weight_g, print_time, base_rate, markup_pct):
    electricity_rate = get_setting("electricity_rate")
    spool_weight = filament["spool_weight_g"]
    if spool_weight <= 0:
        logger.warning(f"Invalid spool_weight_g for filament id={filament['id']}, using default 1")
        spool_weight = 1.0
    price_per_gram = filament["spool_price"] / spool_weight
    filament_cost = weight_g * price_per_gram
    electricity_cost = print_time * (printer["power_watts"] / 1000) * electricity_rate
    depreciation_cost = print_time * printer["depreciation_per_hour"]
    subtotal = base_rate + filament_cost + electricity_cost + depreciation_cost
    markup_amount = subtotal * (markup_pct / 100)
    total = subtotal + markup_amount
    return {
        "price_per_gram": price_per_gram,
        "filament_cost": filament_cost,
        "electricity_cost": electricity_cost,
        "depreciation_cost": depreciation_cost,
        "subtotal": subtotal,
        "markup_amount": markup_amount,
        "total": total,
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


@app.route("/printers")
def printers():
    db = get_db()
    printer_list = db.execute("SELECT * FROM printers ORDER BY name").fetchall()
    db.close()
    return render_template("printers.html", printers=printer_list, lang=request.lang)


@app.route("/printers/add", methods=["POST"])
def add_printer():
    db = get_db()
    db.execute(
        "INSERT INTO printers (name, power_watts, purchase_price, depreciation_per_hour, ip_address, camera_ip) VALUES (?, ?, ?, ?, ?, ?)",
        (request.form["name"], safe_float(request.form["power_watts"], 200, 1, 10000), safe_float(request.form["purchase_price"], 0, 0, 1000000), safe_float(request.form["depreciation_per_hour"], 0, 0, 100), request.form.get("ip_address", ""), request.form.get("camera_ip", ""))
    )
    db.commit()
    db.close()
    if request.headers.get("X-Requested-With") == "fetch":
        return "ok"
    return redirect(url_for("printers"))


@app.route("/printers/<int:id>/edit", methods=["POST"])
def edit_printer(id):
    db = get_db()
    db.execute(
        "UPDATE printers SET name=?, power_watts=?, purchase_price=?, depreciation_per_hour=?, ip_address=?, camera_ip=? WHERE id=?",
        (request.form["name"], safe_float(request.form["power_watts"], 200, 1, 10000), safe_float(request.form["purchase_price"], 0, 0, 1000000), safe_float(request.form["depreciation_per_hour"], 0, 0, 100), request.form.get("ip_address", ""), request.form.get("camera_ip", ""), id)
    )
    db.commit()
    db.close()
    if request.headers.get("X-Requested-With") == "fetch":
        return "ok"
    return redirect(url_for("printers"))


@app.route("/printers/<int:id>/delete", methods=["POST"])
def delete_printer(id):
    db = get_db()
    db.execute("DELETE FROM printers WHERE id = ?", (id,))
    db.commit()
    db.close()
    return "ok", 200


@app.route("/printers/monitor")
def printers_monitor():
    db = get_db()
    printer_list = db.execute("SELECT * FROM printers WHERE ip_address IS NOT NULL AND ip_address != '' ORDER BY name").fetchall()
    db.close()
    return render_template("printers_monitor.html", printers=printer_list, lang=request.lang)


@app.route("/filaments")
def filaments():
    db = get_db()
    filament_list = db.execute("SELECT *, CASE WHEN spool_weight_g > 0 THEN (spool_price / spool_weight_g) ELSE 0 END as price_per_g FROM filaments ORDER BY name").fetchall()
    db.close()
    return render_template("filaments.html", filaments=filament_list, lang=request.lang)


@app.route("/filaments/add", methods=["POST"])
def add_filament():
    db = get_db()
    weight = safe_float(request.form["spool_weight_g"], 1000)
    db.execute(
        "INSERT INTO filaments (name, filament_type, color, spool_weight_g, spool_price, remaining_g) VALUES (?, ?, ?, ?, ?, ?)",
        (request.form["name"], request.form["filament_type"], request.form["color"], weight, safe_float(request.form["spool_price"]), weight)
    )
    db.commit()
    db.close()
    return "ok", 200


@app.route("/filaments/<int:id>/edit", methods=["POST"])
def edit_filament(id):
    db = get_db()
    db.execute(
        "UPDATE filaments SET name=?, filament_type=?, color=?, spool_weight_g=?, spool_price=? WHERE id=?",
        (request.form["name"], request.form["filament_type"], request.form["color"], safe_float(request.form["spool_weight_g"], 1000), safe_float(request.form["spool_price"]), id)
    )
    db.commit()
    db.close()
    return "ok", 200


@app.route("/filaments/<int:id>/adjust", methods=["POST"])
def adjust_filament(id):
    db = get_db()
    db.execute("UPDATE filaments SET remaining_g = ? WHERE id = ?", (safe_float(request.form["remaining_g"]), id))
    db.commit()
    db.close()
    return "ok", 200


@app.route("/filaments/<int:id>/delete", methods=["POST"])
def delete_filament(id):
    db = get_db()
    db.execute("DELETE FROM filaments WHERE id = ?", (id,))
    db.commit()
    db.close()
    return "ok", 200


@app.route("/filaments/export")
def export_filaments():
    db = get_db()
    filaments = db.execute("SELECT name, filament_type, color, spool_weight_g, spool_price, remaining_g FROM filaments ORDER BY name").fetchall()
    db.close()
    data = [dict(f) for f in filaments]
    return Response(json.dumps(data, indent=2, ensure_ascii=False), mimetype="application/json",
                    headers={"Content-Disposition": "attachment;filename=filaments.json"})


@app.route("/filaments/import", methods=["POST"])
def import_filaments():
    file = request.files.get("import_file")
    if not file or not file.filename:
        flash("Файл не выбран", "error")
        return redirect(url_for("filaments"))
    try:
        data = json.load(file.stream)
    except Exception:
        flash("Ошибка чтения JSON", "error")
        return redirect(url_for("filaments"))
    if not isinstance(data, list):
        flash("Неверный формат файла", "error")
        return redirect(url_for("filaments"))
    db = get_db()
    count = 0
    for f in data:
        try:
            db.execute(
                "INSERT INTO filaments (name, filament_type, color, spool_weight_g, spool_price, remaining_g) VALUES (?, ?, ?, ?, ?, ?)",
                (f["name"], f["filament_type"], f["color"], float(f["spool_weight_g"]), float(f["spool_price"]), float(f.get("remaining_g", f["spool_weight_g"])))
            )
            count += 1
        except Exception:
            pass
    db.commit()
    db.close()
    flash(f"Импортировано {count} филаментов", "success")
    return redirect(url_for("filaments"))


@app.route("/calculator")
def calculator():
    db = get_db()
    all_printers = db.execute("SELECT * FROM printers ORDER BY name").fetchall()
    all_filaments = db.execute("SELECT *, CASE WHEN spool_weight_g > 0 THEN (spool_price / spool_weight_g) ELSE 0 END as price_per_g FROM filaments ORDER BY name").fetchall()
    db.close()
    return render_template(
        "calculator.html",
        printers=all_printers,
        filaments=all_filaments,
        default_base=get_setting("base_rate"),
        default_markup=get_setting("markup_percent"),
        preview=None,
        lang=request.lang,
    )


@app.route("/calculator/preview", methods=["POST"])
def preview_cost():
    db = get_db()
    printer = db.execute("SELECT * FROM printers WHERE id = ?", (request.form["printer_id"],)).fetchone()
    print_time = safe_float(request.form["print_time_hours"], 1, 0, 8760)
    base_rate = safe_float(request.form.get("base_rate", DEFAULT_BASE_RATE), DEFAULT_BASE_RATE, 0, 10000)
    markup_pct = safe_float(request.form.get("markup_percent", DEFAULT_MARKUP_PERCENT), DEFAULT_MARKUP_PERCENT, 0, 500)

    filament_ids = request.form.getlist("filament_id")
    filament_weights = request.form.getlist("filament_weight")
    total_weight = 0
    filament_costs_list = []
    total_filament_cost = 0
    for fid, fweight in zip(filament_ids, filament_weights):
        f = db.execute("SELECT *, CASE WHEN spool_weight_g > 0 THEN (spool_price / spool_weight_g) ELSE 0 END as price_per_g FROM filaments WHERE id = ?", (fid,)).fetchone()
        w = safe_float(fweight, 0)
        cost = w * f["price_per_g"]
        total_weight += w
        total_filament_cost += cost
        filament_costs_list.append({
            "id": f["id"],
            "name": f["name"],
            "color": f["color"],
            "weight": w,
            "cost": cost,
        })

    tmp_file = None
    tmp_orig_name = ""
    if "model_file" in request.files:
        file = request.files["model_file"]
        if file and file.filename:
            tmp_file, tmp_orig_name = save_uploaded_file(file)

    all_printers = db.execute("SELECT * FROM printers ORDER BY name").fetchall()
    all_filaments = db.execute("SELECT *, CASE WHEN spool_weight_g > 0 THEN (spool_price / spool_weight_g) ELSE 0 END as price_per_g FROM filaments ORDER BY name").fetchall()
    db.close()

    electricity_cost = print_time * (printer["power_watts"] / 1000) * get_setting("electricity_rate")
    depreciation_cost = print_time * printer["depreciation_per_hour"]
    subtotal = base_rate + total_filament_cost + electricity_cost + depreciation_cost
    markup_amount = subtotal * (markup_pct / 100)
    total = subtotal + markup_amount

    return render_template(
        "calculator.html",
        printers=all_printers,
        filaments=all_filaments,
        default_base=get_setting("base_rate"),
        default_markup=get_setting("markup_percent"),
        preview={
            "printer": printer,
            "model_name": request.form["model_name"],
            "print_time": print_time,
            "base_rate": base_rate,
            "markup_pct": markup_pct,
            "tmp_file": tmp_file,
            "tmp_orig_name": tmp_orig_name,
            "filament_costs": filament_costs_list,
            "total_weight": total_weight,
            "electricity_cost": electricity_cost,
            "depreciation_cost": depreciation_cost,
            "subtotal": subtotal,
            "markup_amount": markup_amount,
            "total": total,
        },
        lang=request.lang,
    )


@app.route("/calculator/save", methods=["POST"])
def save_calculation():
    db = get_db()
    printer = db.execute("SELECT * FROM printers WHERE id = ?", (request.form["printer_id"],)).fetchone()
    print_time = safe_float(request.form["print_time_hours"], 1, 0, 8760)
    base_rate = safe_float(request.form["base_rate"], DEFAULT_BASE_RATE, 0, 10000)
    markup_pct = safe_float(request.form["markup_percent"], DEFAULT_MARKUP_PERCENT, 0, 500)

    filament_ids = request.form.getlist("filament_id")
    filament_weights = request.form.getlist("filament_weight")
    total_weight = 0
    total_filament_cost = 0
    filament_data = []
    
    for fid, fweight in zip(filament_ids, filament_weights):
        f = db.execute("SELECT *, CASE WHEN spool_weight_g > 0 THEN (spool_price / spool_weight_g) ELSE 0 END as price_per_g FROM filaments WHERE id = ?", (fid,)).fetchone()
        w = safe_float(fweight, 0)
        total_weight += w
        total_filament_cost += w * f["price_per_g"]
        filament_data.append({"id": fid, "name": f["name"], "weight": w, "cost": w * f["price_per_g"]})

    electricity_cost = print_time * (printer["power_watts"] / 1000) * get_setting("electricity_rate")
    depreciation_cost = print_time * printer["depreciation_per_hour"]
    subtotal = base_rate + total_filament_cost + electricity_cost + depreciation_cost
    markup_amount = subtotal * (markup_pct / 100)
    total = subtotal + markup_amount

    model_file = request.form.get("tmp_file") or None
    model_orig_name = request.form.get("tmp_orig_name") or ""
    if not model_file and "model_file" in request.files:
        file = request.files["model_file"]
        if file and file.filename:
            safe_name, orig_name = save_uploaded_file(file)
            if safe_name:
                model_file = safe_name
                model_orig_name = orig_name

    first_fid = filament_ids[0] if filament_ids else 1
    filament_data_json = json.dumps(filament_data, ensure_ascii=False)
    
    try:
        db.execute(
            "INSERT INTO calculations (printer_id, filament_id, model_name, weight_g, print_time_hours, base_rate, filament_cost, electricity_cost, depreciation_cost, markup_percent, markup_amount, total_cost, model_file, model_orig_name, filament_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (printer["id"], first_fid, request.form["model_name"], total_weight, print_time, base_rate, total_filament_cost, electricity_cost, depreciation_cost, markup_pct, markup_amount, total, model_file, model_orig_name, filament_data_json)
        )
    except Exception as e:
        logger.error(f"Insert with filament_data failed: {e}")
        db.execute(
            "INSERT INTO calculations (printer_id, filament_id, model_name, weight_g, print_time_hours, base_rate, filament_cost, electricity_cost, depreciation_cost, markup_percent, markup_amount, total_cost, model_file, model_orig_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (printer["id"], first_fid, request.form["model_name"], total_weight, print_time, base_rate, total_filament_cost, electricity_cost, depreciation_cost, markup_pct, markup_amount, total, model_file, model_orig_name)
        )
    for fid, fweight in zip(filament_ids, filament_weights):
        db.execute("UPDATE filaments SET remaining_g = remaining_g - ? WHERE id = ?", (safe_float(fweight, 0), fid))
    db.commit()
    db.close()
    flash(f"Расчёт сохранён! Итого: {total:.2f} руб.", "success")
    return redirect(url_for("history"))


@app.route("/theme.css")
def theme_css():
    s = get_settings()
    preset_name = request.args.get("preset", s.get("theme_preset", "modern"))
    theme = request.args.get("theme", "light")
    glass = request.args.get("glass", s.get("glass_mode", 1))

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

    lines.append("}")
    return Response("\n".join(lines), mimetype="text/css")


@app.route("/history")
def history():
    db = get_db()
    calc_list = db.execute("""
        SELECT c.*, p.name as printer_name, f.name as filament_name, f.color as filament_color
        FROM calculations c
        JOIN printers p ON c.printer_id = p.id
        JOIN filaments f ON c.filament_id = f.id
        ORDER BY c.created_at DESC
    """).fetchall()
    db.close()
    return render_template("history.html", calculations=calc_list, lang=request.lang)


@app.route("/history/<int:id>/delete", methods=["POST"])
def delete_calculation(id):
    db = get_db()
    row = db.execute("SELECT model_file, filament_data FROM calculations WHERE id = ?", (id,)).fetchone()
    if row:
        if row["model_file"]:
            fpath = os.path.join(UPLOAD_DIR, row["model_file"])
            if os.path.exists(fpath):
                os.remove(fpath)
        if row["filament_data"]:
            try:
                filament_data = json.loads(row["filament_data"])
                for f in filament_data:
                    db.execute("UPDATE filaments SET remaining_g = remaining_g + ? WHERE id = ?", (f["weight"], f["id"]))
            except Exception as e:
                logger.warning(f"Failed to restore filament data: {e}")
        db.execute("DELETE FROM calculations WHERE id = ?", (id,))
        db.commit()
    db.close()
    return "ok", 200


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


PRESETS = {
    "modern": {
        "name": "Модерн",
        "light": {
            "bg": "#e8ecf1", "bg-gradient-1": "#c3cfe2", "bg-gradient-2": "#e8ecf1", "bg-gradient-3": "#f5f0eb",
            "glass-bg": "rgba(255,255,255,0.55)", "glass-bg-hover": "rgba(255,255,255,0.65)",
            "glass-border": "rgba(255,255,255,0.6)", "glass-border-strong": "rgba(255,255,255,0.85)",
            "glass-shadow": "0 8px 32px rgba(0,0,0,0.08)", "glass-shadow-lg": "0 16px 48px rgba(0,0,0,0.12)",
            "glass-blur": "16px", "bg-card": "rgba(255,255,255,0.6)", "bg-input": "rgba(255,255,255,0.7)",
            "bg-navbar": "rgba(30,30,60,0.85)", "bg-table-header": "rgba(0,0,0,0.03)",
            "bg-table-hover": "rgba(0,0,0,0.04)", "bg-modal-overlay": "rgba(0,0,0,0.4)",
            "bg-cost-breakdown": "rgba(67,97,238,0.06)", "bg-warning": "rgba(255,193,7,0.15)",
            "bg-row-low": "rgba(231,76,60,0.06)", "bg-row-medium": "rgba(243,156,18,0.06)",
            "bg-filament-color": "rgba(0,0,0,0.06)", "bg-remaining-bar": "rgba(0,0,0,0.08)",
            "bg-mini-bar": "rgba(0,0,0,0.08)",
            "text": "#1a1a2e", "text-secondary": "#5a5a7a", "text-muted": "#8888a0",
            "text-navbar": "#b0b0c8", "text-navbar-active": "#fff",
            "text-card-header": "#2a2a4a", "text-label": "#4a4a6a", "text-table-header": "#5a5a7a",
            "text-warning": "#856404", "text-success-flash": "#155724", "text-error-flash": "#721c24",
            "border": "rgba(0,0,0,0.1)", "border-table": "rgba(0,0,0,0.06)",
            "border-cost-row": "rgba(0,0,0,0.08)", "border-flash-success": "#c3e6cb",
            "border-flash-error": "#f5c6cb", "border-warning": "#ffc107",
            "accent": "#4361ee", "accent-hover": "#3a56d4", "accent-light": "rgba(67,97,238,0.12)",
            "danger": "#e74c3c", "danger-hover": "#c0392b",
            "success": "#2ecc71", "success-hover": "#27ae60",
            "secondary": "#6c757d", "secondary-hover": "#5a6268",
            "warning-accent": "#f39c12", "low-accent": "#e74c3c",
            "glow-accent": "rgba(67,97,238,0.25)",
        },
        "dark": {
            "bg": "#0a0a14", "bg-gradient-1": "#0a0a1a", "bg-gradient-2": "#0f0f20", "bg-gradient-3": "#12122a",
            "glass-bg": "rgba(25,25,50,0.6)", "glass-bg-hover": "rgba(30,30,60,0.7)",
            "glass-border": "rgba(255,255,255,0.08)", "glass-border-strong": "rgba(255,255,255,0.15)",
            "glass-shadow": "0 8px 32px rgba(0,0,0,0.4)", "glass-shadow-lg": "0 16px 48px rgba(0,0,0,0.5)",
            "glass-blur": "20px", "bg-card": "rgba(20,20,45,0.65)", "bg-input": "rgba(30,30,60,0.7)",
            "bg-navbar": "rgba(8,8,20,0.9)", "bg-table-header": "rgba(255,255,255,0.03)",
            "bg-table-hover": "rgba(255,255,255,0.04)", "bg-modal-overlay": "rgba(0,0,0,0.7)",
            "bg-cost-breakdown": "rgba(67,97,238,0.08)", "bg-warning": "rgba(255,193,7,0.1)",
            "bg-row-low": "rgba(231,76,60,0.1)", "bg-row-medium": "rgba(243,156,18,0.1)",
            "bg-filament-color": "rgba(255,255,255,0.08)", "bg-remaining-bar": "rgba(255,255,255,0.08)",
            "bg-mini-bar": "rgba(255,255,255,0.08)",
            "text": "#d8d8f0", "text-secondary": "#9898b8", "text-muted": "#6868888",
            "text-navbar": "#7878a0", "text-navbar-active": "#fff",
            "text-card-header": "#e0e0f0", "text-label": "#b0b0cc", "text-table-header": "#9090b0",
            "text-warning": "#ffc107", "text-success-flash": "#75b798", "text-error-flash": "#ea868f",
            "border": "rgba(255,255,255,0.08)", "border-table": "rgba(255,255,255,0.05)",
            "border-cost-row": "rgba(255,255,255,0.06)", "border-flash-success": "#75b798",
            "border-flash-error": "#ea868f", "border-warning": "#ffc107",
            "accent": "#6c8cff", "accent-hover": "#5c7cff", "accent-light": "rgba(108,140,255,0.15)",
            "danger": "#e74c3c", "danger-hover": "#c0392b",
            "success": "#2ecc71", "success-hover": "#27ae60",
            "secondary": "#6c757d", "secondary-hover": "#5a6268",
            "warning-accent": "#f39c12", "low-accent": "#e74c3c",
            "glow-accent": "rgba(108,140,255,0.3)",
        },
    },
    "retro": {
        "name": "Ретро",
        "light": {
            "bg": "#f5f0e1", "bg-gradient-1": "#e8dcc8", "bg-gradient-2": "#f5f0e1", "bg-gradient-3": "#faf6ed",
            "glass-bg": "rgba(255,250,230,0.7)", "glass-bg-hover": "rgba(255,250,230,0.8)",
            "glass-border": "rgba(139,119,80,0.2)", "glass-border-strong": "rgba(139,119,80,0.35)",
            "glass-shadow": "0 8px 32px rgba(80,60,30,0.1)", "glass-shadow-lg": "0 16px 48px rgba(80,60,30,0.15)",
            "glass-blur": "12px", "bg-card": "rgba(255,250,230,0.75)", "bg-input": "rgba(255,250,230,0.85)",
            "bg-navbar": "rgba(62,48,28,0.9)", "bg-table-header": "rgba(80,60,30,0.05)",
            "bg-table-hover": "rgba(80,60,30,0.06)", "bg-modal-overlay": "rgba(40,30,15,0.5)",
            "bg-cost-breakdown": "rgba(139,119,80,0.08)", "bg-warning": "rgba(180,130,40,0.15)",
            "bg-row-low": "rgba(180,60,40,0.06)", "bg-row-medium": "rgba(180,130,40,0.06)",
            "bg-filament-color": "rgba(80,60,30,0.08)", "bg-remaining-bar": "rgba(80,60,30,0.1)",
            "bg-mini-bar": "rgba(80,60,30,0.1)",
            "text": "#3e3020", "text-secondary": "#6b5a45", "text-muted": "#8a7a65",
            "text-navbar": "#c8b898", "text-navbar-active": "#fff",
            "text-card-header": "#3e3020", "text-label": "#5a4a35", "text-table-header": "#6b5a45",
            "text-warning": "#8a6a10", "text-success-flash": "#2a5a20", "text-error-flash": "#7a2020",
            "border": "rgba(80,60,30,0.15)", "border-table": "rgba(80,60,30,0.08)",
            "border-cost-row": "rgba(80,60,30,0.1)", "border-flash-success": "#a0c8a0",
            "border-flash-error": "#c8a0a0", "border-warning": "#b48828",
            "accent": "#8b6914", "accent-hover": "#7a5c10", "accent-light": "rgba(139,105,20,0.12)",
            "danger": "#a04030", "danger-hover": "#8a3528",
            "success": "#5a8a40", "success-hover": "#4a7a35",
            "secondary": "#7a6a55", "secondary-hover": "#6a5a45",
            "warning-accent": "#b48828", "low-accent": "#a04030",
            "glow-accent": "rgba(139,105,20,0.25)",
        },
        "dark": {
            "bg": "#1a1510", "bg-gradient-1": "#1a1510", "bg-gradient-2": "#201a14", "bg-gradient-3": "#252018",
            "glass-bg": "rgba(35,28,18,0.7)", "glass-bg-hover": "rgba(40,32,22,0.8)",
            "glass-border": "rgba(139,119,80,0.15)", "glass-border-strong": "rgba(139,119,80,0.25)",
            "glass-shadow": "0 8px 32px rgba(0,0,0,0.5)", "glass-shadow-lg": "0 16px 48px rgba(0,0,0,0.6)",
            "glass-blur": "16px", "bg-card": "rgba(30,24,16,0.75)", "bg-input": "rgba(35,28,18,0.85)",
            "bg-navbar": "rgba(15,12,8,0.95)", "bg-table-header": "rgba(255,255,255,0.03)",
            "bg-table-hover": "rgba(255,255,255,0.04)", "bg-modal-overlay": "rgba(0,0,0,0.7)",
            "bg-cost-breakdown": "rgba(139,105,20,0.08)", "bg-warning": "rgba(180,130,40,0.1)",
            "bg-row-low": "rgba(180,60,40,0.1)", "bg-row-medium": "rgba(180,130,40,0.1)",
            "bg-filament-color": "rgba(139,119,80,0.1)", "bg-remaining-bar": "rgba(139,119,80,0.1)",
            "bg-mini-bar": "rgba(139,119,80,0.1)",
            "text": "#d8c8a8", "text-secondary": "#a09078", "text-muted": "#706050",
            "text-navbar": "#8a7a60", "text-navbar-active": "#f0e0c0",
            "text-card-header": "#e8d8b8", "text-label": "#b0a088", "text-table-header": "#908068",
            "text-warning": "#d4a830", "text-success-flash": "#80b070", "text-error-flash": "#d08080",
            "border": "rgba(139,119,80,0.12)", "border-table": "rgba(139,119,80,0.08)",
            "border-cost-row": "rgba(139,119,80,0.08)", "border-flash-success": "#608060",
            "border-flash-error": "#806060", "border-warning": "#b48828",
            "accent": "#c8a040", "accent-hover": "#b89038", "accent-light": "rgba(200,160,64,0.15)",
            "danger": "#c05040", "danger-hover": "#a84038",
            "success": "#70a050", "success-hover": "#609040",
            "secondary": "#8a7a60", "secondary-hover": "#7a6a50",
            "warning-accent": "#c8a040", "low-accent": "#c05040",
            "glow-accent": "rgba(200,160,64,0.3)",
        },
    },
    "terminal": {
        "name": "Терминал",
        "light": {
            "bg": "#f0f0f0", "bg-gradient-1": "#e0e0e0", "bg-gradient-2": "#f0f0f0", "bg-gradient-3": "#e8e8e8",
            "glass-bg": "rgba(240,240,240,0.8)", "glass-bg-hover": "rgba(235,235,235,0.9)",
            "glass-border": "rgba(0,0,0,0.15)", "glass-border-strong": "rgba(0,0,0,0.25)",
            "glass-shadow": "0 2px 8px rgba(0,0,0,0.1)", "glass-shadow-lg": "0 4px 16px rgba(0,0,0,0.15)",
            "glass-blur": "4px", "bg-card": "rgba(245,245,245,0.9)", "bg-input": "rgba(240,240,240,0.95)",
            "bg-navbar": "#1a1a1a", "bg-table-header": "rgba(0,0,0,0.04)",
            "bg-table-hover": "rgba(0,0,0,0.06)", "bg-modal-overlay": "rgba(0,0,0,0.5)",
            "bg-cost-breakdown": "rgba(0,0,0,0.03)", "bg-warning": "rgba(200,180,0,0.1)",
            "bg-row-low": "rgba(200,0,0,0.04)", "bg-row-medium": "rgba(200,150,0,0.04)",
            "bg-filament-color": "rgba(0,0,0,0.06)", "bg-remaining-bar": "rgba(0,0,0,0.1)",
            "bg-mini-bar": "rgba(0,0,0,0.1)",
            "text": "#1a1a1a", "text-secondary": "#4a4a4a", "text-muted": "#888",
            "text-navbar": "#00ff41", "text-navbar-active": "#00ff41",
            "text-card-header": "#1a1a1a", "text-label": "#333", "text-table-header": "#4a4a4a",
            "text-warning": "#8a7a00", "text-success-flash": "#006600", "text-error-flash": "#aa0000",
            "border": "rgba(0,0,0,0.15)", "border-table": "rgba(0,0,0,0.08)",
            "border-cost-row": "rgba(0,0,0,0.1)", "border-flash-success": "#00aa00",
            "border-flash-error": "#aa0000", "border-warning": "#c8b400",
            "accent": "#00aa30", "accent-hover": "#009928", "accent-light": "rgba(0,170,48,0.12)",
            "danger": "#cc0000", "danger-hover": "#aa0000",
            "success": "#00aa30", "success-hover": "#009928",
            "secondary": "#555", "secondary-hover": "#444",
            "warning-accent": "#c8b400", "low-accent": "#cc0000",
            "glow-accent": "rgba(0,170,48,0.3)",
        },
        "dark": {
            "bg": "#0a0a0a", "bg-gradient-1": "#0a0a0a", "bg-gradient-2": "#0f0f0f", "bg-gradient-3": "#0d0d0d",
            "glass-bg": "rgba(15,15,15,0.8)", "glass-bg-hover": "rgba(20,20,20,0.9)",
            "glass-border": "rgba(0,255,65,0.1)", "glass-border-strong": "rgba(0,255,65,0.2)",
            "glass-shadow": "0 2px 8px rgba(0,255,65,0.05)", "glass-shadow-lg": "0 4px 16px rgba(0,255,65,0.08)",
            "glass-blur": "4px", "bg-card": "rgba(12,12,12,0.9)", "bg-input": "rgba(15,15,15,0.95)",
            "bg-navbar": "#050505", "bg-table-header": "rgba(0,255,65,0.03)",
            "bg-table-hover": "rgba(0,255,65,0.04)", "bg-modal-overlay": "rgba(0,0,0,0.8)",
            "bg-cost-breakdown": "rgba(0,255,65,0.03)", "bg-warning": "rgba(200,180,0,0.08)",
            "bg-row-low": "rgba(200,0,0,0.06)", "bg-row-medium": "rgba(200,150,0,0.06)",
            "bg-filament-color": "rgba(0,255,65,0.05)", "bg-remaining-bar": "rgba(0,255,65,0.08)",
            "bg-mini-bar": "rgba(0,255,65,0.08)",
            "text": "#00ff41", "text-secondary": "#00cc33", "text-muted": "#008822",
            "text-navbar": "#00ff41", "text-navbar-active": "#00ff41",
            "text-card-header": "#00ff41", "text-label": "#00dd38", "text-table-header": "#00aa2a",
            "text-warning": "#c8b400", "text-success-flash": "#00ff41", "text-error-flash": "#ff4444",
            "border": "rgba(0,255,65,0.1)", "border-table": "rgba(0,255,65,0.06)",
            "border-cost-row": "rgba(0,255,65,0.06)", "border-flash-success": "#00aa2a",
            "border-flash-error": "#aa2222", "border-warning": "#c8b400",
            "accent": "#00ff41", "accent-hover": "#00dd38", "accent-light": "rgba(0,255,65,0.1)",
            "danger": "#ff4444", "danger-hover": "#cc3333",
            "success": "#00ff41", "success-hover": "#00dd38",
            "secondary": "#008822", "secondary-hover": "#006618",
            "warning-accent": "#c8b400", "low-accent": "#ff4444",
            "glow-accent": "rgba(0,255,65,0.4)",
        },
    },
    "material": {
        "name": "Material",
        "light": {
            "bg": "#fafafa", "bg-gradient-1": "#f0f0f0", "bg-gradient-2": "#fafafa", "bg-gradient-3": "#f5f5f5",
            "glass-bg": "rgba(255,255,255,0.95)", "glass-bg-hover": "rgba(255,255,255,0.98)",
            "glass-border": "rgba(0,0,0,0.08)", "glass-border-strong": "rgba(0,0,0,0.12)",
            "glass-shadow": "0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08)",
            "glass-shadow-lg": "0 3px 6px rgba(0,0,0,0.16), 0 3px 6px rgba(0,0,0,0.12)",
            "glass-blur": "0px", "bg-card": "rgba(255,255,255,0.98)", "bg-input": "rgba(255,255,255,1)",
            "bg-navbar": "#1565c0", "bg-table-header": "rgba(0,0,0,0.02)",
            "bg-table-hover": "rgba(21,101,192,0.04)", "bg-modal-overlay": "rgba(0,0,0,0.5)",
            "bg-cost-breakdown": "rgba(21,101,192,0.04)", "bg-warning": "rgba(255,183,77,0.15)",
            "bg-row-low": "rgba(211,47,47,0.04)", "bg-row-medium": "rgba(255,183,77,0.04)",
            "bg-filament-color": "rgba(0,0,0,0.04)", "bg-remaining-bar": "rgba(0,0,0,0.08)",
            "bg-mini-bar": "rgba(0,0,0,0.08)",
            "text": "#212121", "text-secondary": "#757575", "text-muted": "#9e9e9e",
            "text-navbar": "#bbdefb", "text-navbar-active": "#fff",
            "text-card-header": "#212121", "text-label": "#424242", "text-table-header": "#616161",
            "text-warning": "#e65100", "text-success-flash": "#2e7d32", "text-error-flash": "#c62828",
            "border": "rgba(0,0,0,0.08)", "border-table": "rgba(0,0,0,0.06)",
            "border-cost-row": "rgba(0,0,0,0.06)", "border-flash-success": "#a5d6a7",
            "border-flash-error": "#ef9a9a", "border-warning": "#ffcc80",
            "accent": "#1976d2", "accent-hover": "#1565c0", "accent-light": "rgba(25,118,210,0.1)",
            "danger": "#d32f2f", "danger-hover": "#c62828",
            "success": "#388e3c", "success-hover": "#2e7d32",
            "secondary": "#757575", "secondary-hover": "#616161",
            "warning-accent": "#ffa726", "low-accent": "#d32f2f",
            "glow-accent": "rgba(25,118,210,0.2)",
        },
        "dark": {
            "bg": "#121212", "bg-gradient-1": "#121212", "bg-gradient-2": "#1a1a1a", "bg-gradient-3": "#151515",
            "glass-bg": "rgba(30,30,30,0.95)", "glass-bg-hover": "rgba(35,35,35,0.98)",
            "glass-border": "rgba(255,255,255,0.06)", "glass-border-strong": "rgba(255,255,255,0.1)",
            "glass-shadow": "0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2)",
            "glass-shadow-lg": "0 3px 6px rgba(0,0,0,0.4), 0 3px 6px rgba(0,0,0,0.3)",
            "glass-blur": "0px", "bg-card": "rgba(28,28,28,0.98)", "bg-input": "rgba(30,30,30,1)",
            "bg-navbar": "#0d47a1", "bg-table-header": "rgba(255,255,255,0.03)",
            "bg-table-hover": "rgba(25,118,210,0.06)", "bg-modal-overlay": "rgba(0,0,0,0.7)",
            "bg-cost-breakdown": "rgba(25,118,210,0.06)", "bg-warning": "rgba(255,183,77,0.1)",
            "bg-row-low": "rgba(211,47,47,0.08)", "bg-row-medium": "rgba(255,183,77,0.08)",
            "bg-filament-color": "rgba(255,255,255,0.05)", "bg-remaining-bar": "rgba(255,255,255,0.08)",
            "bg-mini-bar": "rgba(255,255,255,0.08)",
            "text": "#e0e0e0", "text-secondary": "#9e9e9e", "text-muted": "#757575",
            "text-navbar": "#90caf9", "text-navbar-active": "#fff",
            "text-card-header": "#e0e0e0", "text-label": "#bdbdbd", "text-table-header": "#9e9e9e",
            "text-warning": "#ffb74d", "text-success-flash": "#81c784", "text-error-flash": "#ef9a9a",
            "border": "rgba(255,255,255,0.06)", "border-table": "rgba(255,255,255,0.05)",
            "border-cost-row": "rgba(255,255,255,0.05)", "border-flash-success": "#388e3c",
            "border-flash-error": "#c62828", "border-warning": "#ffa726",
            "accent": "#42a5f5", "accent-hover": "#1e88e5", "accent-light": "rgba(66,165,245,0.12)",
            "danger": "#ef5350", "danger-hover": "#e53935",
            "success": "#66bb6a", "success-hover": "#4caf50",
            "secondary": "#757575", "secondary-hover": "#616161",
            "warning-accent": "#ffa726", "low-accent": "#ef5350",
            "glow-accent": "rgba(66,165,245,0.25)",
        },
    },
    "pastel": {
        "name": "Pastel",
        "light": {
            "bg": "#f0f4f8", "bg-gradient-1": "#e2e8f0", "bg-gradient-2": "#f0f4f8", "bg-gradient-3": "#fef7f0",
            "glass-bg": "rgba(255,255,255,0.6)", "glass-bg-hover": "rgba(255,255,255,0.7)",
            "glass-border": "rgba(255,255,255,0.7)", "glass-border-strong": "rgba(255,255,255,0.9)",
            "glass-shadow": "0 4px 20px rgba(0,0,0,0.06)", "glass-shadow-lg": "0 8px 40px rgba(0,0,0,0.1)",
            "glass-blur": "20px", "bg-card": "rgba(255,255,255,0.65)", "bg-input": "rgba(255,255,255,0.75)",
            "bg-navbar": "rgba(100,116,139,0.85)", "bg-table-header": "rgba(0,0,0,0.02)",
            "bg-table-hover": "rgba(0,0,0,0.03)", "bg-modal-overlay": "rgba(0,0,0,0.4)",
            "bg-cost-breakdown": "rgba(139,92,246,0.06)", "bg-warning": "rgba(251,191,36,0.15)",
            "bg-row-low": "rgba(248,113,113,0.06)", "bg-row-medium": "rgba(251,191,36,0.06)",
            "bg-filament-color": "rgba(0,0,0,0.06)", "bg-remaining-bar": "rgba(0,0,0,0.08)",
            "bg-mini-bar": "rgba(0,0,0,0.08)",
            "text": "#1e293b", "text-secondary": "#64748b", "text-muted": "#94a3b8",
            "text-navbar": "#cbd5e1", "text-navbar-active": "#fff",
            "text-card-header": "#334155", "text-label": "#475569", "text-table-header": "#64748b",
            "text-warning": "#f59e0b", "text-success-flash": "#155724", "text-error-flash": "#721c24",
            "border": "rgba(0,0,0,0.08)", "border-table": "rgba(0,0,0,0.04)",
            "border-cost-row": "rgba(0,0,0,0.06)", "border-flash-success": "#c3e6cb",
            "border-flash-error": "#f5c6cb", "border-warning": "#ffc107",
            "accent": "#8b5cf6", "accent-hover": "#7c3aed", "accent-light": "rgba(139,92,246,0.1)",
            "danger": "#f472b6", "danger-hover": "#ec4899",
            "success": "#34d399", "success-hover": "#10b981",
            "secondary": "#94a3b8", "secondary-hover": "#64748b",
            "warning-accent": "#fbbf24", "low-accent": "#f87171",
            "glow-accent": "rgba(139,92,246,0.2)",
        },
        "dark": {
            "bg": "#1e1b2e", "bg-gradient-1": "#1e1b2e", "bg-gradient-2": "#252240", "bg-gradient-3": "#2d2a4e",
            "glass-bg": "rgba(37,34,64,0.7)", "glass-bg-hover": "rgba(45,42,78,0.8)",
            "glass-border": "rgba(139,92,246,0.15)", "glass-border-strong": "rgba(139,92,246,0.25)",
            "glass-shadow": "0 8px 32px rgba(0,0,0,0.4)", "glass-shadow-lg": "0 16px 48px rgba(0,0,0,0.5)",
            "glass-blur": "20px", "bg-card": "rgba(37,34,64,0.75)", "bg-input": "rgba(45,42,78,0.85)",
            "bg-navbar": "rgba(30,27,46,0.95)", "bg-table-header": "rgba(255,255,255,0.03)",
            "bg-table-hover": "rgba(255,255,255,0.04)", "bg-modal-overlay": "rgba(0,0,0,0.7)",
            "bg-cost-breakdown": "rgba(139,92,246,0.08)", "bg-warning": "rgba(251,191,36,0.1)",
            "bg-row-low": "rgba(244,114,182,0.1)", "bg-row-medium": "rgba(251,191,36,0.1)",
            "bg-filament-color": "rgba(255,255,255,0.08)", "bg-remaining-bar": "rgba(255,255,255,0.08)",
            "bg-mini-bar": "rgba(255,255,255,0.08)",
            "text": "#e2e0f0", "text-secondary": "#a5a0c0", "text-muted": "#7870a0",
            "text-navbar": "#a78bfa", "text-navbar-active": "#fff",
            "text-card-header": "#e2e0f0", "text-label": "#c0bce0", "text-table-header": "#a5a0c0",
            "text-warning": "#fbbf24", "text-success-flash": "#34d399", "text-error-flash": "#f472b6",
            "border": "rgba(139,92,246,0.12)", "border-table": "rgba(139,92,246,0.08)",
            "border-cost-row": "rgba(139,92,246,0.08)", "border-flash-success": "#34d399",
            "border-flash-error": "#f472b6", "border-warning": "#fbbf24",
            "accent": "#a78bfa", "accent-hover": "#8b5cf6", "accent-light": "rgba(167,139,250,0.15)",
            "danger": "#f472b6", "danger-hover": "#ec4899",
            "success": "#34d399", "success-hover": "#10b981",
            "secondary": "#7870a0", "secondary-hover": "#5a5480",
            "warning-accent": "#fbbf24", "low-accent": "#f472b6",
            "glow-accent": "rgba(167,139,250,0.3)",
        },
    },
    "nord": {
        "name": "Nord",
        "light": {
            "bg": "#eceff4", "bg-gradient-1": "#e5e9f0", "bg-gradient-2": "#eceff4", "bg-gradient-3": "#f5f7fa",
            "glass-bg": "rgba(236,239,244,0.7)", "glass-bg-hover": "rgba(236,239,244,0.8)",
            "glass-border": "rgba(136,192,208,0.2)", "glass-border-strong": "rgba(136,192,208,0.35)",
            "glass-shadow": "0 4px 20px rgba(0,0,0,0.06)", "glass-shadow-lg": "0 8px 40px rgba(0,0,0,0.1)",
            "glass-blur": "20px", "bg-card": "rgba(236,239,244,0.75)", "bg-input": "rgba(236,239,244,0.85)",
            "bg-navbar": "rgba(76,86,106,0.9)", "bg-table-header": "rgba(0,0,0,0.03)",
            "bg-table-hover": "rgba(0,0,0,0.04)", "bg-modal-overlay": "rgba(0,0,0,0.4)",
            "bg-cost-breakdown": "rgba(136,192,208,0.06)", "bg-warning": "rgba(235,203,139,0.15)",
            "bg-row-low": "rgba(191,97,106,0.06)", "bg-row-medium": "rgba(235,203,139,0.06)",
            "bg-filament-color": "rgba(0,0,0,0.06)", "bg-remaining-bar": "rgba(0,0,0,0.08)",
            "bg-mini-bar": "rgba(0,0,0,0.08)",
            "text": "#2e3440", "text-secondary": "#4c566a", "text-muted": "#d8dee9",
            "text-navbar": "#81a1c1", "text-navbar-active": "#fff",
            "text-card-header": "#2e3440", "text-label": "#4c566a", "text-table-header": "#4c566a",
            "text-warning": "#b48828", "text-success-flash": "#155724", "text-error-flash": "#721c24",
            "border": "rgba(0,0,0,0.08)", "border-table": "rgba(0,0,0,0.05)",
            "border-cost-row": "rgba(0,0,0,0.06)", "border-flash-success": "#c3e6cb",
            "border-flash-error": "#f5c6cb", "border-warning": "#ffc107",
            "accent": "#5e81ac", "accent-hover": "#81a1c1", "accent-light": "rgba(94,129,172,0.1)",
            "danger": "#bf616a", "danger-hover": "#a94442",
            "success": "#a3be8c", "success-hover": "#8fbc8f",
            "secondary": "#4c566a", "secondary-hover": "#3b4252",
            "warning-accent": "#ebcb8b", "low-accent": "#bf616a",
            "glow-accent": "rgba(94,129,172,0.2)",
        },
        "dark": {
            "bg": "#2e3440", "bg-gradient-1": "#2e3440", "bg-gradient-2": "#3b4252", "bg-gradient-3": "#434c5e",
            "glass-bg": "rgba(59,66,82,0.7)", "glass-bg-hover": "rgba(67,76,94,0.8)",
            "glass-border": "rgba(136,192,208,0.15)", "glass-border-strong": "rgba(136,192,208,0.25)",
            "glass-shadow": "0 8px 32px rgba(0,0,0,0.3)", "glass-shadow-lg": "0 16px 48px rgba(0,0,0,0.4)",
            "glass-blur": "16px", "bg-card": "rgba(59,66,82,0.75)", "bg-input": "rgba(67,76,94,0.8)",
            "bg-navbar": "rgba(46,52,64,0.95)", "bg-table-header": "rgba(0,0,0,0.1)",
            "bg-table-hover": "rgba(0,0,0,0.15)", "bg-modal-overlay": "rgba(0,0,0,0.7)",
            "bg-cost-breakdown": "rgba(136,192,208,0.08)", "bg-warning": "rgba(235,203,139,0.1)",
            "bg-row-low": "rgba(191,97,106,0.1)", "bg-row-medium": "rgba(235,203,139,0.1)",
            "bg-filament-color": "rgba(255,255,255,0.08)", "bg-remaining-bar": "rgba(255,255,255,0.08)",
            "bg-mini-bar": "rgba(255,255,255,0.08)",
            "text": "#eceff4", "text-secondary": "#d8dee9", "text-muted": "#4c566a",
            "text-navbar": "#81a1c1", "text-navbar-active": "#fff",
            "text-card-header": "#eceff4", "text-label": "#d8dee9", "text-table-header": "#81a1c1",
            "text-warning": "#ebcb8b", "text-success-flash": "#a3be8c", "text-error-flash": "#bf616a",
            "border": "rgba(136,192,208,0.12)", "border-table": "rgba(136,192,208,0.08)",
            "border-cost-row": "rgba(136,192,208,0.1)", "border-flash-success": "#a3be8c",
            "border-flash-error": "#bf616a", "border-warning": "#ebcb8b",
            "accent": "#88c0d0", "accent-hover": "#81a1c1", "accent-light": "rgba(136,192,208,0.15)",
            "danger": "#bf616a", "danger-hover": "#a94442",
            "success": "#a3be8c", "success-hover": "#8fbc8f",
            "secondary": "#4c566a", "secondary-hover": "#3b4252",
            "warning-accent": "#ebcb8b", "low-accent": "#bf616a",
            "glow-accent": "rgba(136,192,208,0.3)",
        },
    },
    "dracula": {
        "name": "Dracula",
        "light": {
            "bg": "#f8f8f2", "bg-gradient-1": "#f0f0ea", "bg-gradient-2": "#f8f8f2", "bg-gradient-3": "#fefefe",
            "glass-bg": "rgba(248,248,242,0.7)", "glass-bg-hover": "rgba(248,248,242,0.8)",
            "glass-border": "rgba(189,147,249,0.2)", "glass-border-strong": "rgba(189,147,249,0.35)",
            "glass-shadow": "0 4px 20px rgba(0,0,0,0.06)", "glass-shadow-lg": "0 8px 40px rgba(0,0,0,0.1)",
            "glass-blur": "20px", "bg-card": "rgba(248,248,242,0.75)", "bg-input": "rgba(248,248,242,0.85)",
            "bg-navbar": "rgba(40,42,54,0.9)", "bg-table-header": "rgba(0,0,0,0.03)",
            "bg-table-hover": "rgba(0,0,0,0.04)", "bg-modal-overlay": "rgba(0,0,0,0.4)",
            "bg-cost-breakdown": "rgba(189,147,249,0.06)", "bg-warning": "rgba(241,250,140,0.15)",
            "bg-row-low": "rgba(255,85,85,0.06)", "bg-row-medium": "rgba(241,250,140,0.06)",
            "bg-filament-color": "rgba(0,0,0,0.06)", "bg-remaining-bar": "rgba(0,0,0,0.08)",
            "bg-mini-bar": "rgba(0,0,0,0.08)",
            "text": "#282a36", "text-secondary": "#44475a", "text-muted": "#6272a4",
            "text-navbar": "#bd93f9", "text-navbar-active": "#fff",
            "text-card-header": "#282a36", "text-label": "#44475a", "text-table-header": "#44475a",
            "text-warning": "#b48828", "text-success-flash": "#155724", "text-error-flash": "#721c24",
            "border": "rgba(0,0,0,0.08)", "border-table": "rgba(0,0,0,0.05)",
            "border-cost-row": "rgba(0,0,0,0.06)", "border-flash-success": "#c3e6cb",
            "border-flash-error": "#f5c6cb", "border-warning": "#ffc107",
            "accent": "#bd93f9", "accent-hover": "#ff79c6", "accent-light": "rgba(189,147,249,0.1)",
            "danger": "#ff5555", "danger-hover": "#ff6e6e",
            "success": "#50fa7b", "success-hover": "#69ff94",
            "secondary": "#6272a4", "secondary-hover": "#44475a",
            "warning-accent": "#f1fa8c", "low-accent": "#ff5555",
            "glow-accent": "rgba(189,147,249,0.2)",
        },
        "dark": {
            "bg": "#282a36", "bg-gradient-1": "#282a36", "bg-gradient-2": "#343746", "bg-gradient-3": "#44475a",
            "glass-bg": "rgba(40,42,54,0.7)", "glass-bg-hover": "rgba(52,55,70,0.8)",
            "glass-border": "rgba(98,114,164,0.2)", "glass-border-strong": "rgba(98,114,164,0.35)",
            "glass-shadow": "0 8px 32px rgba(0,0,0,0.4)", "glass-shadow-lg": "0 16px 48px rgba(0,0,0,0.5)",
            "glass-blur": "16px", "bg-card": "rgba(40,42,54,0.75)", "bg-input": "rgba(52,55,70,0.8)",
            "bg-navbar": "rgba(40,42,54,0.95)", "bg-table-header": "rgba(0,0,0,0.15)",
            "bg-table-hover": "rgba(0,0,0,0.2)", "bg-modal-overlay": "rgba(0,0,0,0.7)",
            "bg-cost-breakdown": "rgba(189,147,249,0.08)", "bg-warning": "rgba(241,250,140,0.1)",
            "bg-row-low": "rgba(255,85,85,0.1)", "bg-row-medium": "rgba(241,250,140,0.1)",
            "bg-filament-color": "rgba(255,255,255,0.08)", "bg-remaining-bar": "rgba(255,255,255,0.08)",
            "bg-mini-bar": "rgba(255,255,255,0.08)",
            "text": "#f8f8f2", "text-secondary": "#bd93f9", "text-muted": "#6272a4",
            "text-navbar": "#bd93f9", "text-navbar-active": "#fff",
            "text-card-header": "#f8f8f2", "text-label": "#f8f8f2", "text-table-header": "#bd93f9",
            "text-warning": "#f1fa8c", "text-success-flash": "#50fa7b", "text-error-flash": "#ff5555",
            "border": "rgba(98,114,164,0.15)", "border-table": "rgba(98,114,164,0.1)",
            "border-cost-row": "rgba(98,114,164,0.12)", "border-flash-success": "#50fa7b",
            "border-flash-error": "#ff5555", "border-warning": "#f1fa8c",
            "accent": "#bd93f9", "accent-hover": "#ff79c6", "accent-light": "rgba(189,147,249,0.15)",
            "danger": "#ff5555", "danger-hover": "#ff6e6e",
            "success": "#50fa7b", "success-hover": "#69ff94",
            "secondary": "#6272a4", "secondary-hover": "#44475a",
            "warning-accent": "#f1fa8c", "low-accent": "#ff5555",
            "glow-accent": "rgba(189,147,249,0.3)",
        },
    },
    "ocean": {
        "name": "Ocean",
        "light": {
            "bg": "#e0f2fe", "bg-gradient-1": "#bae6fd", "bg-gradient-2": "#e0f2fe", "bg-gradient-3": "#f0f9ff",
            "glass-bg": "rgba(255,255,255,0.6)", "glass-bg-hover": "rgba(255,255,255,0.7)",
            "glass-border": "rgba(14,165,233,0.15)", "glass-border-strong": "rgba(14,165,233,0.3)",
            "glass-shadow": "0 4px 20px rgba(14,165,233,0.08)", "glass-shadow-lg": "0 8px 40px rgba(14,165,233,0.12)",
            "glass-blur": "20px", "bg-card": "rgba(255,255,255,0.65)", "bg-input": "rgba(255,255,255,0.75)",
            "bg-navbar": "rgba(8,145,178,0.85)", "bg-table-header": "rgba(14,165,233,0.05)",
            "bg-table-hover": "rgba(14,165,233,0.08)", "bg-modal-overlay": "rgba(0,0,0,0.4)",
            "bg-cost-breakdown": "rgba(14,165,233,0.06)", "bg-warning": "rgba(245,158,11,0.15)",
            "bg-row-low": "rgba(239,68,68,0.06)", "bg-row-medium": "rgba(245,158,11,0.06)",
            "bg-filament-color": "rgba(0,0,0,0.06)", "bg-remaining-bar": "rgba(0,0,0,0.08)",
            "bg-mini-bar": "rgba(0,0,0,0.08)",
            "text": "#0c4a6e", "text-secondary": "#0369a1", "text-muted": "#38bdf8",
            "text-navbar": "#7dd3fc", "text-navbar-active": "#fff",
            "text-card-header": "#0c4a6e", "text-label": "#0369a1", "text-table-header": "#0284c7",
            "text-warning": "#f59e0b", "text-success-flash": "#155724", "text-error-flash": "#721c24",
            "border": "rgba(14,165,233,0.12)", "border-table": "rgba(14,165,233,0.08)",
            "border-cost-row": "rgba(14,165,233,0.1)", "border-flash-success": "#c3e6cb",
            "border-flash-error": "#f5c6cb", "border-warning": "#ffc107",
            "accent": "#0ea5e9", "accent-hover": "#0284c7", "accent-light": "rgba(14,165,233,0.12)",
            "danger": "#ef4444", "danger-hover": "#dc2626",
            "success": "#10b981", "success-hover": "#059669",
            "secondary": "#64748b", "secondary-hover": "#475569",
            "warning-accent": "#f59e0b", "low-accent": "#ef4444",
            "glow-accent": "rgba(14,165,233,0.25)",
        },
        "dark": {
            "bg": "#0c1929", "bg-gradient-1": "#0c1929", "bg-gradient-2": "#0f2438", "bg-gradient-3": "#132e4a",
            "glass-bg": "rgba(15,36,56,0.7)", "glass-bg-hover": "rgba(19,46,74,0.8)",
            "glass-border": "rgba(14,165,233,0.15)", "glass-border-strong": "rgba(14,165,233,0.25)",
            "glass-shadow": "0 8px 32px rgba(0,0,0,0.4)", "glass-shadow-lg": "0 16px 48px rgba(0,0,0,0.5)",
            "glass-blur": "20px", "bg-card": "rgba(15,36,56,0.75)", "bg-input": "rgba(19,46,74,0.85)",
            "bg-navbar": "rgba(12,25,41,0.95)", "bg-table-header": "rgba(255,255,255,0.03)",
            "bg-table-hover": "rgba(255,255,255,0.04)", "bg-modal-overlay": "rgba(0,0,0,0.7)",
            "bg-cost-breakdown": "rgba(14,165,233,0.08)", "bg-warning": "rgba(245,158,11,0.1)",
            "bg-row-low": "rgba(239,68,68,0.1)", "bg-row-medium": "rgba(245,158,11,0.1)",
            "bg-filament-color": "rgba(255,255,255,0.08)", "bg-remaining-bar": "rgba(255,255,255,0.08)",
            "bg-mini-bar": "rgba(255,255,255,0.08)",
            "text": "#e0f2fe", "text-secondary": "#7dd3fc", "text-muted": "#38bdf8",
            "text-navbar": "#38bdf8", "text-navbar-active": "#fff",
            "text-card-header": "#e0f2fe", "text-label": "#7dd3fc", "text-table-header": "#38bdf8",
            "text-warning": "#fbbf24", "text-success-flash": "#34d399", "text-error-flash": "#f87171",
            "border": "rgba(14,165,233,0.12)", "border-table": "rgba(14,165,233,0.08)",
            "border-cost-row": "rgba(14,165,233,0.08)", "border-flash-success": "#34d399",
            "border-flash-error": "#f87171", "border-warning": "#fbbf24",
            "accent": "#0ea5e9", "accent-hover": "#0284c7", "accent-light": "rgba(14,165,233,0.15)",
            "danger": "#ef4444", "danger-hover": "#dc2626",
            "success": "#10b981", "success-hover": "#059669",
            "secondary": "#38bdf8", "secondary-hover": "#0ea5e9",
            "warning-accent": "#fbbf24", "low-accent": "#ef4444",
            "glow-accent": "rgba(14,165,233,0.3)",
        },
    },
    "sunset": {
        "name": "Sunset",
        "light": {
            "bg": "#fef3c7", "bg-gradient-1": "#fde68a", "bg-gradient-2": "#fef3c7", "bg-gradient-3": "#fff7ed",
            "glass-bg": "rgba(255,255,255,0.6)", "glass-bg-hover": "rgba(255,255,255,0.7)",
            "glass-border": "rgba(245,158,11,0.15)", "glass-border-strong": "rgba(245,158,11,0.3)",
            "glass-shadow": "0 4px 20px rgba(245,158,11,0.08)", "glass-shadow-lg": "0 8px 40px rgba(245,158,11,0.12)",
            "glass-blur": "20px", "bg-card": "rgba(255,255,255,0.65)", "bg-input": "rgba(255,255,255,0.75)",
            "bg-navbar": "rgba(180,83,9,0.85)", "bg-table-header": "rgba(245,158,11,0.05)",
            "bg-table-hover": "rgba(245,158,11,0.08)", "bg-modal-overlay": "rgba(0,0,0,0.4)",
            "bg-cost-breakdown": "rgba(245,158,11,0.06)", "bg-warning": "rgba(245,158,11,0.15)",
            "bg-row-low": "rgba(239,68,68,0.06)", "bg-row-medium": "rgba(245,158,11,0.06)",
            "bg-filament-color": "rgba(0,0,0,0.06)", "bg-remaining-bar": "rgba(0,0,0,0.08)",
            "bg-mini-bar": "rgba(0,0,0,0.08)",
            "text": "#78350f", "text-secondary": "#92400e", "text-muted": "#d97706",
            "text-navbar": "#fcd34d", "text-navbar-active": "#fff",
            "text-card-header": "#78350f", "text-label": "#92400e", "text-table-header": "#b45309",
            "text-warning": "#b45309", "text-success-flash": "#155724", "text-error-flash": "#721c24",
            "border": "rgba(245,158,11,0.12)", "border-table": "rgba(245,158,11,0.08)",
            "border-cost-row": "rgba(245,158,11,0.1)", "border-flash-success": "#c3e6cb",
            "border-flash-error": "#f5c6cb", "border-warning": "#ffc107",
            "accent": "#f59e0b", "accent-hover": "#d97706", "accent-light": "rgba(245,158,11,0.12)",
            "danger": "#ef4444", "danger-hover": "#dc2626",
            "success": "#10b981", "success-hover": "#059669",
            "secondary": "#78716c", "secondary-hover": "#57534e",
            "warning-accent": "#f59e0b", "low-accent": "#ef4444",
            "glow-accent": "rgba(245,158,11,0.25)",
        },
        "dark": {
            "bg": "#1c1008", "bg-gradient-1": "#1c1008", "bg-gradient-2": "#2a1810", "bg-gradient-3": "#382018",
            "glass-bg": "rgba(42,24,16,0.7)", "glass-bg-hover": "rgba(56,32,24,0.8)",
            "glass-border": "rgba(245,158,11,0.15)", "glass-border-strong": "rgba(245,158,11,0.25)",
            "glass-shadow": "0 8px 32px rgba(0,0,0,0.4)", "glass-shadow-lg": "0 16px 48px rgba(0,0,0,0.5)",
            "glass-blur": "20px", "bg-card": "rgba(42,24,16,0.75)", "bg-input": "rgba(56,32,24,0.85)",
            "bg-navbar": "rgba(28,16,8,0.95)", "bg-table-header": "rgba(255,255,255,0.03)",
            "bg-table-hover": "rgba(255,255,255,0.04)", "bg-modal-overlay": "rgba(0,0,0,0.7)",
            "bg-cost-breakdown": "rgba(245,158,11,0.08)", "bg-warning": "rgba(245,158,11,0.1)",
            "bg-row-low": "rgba(239,68,68,0.1)", "bg-row-medium": "rgba(245,158,11,0.1)",
            "bg-filament-color": "rgba(255,255,255,0.08)", "bg-remaining-bar": "rgba(255,255,255,0.08)",
            "bg-mini-bar": "rgba(255,255,255,0.08)",
            "text": "#fef3c7", "text-secondary": "#fcd34d", "text-muted": "#d97706",
            "text-navbar": "#fbbf24", "text-navbar-active": "#fff",
            "text-card-header": "#fef3c7", "text-label": "#fcd34d", "text-table-header": "#fbbf24",
            "text-warning": "#fbbf24", "text-success-flash": "#34d399", "text-error-flash": "#f87171",
            "border": "rgba(245,158,11,0.12)", "border-table": "rgba(245,158,11,0.08)",
            "border-cost-row": "rgba(245,158,11,0.08)", "border-flash-success": "#34d399",
            "border-flash-error": "#f87171", "border-warning": "#fbbf24",
            "accent": "#f59e0b", "accent-hover": "#d97706", "accent-light": "rgba(245,158,11,0.15)",
            "danger": "#ef4444", "danger-hover": "#dc2626",
            "success": "#10b981", "success-hover": "#059669",
            "secondary": "#d97706", "secondary-hover": "#b45309",
            "warning-accent": "#fbbf24", "low-accent": "#ef4444",
            "glow-accent": "rgba(245,158,11,0.3)",
        },
    },
}


@app.route("/settings")
def settings():
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


@app.route("/settings/lang", methods=["POST"])
def save_lang():
    db = get_db()
    lang = request.form.get("lang", "ru")
    if lang in ("ru", "en", "es"):
        db.execute("UPDATE settings SET value = ? WHERE key = 'language'", (lang,))
        db.commit()
    db.close()
    resp = make_response("ok")
    resp.set_cookie("lang", lang, max_age=31536000)
    return resp


@app.route("/settings/theme", methods=["POST"])
def save_theme():
    db = get_db()
    db.execute("UPDATE settings SET value = ? WHERE key = 'theme'", (request.form["theme"],))
    db.commit()
    db.close()
    return "ok"


@app.route("/settings/preset", methods=["POST"])
def save_preset():
    db = get_db()
    preset = request.form["preset"]
    if preset in PRESETS:
        db.execute("UPDATE settings SET value = ? WHERE key = 'theme_preset'", (preset,))
        db.commit()
    db.close()
    return "ok"


@app.route("/settings/glass", methods=["POST"])
def save_glass():
    db = get_db()
    db.execute("UPDATE settings SET value = ? WHERE key = 'glass_mode'", (float(request.form["glass"]),))
    db.commit()
    db.close()
    return "ok"


@app.route("/settings/save", methods=["POST"])
def save_settings():
    db = get_db()
    db.execute("UPDATE settings SET value = ? WHERE key = 'electricity_rate'", (float(request.form["electricity_rate"]),))
    db.execute("UPDATE settings SET value = ? WHERE key = 'base_rate'", (float(request.form["base_rate"]),))
    db.execute("UPDATE settings SET value = ? WHERE key = 'markup_percent'", (float(request.form["markup_percent"]),))
    db.commit()
    db.close()
    flash("Настройки сохранены!", "success")
    return redirect(url_for("settings"))


@app.route("/settings/clear_history", methods=["POST"])
def clear_history():
    db = get_db()
    for row in db.execute("SELECT model_file FROM calculations").fetchall():
        if row["model_file"]:
            fpath = os.path.join(UPLOAD_DIR, row["model_file"])
            if os.path.exists(fpath):
                os.remove(fpath)
    db.execute("DELETE FROM calculations")
    db.commit()
    db.close()
    flash("История очищена!", "success")
    return redirect(url_for("settings"))


@app.route("/settings/tab_order", methods=["POST"])
def save_tab_order():
    db = get_db()
    db.execute("UPDATE settings SET value = ? WHERE key = 'tab_order'", (request.form["tab_order"],))
    db.commit()
    db.close()
    return "ok"


@app.route("/settings/maintenance", methods=["POST"])
def save_maintenance():
    db = get_db()
    for key, val in request.form.items():
        if key.startswith("maint_"):
            printer_id = key.replace("maint_", "")
            db.execute("UPDATE printers SET maintenance_hours = ? WHERE id = ?", (float(val), printer_id))
    db.commit()
    db.close()
    flash("Настройки обслуживания сохранены!", "success")
    return redirect(url_for("settings"))


@app.route("/history/export")
def export_history():
    db = get_db()
    calc_list = db.execute("""
        SELECT c.*, p.name as printer_name, f.name as filament_name, f.color as filament_color
        FROM calculations c
        JOIN printers p ON c.printer_id = p.id
        JOIN filaments f ON c.filament_id = f.id
        ORDER BY c.created_at DESC
    """).fetchall()
    db.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Дата', 'Модель', 'Принтер', 'Филамент', 'Цвет', 'Вес (г)', 'Время (ч)', 'Филамент (руб)', 'Электричество (руб)', 'Амортизация (руб)', 'Наценка (%)', 'Итого (руб)'])
    for c in calc_list:
        writer.writerow([
            c["created_at"][:10], c["model_name"], c["printer_name"],
            c["filament_name"], c["filament_color"], "%.1f" % c["weight_g"],
            "%.1f" % c["print_time_hours"], "%.2f" % c["filament_cost"],
            "%.2f" % c["electricity_cost"], "%.2f" % c["depreciation_cost"],
            "%.0f" % c["markup_percent"], "%.2f" % c["total_cost"]
        ])
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=printpal_history.csv"})


@app.route("/about")
def about():
    return render_template("about.html", lang=request.lang)


SHPOLKEN_GITHUB = "https://raw.githubusercontent.com/dontneedfriends-jpg/ShpoolkenDB/main/filaments"


def check_internet():
    try:
        req = urllib.request.Request("https://api.github.com/")
        req.add_header("User-Agent", "Mozilla/5.0")
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return False


@app.route("/shpoolken")
def shpoolken():
    init_shpoolken_db()
    has_internet = check_internet()
    loaded = is_shpoolken_loaded()
    manufacturers = get_shpoolken_manufacturers() if loaded else []
    materials = get_shpoolken_materials() if loaded else []
    stats = get_shpoolken_stats() if loaded else {}
    return render_template(
        "shpoolken.html",
        loaded=loaded,
        has_internet=has_internet,
        manufacturers=manufacturers,
        materials=materials,
        stats=stats,
        lang=request.lang,
    )


@app.route("/shpoolken/sync", methods=["POST"])
def shpoolken_sync():
    init_shpoolken_db()
    
    if not check_internet():
        return jsonify({"success": False, "error": "no_internet"})
    
    try:
        filaments_data = []
        
        req = urllib.request.Request("https://api.github.com/repos/dontneedfriends-jpg/ShpoolkenDB/contents/filaments")
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=30) as resp:
            files = json.loads(resp.read().decode())
        
        total = len([f for f in files if f["name"].endswith(".json")])
        
        for i, f in enumerate(files):
            if not f["name"].endswith(".json"):
                continue
            
            try:
                req = urllib.request.Request(f["download_url"])
                req.add_header("User-Agent", "Mozilla/5.0")
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode())
                    filaments_data.append(data)
            except Exception as e:
                logger.warning(f"Failed to download {f['name']}: {e}")
        
        insert_shpoolken_filaments(filaments_data)
        
        return jsonify({
            "success": True,
            "stats": get_shpoolken_stats()
        })
    except Exception as e:
        logger.error(f"Shpoolken sync error: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route("/shpoolken/search")
def shpoolken_search():
    if not is_shpoolken_loaded():
        return jsonify([])
    
    q = request.args.get("q", "")
    manufacturer = request.args.get("manufacturer", "")
    material = request.args.get("material", "")
    
    results = get_shpoolken_filaments(
        manufacturer=manufacturer if manufacturer else None,
        material=material if material else None,
        search=q if q else None,
        limit=100
    )
    
    return jsonify([dict(r) for r in results])


@app.route("/shpoolken/add", methods=["POST"])
def shpoolken_add():
    db = get_db()
    
    manufacturer = request.form.get("manufacturer", "")
    name = request.form.get("name", "")
    material = request.form.get("material", "")
    color = request.form.get("color", "")
    color_hex = request.form.get("color_hex", "")
    density = safe_float(request.form.get("density"))
    diameter = safe_float(request.form.get("diameter"), 1.75)
    weight = safe_float(request.form.get("weight"), 1000)
    spool_price = safe_float(request.form.get("spool_price"))
    
    full_name = f"{manufacturer} {name}" if manufacturer else name
    if color:
        full_name = f"{full_name} {color}"
    
    db.execute("""
        INSERT INTO filaments (name, filament_type, color, color_hex, spool_weight_g, spool_price, remaining_g, density, diameter)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (full_name, material, color, color_hex, weight, spool_price, weight, density or 0, diameter or 1.75))
    db.commit()
    db.close()
    
    flash("Филамент добавлен!", "success")
    return redirect(url_for("filaments"))


if __name__ == "__main__":
    init_db()
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    app.run(debug=False, host="127.0.0.1", port=5000, threaded=True)
