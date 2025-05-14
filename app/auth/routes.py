# app/auth/routes.py

from datetime import datetime
from app.models.user import User
from app.db_setup import get_db_connection
from flask_login import login_required, login_user, logout_user, current_user
from flask import Blueprint, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone_number = request.form.get('phone_number')
        password = generate_password_hash(request.form['password'])
        address_line1 = request.form.get('address_line1')
        address_line2 = request.form.get('address_line2')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zip_code')
        role = request.form['role']

        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO users (
                    email, phone_number, password, first_name, last_name,
                    address_line1, address_line2, city, state, zip_code, role
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                email, phone_number, password, first_name, last_name,
                address_line1, address_line2, city, state, zip_code, role
            ))

            conn.commit()
            return redirect(url_for('auth.login'))
        except Exception as e:
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e).lower():
                return "Email already registered!"
            return f"Registration error: {e}"
        finally:
            conn.close()

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password_input = request.form['password']

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT user_id, email, phone_number, password, first_name, last_name, address_line1, address_line2, city, state, zip_code, role
            FROM users
            WHERE email = %s
        """, (email,))
        user_data = c.fetchone()
        conn.close()

        if user_data and check_password_hash(user_data["password"], password_input):
            user = User(
                user_id=user_data['user_id'],
                email=user_data['email'],
                phone_number=user_data['phone_number'],
                password=user_data['password'],
                created_at=None,
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                address_line1=user_data['address_line1'],
                address_line2=user_data['address_line2'],
                city=user_data['city'],
                state=user_data['state'],
                zip_code=user_data['zip_code'],
                role=user_data['role']
            )

            login_user(user)
            print("Logged in as:", current_user.first_name)

            if user.role == 'admin':
                return redirect(url_for('main.admin'))
            elif user.role == 'employee':
                return redirect(url_for('main.employee'))
            else:
                return redirect(url_for('main.customer'))

        return "Invalid credentials"

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.home'))
