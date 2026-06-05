import json as _json
import urllib.request
import urllib.error
import urllib.parse
import math

from flask import Blueprint, request, redirect, url_for, jsonify, render_template, Response
from database import get_db
from utils import safe_float, safe_int

QUICK_SCRIPTS = {
    "preheat_pla": {"label": "Preheat PLA", "script": "M104 S210\nM140 S60", "icon": "🔥"},
    "preheat_petg": {"label": "Preheat PETG", "script": "M104 S230\nM140 S75", "icon": "🔥"},
    "cool_down": {"label": "Cool Down", "script": "M104 S0\nM140 S0", "icon": "❄️"},
    "fan_off": {"label": "Fan Off", "script": "M106 S0", "icon": "🌀"},
    "motors_off": {"label": "Motors Off", "script": "M84", "icon": "🔌"},
}

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
        "INSERT INTO printers (name, power_watts, purchase_price, depreciation_per_hour, ip_address, camera_ip, commissioning_date, tags, moonraker_port, moonraker_api_key, filament_diameter) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (request.form["name"], safe_float(request.form["power_watts"], 200, 1, 10000), safe_float(request.form["purchase_price"], 0, 0, 1000000), safe_float(request.form["depreciation_per_hour"], 0, 0, 100), request.form.get("ip_address", ""), request.form.get("camera_ip", ""), request.form.get("commissioning_date", ""), request.form.get("tags", ""), safe_int(request.form.get("moonraker_port", 7125), 7125, 1, 65535), request.form.get("moonraker_api_key", ""), safe_float(request.form.get("filament_diameter", 1.75), 1.75, 0.5, 5.0))
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
        "UPDATE printers SET name=?, power_watts=?, purchase_price=?, depreciation_per_hour=?, ip_address=?, camera_ip=?, commissioning_date=?, tags=?, moonraker_port=?, moonraker_api_key=?, filament_diameter=? WHERE id=?",
        (request.form["name"], safe_float(request.form["power_watts"], 200, 1, 10000), safe_float(request.form["purchase_price"], 0, 0, 1000000), safe_float(request.form["depreciation_per_hour"], 0, 0, 100), request.form.get("ip_address", ""), request.form.get("camera_ip", ""), request.form.get("commissioning_date", ""), request.form.get("tags", ""), safe_int(request.form.get("moonraker_port", 7125), 7125, 1, 65535), request.form.get("moonraker_api_key", ""), safe_float(request.form.get("filament_diameter", 1.75), 1.75, 0.5, 5.0), id)
    )
    db.commit()
    db.close()
    if request.headers.get("X-Requested-With") == "fetch":
        return "ok"
    return redirect(url_for(".printers"))


@printers_bp.route("/printers/<int:id>/copy", methods=["POST"])
def copy_printer(id):
    db = get_db()
    row = db.execute("SELECT * FROM printers WHERE id = ?", (id,)).fetchone()
    if not row:
        db.close()
        return "not found", 404
    data = dict(row)
    db.execute(
        "INSERT INTO printers (name, power_watts, purchase_price, depreciation_per_hour, ip_address, camera_ip, maintenance_hours, commissioning_date, tags, moonraker_port, moonraker_api_key, filament_diameter) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (data["name"] + " (копия)", data["power_watts"], data["purchase_price"], data["depreciation_per_hour"], data.get("ip_address", ""), data.get("camera_ip", ""), data.get("maintenance_hours", 0), data.get("commissioning_date", ""), data.get("tags", ""), data.get("moonraker_port", 7125), data.get("moonraker_api_key", ""), data.get("filament_diameter", 1.75))
    )
    db.commit()
    db.close()
    return "ok", 200


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
    db.execute("INSERT INTO printers (name, power_watts, purchase_price, depreciation_per_hour, ip_address, camera_ip, maintenance_hours, commissioning_date, tags, moonraker_port, moonraker_api_key, filament_diameter) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (data["name"], data["power_watts"], data["purchase_price"], data["depreciation_per_hour"], data.get("ip_address", ""), data.get("camera_ip", ""), data.get("maintenance_hours", 0), data.get("commissioning_date", ""), data.get("tags", ""), data.get("moonraker_port", 7125), data.get("moonraker_api_key", ""), data.get("filament_diameter", 1.75)))
    db.commit()
    db.close()
    return "ok", 200


@printers_bp.route("/printers/monitor")
def printers_monitor():
    db = get_db()
    printer_list = db.execute("SELECT * FROM printers WHERE ip_address IS NOT NULL AND ip_address != '' ORDER BY name").fetchall()
    db.close()
    return render_template("printers_monitor.html", printers=printer_list, lang=request.lang)


@printers_bp.route("/printers/<int:id>/maintenance")
def get_maintenance(id):
    db = get_db()
    logs = db.execute("SELECT * FROM maintenance_logs WHERE printer_id = ? ORDER BY date DESC", (id,)).fetchall()
    db.close()
    return jsonify([dict(l) for l in logs])


@printers_bp.route("/printers/<int:id>/maintenance", methods=["POST"])
def add_maintenance(id):
    db = get_db()
    db.execute(
        "INSERT INTO maintenance_logs (printer_id, date, type, description, cost, hours_spent) VALUES (?, ?, ?, ?, ?, ?)",
        (id, request.form.get("date", ""), request.form.get("type", "other"), request.form.get("description", ""), safe_float(request.form.get("cost", 0), 0), safe_float(request.form.get("hours_spent", 0), 0))
    )
    db.commit()
    db.close()
    return jsonify({"ok": True})


@printers_bp.route("/printers/maintenance/<int:log_id>/delete", methods=["POST"])
def delete_maintenance(log_id):
    db = get_db()
    db.execute("DELETE FROM maintenance_logs WHERE id = ?", (log_id,))
    db.commit()
    db.close()
    return jsonify({"ok": True})


FILAMENT_DENSITY_DEFAULT = 1.24  # g/cm³ for PLA


def _moonraker_url(printer_ip, port, path):
    return f"http://{printer_ip}:{port}/{path.lstrip('/')}"


def _proxy_request(printer_ip, port, method, path, body=None, content_type="application/json", api_key=""):
    url = _moonraker_url(printer_ip, port, path)
    headers = {"Content-Type": content_type}
    if api_key:
        headers["X-Api-Key"] = api_key
    data = body.encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            return raw, resp.status, resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.read(), e.code, e.headers.get("Content-Type", "")
    except urllib.error.URLError:
        return _json.dumps({"error": "Connection refused"}), 502, "application/json"
    except Exception as e:
        return _json.dumps({"error": str(e)}), 500, "application/json"


def _get_printer_data(id):
    db = get_db()
    p = db.execute("SELECT * FROM printers WHERE id = ?", (id,)).fetchone()
    db.close()
    if p:
        return dict(p)
    return None


@printers_bp.route("/printers/<int:id>/klipper")
def klipper_control(id):
    printer = _get_printer_data(id)
    if not printer:
        return render_template("error.html", code=404, message="Printer not found", lang=request.lang), 404
    return render_template("printer_klipper.html", printer=printer, lang=request.lang)


@printers_bp.route("/printers/<int:id>/klipper/proxy/<path:moonraker_path>", methods=["GET", "POST", "DELETE"])
def klipper_proxy(id, moonraker_path):
    printer = _get_printer_data(id)
    if not printer or not printer.get("ip_address"):
        return jsonify({"error": "Printer not found or no IP address"}), 404

    ip = printer["ip_address"]
    port = int(printer.get("moonraker_port", 7125))
    api_key = printer.get("moonraker_api_key", "") or ""

    method = request.method
    body = None
    ct = "application/json"
    if method in ("POST", "DELETE"):
        if request.is_json:
            body = _json.dumps(request.get_json())
        elif request.form:
            body = "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in request.form.items())
            ct = "application/x-www-form-urlencoded"
        else:
            body = request.get_data(as_text=True)

    raw, status, resp_ct = _proxy_request(ip, port, method, moonraker_path, body, ct, api_key)

    if resp_ct.startswith("application/json"):
        try:
            data = _json.loads(raw)
            return jsonify(data), status
        except (_json.JSONDecodeError, ValueError):
            pass
    return Response(raw, status=status, content_type=resp_ct)


@printers_bp.route("/printers/<int:id>/klipper/filament-calc")
def klipper_filament_calc(id):
    """Return auto-calculated filament usage from Klipper's print_stats."""
    printer = _get_printer_data(id)
    if not printer or not printer.get("ip_address"):
        return jsonify({"ok": False, "error": "No printer/IP"}), 404

    ip = printer["ip_address"]
    port = int(printer.get("moonraker_port", 7125))
    api_key = printer.get("moonraker_api_key", "") or ""
    diameter = float(printer.get("filament_diameter", 1.75))
    density = FILAMENT_DENSITY_DEFAULT

    raw, status, ct = _proxy_request(ip, port, "GET", "printer/objects/query?print_stats", api_key=api_key)
    if status != 200:
        return jsonify({"ok": False, "error": f"Moonraker error {status}"}), status

    try:
        data = _json.loads(raw)
        ps = data.get("result", {}).get("status", {}).get("print_stats", {})
        filament_mm = ps.get("filament_used", 0)
        filename = ps.get("filename", "")
        state = ps.get("state", "standby")
        print_duration = ps.get("print_duration", 0)

        # mm to grams: V = π * (d/2)² * L, m = V * density / 1000 (mm³ to cm³)
        radius_mm = diameter / 2.0
        area_mm2 = math.pi * radius_mm * radius_mm
        volume_mm3 = area_mm2 * filament_mm
        volume_cm3 = volume_mm3 / 1000.0
        mass_g = volume_cm3 * density

        return jsonify({
            "ok": True,
            "filament_mm": filament_mm,
            "filament_m": round(filament_mm / 1000, 2),
            "filament_g": round(mass_g, 2),
            "diameter": diameter,
            "density": density,
            "filename": filename,
            "state": state,
            "print_duration": print_duration,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@printers_bp.route("/printers/<int:id>/klipper/bed-mesh")
def klipper_bed_mesh(id):
    """Fetch bed mesh data from Moonraker."""
    printer = _get_printer_data(id)
    if not printer or not printer.get("ip_address"):
        return jsonify({"ok": False, "error": "No printer/IP"}), 404

    ip = printer["ip_address"]
    port = int(printer.get("moonraker_port", 7125))
    api_key = printer.get("moonraker_api_key", "") or ""

    raw, status, ct = _proxy_request(ip, port, "GET", "printer/objects/query?bed_mesh", api_key=api_key)
    if status != 200:
        return jsonify({"ok": False, "error": f"Moonraker error {status}"}), status

    try:
        data = _json.loads(raw)
        bm = data.get("result", {}).get("status", {}).get("bed_mesh", {})
        return jsonify({"ok": True, "bed_mesh": bm})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@printers_bp.route("/printers/<int:id>/klipper/filaments")
def klipper_filaments_list(id):
    """List filaments bound to this printer or unbound."""
    db = get_db()
    filaments = db.execute(
        "SELECT id, name, manufacturer, filament_type, color, color_hex, remaining_g, spool_weight_g, printer_id FROM filaments WHERE printer_id IS NULL OR printer_id = ? ORDER BY name",
        (id,)
    ).fetchall()
    db.close()
    return jsonify({"ok": True, "filaments": [dict(f) for f in filaments]})


@printers_bp.route("/printers/<int:id>/klipper/set-filament", methods=["POST"])
def klipper_set_filament(id):
    """Set the active filament for this printer."""
    filament_id = request.get_json().get("filament_id")
    db = get_db()
    db.execute("UPDATE printers SET active_filament_id = ? WHERE id = ?", (filament_id, id))
    db.commit()
    db.close()
    return jsonify({"ok": True})


@printers_bp.route("/printers/<int:id>/klipper/deduct-filament", methods=["POST"])
def klipper_deduct_filament(id):
    """Deduct filament weight from the active spool."""
    printer = _get_printer_data(id)
    if not printer:
        return jsonify({"ok": False, "error": "Printer not found"}), 404

    active_id = printer.get("active_filament_id")
    if not active_id:
        return jsonify({"ok": False, "error": "No active filament set"}), 400

    body = request.get_json() or {}
    weight_g = safe_float(body.get("weight_g"), 0, 0, 10000)
    if weight_g <= 0:
        return jsonify({"ok": False, "error": "Invalid weight"}), 400

    db = get_db()
    row = db.execute("SELECT * FROM filaments WHERE id = ?", (active_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"ok": False, "error": "Filament not found"}), 404

    new_remaining = max(0, row["remaining_g"] - weight_g)
    db.execute("UPDATE filaments SET remaining_g = ? WHERE id = ?", (new_remaining, active_id))
    db.commit()
    db.close()
    return jsonify({"ok": True, "new_remaining": new_remaining, "deducted": weight_g})


@printers_bp.route("/printers/<int:id>/klipper/save-print", methods=["POST"])
def klipper_save_print(id):
    """Save a print record from Klipper with deduction."""
    printer = _get_printer_data(id)
    if not printer:
        return jsonify({"ok": False, "error": "Printer not found"}), 404

    body = request.get_json() or {}
    weight_g = safe_float(body.get("weight_g"), 0, 0, 10000)
    print_hours = safe_float(body.get("print_hours"), 0, 0, 8760)
    model_name = body.get("model_name", "Klipper Print")

    db = get_db()
    db.execute(
        "INSERT INTO calculations (printer_id, filament_id, model_name, weight_g, print_time_hours, base_rate, filament_cost, electricity_cost, depreciation_cost, other_expenses, markup_percent, markup_amount, total_cost) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (id, 1, model_name, weight_g, print_hours, 0, 0, 0, 0, 0, 0, 0, 0)
    )
    db.commit()
    db.close()
    return jsonify({"ok": True, "saved": True})


@printers_bp.route("/printers/<int:id>/klipper/macros")
def klipper_macros(id):
    """List custom macros from Moonraker (gcode_macro objects)."""
    printer = _get_printer_data(id)
    if not printer or not printer.get("ip_address"):
        return jsonify({"ok": False, "error": "No printer/IP"}), 404

    ip = printer["ip_address"]
    port = int(printer.get("moonraker_port", 7125))
    api_key = printer.get("moonraker_api_key", "") or ""

    raw, status, _ = _proxy_request(ip, port, "GET", "printer/objects/list", api_key=api_key)
    if status != 200:
        return jsonify({"ok": False, "error": f"Moonraker error {status}"}), status

    try:
        data = _json.loads(raw)
        objects = data.get("result", {}).get("objects", [])
        macros = [o.split(" ", 1)[1] for o in objects if o.startswith("gcode_macro")]
        macros.sort()
        return jsonify({"ok": True, "macros": macros})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
