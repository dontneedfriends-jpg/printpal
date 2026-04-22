from flask import Blueprint, request, Response, flash, redirect, url_for, jsonify, render_template
from database import get_db
from config import UPLOAD_DIR
from utils import safe_float
from translations import t as _t
import json

filaments_bp = Blueprint("filaments", __name__)


@filaments_bp.route("/filaments")
def filaments():
    db = get_db()
    filament_list = db.execute("SELECT *, CASE WHEN spool_weight_g > 0 THEN (spool_price / spool_weight_g) ELSE 0 END as price_per_g FROM filaments ORDER BY name").fetchall()
    db.close()
    return render_template("filaments.html", filaments=filament_list, lang=request.lang)


@filaments_bp.route("/filaments/add", methods=["POST"])
def add_filament():
    db = get_db()
    weight = safe_float(request.form["spool_weight_g"], 1000)
    db.execute(
        "INSERT INTO filaments (name, filament_type, color, spool_weight_g, spool_price, remaining_g, color_hex, barcode) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (request.form["name"], request.form["filament_type"], request.form["color"], weight, safe_float(request.form["spool_price"]), weight, request.form.get("color_hex", ""), request.form.get("barcode", ""))
    )
    db.commit()
    db.close()
    return "ok", 200


@filaments_bp.route("/filaments/<int:id>/edit", methods=["POST"])
def edit_filament(id):
    db = get_db()
    db.execute(
        "UPDATE filaments SET name=?, filament_type=?, color=?, spool_weight_g=?, spool_price=?, color_hex=?, barcode=? WHERE id=?",
        (request.form["name"], request.form["filament_type"], request.form["color"], safe_float(request.form["spool_weight_g"], 1000), safe_float(request.form["spool_price"]), request.form.get("color_hex", ""), request.form.get("barcode", ""), id)
    )
    db.commit()
    db.close()
    return "ok", 200


@filaments_bp.route("/filaments/<int:id>/adjust", methods=["POST"])
def adjust_filament(id):
    db = get_db()
    db.execute("UPDATE filaments SET remaining_g = ? WHERE id = ?", (safe_float(request.form["remaining_g"]), id))
    db.commit()
    db.close()
    return "ok", 200


@filaments_bp.route("/filaments/<int:id>/delete", methods=["POST"])
def delete_filament(id):
    db = get_db()
    row = db.execute("SELECT * FROM filaments WHERE id = ?", (id,)).fetchone()
    deleted_data = dict(row) if row else None
    
    db.execute("DELETE FROM calculations WHERE filament_id = ?", (id,))
    db.execute("DELETE FROM filaments WHERE id = ?", (id,))
    db.commit()
    db.close()
    if deleted_data:
        return jsonify({"ok": True, "data": deleted_data})
    return jsonify({"ok": True})


@filaments_bp.route("/filaments/restore", methods=["POST"])
def restore_filament():
    data = request.get_json()
    db = get_db()
    db.execute("INSERT INTO filaments (name, filament_type, color, spool_weight_g, spool_price, remaining_g, density, diameter, color_hex, barcode) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (data["name"], data["filament_type"], data["color"], data["spool_weight_g"], data["spool_price"], data["remaining_g"], data.get("density", 0), data.get("diameter", 1.75), data.get("color_hex", ""), data.get("barcode", "")))
    db.commit()
    db.close()
    return "ok", 200


@filaments_bp.route("/filaments/export")
def export_filaments():
    db = get_db()
    filaments = db.execute("SELECT id, name, filament_type, color, color_hex, spool_weight_g, spool_price, remaining_g, density, diameter, barcode FROM filaments ORDER BY name").fetchall()
    db.close()
    data = [dict(f) for f in filaments]
    return Response(json.dumps(data, indent=2, ensure_ascii=False), mimetype="application/json",
                    headers={"Content-Disposition": "attachment;filename=filaments.json"})


@filaments_bp.route("/filaments/import", methods=["POST"])
def import_filaments():
    file = request.files.get("import_file")
    if not file or not file.filename:
        flash(_t(request.lang, "file_not_selected"), "error")
        return redirect(url_for(".filaments"))
    try:
        data = json.load(file.stream)
    except (ValueError, json.JSONDecodeError):
        flash(_t(request.lang, "json_read_error"), "error")
        return redirect(url_for(".filaments"))
    if not isinstance(data, list):
        flash(_t(request.lang, "invalid_file_format"), "error")
        return redirect(url_for(".filaments"))
    db = get_db()
    count = 0
    for f in data:
        try:
            db.execute(
                "INSERT INTO filaments (name, filament_type, color, spool_weight_g, spool_price, remaining_g) VALUES (?, ?, ?, ?, ?, ?)",
                (f["name"], f["filament_type"], f["color"], float(f["spool_weight_g"]), float(f["spool_price"]), float(f.get("remaining_g", f["spool_weight_g"])))
            )
            count += 1
        except (KeyError, ValueError, TypeError):
            pass
    db.commit()
    db.close()
    flash(f"{_t(request.lang, 'imported_count')} {count}", "success")
    return redirect(url_for(".filaments"))
