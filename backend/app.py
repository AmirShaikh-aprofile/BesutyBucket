# backend/app.py
from flask import Flask, request, jsonify, send_file
import sqlite3, os, openpyxl, logging

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

DB = "/var/www/beautybucket/backend/beautybucket.db"
UPLOAD_FOLDER = "/var/www/beautybucket/backend/static/images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)
    # products table may already exist; ensure columns exist via migrations instead
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
            image_url TEXT,
            -- new fields default to NULL for compatibility
            our_purchase_price REAL,
            discount_we_got_percent REAL,
            selling_price_1 REAL,
            selling_price_5 REAL,
            discount_percent_1 REAL,
            discount_percent_5 REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

def row_to_product(r):
    return {
        "id": r[0], "name": r[1], "category": r[2], "details": r[3],
        "mrp": r[4], "purchase_price": r[5], "discount_1": r[6],
        "discount_5": r[7], "stock": r[8], "image_url": r[9],
        "our_purchase_price": r[10] if len(r) > 10 else None,
        "discount_we_got_percent": r[11] if len(r) > 11 else None,
        "selling_price_1": r[12] if len(r) > 12 else None,
        "selling_price_5": r[13] if len(r) > 13 else None,
        "discount_percent_1": r[14] if len(r) > 14 else None,
        "discount_percent_5": r[15] if len(r) > 15 else None
    }

@app.get("/api/products")
def get_products():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    rows = c.fetchall()
    conn.close()
    products = [row_to_product(r) for r in rows]
    return jsonify(products)

@app.get("/api/product/<int:id>")
def get_single_product(id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id = ?", (id,))
    r = c.fetchone()
    conn.close()
    if not r:
        return {"error": "Product not found"}, 404
    return row_to_product(r)

@app.route("/api/add-product", methods=["POST"])
def add_product_admin():
    try:
        name = request.form.get("name")
        category = request.form.get("category")
        details = request.form.get("details")
        mrp = float(request.form.get("mrp", 0))
        # accept both old 'purchase' and new 'our_purchase_price'
        our_purchase = request.form.get("our_purchase_price") or request.form.get("purchase") or 0
        our_purchase = float(our_purchase)
        discount1 = float(request.form.get("discount1", 0))
        discount5 = float(request.form.get("discount5", 0))
        stock = int(request.form.get("stock", 0))

        selling_price_1 = request.form.get("selling_price_1")
        selling_price_5 = request.form.get("selling_price_5")
        selling_price_1 = float(selling_price_1) if selling_price_1 not in (None, '') else (mrp - discount1)
        selling_price_5 = float(selling_price_5) if selling_price_5 not in (None, '') else (mrp - discount5)

        # compute percents server side
        discount_we_got_percent = ((mrp - our_purchase)/mrp)*100 if mrp>0 else 0
        discount_percent_1 = ((mrp - selling_price_1)/mrp)*100 if mrp>0 else 0
        discount_percent_5 = ((mrp - selling_price_5)/mrp)*100 if mrp>0 else 0

        image_file = request.files.get("image")
        image_name = ""
        if image_file:
            image_name = image_file.filename
            image_file.save(os.path.join(UPLOAD_FOLDER, image_name))

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("""
            INSERT INTO products
            (name, category, details, mrp, purchase_price, discount_1, discount_5, stock, image_url,
             our_purchase_price, discount_we_got_percent, selling_price_1, selling_price_5,
             discount_percent_1, discount_percent_5)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, category, details, mrp, our_purchase, discount1, discount5, stock, image_name,
              our_purchase, discount_we_got_percent, selling_price_1, selling_price_5,
              discount_percent_1, discount_percent_5))
        conn.commit()
        conn.close()
        return {"message": "Product added successfully!"}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/api/update-product/<int:id>", methods=["POST"])
def update_product(id):
    try:
        name = request.form.get("name")
        category = request.form.get("category")
        details = request.form.get("details")
        mrp = float(request.form.get("mrp", 0))
        our_purchase = request.form.get("our_purchase_price") or request.form.get("purchase") or 0
        our_purchase = float(our_purchase)
        discount1 = float(request.form.get("discount1", 0))
        discount5 = float(request.form.get("discount5", 0))
        stock = int(request.form.get("stock", 0))

        selling_price_1 = request.form.get("selling_price_1")
        selling_price_5 = request.form.get("selling_price_5")
        selling_price_1 = float(selling_price_1) if selling_price_1 not in (None, '') else (mrp - discount1)
        selling_price_5 = float(selling_price_5) if selling_price_5 not in (None, '') else (mrp - discount5)

        discount_we_got_percent = ((mrp - our_purchase)/mrp)*100 if mrp>0 else 0
        discount_percent_1 = ((mrp - selling_price_1)/mrp)*100 if mrp>0 else 0
        discount_percent_5 = ((mrp - selling_price_5)/mrp)*100 if mrp>0 else 0

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        image_file = request.files.get("image")
        if image_file:
            image_name = image_file.filename
            image_file.save(os.path.join(UPLOAD_FOLDER, image_name))
            c.execute("""
                UPDATE products
                SET name=?, category=?, details=?, mrp=?, purchase_price=?, discount_1=?, discount_5=?, stock=?, image_url=?,
                    our_purchase_price=?, discount_we_got_percent=?, selling_price_1=?, selling_price_5=?, discount_percent_1=?, discount_percent_5=?
                WHERE id=?
            """, (name, category, details, mrp, our_purchase, discount1, discount5, stock, image_name,
                  our_purchase, discount_we_got_percent, selling_price_1, selling_price_5,
                  discount_percent_1, discount_percent_5, id))
        else:
            c.execute("""
                UPDATE products
                SET name=?, category=?, details=?, mrp=?, purchase_price=?, discount_1=?, discount_5=?, stock=?,
                    our_purchase_price=?, discount_we_got_percent=?, selling_price_1=?, selling_price_5=?, discount_percent_1=?, discount_percent_5=?
                WHERE id=?
            """, (name, category, details, mrp, our_purchase, discount1, discount5, stock,
                  our_purchase, discount_we_got_percent, selling_price_1, selling_price_5,
                  discount_percent_1, discount_percent_5, id))

        conn.commit()
        conn.close()
        return {"message": "Product updated successfully!"}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/api/add-category", methods=["POST"])
def add_category():
    try:
        name = request.form.get("name")
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
        return {"message": "Category added successfully!"}
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/api/categories")
def get_categories():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM categories")
    rows = c.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "name": r[1]} for r in rows])

@app.get("/api/category/<cat>")
def products_by_category(cat):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE category = ?", (cat,))
    rows = c.fetchall()
    conn.close()
    return jsonify([row_to_product(r) for r in rows])

@app.get("/export")
def export():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    rows = c.fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ID","Name","Category","Details","MRP","Purchase","Discount1","Discount5","Stock","Image","OurPurchase","DiscGot%","Sell1","Sell5","Disc1%","Disc5%"])
    for r in rows:
        ws.append(r)
    file_path = "/var/www/beautybucket/backend/products.xlsx"
    wb.save(file_path)
    return send_file(file_path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

