from flask import Blueprint, request, render_template, jsonify
from database import get_db
from config import UPLOAD_DIR
import json
import os

history_bp = Blueprint("history", __name__)


@history_bp.route("/history")
def history():
    db = get_db()
    calc_list = db.execute("""
        SELECT c.*, p.name as printer_name, p.power_watts, f.name as filament_name, f.color as filament_color
        FROM calculations c
        JOIN printers p ON c.printer_id = p.id
        JOIN filaments f ON c.filament_id = f.id
        ORDER BY c.created_at DESC
    """).fetchall()
    db.close()
    return render_template("history.html", calculations=calc_list, lang=request.lang)


@history_bp.route("/history/<int:id>/delete", methods=["POST"])
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
            except (ValueError, TypeError, KeyError) as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to restore filament data: {e}")
        db.execute("DELETE FROM calculations WHERE id = ?", (id,))
        db.commit()
    db.close()
    return jsonify({"ok": True})


@history_bp.route("/history/export")
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

    output = __import__('io').StringIO()
    writer = __import__('csv').writer(output, delimiter=';')
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
    from flask import Response
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=printpal_history.csv"})
