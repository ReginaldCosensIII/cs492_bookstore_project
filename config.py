# cs492_bookstore_project/config.py
import os
import logging # Used for logging issues during config loading itself
from dotenv import load_dotenv

# Configure a basic logger for early messages from this config file.
# This helps diagnose issues if .env loading or initial config values are problematic,
# even before the main application logger is fully set up.
config_module_logger = logging.getLogger(__name__) 
# Note: This logger won't have the app's full formatting until setup_logger runs.
# For critical startup messages, print() might be more reliable if issues occur before any logging config.

# Determine the absolute path to the project root directory.
# This assumes config.py is located directly in the project root.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
# Construct the path to the .env file located in the project root.
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')

if os.path.exists(DOTENV_PATH):
    load_dotenv(DOTENV_PATH)
    # Using print here for very early feedback as logger might not be fully set.
    print(f"INFO: [config.py] Loaded environment variables from: {DOTENV_PATH}")
else:
    print(f"INFO: [config.py] .env file not found at '{DOTENV_PATH}'. "
          f"Application will rely on environment variables set directly or default values.")

class Config:
    """
    Base configuration class for the Flask application.
    
    This class defines default configuration settings and loads sensitive or
    environment-specific values from environment variables. Subclasses can
    override these settings for different environments like development,
    production, or testing.

    Attributes:
        SECRET_KEY (str): A secret key used for session management, CSRF protection,
                          and other security-related features. It's crucial that this
                          is a strong, unique, and private value, especially in production.
        DATABASE_URL (str): The connection string for the PostgreSQL database.
                            Format: "postgresql://user:password@host:port/database_name"
        LOG_LEVEL (str): The logging level for the application (e.g., 'DEBUG', 'INFO', 
                         'WARNING', 'ERROR', 'CRITICAL'). Controls verbosity of logs.
        ITEMS_PER_PAGE (int): Default number of items to display per page for features
                              that use pagination (e.g., book listings, order history).
    """
    # --- Security Sensitive Configurations ---
    # Loaded from environment variables, with a default for development (must be changed for production).
    SECRET_KEY: str = os.environ.get('FLASK_SECRET_KEY', 'a_very_secret_default_key_please_change_me_immediately_for_production_!')
    DATABASE_URL: str | None = os.environ.get('DATABASE_URL')

    # --- Application Behavior Configurations ---
    LOG_LEVEL: str = os.environ.get('LOG_LEVEL', 'INFO').upper()
    ITEMS_PER_PAGE: int = 10 

    # --- Initial Sanity Checks (performed when this module is imported) ---
    # These checks provide immediate feedback in the console if critical environment variables are missing.
    if not DATABASE_URL:
        print("CRITICAL ERROR: [config.py] DATABASE_URL environment variable is not set. "
              "The application will likely fail to connect to the database.")
    
    if SECRET_KEY == 'a_very_secret_default_key_please_change_me_immediately_for_production_!' and \
       os.environ.get('FLASK_ENV', 'development').lower() == 'production':
        print(
            "CRITICAL SECURITY WARNING: [config.py] The default FLASK_SECRET_KEY is being used "
            "in what appears to be a production environment (FLASK_ENV=production). "
            "This is highly insecure. Please set a strong, unique secret key for production "
            "in your environment variables or .env file."
        )

    # --- Email Configurations ---
    MAIL_SERVER: str = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT: int = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS: bool = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME: str | None = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD: str | None = os.environ.get('MAIL_APP_PASSWORD') # Use MAIL_APP_PASSWORD for clarity
    MAIL_DEFAULT_SENDER: str = os.environ.get('MAIL_DEFAULT_SENDER', 'your-email@gmail.com')

    # --- Initial Sanity Checks (add these) ---
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print(
            "WARNING: [config.py] MAIL_USERNAME or MAIL_APP_PASSWORD environment variables are not set. "
            "Email functionality will not work."
        )
    elif MAIL_USERNAME == 'your-email@gmail.com' and os.environ.get('FLASK_ENV', 'development').lower() == 'production':
        print(
            "CRITICAL SECURITY WARNING: [config.py] Default placeholder MAIL_USERNAME is being used "
            "in what appears to be a production environment. Please configure your actual email credentials."
        )

    @staticmethod
    def init_app(app):
        """
        Allows configurations to perform further app-specific initializations after the 
        Flask app object has been created and its `app.config` has been populated from this
        Config object. This is useful for checks or setups that require access to `app.logger`.

        Args:
            app (Flask): The Flask application instance.
        """
        # Use the app's configured logger, which should be set up by app/logger.py by this point.
        app_logger = app.logger 
        
        if not app.config.get('DATABASE_URL'):
            app_logger.critical("DATABASE_URL is not set in app.config during init_app. Database functionality will fail.")
        
        if app.config.get('SECRET_KEY') == 'a_very_secret_default_key_please_change_me_immediately_for_production_!' and \
           app.config.get("ENV") == "production": # FLASK_ENV is mapped to app.config['ENV'] by Flask
             app_logger.critical(
                 "FLASK_SECRET_KEY is using the default development value in a production environment "
                 "(app.config['ENV'] == 'production') during init_app. This is highly insecure!"
            )
                          
        if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
            app_logger.warning(
                "MAIL_USERNAME or MAIL_APP_PASSWORD not set in app.config during init_app. "
                "Email functionality will be disabled."
            )

        elif app.config.get('MAIL_USERNAME') == 'your-email@gmail.com' and app.config.get("ENV") == "production":
            app_logger.critical(
                "Default placeholder MAIL_USERNAME is being used in production. Email configuration is insecure."
            )

        app_logger.debug("Config.init_app() completed its initializations (including mail config checks).")

class DevelopmentConfig(Config):
    """
    Configuration settings specifically tailored for the development environment.
    Inherits from the base `Config` class and overrides settings as needed for development.
    
    Attributes:
        DEBUG (bool): Enables Flask's debug mode, providing helpful error pages and auto-reloading.
        FLASK_ENV (str): Explicitly sets the environment type for Flask.
        LOG_LEVEL (str): Sets a more verbose logging level (DEBUG) for development.
    """
    DEBUG: bool = True
    FLASK_ENV: str = 'development' 
    LOG_LEVEL: str = os.environ.get('LOG_LEVEL_DEV', 'DEBUG').upper() # More verbose logging for dev


class ProductionConfig(Config):
    """
    Configuration settings specifically tailored for the production environment.
    Inherits from the base `Config` class, prioritizing security and performance.
    
    Attributes:
        DEBUG (bool): Disables Flask's debug mode for production.
        FLASK_ENV (str): Explicitly sets the environment type for Flask.
        LOG_LEVEL (str): Sets a less verbose logging level (INFO) for production.
    """
    DEBUG: bool = False
    FLASK_ENV: str = 'production'
    LOG_LEVEL: str = os.environ.get('LOG_LEVEL_PROD', 'INFO').upper()
    
    # Example: Production-specific security settings for session cookies.
    # These should be enabled if your application is served over HTTPS in production.
    # SESSION_COOKIE_SECURE: bool = True       # Ensures session cookies are only sent over HTTPS.
    # REMEMBER_COOKIE_SECURE: bool = True      # Ensures "remember me" cookies are only sent over HTTPS.
    # SESSION_COOKIE_HTTPONLY: bool = True   # Prevents client-side JavaScript from accessing the session cookie.
    # REMEMBER_COOKIE_HTTPONLY: bool = True  # Prevents client-side JavaScript from accessing the remember_me cookie.
    # SESSION_COOKIE_SAMESITE: str = 'Lax'   # Provides some protection against CSRF attacks for session cookie.
    
    # SERVER_NAME = os.environ.get('SERVER_NAME') # e.g., 'yourbookstore.com'. 
                                                # Useful for URL generation outside of a request context, if needed.


class TestingConfig(Config):
    """
    Configuration settings specifically tailored for the testing environment.
    Inherits from the base `Config` class.
    
    Attributes:
        TESTING (bool): Enables Flask's testing mode, which alters behavior of error handlers
                        and can be used by extensions.
        DEBUG (bool): Often set to True during test development for more detailed error output.
        FLASK_ENV (str): Explicitly sets the environment type.
        DATABASE_URL (str): Should point to a separate test database to avoid data conflicts.
        SECRET_KEY (str): Uses a distinct secret key for testing.
        LOG_LEVEL (str): Can be set to DEBUG for test output or WARNING to reduce noise.
    """
    TESTING: bool = True
    DEBUG: bool = True 
    FLASK_ENV: str = 'testing'
    
    # Use a separate database for testing if possible.
    # Ensure TEST_DATABASE_URL is set in your .env or testing environment.
    DATABASE_URL: str | None = os.environ.get('TEST_DATABASE_URL') or Config.DATABASE_URL # Fallback to main DB_URL
    SECRET_KEY: str = 'a_dedicated_secret_key_for_testing_only_not_for_prod_use'
    LOG_LEVEL: str = 'DEBUG' 
    
    # Example: If using Flask-WTF for forms, CSRF protection is often disabled for programmatic tests.
    # WTF_CSRF_ENABLED: bool = False 


# Dictionary to map configuration names to their respective classes.
# This allows the application factory to select the correct configuration based on an environment variable.
config: dict[str, type[Config]] = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig # Configuration to use if FLASK_CONFIG environment variable is not set or invalid.
}