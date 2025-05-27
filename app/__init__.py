# cs492_bookstore_project/app/__init__.py
import os
from decimal import Decimal # Not directly used here, but good if _get_cart_summary_for_context were more complex
from datetime import datetime
from flask_login import LoginManager
from flask import Flask, jsonify, request, render_template, flash, redirect, url_for, session # Added session

# Assuming config.py is at the project root (cs492_bookstore_project/)
from config import config 

# Import app-specific modules
from .logger import setup_logger, get_logger # From app/logger.py
from .models.user import load_user as app_load_user # Alias for clarity
from .services.exceptions import AppException, NotFoundError, AuthorizationError, AuthenticationError
from typing import Dict, Any # For type hinting

# Initialize Flask-Login extension
login_manager = LoginManager()
login_manager.login_message_category = "warning" # Bootstrap alert category
login_manager.login_message = "Please log in to access this page or complete this action."
login_manager.login_view = 'auth.login' # Endpoint for login page (blueprint_name.view_function_name)

def _get_cart_summary_for_context() -> Dict[str, Any]:
    """
    Retrieves a summary of the user's shopping cart from the session.
    
    This helper function calculates the total number of items (sum of quantities) 
    in the cart. It's designed to be lightweight for use in a context processor 
    that runs on every request. It assumes the cart is stored in the session as a 
    dictionary where keys are item IDs (strings) and values are quantities (integers).

    Returns:
        Dict[str, Any]: A dictionary containing:
            - "cart_item_count" (int): Total number of items (sum of quantities) in the cart.
            - Potentially "cart_total_str" (str) if full calculation were added here.
    """
    cart_session = session.get("cart", {}) # Safely get cart from session, defaulting to empty dict
    item_count = 0
    # Calculate total items by summing up the quantities of each item in the cart.
    for quantity in cart_session.values():
        if isinstance(quantity, int) and quantity > 0: # Ensure quantity is a positive integer
            item_count += quantity
        # else: Potentially log or handle non-integer/non-positive quantities if they can occur
    
    # For a more complex summary including total price, you would need to call
    # a function similar to _calculate_current_cart_total_and_items from cart/routes.py.
    # However, that involves database calls for prices and might be too heavy for every request
    # if not carefully optimized or cached. For navbar count, sum of quantities is sufficient.
    return {"cart_item_count": item_count} 


@login_manager.user_loader
def _flask_login_user_loader(user_id_str: str):
    """
    Loads a user by ID for Flask-Login session management.
    This function is registered with Flask-Login via the @login_manager.user_loader decorator.
    It's called to reload the user object from the user ID stored in the session.

    Args:
        user_id_str (str): The user ID (as a string) retrieved from the session cookie.
    
    Returns:
        User | None: The User object if found and valid, otherwise None.
    """
    logger = get_logger() 
    logger.debug(f"Flask-Login: Attempting to load user by ID: '{user_id_str}'")
    
    user = app_load_user(user_id_str) 
    
    if user:
        user_email_log = getattr(user, 'email', 'N/A') 
        logger.debug(f"Flask-Login: User '{user_id_str}' (Email: {user_email_log}) loaded successfully.")
    else:
        logger.warning(f"Flask-Login: User with ID '{user_id_str}' NOT found by app_load_user. Session may be invalid or user deleted.")
    return user

def create_app(config_name: str = 'default') -> Flask:
    """
    Application Factory Function.
    Creates, configures, and returns the Flask application instance. This pattern 
    allows for creating multiple app instances with different configurations, which is 
    beneficial for testing, multiple deployment environments, etc.

    Args:
        config_name (str): The name of the configuration to use (e.g., 'development', 
                           'production', 'testing'). Corresponds to keys in the `config` dict
                           from `config.py`. Defaults to 'default'.
    
    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__, instance_relative_config=False)

    selected_config_obj = config.get(config_name, config['default'])
    app.config.from_object(selected_config_obj)
    
    if hasattr(selected_config_obj, 'init_app'): 
        selected_config_obj.init_app(app)

    setup_logger(app)
    logger = get_logger() 
    
    logger.info(f"Flask application '{app.name}' created using '{config_name}' configuration.")
    logger.debug(f"Application Debug Mode: {app.debug}")
    logger.debug(f"Application Testing Mode: {app.testing}")
    logger.debug(f"Database URL configured: {'YES' if app.config.get('DATABASE_URL') else 'NO - CRITICAL!'}")

    # Check for default SECRET_KEY in non-debug environments
    default_secret_key_dev = 'your_default_dev_secret_key_CHANGE_ME_IN_PROD_!' # From config.py
    default_secret_key_old = 'a_very_secret_default_key_please_change_me_immediately' # Your older default
    current_secret_key = app.config.get('SECRET_KEY')

    if (current_secret_key == default_secret_key_dev or current_secret_key == default_secret_key_old) and \
       not app.debug and app.config.get("ENV") == "production": # Check ENV as well
        logger.critical(
            "SECURITY ALERT: A default Flask SECRET_KEY is in use in a production environment! "
            "This key MUST be changed for security."
        )

    login_manager.init_app(app)
    logger.info("Flask-Login extension initialized and configured for the application.")

    logger.info("Registering application blueprints...")
    from .main import main_bp
    app.register_blueprint(main_bp) 
    logger.info(f"Registered blueprint: '{main_bp.name}' (Effective URL prefix: '{main_bp.url_prefix or '/'}')")
    from .auth import auth_bp
    app.register_blueprint(auth_bp)
    logger.info(f"Registered blueprint: '{auth_bp.name}' (Effective URL prefix: '{auth_bp.url_prefix}')")
    from .cart import cart_bp
    app.register_blueprint(cart_bp)
    logger.info(f"Registered blueprint: '{cart_bp.name}' (Effective URL prefix: '{cart_bp.url_prefix}')")
    from .reviews import reviews_api_bp 
    app.register_blueprint(reviews_api_bp)
    logger.info(f"Registered blueprint: '{reviews_api_bp.name}' (Effective URL prefix: '{reviews_api_bp.url_prefix}')")
    from .order import order_bp 
    app.register_blueprint(order_bp)
    logger.info(f"Registered blueprint: '{order_bp.name}' (Effective URL prefix: '{order_bp.url_prefix}')")
    logger.info("All blueprints registered.")

    # Context Processors - make variables automatically available to all templates
    @app.context_processor
    def inject_common_template_variables(): # Merged the two context processors
        """
        Injects common variables into the template context for all rendered templates.
        This includes the current year (for footer copyright) and a summary of the
        user's shopping cart (item count for the navbar badge).

        Returns:
            dict: A dictionary containing:
                - 'current_year' (int): The current UTC year.
                - 'navbar_cart_item_count' (int): Total number of items in the user's cart.
        """
        cart_summary = _get_cart_summary_for_context() # Call the helper
        common_vars = {
            'current_year': datetime.utcnow().year,
            'navbar_cart_item_count': cart_summary.get('cart_item_count', 0)
            # If you decide to pass cart total string as well:
            # 'navbar_cart_total_str': cart_summary.get('cart_total_str', "0.00")
        }
        logger.debug(f"Context processor injecting: {common_vars}")
        return common_vars
    
    logger.debug("Registered 'inject_common_template_variables' context processor (with current_year and cart summary).")
    
    # ----- Global Error Handlers (from response #79) -----
    @app.errorhandler(AppException)
    def handle_app_exception(error: AppException):
        logger.error(f"AppException caught: '{error.log_message}' (Status: {error.status_code}) for URL {request.url}", exc_info=error.original_exception)
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            response = jsonify(error.to_dict()); response.status_code = error.status_code
            return response
        error_template_name = f'errors/{error.status_code}.html'
        try:
            return render_template(error_template_name, error=error, error_message=error.user_facing_message, errors_dict=error.errors, debug_mode=app.debug), error.status_code
        except: 
            return render_template('errors/general_error.html', error=error, error_message=error.user_facing_message, debug_mode=app.debug), error.status_code

    @app.errorhandler(400) 
    def handle_400_bad_request(werkzeug_error): 
        user_msg = getattr(werkzeug_error, 'description', "Bad request.")
        logger.warning(f"400 Bad Request: {user_msg} for URL {request.url}", exc_info=app.debug)
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": "Bad Request", "message": user_msg}), 400
        return render_template('errors/400.html', error_message=user_msg, error=werkzeug_error, debug_mode=app.debug), 400

    @app.errorhandler(401) 
    def handle_401_unauthorized(werkzeug_error): 
        user_msg = getattr(werkzeug_error, 'description', "Authentication required.")
        logger.warning(f"401 Unauthorized: {user_msg} for URL {request.url}")
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": "Unauthorized", "message": "Authentication required."}), 401
        flash(login_manager.login_message or "Please log in.", login_manager.login_message_category or "warning")
        return redirect(url_for(login_manager.login_view, next=request.full_path))

    @app.errorhandler(403)
    def handle_403_forbidden(werkzeug_error):
        user_msg = getattr(werkzeug_error, 'description', "Access forbidden.")
        logger.warning(f"403 Forbidden: {user_msg} for URL {request.url}")
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": "Forbidden", "message": user_msg}), 403
        return render_template('errors/403.html', error_message=user_msg, error=werkzeug_error, debug_mode=app.debug), 403

    @app.errorhandler(404)
    def handle_404_not_found(werkzeug_error):
        user_msg = getattr(werkzeug_error, 'description', "Resource not found.")
        logger.warning(f"404 Not Found: URL {request.url}. Description: {user_msg}")
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": "Not Found", "message": user_msg}), 404
        return render_template('errors/404.html', error_message=user_msg, error=werkzeug_error, debug_mode=app.debug), 404

    @app.errorhandler(500) 
    def handle_500_internal_server_error(internal_error): 
        user_msg="An unexpected internal server error occurred."
        logger.error(f"500 Internal Server Error: Unhandled exception on URL {request.url}", exc_info=internal_error) 
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": "Internal Server Error", "message": user_msg}), 500
        return render_template('errors/500.html', error_message=user_msg, error=internal_error, debug_mode=app.debug), 500
        
    @app.route('/health')
    def health_check():
        """Simple health check endpoint."""
        logger.debug(f"Health check endpoint '/health' accessed by {request.remote_addr}.")
        return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}), 200

    return app