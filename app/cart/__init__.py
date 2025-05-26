# cs492_bookstore_project/app/cart/__init__.py
"""
This package implements the shopping cart blueprint for the application.

It handles functionalities related to managing the user's shopping cart,
such as adding items, viewing the cart, updating quantities, removing items,
and proceeding to checkout. Routes are defined in `routes.py`.
The blueprint is registered with the main application in `app/__init__.py`.
"""
from flask import Blueprint

# Create the cart blueprint instance.
# - 'cart': Name of the blueprint.
# - template_folder: Points to the main app/templates/ directory.
# - url_prefix: All cart-related routes will be prefixed with '/cart'.
cart_bp = Blueprint(
    'cart', 
    __name__,
    template_folder='../templates',
    url_prefix='/cart'
)

from . import routes # Import routes after blueprint object is defined