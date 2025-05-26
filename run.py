# run.py

import os
from app import create_app # Imports the application factory from app/__init__.py

# Determine the configuration name from the FLASK_CONFIG environment variable.
# This allows switching between 'development', 'production', 'testing' configurations
# by setting the environment variable before running the application.
# It defaults to 'development' if FLASK_CONFIG is not set.
config_name = os.environ.get('FLASK_CONFIG', 'development').lower()

# Create the Flask app instance using the factory pattern and the selected configuration.
app = create_app(config_name)

if __name__ == '__main__':
    # This block executes only when the script is run directly (e.g., `python run.py`),
    # not when it's imported as a module (e.g., by a WSGI server like Gunicorn).

    # Debug mode is controlled by the configuration object loaded into the app 
    # (e.g., DevelopmentConfig.DEBUG = True).
    # Host and port can also be driven by config or environment variables for flexibility.
    
    # For Render.com, Gunicorn will typically handle host/port based on its own config or PORT env var.
    # For local development using `python run.py`:
    host = os.environ.get("FLASK_RUN_HOST", "0.0.0.0") # Use 0.0.0.0 to be accessible on network for local dev
    port = int(os.environ.get("FLASK_RUN_PORT", 5000))   # Default to port 5000 for local dev
    
    # The application logger (app.logger) is already configured by setup_logger within create_app.
    # Log startup information using the configured application logger.
    app.logger.info(f"Attempting to start Flask development server on http://{host}:{port}")
    app.logger.info(f"Application Name: {app.name}") 
    app.logger.info(f"Environment: {app.config.get('ENV')}") 
    app.logger.info(f"Debug Mode: {app.debug}")
    
    # app.run() is suitable for development. It includes a built-in Werkzeug server.
    # For production deployments, use a production-ready WSGI server like Gunicorn.
    # The debug=app.debug argument ensures that the debug mode from the loaded config 
    # is used by the Flask development server, enabling features like the interactive 
    # debugger and auto-reloader.
    try:
        app.run(host=host, port=port, debug=app.debug)
    except Exception as e:
        app.logger.critical(f"Failed to start Flask development server: {e}", exc_info=True)
        # Optionally, re-raise or exit if startup fails critically
        # raise