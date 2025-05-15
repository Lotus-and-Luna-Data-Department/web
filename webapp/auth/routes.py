# dash/auth/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from webapp.db_helpers import get_db_connection
from webapp.auth.models import User

auth_bp = Blueprint("auth", __name__, template_folder="templates")

# ---------- register --------------------------------------------------
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        if not username.lower().endswith("@lotusandluna.com"):
            flash("You must use your @lotusandluna.com email address.", "warning")
            return redirect(url_for("auth.register"))

        if not password:
            flash("Password is required.", "warning")
            return redirect(url_for("auth.register"))

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, password_hash, role) "
                "VALUES (%s, %s, 'user')",
                (username, generate_password_hash(password))
            )
            conn.commit()
            flash(
                "You have successfully registered. "
                "Please chat, email, or yell at Matt to be approved.",
                "success"
            )
            return redirect(url_for("auth.login"))
        except Exception as e:
            flash(f"Error: {e}", "danger")
        finally:
            cur.close()
            conn.close()

    return render_template("register.html")

# ---------- login -----------------------------------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, password_hash, role, approved "
            "FROM users WHERE username = %s",
            (username,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row or not check_password_hash(row[2], password):
            flash("Invalid credentials.", "danger")
        elif row[3] != "admin" and not row[4]:
            flash("Your account is pending approval.", "warning")
        else:
            login_user(User(row[0], row[1], row[2], row[3]))
            return redirect(url_for("dashboard.dashboard"))

    return render_template("login.html")

# ---------- logout ----------------------------------------------------
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))
