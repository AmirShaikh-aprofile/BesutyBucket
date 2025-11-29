from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
DB_PATH = '/var/www/beautybucket/backend/beautybucket.db'
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------- CATEGORIES --------------------
@app.route('/api/categories', methods=['GET'])
def get_categories():
    conn = get_db_connection()
    cats = conn.execute('SELECT * FROM categories').fetchall()
    conn.close()
    return jsonify([dict(c) for c in cats])

@app.route('/api/category/<string:name>', methods=['GET'])
def get_category_products(name):
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products WHERE category=?', (name,)).fetchall()
    conn.close()
    return jsonify([dict(p) for p in products])

# -------------------- PRODUCTS --------------------
@app.route('/api/products', methods=['GET'])
def get_products():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return jsonify([dict(p) for p in products])

@app.route('/api/product/<int:id>', methods=['GET'])
def get_product(id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id=?', (id,)).fetchone()
    conn.close()
    return jsonify(dict(product))

@app.route('/api/add-product', methods=['POST'])
def add_product():
    try:
        name = request.form['name']
        category = request.form['category']
        details = request.form.get('details', '')
        mrp = float(request.form.get('mrp', 0))
        purchase_price = float(request.form.get('purchase', 0))
        selling_price_1pc = float(request.form.get('selling_price_1pc', 0))
        selling_price_5pc = float(request.form.get('selling_price_5pc', 0))
        stock = int(request.form.get('stock', 0))

        # Calculate discount % for MRP
        discount_mrp_percent = round(((mrp - purchase_price) / mrp) * 100, 2) if mrp else 0
        # Calculate discount % for selling prices
        discount_1pc_percent = round(((mrp - selling_price_1pc) / mrp) * 100, 2) if mrp else 0
        discount_5pc_percent = round(((mrp - selling_price_5pc) / mrp) * 100, 2) if mrp else 0

        # Image upload
        image_file = request.files.get('image')
        if image_file:
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = 'Pic.jpg'

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO products 
            (name, category, details, mrp, purchase_price, discount_mrp_percent, 
             selling_price_1pc, selling_price_5pc, discount_1pc_percent, discount_5pc_percent, stock, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, category, details, mrp, purchase_price, discount_mrp_percent,
              selling_price_1pc, selling_price_5pc, discount_1pc_percent, discount_5pc_percent, stock, filename))
        conn.commit()
        conn.close()
        return jsonify({"message": "Product added successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/update-product/<int:id>', methods=['POST'])
def update_product(id):
    try:
        name = request.form['name']
        category = request.form['category']
        details = request.form.get('details', '')
        mrp = float(request.form.get('mrp', 0))
        purchase_price = float(request.form.get('purchase', 0))
        selling_price_1pc = float(request.form.get('selling_price_1pc', 0))
        selling_price_5pc = float(request.form.get('selling_price_5pc', 0))
        stock = int(request.form.get('stock', 0))

        discount_mrp_percent = round(((mrp - purchase_price) / mrp) * 100, 2) if mrp else 0
        discount_1pc_percent = round(((mrp - selling_price_1pc) / mrp) * 100, 2) if mrp else 0
        discount_5pc_percent = round(((mrp - selling_price_5pc) / mrp) * 100, 2) if mrp else 0

        image_file = request.files.get('image')
        conn = get_db_connection()
        if image_file:
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.execute('''
                UPDATE products SET name=?, category=?, details=?, mrp=?, purchase_price=?, 
                discount_mrp_percent=?, selling_price_1pc=?, selling_price_5pc=?, 
                discount_1pc_percent=?, discount_5pc_percent=?, stock=?, image_url=?
                WHERE id=?
            ''', (name, category, details, mrp, purchase_price, discount_mrp_percent,
                  selling_price_1pc, selling_price_5pc, discount_1pc_percent, discount_5pc_percent, stock, filename, id))
        else:
            conn.execute('''
                UPDATE products SET name=?, category=?, details=?, mrp=?, purchase_price=?, 
                discount_mrp_percent=?, selling_price_1pc=?, selling_price_5pc=?, 
                discount_1pc_percent=?, discount_5pc_percent=?, stock=?
                WHERE id=?
            ''', (name, category, details, mrp, purchase_price, discount_mrp_percent,
                  selling_price_1pc, selling_price_5pc, discount_1pc_percent, discount_5pc_percent, stock, id))
        conn.commit()
        conn.close()
        return jsonify({"message": "Product updated successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)})

# -------------------- IMAGE SERVE --------------------
@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

