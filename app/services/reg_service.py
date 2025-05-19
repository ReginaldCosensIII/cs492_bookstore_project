# app/services/reg_service.py

import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash
from app.models.user import User
import os

def register_user(form):
    try:
        password = form.get('password')
        hashed_password = generate_password_hash(password)

        with psycopg2.connect(os.getenv('DATABASE_URL'), cursor_factory=psycopg2.extras.RealDictCursor) as connection:
            with connection.cursor() as cursor:
                # Check for existing user
                cursor.execute("SELECT * FROM users WHERE email = %s", (form.get('email'),))
                if cursor.fetchone():
                    return None, "An account with this email already exists."

                # Insert new user and return all columns needed by User class
                cursor.execute("""
                    INSERT INTO users (
                        first_name, last_name, email, phone_number, password, 
                        address_line1, address_line2, city, state, zip_code, role
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING user_id, email, phone_number, password, created_at,
                              first_name, last_name, address_line1, address_line2,
                              city, state, zip_code, role
                """, (
                    form.get('first_name'),
                    form.get('last_name'),
                    form.get('email'),
                    form.get('phone_number'),
                    hashed_password,
                    form.get('address_line1'),
                    form.get('address_line2'),
                    form.get('city'),
                    form.get('state'),
                    form.get('zip_code'),
                    form.get('role', 'customer')
                ))

                user_row = cursor.fetchone()

                # Unpack and pass as positional args to User
                return User(
                    user_row['user_id'],
                    user_row['email'],
                    user_row['phone_number'],
                    user_row['password'],
                    user_row['created_at'],
                    user_row['first_name'],
                    user_row['last_name'],
                    user_row['address_line1'],
                    user_row['address_line2'],
                    user_row['city'],
                    user_row['state'],
                    user_row['zip_code'],
                    user_row['role']
                ), None

    except Exception as e:
        return None, str(e)
