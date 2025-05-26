# app/models/__init__.py
"""
This package contains the data models for the Bookstore application.

Models are typically Python classes that represent database tables or data structures
used throughout the application. They might include methods for data manipulation,
validation, or conversion.
"""

# For easier imports from other parts of the application,
# you can expose your primary model classes here.
from .user import User, load_user # load_user is essential for Flask-Login
from .book import Book
from .review import Review
from .order import Order
from .order_item import OrderItem

# The following (Admin, Customer, Employee) are currently stubs.
# They will be fully utilized or refined as role-specific functionalities are built out.
# For now, the User model with its 'role' attribute is the primary way to differentiate users.
# from .admin import Admin
# from .customer import Customer
# from .employee import Employee

# __all__ defines the public interface of this package when using 'from app.models import *'
# It's good practice to explicitly list what is intended to be exported.
__all__ = [
    'User', 'load_user',
    'Book',
    'Review',
    'Order',
    'OrderItem',
    # 'Admin', 'Customer', 'Employee' # Commented out until they have distinct functionality
]