from flask import Blueprint, render_template, url_for, redirect, abort, flash
from flask_login import login_required, current_user
from webapp.db_helpers import get_db_connection

dash_bp = Blueprint("dashboard", __name__, template_folder="templates")

@dash_bp.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))
    return render_template("home.html")

@dash_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        is_admin=current_user.is_admin()
    )

@dash_bp.route("/prefect")
@login_required
def prefect_ui():
    if not current_user.is_admin():
        return "Access denied", 403
    return redirect("/prefect")

@dash_bp.route("/ar_reporting")
@login_required
def ar_reporting():
    return render_template("ar_reporting.html")

# ——— Admin only: pending list & approve ———

@dash_bp.route("/admin/pending")
@login_required
def pending_users():
    if not current_user.is_admin():
        abort(403)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username FROM users "
        "WHERE approved = FALSE AND role != 'admin'"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    pendings = [{"id": r[0], "username": r[1]} for r in rows]
    return render_template("pending_users.html", pendings=pendings)

@dash_bp.route("/admin/approve/<int:user_id>")
@login_required
def approve_user(user_id):
    if not current_user.is_admin():
        abort(403)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET approved = TRUE WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("User approved!", "success")
    return redirect(url_for("dashboard.pending_users"))
