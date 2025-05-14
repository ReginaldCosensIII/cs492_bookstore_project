# app/main/routes.py
from flask_login import login_required, current_user
from app.services.book_service import get_all_books
from flask import Blueprint, session, redirect, url_for, render_template

main_bp = Blueprint('main', __name__)  # Updated to match the expected name

@main_bp.route('/')
def home():
    books = get_all_books()
    return render_template('home.html', books=books)

@main_bp.route('/customer')
@login_required
def customer():
    print("Current user in customer dashboard:", current_user)
    if current_user.is_authenticated:
        print("User first name:", current_user.first_name)
    else:
        print("No authenticated user.")
        
    books = get_all_books()
    return render_template('customer.html', books=books)

@main_bp.route('/admin')
@login_required
def admin():
    return render_template('admin.html')

@main_bp.route('/employee')
@login_required
def employee():
    return render_template('employee.html')
