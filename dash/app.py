import os
import psycopg2
from flask import Flask, request, render_template_string, redirect, url_for
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

# Instantiate Flask
app = Flask(__name__)

# 1) Secret key from .env
secret_key = os.getenv("APP_SECRET_KEY")
if not secret_key:
    raise ValueError("APP_SECRET_KEY not set in environment.")
app.secret_key = secret_key

# 2) Database environment variables from .env
DB_HOST = os.getenv("DB_HOST_PROD")
DB_NAME = os.getenv("DB_NAME_PROD")
DB_USER = os.getenv("DB_USER_PROD")
DB_PASSWORD = os.getenv("DB_PASSWORD_PROD")
DB_PORT = os.getenv("DB_PORT_PROD")

# 3) Optional checks
if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT]):
    # It's fine to raise an error if you're sure these must exist
    print("Warning: One or more DB environment variables are missing. The app might fail on DB calls.")

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Simple user model
class User(UserMixin):
    def __init__(self, id_, username, password_hash, role):
        self.id = str(id_)
        self.username = username
        self.password_hash = password_hash
        self.role = role

    def is_admin(self):
        return self.role == "admin"

# DB Helpers
def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )

def get_user_by_username(username):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, password_hash, role FROM users WHERE username = %s",
                (username,)
            )
            row = cur.fetchone()
            if row:
                return User(*row)  # (id, username, password_hash, role)
            return None
    finally:
        conn.close()

def get_user_by_id(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, password_hash, role FROM users WHERE id = %s",
                (user_id,)
            )
            row = cur.fetchone()
            if row:
                return User(*row)
            return None
    finally:
        conn.close()

# Flask-Login hook
@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)

#####################
# ROUTES
#####################

# Health endpoint for Docker's healthcheck
@app.route("/health")
def health():
    return "OK", 200

@app.route("/")
def home():
    if current_user.is_authenticated:
        return f"""
        <h1>Welcome, {current_user.username}!</h1>
        <p>Your role: {current_user.role}</p>
        <p><a href="{url_for('dashboard')}">Go to Dashboard</a></p>
        <p><a href="{url_for('logout')}">Logout</a></p>
        """
    else:
        return """
        <h1>Welcome to the Lotus & Luna Landing Page</h1>
        <p>Please <a href="/login">login</a> to view dashboards or Prefect UI.</p>
        """

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = get_user_by_username(username)
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("home"))
        else:
            return "Invalid credentials", 401

    return render_template_string("""
    <h1>Login</h1>
    <form method="POST">
        Username: <input name="username" type="text"><br/>
        Password: <input name="password" type="password"><br/>
        <button type="submit">Login</button>
    </form>
    """)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return "You have been logged out. <a href='/'>Return Home</a>"

@app.route("/dashboard")
@login_required
def dashboard():
    links = []
    links.append("<a href='https://app.powerbi.com/home'>Power BI</a>")
    if current_user.is_admin():
        links.append("<a href='/prefect'>Prefect UI</a> (Admin only)")

    html_links = "<br/>".join(links)
    return f"""
    <h1>Dashboard</h1>
    <p>Hello, {current_user.username}! Here are your available links:</p>
    {html_links}
    <p><a href="/">Home</a></p>
    """

@app.route("/prefect")
@login_required
def prefect_redirect():
    if not current_user.is_admin():
        return "Access denied", 403
    return """
    <h1>Prefect UI</h1>
    <p>This would route you to the real Prefect UI at /prefect, or do a redirect.</p>
    """

@app.route("/genpass/<plaintext>")
def genpass(plaintext):
    hashed = generate_password_hash(plaintext)
    return f"Hashed password: {hashed}"

# Actually run the app on 0.0.0.0:8000
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
