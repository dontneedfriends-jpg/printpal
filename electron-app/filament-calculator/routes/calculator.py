from flask import Blueprint, request, render_template, jsonify, flash
from database import get_db
from config import DEFAULT_BASE_RATE, DEFAULT_MARKUP_PERCENT
from utils import safe_float
from translations import t as _t
import json

calculator_bp = Blueprint("calculator", __name__)


@calculator_bp.route("/calculator")
def calculator():
    db = get_db()
    all_printers = db.execute("SELECT * FROM printers ORDER BY name").fetchall()
    all_filaments = db.execute("SELECT *, CASE WHEN spool_weight_g > 0 THEN (spool_price / spool_weight_g) ELSE 0 END as price_per_g FROM filaments ORDER BY name").fetchall()
    all_clients = db.execute("SELECT id, name FROM clients ORDER BY name").fetchall()
    db.close()
    filaments_json = [dict(f) for f in all_filaments]
    from app import get_setting
    return render_template(
        "calculator.html",
        printers=all_printers,
        filaments=all_filaments,
        filaments_json=filaments_json,
        clients=all_clients,
        default_base=get_setting("base_rate"),
        default_markup=get_setting("markup_percent"),
        preview=None,
        lang=request.lang,
    )


@calculator_bp.route("/calculator/preview", methods=["POST"])
def preview_cost():
    db = get_db()
    printer_id = request.form.get("printer_id")
    if not printer_id:
        db.close()
        return _t(request.lang, "select_printer"), 400
    
    printer = db.execute("SELECT * FROM printers WHERE id = ?", (printer_id,)).fetchone()
    if not printer:
        db.close()
        return _t(request.lang, "printer_not_found"), 400
    
    print_time = safe_float(request.form.get("print_time_hours", 1), 1, 0, 8760)
    base_rate = safe_float(request.form.get("base_rate", DEFAULT_BASE_RATE), DEFAULT_BASE_RATE, 0, 10000)
    markup_pct = safe_float(request.form.get("markup_percent", DEFAULT_MARKUP_PERCENT), DEFAULT_MARKUP_PERCENT, 0, 500)
    other_expenses = safe_float(request.form.get("other_expenses", 0), 0, 0, 1000000)

    filament_ids = request.form.getlist("filament_id")
    filament_weights = request.form.getlist("filament_weight")
    
    filaments_data = []
    for fid, fweight in zip(filament_ids, filament_weights):
        f = db.execute("SELECT * FROM filaments WHERE id = ?", (fid,)).fetchone()
        w = safe_float(fweight, 0)
        if f and w > 0:
            filaments_data.append({"filament": f, "weight": w})

    tmp_file = None
    tmp_orig_name = ""
    if "model_file" in request.files:
        file = request.files["model_file"]
        if file and file.filename:
            from app import save_uploaded_file
            tmp_file, tmp_orig_name = save_uploaded_file(file)

    all_printers = db.execute("SELECT * FROM printers ORDER BY name").fetchall()
    all_filaments = db.execute("SELECT *, CASE WHEN spool_weight_g > 0 THEN (spool_price / spool_weight_g) ELSE 0 END as price_per_g FROM filaments ORDER BY name").fetchall()
    all_clients = db.execute("SELECT id, name FROM clients ORDER BY name").fetchall()
    filaments_json = [dict(f) for f in all_filaments]
    db.close()

    client_id = request.form.get("client_id") or None
    from app import calculate_cost_details, get_setting
    details = calculate_cost_details(printer, filaments_data, print_time, base_rate, markup_pct, other_expenses)

    return render_template(
        "calculator.html",
        printers=all_printers,
        filaments=all_filaments,
        filaments_json=filaments_json,
        clients=all_clients,
        default_base=get_setting("base_rate"),
        default_markup=get_setting("markup_percent"),
        preview={
            "printer": dict(printer),
            "client_id": client_id,
            "model_name": request.form["model_name"],
            "print_time": print_time,
            "base_rate": base_rate,
            "markup_pct": markup_pct,
            "other_expenses": other_expenses,
            "tmp_file": tmp_file,
            "tmp_orig_name": tmp_orig_name,
            "filament_costs": details["filament_costs"],
            "total_weight": details["total_weight"],
            "electricity_cost": details["electricity_cost"],
            "depreciation_cost": details["depreciation_cost"],
            "other_expenses_cost": details["other_expenses"],
            "subtotal": details["subtotal"],
            "markup_amount": details["markup_amount"],
            "total": details["total"],
        },
        lang=request.lang,
    )


@calculator_bp.route("/calculator/save", methods=["POST"])
def save_calculation():
    db = get_db()
    printer_id = request.form.get("printer_id")
    if not printer_id:
        db.close()
        return _t(request.lang, "select_printer"), 400
    
    printer = db.execute("SELECT * FROM printers WHERE id = ?", (printer_id,)).fetchone()
    if not printer:
        db.close()
        return _t(request.lang, "printer_not_found"), 400
    
    print_time = safe_float(request.form.get("print_time_hours", 1), 1, 0, 8760)
    base_rate = safe_float(request.form.get("base_rate", DEFAULT_BASE_RATE), DEFAULT_BASE_RATE, 0, 10000)
    markup_pct = safe_float(request.form.get("markup_percent", DEFAULT_MARKUP_PERCENT), DEFAULT_MARKUP_PERCENT, 0, 500)
    other_expenses = safe_float(request.form.get("other_expenses", 0), 0, 0, 1000000)

    filament_ids = request.form.getlist("filament_id")
    filament_weights = request.form.getlist("filament_weight")
    
    filaments_data = []
    for fid, fweight in zip(filament_ids, filament_weights):
        f = db.execute("SELECT * FROM filaments WHERE id = ?", (fid,)).fetchone()
        w = safe_float(fweight, 0)
        if f and w > 0:
            filaments_data.append({"filament": f, "weight": w})

    from app import calculate_cost_details, save_uploaded_file, logger
    details = calculate_cost_details(printer, filaments_data, print_time, base_rate, markup_pct, other_expenses)

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
    filament_data_json = json.dumps(details["filament_costs"], ensure_ascii=False)
    client_id = request.form.get("client_id") or None
    
    try:
        db.execute(
            "INSERT INTO calculations (printer_id, filament_id, model_name, weight_g, print_time_hours, base_rate, filament_cost, electricity_cost, depreciation_cost, other_expenses, markup_percent, markup_amount, total_cost, model_file, model_orig_name, filament_data, client_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (printer["id"], first_fid, request.form["model_name"], details["total_weight"], print_time, base_rate, details["total_filament_cost"], details["electricity_cost"], details["depreciation_cost"], other_expenses, markup_pct, details["markup_amount"], details["total"], model_file, model_orig_name, filament_data_json, client_id)
        )
    except (ValueError, TypeError) as e:
        logger.error(f"Insert with filament_data failed: {e}")
        db.execute(
            "INSERT INTO calculations (printer_id, filament_id, model_name, weight_g, print_time_hours, base_rate, filament_cost, electricity_cost, depreciation_cost, other_expenses, markup_percent, markup_amount, total_cost, model_file, model_orig_name, client_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (printer["id"], first_fid, request.form["model_name"], details["total_weight"], print_time, base_rate, details["total_filament_cost"], details["electricity_cost"], details["depreciation_cost"], other_expenses, markup_pct, details["markup_amount"], details["total"], model_file, model_orig_name, client_id)
        )
    for fid, fweight in zip(filament_ids, filament_weights):
        db.execute("UPDATE filaments SET remaining_g = remaining_g - ? WHERE id = ?", (safe_float(fweight, 0), fid))
    db.commit()
    db.close()
    
    logger.info(f"Calculation saved: {request.form['model_name']}, total: {details['total']}")
    
    if request.headers.get("X-Requested-With") == "fetch":
        return json.dumps({"ok": True, "total": details["total"], "model_name": request.form["model_name"]})
    
    flash(f"{_t(request.lang, 'calc_saved')}: {details['total']:.2f} {_t(request.lang, 'rub')}", "success")
    return redirect(url_for("history.history"))
