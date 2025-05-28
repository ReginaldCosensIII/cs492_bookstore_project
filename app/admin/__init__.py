# app/admin/__init__.py

"""
This package implements the Admin blueprint for the application.

It handles routes and functionalities specific to administrators, such as
user management, book inventory management, order overview, and potentially
site configuration or analytics in the future. Access to these routes is
typically restricted to users with an 'admin' role.
"""
from flask import Blueprint

# Create the Admin blueprint instance.
# - 'admin': The name of the blueprint, used in url_for() calls (e.g., url_for('admin.dashboard')).
# - __name__: The import name of the blueprint package.
# - template_folder: Specifies that admin-specific templates will be located in an 'admin'
#   subdirectory within the main application's templates folder (i.e., 'app/templates/admin/').
# - url_prefix: All routes defined in this blueprint will be prefixed with '/admin'.
admin_bp = Blueprint(
    'admin', 
    __name__,
    template_folder='admin', # Relative to the main app's template folder (app/templates)
    url_prefix='/admin'
)

# Import the routes module for this blueprint at the end to avoid circular dependencies.
# The routes module will use the 'admin_bp' object to define its routes.
from . import routes