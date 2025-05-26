# cs492_bookstore_project/app/reviews/__init__.py
"""
This package implements the reviews API blueprint for the application.

It handles API endpoints for fetching, submitting, updating, and deleting
book reviews. These endpoints are typically consumed by client-side JavaScript
to provide dynamic review functionality.
Routes are defined in `routes.py`.
The blueprint is registered with the main application in `app/__init__.py`.
"""
from flask import Blueprint

# Create the reviews API blueprint instance.
# - 'reviews_api': Name of the blueprint, distinguishing it as an API.
# - template_folder: Set for consistency, though API blueprints usually don't render templates directly.
# - url_prefix: All review API routes will be prefixed with '/api'.
reviews_api_bp = Blueprint(
    'reviews_api', 
    __name__,
    template_folder='../templates', # Consistent, though less critical for pure API blueprints
    url_prefix='/api'
)

from . import routes # Import routes after blueprint object is defined