# cs492_bookstore_project/app/order/__init__.py
"""
This package implements the order management blueprint for the application.

It handles routes related to viewing order confirmations and order details.
Order creation logic is typically initiated from the cart blueprint but results
in redirection to routes within this order blueprint.
Routes are defined in `routes.py`.
The blueprint is registered with the main application in `app/__init__.py`.
"""
from flask import Blueprint

# Create the order blueprint instance.
# - 'order': Name of the blueprint.
# - template_folder: Points to the main app/templates/ directory.
# - url_prefix: All order-related routes will be prefixed with '/orders'.
order_bp = Blueprint(
    'order', 
    __name__,
    template_folder='../templates',
    url_prefix='/orders' # Using '/orders' as per your provided file
)

from . import routes # Import routes after blueprint object is defined