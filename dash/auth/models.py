# dash/auth/models.py
from flask_login import UserMixin
from db_helpers import get_db_connection

class User(UserMixin):
    def __init__(self, id_, username, password_hash, role):
        self.id = str(id_)
        self.username = username
        self.password_hash = password_hash
        self.role = role

    def is_admin(self):
        return self.role == "admin"

def load_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, password_hash, role "
        "FROM users WHERE id = %s",
        (user_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return User(*row)
    return None
