from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from database import get_db
from translations import t as _t

clients_bp = Blueprint("clients", __name__)


@clients_bp.route("/clients")
def clients():
    db = get_db()
    client_list = db.execute("SELECT * FROM clients ORDER BY name").fetchall()
    db.close()
    return render_template("clients.html", clients=client_list, lang=request.lang)


@clients_bp.route("/clients/add", methods=["POST"])
def add_client():
    db = get_db()
    db.execute(
        "INSERT INTO clients (name, contact, phone, email, notes) VALUES (?, ?, ?, ?, ?)",
        (request.form["name"], request.form.get("contact", ""), request.form.get("phone", ""), request.form.get("email", ""), request.form.get("notes", ""))
    )
    db.commit()
    db.close()
    return redirect(url_for(".clients"))


@clients_bp.route("/clients/<int:id>/edit", methods=["POST"])
def edit_client(id):
    db = get_db()
    db.execute(
        "UPDATE clients SET name=?, contact=?, phone=?, email=?, notes=? WHERE id=?",
        (request.form["name"], request.form.get("contact", ""), request.form.get("phone", ""), request.form.get("email", ""), request.form.get("notes", ""), id)
    )
    db.commit()
    db.close()
    return redirect(url_for(".clients"))


@clients_bp.route("/clients/<int:id>/delete", methods=["POST"])
def delete_client(id):
    db = get_db()
    db.execute("DELETE FROM clients WHERE id = ?", (id,))
    db.commit()
    db.close()
    return jsonify({"ok": True})


@clients_bp.route("/clients/api/list")
def api_clients():
    db = get_db()
    rows = db.execute("SELECT id, name, phone, email FROM clients ORDER BY name").fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])
