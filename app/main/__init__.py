# cs492_bookstore_project/app/main/__init__.py
"""
This package implements the main blueprint for the application.

It typically handles core application routes such as the home page, 
customer dashboard, user profile, and potentially administrative or
employee dashboards if not separated into their own blueprints.
Routes are defined in `routes.py`.
The blueprint is registered with the main application in `app/__init__.py`.
"""
from flask import Blueprint

# Create the main blueprint instance.
# - 'main': Name of the blueprint.
# - template_folder: Points to the main app/templates/ directory.
# - No url_prefix is set, so routes in this blueprint will be at the application root
#   (e.g., '/', '/profile') unless specified otherwise in the route definition itself.
main_bp = Blueprint(
    'main', 
    __name__,
    template_folder='../templates'
)

from . import routes # Import routes after blueprint object is defined