from flask import Blueprint, request, redirect, url_for, jsonify, render_template
from database import get_db
from utils import safe_float

printers_bp = Blueprint("printers", __name__)


@printers_bp.route("/printers")
def printers():
    db = get_db()
    printer_list = db.execute("SELECT * FROM printers ORDER BY name").fetchall()
    db.close()
    return render_template("printers.html", printers=printer_list, lang=request.lang)


@printers_bp.route("/printers/add", methods=["POST"])
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
    return redirect(url_for(".printers"))


@printers_bp.route("/printers/<int:id>/edit", methods=["POST"])
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
    return redirect(url_for(".printers"))


@printers_bp.route("/printers/<int:id>/delete", methods=["POST"])
def delete_printer(id):
    db = get_db()
    row = db.execute("SELECT * FROM printers WHERE id = ?", (id,)).fetchone()
    deleted_data = dict(row) if row else None
    
    db.execute("DELETE FROM calculations WHERE printer_id = ?", (id,))
    db.execute("DELETE FROM printers WHERE id = ?", (id,))
    db.commit()
    db.close()
    if deleted_data:
        return jsonify({"ok": True, "data": deleted_data})
    return jsonify({"ok": True})


@printers_bp.route("/printers/restore", methods=["POST"])
def restore_printer():
    data = request.get_json()
    db = get_db()
    db.execute("INSERT INTO printers (name, power_watts, purchase_price, depreciation_per_hour, ip_address, camera_ip, maintenance_hours) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (data["name"], data["power_watts"], data["purchase_price"], data["depreciation_per_hour"], data.get("ip_address", ""), data.get("camera_ip", ""), data.get("maintenance_hours", 0)))
    db.commit()
    db.close()
    return "ok", 200


@printers_bp.route("/printers/monitor")
def printers_monitor():
    db = get_db()
    printer_list = db.execute("SELECT * FROM printers WHERE ip_address IS NOT NULL AND ip_address != '' ORDER BY name").fetchall()
    db.close()
    return render_template("printers_monitor.html", printers=printer_list, lang=request.lang)
