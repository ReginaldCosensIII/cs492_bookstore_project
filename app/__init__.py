# cs492_bookstore_project/app/__init__.py
import os
from datetime import datetime
from flask_login import LoginManager
from flask import Flask, jsonify, request, render_template, flash, redirect, url_for

# Assuming config.py is at the project root (cs492_bookstore_project/)
from config import config 

# Import app-specific modules
from .logger import setup_logger, get_logger # From app/logger.py
from .models.user import load_user as app_load_user # Alias for clarity
from .services.exceptions import AppException, NotFoundError, AuthorizationError, AuthenticationError

# Initialize Flask-Login extension
login_manager = LoginManager()
login_manager.login_message_category = "warning" # Bootstrap alert category
login_manager.login_message = "Please log in to access this page or complete this action."
login_manager.login_view = 'auth.login'  # Endpoint for login page (blueprint_name.view_function_name)


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
    # Get the configured application logger instance
    # Note: Using get_logger() here is fine. If app context is not fully up during very early
    # calls (unlikely for user_loader), it has a fallback.
    logger = get_logger() 
    logger.debug(f"Flask-Login: Attempting to load user by ID: '{user_id_str}'")
    
    user = app_load_user(user_id_str) # Calls app.models.user.load_user
    
    if user:
        user_email_log = getattr(user, 'email', 'N/A') # Safely access email for logging
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
    app = Flask(__name__, instance_relative_config=False) # instance_relative_config=False if config.py is at project root

    # Load configuration from config.py based on the selected config_name
    selected_config_obj = config.get(config_name, config['default']) # Fallback to default config if name is invalid
    app.config.from_object(selected_config_obj)
    
    # Allow the loaded configuration object to perform further app-specific initializations
    if hasattr(selected_config_obj, 'init_app'): 
        selected_config_obj.init_app(app) # Calls Config.init_app(app) or its subclass's version

    # Setup Application Logger using the app's configuration.
    # app.logger will be configured by this call.
    setup_logger(app)
    logger = get_logger() # Get the app's configured logger for use within this factory
    
    logger.info(f"Flask application '{app.name}' created using '{config_name}' configuration.")
    logger.debug(f"Application Debug Mode: {app.debug}")
    logger.debug(f"Application Testing Mode: {app.testing}")
    logger.debug(f"Database URL configured: {'YES' if app.config.get('DATABASE_URL') else 'NO - CRITICAL!'}")

    if app.config.get('SECRET_KEY') == 'your_default_dev_secret_key_CHANGE_ME_IN_PROD_!' and not app.debug:
        logger.critical(
            "SECURITY ALERT: Default Flask SECRET_KEY is in use in a non-debug (potentially production) environment! "
            "This key MUST be changed for security."
        )

    # Initialize Flask extensions with the app instance
    login_manager.init_app(app)
    logger.info("Flask-Login extension initialized and configured for the application.")

    # Register Blueprints
    # Assumes each blueprint is a package (e.g., app/main/) with an __init__.py 
    # that defines its Blueprint object (e.g., main_bp) and imports its routes.
    logger.info("Registering application blueprints...")
    
    from .main import main_bp
    app.register_blueprint(main_bp) 
    logger.info(f"Registered blueprint: '{main_bp.name}' (Effective URL prefix: '{main_bp.url_prefix or '/'}')")

    from .auth import auth_bp
    app.register_blueprint(auth_bp) # url_prefix is defined in auth_bp creation
    logger.info(f"Registered blueprint: '{auth_bp.name}' (Effective URL prefix: '{auth_bp.url_prefix}')")

    from .cart import cart_bp
    app.register_blueprint(cart_bp) # url_prefix is defined in cart_bp creation
    logger.info(f"Registered blueprint: '{cart_bp.name}' (Effective URL prefix: '{cart_bp.url_prefix}')")
    
    from .reviews import reviews_api_bp # Ensure this is the name in app/reviews/__init__.py
    app.register_blueprint(reviews_api_bp) # url_prefix is defined in reviews_api_bp creation
    logger.info(f"Registered blueprint: '{reviews_api_bp.name}' (Effective URL prefix: '{reviews_api_bp.url_prefix}')")
    
    from .order import order_bp # For order confirmation, details etc.
    app.register_blueprint(order_bp) # url_prefix is defined in order_bp creation
    logger.info(f"Registered blueprint: '{order_bp.name}' (Effective URL prefix: '{order_bp.url_prefix}')")
    logger.info("All blueprints registered.")

    # Context Processors - make variables automatically available to all templates
    @app.context_processor
    def inject_common_template_variables():
        """Injects common variables (e.g., current year) into the template context."""
        return {'current_year': datetime.utcnow().year}
    logger.debug("Registered 'inject_common_template_variables' context processor.")

    # ----- Global Error Handlers -----
    # These handlers catch specified exceptions application-wide and provide consistent responses.
    # They distinguish between AJAX (JSON) requests and regular browser requests.

    @app.errorhandler(AppException)
    def handle_app_exception(error: AppException):
        """Handles custom application exceptions derived from AppException."""
        logger.error(
            f"AppException caught: '{error.log_message}' (Status: {error.status_code}) for URL {request.url}", 
            exc_info=error.original_exception # Log original exception if available
        )

        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            response = jsonify(error.to_dict())
            response.status_code = error.status_code
            return response
        
        error_template_name = f'errors/{error.status_code}.html'

        try:
            return render_template(error_template_name, 
                                   error=error, 
                                   error_message=error.user_facing_message, 
                                   errors_dict=error.errors, 
                                   debug_mode=app.debug), error.status_code
        
        except Exception as template_error: 
            logger.error(f"Error rendering specific error template '{error_template_name}': {template_error}", exc_info=True)
            return render_template('errors/general_error.html', 
                                   error=error, 
                                   error_message=error.user_facing_message, 
                                   debug_mode=app.debug), error.status_code

    # Standard HTTP error handlers
    @app.errorhandler(400) 
    def handle_400_bad_request(werkzeug_error): 
        """Handles HTTP 400 Bad Request errors (e.g., malformed request syntax)."""
        user_msg = getattr(werkzeug_error, 'description', "The server could not understand the request due to invalid syntax.")
        logger.warning(f"400 Bad Request: {user_msg} for URL {request.url}", exc_info=True if app.debug else False)

        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": "Bad Request", "message": user_msg}), 400
        
        return render_template('errors/400.html', error_message=user_msg, error=werkzeug_error, debug_mode=app.debug), 400

    @app.errorhandler(401) 
    def handle_401_unauthorized(werkzeug_error): 
        """Handles HTTP 401 Unauthorized errors (authentication required)."""
        user_msg = getattr(werkzeug_error, 'description', "Authentication is required to access this resource.")
        logger.warning(f"401 Unauthorized: {user_msg} for URL {request.url}")

        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": "Unauthorized", "message": "Authentication required."}), 401
        
        flash(login_manager.login_message or "You must be logged in to access this page.", 
              login_manager.login_message_category or "warning")
        
        return redirect(url_for(login_manager.login_view, next=request.full_path))

    @app.errorhandler(403)
    def handle_403_forbidden(werkzeug_error):
        """Handles HTTP 403 Forbidden errors (authenticated user lacks permission)."""
        user_msg = getattr(werkzeug_error, 'description', "You do not have the necessary permissions to access this resource.")
        logger.warning(f"403 Forbidden: {user_msg} for URL {request.url}")

        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": "Forbidden", "message": user_msg}), 403
        
        return render_template('errors/403.html', error_message=user_msg, error=werkzeug_error, debug_mode=app.debug), 403

    @app.errorhandler(404)
    def handle_404_not_found(werkzeug_error):
        """Handles HTTP 404 Not Found errors (URL does not match any route)."""

        user_msg = getattr(werkzeug_error, 'description', "The requested resource was not found on this server.")
        logger.warning(f"404 Not Found: URL {request.url}. Description: {user_msg}")

        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": "Not Found", "message": user_msg}), 404
        
        return render_template('errors/404.html', error_message=user_msg, error=werkzeug_error, debug_mode=app.debug), 404

    @app.errorhandler(500) 
    def handle_500_internal_server_error(internal_error): # Parameter 'internal_error' is the actual exception instance
        """Handles HTTP 500 Internal Server Errors from unhandled exceptions in application code."""

        user_msg="An unexpected internal server error occurred. We are looking into it and apologize for the inconvenience."
        logger.error(f"500 Internal Server Error: Unhandled exception on URL {request.url}", exc_info=internal_error) 

        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": "Internal Server Error", "message": user_msg}), 500
        
        return render_template('errors/500.html', error_message=user_msg, error=internal_error, debug_mode=app.debug), 500
        
    @app.route('/health')
    def health_check():
        """Simple health check endpoint, useful for deployment monitoring (e.g., Render health checks)."""
        
        logger.debug("Health check endpoint '/health' accessed.")
        return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}), 200

    return app