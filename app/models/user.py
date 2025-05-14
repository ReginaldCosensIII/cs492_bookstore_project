# app/models/user.py

from flask_login import UserMixin, current_user
from app.db_setup import get_db_connection

class User(UserMixin):
    def __init__(self, user_id, email, phone_number, password, created_at,
                 first_name, last_name, address_line1, address_line2,
                 city, state, zip_code, role):
        self.id = user_id
        self.email = email
        self.phone_number = phone_number
        self.password_hash = password
        self.created_at = created_at
        self.first_name = first_name
        self.last_name = last_name
        self.address_line1 = address_line1
        self.address_line2 = address_line2
        self.city = city
        self.state = state
        self.zip_code = zip_code
        self.role = role

    def get_id(self):
        return str(self.id)

# This function will be registered with Flask-Login
def load_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
    SELECT user_id, email, phone_number, password, created_at,
           first_name, last_name, address_line1, address_line2,
           city, state, zip_code, role
    FROM users
    WHERE user_id = %s
""", (user_id,))
    user = cur.fetchone()
    conn.close()
    if user:
        print("Loaded user:", user)
        return User(**user)
    return None
