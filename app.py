from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import os, uuid, csv, datetime, json

# ---------- Google Sheets ----------
import gspread
from google.oauth2.service_account import Credentials

def _gclient():
    # ต้องมี GOOGLE_CREDENTIALS และ SHEET_ID ใน Environment (Render)
    creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def _ws(name):
    gc = _gclient()
    sh = gc.open_by_key(os.environ["SHEET_ID"])
    try:
        return sh.worksheet(name)
    except gspread.WorksheetNotFound:
        return sh.add_worksheet(title=name, rows=1000, cols=20)

def load_products():
    ws = _ws("products")
    rows = ws.get_all_records()  # list of dicts
    products = []
    for r in rows:
        products.append({
            "id": r.get("id",""),
            "name": r.get("name",""),
            "price": float(r.get("price") or 0),
            "category": r.get("category","อื่นๆ"),
            "image": r.get("image",""),
            "active": str(r.get("active","TRUE")).upper() in ("TRUE","1","YES")
        })
    return products

def save_products(items):
    ws = _ws("products")
    ws.clear()
    header = ["id","name","price","category","image","active"]
    ws.append_row(header)
    for p in items:
        ws.append_row([
            p["id"], p["name"], float(p["price"]),
            p.get("category","อื่นๆ"), p.get("image",""),
            bool(p.get("active", True))
        ])

def append_order(order_row):
    ws = _ws("orders")
    if not ws.acell("A1").value:
        ws.append_row(["order_id","datetime","items(json)","subtotal","discount","total","payment"])
    ws.append_row(order_row)

# ---------- Flask App ----------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key")

# ---------------------- PAGES ----------------------
@app.route("/")
def pos():
    products = load_products()
    categories = sorted(set(p.get("category","อื่นๆ") for p in products))
    return render_template("pos.html", products=products, categories=categories)

@app.route("/checkout", methods=["POST"])
def checkout():
    data = request.get_json(force=True)
    order_id = str(uuid.uuid4())[:8]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    items = data.get("items", [])
    subtotal = sum(i["price"]*i["qty"] for i in items)
    discount = float(data.get("discount", 0) or 0)
    total = max(subtotal - discount, 0)
    payment = data.get("payment", "CASH")
    append_order([order_id, now, json.dumps(items, ensure_ascii=False), subtotal, discount, total, payment])
    return jsonify({"ok": True, "order_id": order_id, "total": total})

@app.route("/backoffice")
def backoffice():
    # ตัวอย่าง: รวมยอดวันนี้จากชีต orders
    total_today = 0.0
    today = datetime.date.today().strftime("%Y-%m-%d")
    try:
        ws = _ws("orders")
        rows = ws.get_all_records()
        for r in rows:
            dt = str(r.get("datetime",""))
            if dt.startswith(today):
                total_today += float(r.get("total") or 0)
    except Exception:
        pass
    return render_template("backoffice.html", total_today=total_today)

# ----------------- PRODUCTS CRUD ------------------
@app.route("/products")
def products_page():
    return render_template("products.html", products=load_products())

@app.route("/products/create", methods=["POST"])
def product_create():
    items = load_products()
    new_item = {
        "id": str(uuid.uuid4())[:8],
        "name": request.form["name"].strip(),
        "price": float(request.form.get("price", 0) or 0),
        "category": request.form.get("category","อื่นๆ").strip(),
        "image": request.form.get("image","").strip(),
        "active": True
    }
    items.append(new_item)
    save_products(items)
    flash("เพิ่มสินค้าเรียบร้อย")
    return redirect(url_for("products_page"))

@app.route("/products/<pid>/toggle", methods=["POST"])
def product_toggle(pid):
    items = load_products()
    for p in items:
        if p["id"] == pid:
            p["active"] = not p.get("active", True)
            break
    save_products(items)
    return redirect(url_for("products_page"))

@app.route("/products/<pid>/update", methods=["POST"])
def product_update(pid):
    items = load_products()
    for p in items:
        if p["id"] == pid:
            p["name"] = request.form["name"].strip()
            p["price"] = float(request.form.get("price", 0) or 0)
            p["category"] = request.form.get("category","อื่นๆ").strip()
            p["image"] = request.form.get("image","").strip()
            break
    save_products(items)
    flash("อัปเดตสินค้าแล้ว")
    return redirect(url_for("products_page"))

@app.route("/products/<pid>/delete", methods=["POST"])
def product_delete(pid):
    items = [p for p in load_products() if p["id"] != pid]
    save_products(items)
    flash("ลบสินค้าแล้ว")
    return redirect(url_for("products_page"))

# ------------- Render-friendly run ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
