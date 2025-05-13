import os
import time
from datetime import date
from glob import glob
from io import StringIO
from csv import DictReader, DictWriter

from flask import Flask
from flask_login import LoginManager
from werkzeug.security import generate_password_hash

from config import ProdConfig, TestConfig
from db_helpers import get_db_connection
from auth.routes import auth_bp
from dashboard.routes import dash_bp

CSV_TABLE_MAP = {
    "odoo_account_moves.csv":       "raw_odoo_account_moves",
    "odoo_listing_items.csv":       "raw_odoo_listing_items",
    "odoo_listings.csv":            "raw_odoo_listings",
    "odoo_orders.csv":              "raw_odoo_orders",
    "odoo_order_tags.csv":          "odoo_order_tags",
    "odoo_products.csv":            "raw_odoo_products",
    "odoo_sale_order_lines.csv":    "raw_odoo_order_lines",
    "odoo_stock_pickings.csv":      "raw_odoo_stock_pickings",
    "shopify_order_line_items.csv": "raw_shopify_order_lines",
    "shopify_orders.csv":           "raw_shopify_orders",
    "shopify_refund_line_items.csv":"raw_shopify_refund_lines",
    "shopify_refunds.csv":          "raw_shopify_refunds",
}

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    cfg = TestConfig if os.getenv("ENV","production") == "test" else ProdConfig
    app.config.from_object(cfg)

    login_manager = LoginManager()
    login_manager.login_view = app.config["LOGIN_VIEW"]
    login_manager.init_app(app)

    from auth.models import load_user
    login_manager.user_loader(load_user)

    # register our blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dash_bp)

    # import & register the AR‐reporting blueprint
    from dashboard.ar_reporting import ar_bp
    app.register_blueprint(ar_bp, url_prefix="/ar")

    if app.config["ENV"] == "test":
        _bootstrap_test_db(app, cfg)

    @app.context_processor
    def inject_current_year():
        return {"current_year": date.today().year}

    return app

def _bootstrap_test_db(app, cfg):
    conn = None
    for i in range(30):
        print(f"[bootstrap] Attempt {i+1}/30: connecting to DB")
        try:
            conn = get_db_connection()
            print("[bootstrap] Connected to DB")
            break
        except Exception as e:
            print(f"[bootstrap] Connection failed: {e!r}")
            time.sleep(1)
    if conn is None:
        raise RuntimeError("Could not connect to the test database after 30 tries")

    cur = conn.cursor()

    print("[bootstrap] Dropping and recreating public schema")
    cur.execute("DROP SCHEMA public CASCADE;")
    cur.execute("CREATE SCHEMA public;")
    conn.commit()

    sql_dir = os.path.join(app.root_path, "schemas")
    all_ddls = sorted(glob(f"{sql_dir}/*.sql"))
    deferred = [p for p in all_ddls if p.endswith("odoo_order_tags.sql")]
    first_pass = [p for p in all_ddls if p not in deferred]

    print(f"[bootstrap] Applying {len(first_pass)} DDL scripts")
    for path in first_pass:
        print(f"[bootstrap] Running DDL: {os.path.basename(path)}")
        with open(path) as f:
            cur.execute(f.read())

    if deferred:
        print(f"[bootstrap] Applying deferred DDL: {os.path.basename(deferred[0])}")
        with open(deferred[0]) as f:
            cur.execute(f.read())

    conn.commit()
    print("[bootstrap] DDL applied")

    print(f"[bootstrap] Loading CSVs from {os.path.join(app.root_path,'output')}")
    for fname, table in CSV_TABLE_MAP.items():
        csv_path = os.path.join(app.root_path, "output", fname)
        print(f"[bootstrap] Processing {fname} → {table}")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Missing CSV: {csv_path}")

        # fetch table columns
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=%s",
            (table,)
        )
        table_cols = {r[0] for r in cur.fetchall()}

        # fetch primary‐key columns
        cur.execute(
            "SELECT kcu.column_name FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "  ON tc.constraint_name=kcu.constraint_name "
            "WHERE tc.constraint_type='PRIMARY KEY' "
            "  AND tc.table_schema='public' AND tc.table_name=%s",
            (table,)
        )
        pk_cols = [r[0] for r in cur.fetchall()]

        # read, filter, dedupe, and buffer
        with open(csv_path, newline="") as csvfile:
            reader = DictReader(csvfile)
            cols = [c for c in reader.fieldnames if c in table_cols]
            buf = StringIO()
            writer = DictWriter(buf, fieldnames=cols, lineterminator="\n")
            writer.writeheader()
            seen = set()
            for row in reader:
                key = tuple(row[k] for k in pk_cols) if pk_cols else None
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                writer.writerow({k: row[k] for k in cols})
            buf.seek(0)

        col_list = ", ".join(cols)
        print(f"[bootstrap] COPY {table} ({col_list})")
        cur.copy_expert(f"COPY {table} ({col_list}) FROM STDIN WITH CSV HEADER", buf)
        conn.commit()
        print(f"[bootstrap] Loaded {table}")

    print("[bootstrap] Seeding test admin")
    cur.execute(
        "INSERT INTO users (username, password_hash, role, approved) "
        "VALUES (%s, %s, 'admin', TRUE)",
        (cfg.TEST_ADMIN_USERNAME, generate_password_hash(cfg.TEST_ADMIN_PASSWORD))
    )
    conn.commit()

    cur.close()
    conn.close()
    print("[bootstrap] Test DB bootstrap complete")

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000)
