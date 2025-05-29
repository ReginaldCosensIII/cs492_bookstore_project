# cs492_bookstore_project/app/services/__init__.py
"""
This package contains the service layer for the Bookstore application.

The service layer is responsible for encapsulating the business logic and data
manipulation operations of the application. It acts as an intermediary between
the route handlers (controllers) in the blueprint packages and the data models
defined in `app.models`. This separation of concerns helps to keep the route
handlers thin and focused on HTTP request/response handling, while the models
remain focused on data representation and basic persistence.

Each module within this package typically corresponds to a major entity or
functional area of the application, such as authentication (`auth_service.py`),
book management (`book_service.py`), order processing (`order_service.py`), 
user registration (`reg_service.py`), and review handling (`review_service.py`). 
Service functions often coordinate operations across multiple models or implement 
complex business rules, including transaction management where necessary.
"""

# By default, this __init__.py file makes the 'services' directory a Python package.
# Other modules can then import specific services or functions using, for example:
# from app.services.book_service import get_all_books
# from app.services.auth_service import authenticate_user

# If you wanted to make certain functions or entire service modules directly
# available when importing `from app.services import ...`, you could expose them here.
# For example:
#
# from .auth_service import authenticate_user
# from .book_service import get_all_books, get_book_by_id
# from .order_service import create_order_from_cart, get_orders_by_user, get_order_details
# from .reg_service import register_user, validate_registration_data
# from .user_service import (
#    admin_get_all_users, admin_get_user_by_id, 
#    admin_disable_user, admin_enable_user,
#    admin_create_user, admin_update_user_details # Add new functions
# )
#
# And then define __all__ if you intend for `from app.services import *` to work predictably:
# __all__ = [
#     # ... other existing service functions ...
#     'admin_get_all_users', 'admin_get_user_by_id',
#     'admin_disable_user', 'admin_enable_user',
# ]
#
# However, explicit imports from the specific service modules (e.g., 
# `from app.services.book_service import get_all_books`) are generally preferred
# for better clarity and to avoid polluting the package's namespace.