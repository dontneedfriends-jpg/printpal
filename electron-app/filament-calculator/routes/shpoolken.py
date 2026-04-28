from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from database import get_db, init_shpoolken_db, is_shpoolken_loaded, get_shpoolken_filaments, get_shpoolken_manufacturers, get_shpoolken_materials, get_shpoolken_stats, insert_shpoolken_filaments
from utils import safe_float
from translations import t as _t
import json
import urllib.request
import logging

logger = logging.getLogger(__name__)
shpoolken_bp = Blueprint("shpoolken", __name__)

SHPOLKEN_GITHUB = "https://raw.githubusercontent.com/dontneedfriends-jpg/ShpoolkenDB/main/filaments"


def check_internet():
    try:
        req = urllib.request.Request("https://api.github.com/")
        req.add_header("User-Agent", "Mozilla/5.0")
        urllib.request.urlopen(req, timeout=5)
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return False


@shpoolken_bp.route("/shpoolken")
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


@shpoolken_bp.route("/shpoolken/sync", methods=["POST"])
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
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to download {f['name']}: {e}")
        
        insert_shpoolken_filaments(filaments_data)
        
        return jsonify({
            "success": True,
            "stats": get_shpoolken_stats()
        })
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError, ValueError) as e:
        logger.error(f"Shpoolken sync error: {e}")
        return jsonify({"success": False, "error": str(e)})


@shpoolken_bp.route("/shpoolken/search")
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


@shpoolken_bp.route("/shpoolken/add", methods=["POST"])
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
    quantity = max(1, min(100, int(request.form.get("quantity", 1))))
    
    full_name = name
    if color and color not in name:
        full_name = f"{full_name} {color}"
    
    for i in range(quantity):
        suffix = f" #{i+1}" if quantity > 1 else ""
        db.execute("""
            INSERT INTO filaments (manufacturer, name, filament_type, color, color_hex, spool_weight_g, spool_price, remaining_g, density, diameter)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (manufacturer, full_name + suffix, material, color, color_hex, weight, spool_price, weight, density or 0, diameter or 1.75))
    
    db.commit()
    db.close()
    
    flash(_t(request.lang, "shpoolken_added") + (f" x{quantity}" if quantity > 1 else ""), "success")
    return redirect(url_for("filaments.filaments"))


@shpoolken_bp.route("/shpoolken/bulk_add", methods=["POST"])
def shpoolken_bulk_add():
    ids = request.form.get("bulk_ids", "").split(",")
    
    if not ids or not ids[0]:
        return redirect(url_for(".shpoolken"))
    
    db = get_db()
    added = 0
    
    for fid in ids:
        f = db.execute("SELECT * FROM filaments WHERE id = ?", (fid,)).fetchone()
        if not f:
            continue
        
        price_key = "price_" + fid
        spool_price = safe_float(request.form.get(price_key))
        qty_key = "qty_" + fid
        quantity = max(1, min(100, int(request.form.get(qty_key, 1))))
        
        manufacturer = f["manufacturer"] or ""
        name = f["name"] or ""
        material = f["material"] or ""
        color = f["color"] or ""
        color_hex = f["color_hex"] or ""
        density = f["density"] or 0
        diameter = f["diameter"] or 1.75
        weight = f["weight"] or 1000
        
        full_name = name
        if color and color not in name:
            full_name = f"{full_name} {color}"
        
        for i in range(quantity):
            suffix = f" #{i+1}" if quantity > 1 else ""
            db.execute("""
                INSERT INTO filaments (manufacturer, name, filament_type, color, color_hex, spool_weight_g, spool_price, remaining_g, density, diameter)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (manufacturer, full_name + suffix, material, color, color_hex, weight, spool_price, weight, density or 0, diameter or 1.75))
            added += 1
    
    db.commit()
    db.close()
    
    flash(f"{_t(request.lang, 'imported_count')} {added}", "success")
    return redirect(url_for("filaments.filaments"))
