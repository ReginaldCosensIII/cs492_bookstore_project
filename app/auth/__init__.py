# cs492_bookstore_project/app/auth/__init__.py
"""
This package implements the authentication blueprint for the application.

It handles user registration, login, logout, and other authentication-related
functionalities. Routes are defined in `routes.py` within this package.
The blueprint is registered with the main application in `app/__init__.py`.
"""
from flask import Blueprint

# Create the authentication blueprint instance.
# - 'auth': The name of the blueprint, used in url_for() calls (e.g., url_for('auth.login')).
# - __name__: The import name of the blueprint package, used by Flask to locate resources.
# - template_folder: Specifies the directory for templates. '../templates' points to the
#   main application's templates folder (app/templates/) relative to this blueprint package.
# - url_prefix: All routes defined in this blueprint will be prefixed with '/auth'.
auth_bp = Blueprint(
    'auth', 
    __name__,
    template_folder='../templates', 
    url_prefix='/auth'
)

# Import the routes module for this blueprint at the end to avoid circular dependencies.
# The routes module will use the 'auth_bp' object to define its routes.
from . import routes