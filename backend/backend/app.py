# /var/www/beautybucket/backend/app.py
from flask import Flask, request, jsonify, send_file, send_from_directory, abort
import sqlite3
import os
import openpyxl
import logging
from werkzeug.utils import secure_filename
from flask_cors import CORS

# --- Config ---
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
CORS(app)  # allow same-origin and external dev calls

DB = "/var/www/beautybucket/backend/beautybucket.db"
UPLOAD_FOLDER = "/var/www/beautybucket/backend/static/images"
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_conn():
    return sqlite3.connect(DB)

# --- DB init ---
def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT,
            details TEXT,
            mrp REAL,
            purchase_price REAL,
            discount_1 REAL,
            discount_5 REAL,
            stock INTEGER,
            image_url TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Helpers ---
def row_to_product(r):
    return {
        "id": r[0], "name": r[1], "category": r[2], "details": r[3],
        "mrp": r[4], "purchase_price": r[5], "discount_1": r[6],
        "discount_5": r[7], "stock": r[8], "image_url": r[9]
    }

def allowed_file(filename):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXT

# --- Routes ---
@app.get("/")
def root():
    return "BeautyBucket Backend Running"

@app.get("/api/health")
def api_health():
    logging.info("GET /api/health")
    return jsonify({"status": "ok"})

@app.get("/api/categories")
def get_categories():
    logging.info("GET /api/categories")
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, name FROM categories ORDER BY name")
    rows = c.fetchall()
    conn.close()
    categories = [{"id": r[0], "name": r[1]} for r in rows]
    return jsonify(categories)

@app.route("/api/add-category", methods=["POST"])
def add_category():
    try:
        name = (request.form.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Category name required"}), 400
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
        logging.info("Added category: %s", name)
        return jsonify({"message": "Category added"})
    except Exception as e:
        logging.exception("add-category error")
        return jsonify({"error": str(e)}), 500

@app.get("/api/products")
def get_products():
    logging.info("GET /api/products")
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM products ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return jsonify([row_to_product(r) for r in rows])

@app.get("/api/product/<int:pid>")
def get_product(pid):
    logging.info("GET /api/product/%d", pid)
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id = ?", (pid,))
    r = c.fetchone()
    conn.close()
    if not r:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(row_to_product(r))

@app.get("/api/category/<string:cat>")
def products_by_category(cat):
    logging.info("GET /api/category/%s", cat)
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE category = ?", (cat,))
    rows = c.fetchall()
    conn.close()
    return jsonify([row_to_product(r) for r in rows])

def save_image(fileobj):
    filename = secure_filename(fileobj.filename)
    if not allowed_file(filename):
        return None
    dest = os.path.join(UPLOAD_FOLDER, filename)
    fileobj.save(dest)
    return filename

@app.route("/api/add-product", methods=["POST"])
def add_product():
    try:
        name = (request.form.get("name") or "").strip()
        category = (request.form.get("category") or "").strip()
        details = (request.form.get("details") or "").strip()
        mrp = float(request.form.get("mrp") or 0)
        purchase = float(request.form.get("purchase") or 0)
        discount1 = float(request.form.get("discount1") or 0)
        discount5 = float(request.form.get("discount5") or 0)
        stock = int(request.form.get("stock") or 0)

        image_file = request.files.get("image")
        image_name = ""
        if image_file and image_file.filename:
            saved = save_image(image_file)
            if not saved:
                return jsonify({"error": "Invalid image file type"}), 400
            image_name = saved

        conn = get_conn()
        c = conn.cursor()
        c.execute("""
            INSERT INTO products
            (name, category, details, mrp, purchase_price, discount_1, discount_5, stock, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, category, details, mrp, purchase, discount1, discount5, stock, image_name))
        conn.commit()
        conn.close()
        logging.info("Added product: %s (%s)", name, category)
        return jsonify({"message": "Product added"})
    except Exception as e:
        logging.exception("add-product error")
        return jsonify({"error": str(e)}), 500

@app.route("/api/update-product/<int:pid>", methods=["POST"])
def update_product(pid):
    try:
        name = (request.form.get("name") or "").strip()
        category = (request.form.get("category") or "").strip()
        details = (request.form.get("details") or "").strip()
        mrp = float(request.form.get("mrp") or 0)
        purchase = float(request.form.get("purchase") or 0)
        discount1 = float(request.form.get("discount1") or 0)
        discount5 = float(request.form.get("discount5") or 0)
        stock = int(request.form.get("stock") or 0)

        image_file = request.files.get("image")
        image_name = None
        if image_file and image_file.filename:
            saved = save_image(image_file)
            if not saved:
                return jsonify({"error": "Invalid image file type"}), 400
            image_name = saved

        conn = get_conn()
        c = conn.cursor()
        if image_name:
            c.execute("""
                UPDATE products
                SET name=?, category=?, details=?, mrp=?, purchase_price=?, discount_1=?, discount_5=?, stock=?, image_url=?
                WHERE id=?
            """, (name, category, details, mrp, purchase, discount1, discount5, stock, image_name, pid))
        else:
            c.execute("""
                UPDATE products
                SET name=?, category=?, details=?, mrp=?, purchase_price=?, discount_1=?, discount_5=?, stock=?
                WHERE id=?
            """, (name, category, details, mrp, purchase, discount1, discount5, stock, pid))
        conn.commit()
        conn.close()
        logging.info("Updated product %d", pid)
        return jsonify({"message": "Product updated"})
    except Exception as e:
        logging.exception("update-product error")
        return jsonify({"error": str(e)}), 500

@app.get("/export")
def export_products():
    logging.info("GET /export")
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    rows = c.fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ID", "Name", "Category", "Details", "MRP", "Purchase", "Discount1", "Discount5", "Stock", "Image"])
    for r in rows:
        ws.append(r)
    file_path = "/var/www/beautybucket/backend/products.xlsx"
    wb.save(file_path)
    return send_file(file_path, as_attachment=True)

# Optional: serve images via Flask if needed (Nginx also serves them)
@app.get("/images/<path:filename>")
def serve_image(filename):
    safe = secure_filename(filename)
    filepath = os.path.join(UPLOAD_FOLDER, safe)
    if not os.path.exists(filepath):
        abort(404)
    return send_from_directory(UPLOAD_FOLDER, safe)

if __name__ == "__main__":
    # for manual testing only
    app.run(host="0.0.0.0", port=5000, debug=False)

