# app/logger.py

import os
import sys
import logging 
from flask import current_app
from logging.handlers import RotatingFileHandler # For file logging

_MAIN_APP_LOGGER_NAME = 'bookstore_project_app' # Default name, updated by setup_logger

def setup_logger(app):
    """
    Configures the primary logger for the Flask application (app.logger).
    Sets logging level, format, and handlers (console and file).
    Removes pre-existing handlers to avoid duplication.

    Args:
        app (Flask): The Flask application instance.
    """

    log_level_str = app.config.get('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    for handler in list(app.logger.handlers):
        app.logger.removeHandler(handler)
    
    for log_filter_item in list(app.logger.filters): # Renamed variable
        app.logger.removeFilter(log_filter_item)

    app.logger.setLevel(log_level)

    # Formatter for both console and file
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s:%(module)s.%(funcName)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    app.logger.addHandler(console_handler)

    # File Handler - Ensure instance folder exists
    # Logs will go to a file like 'instance/app.log'
    # The 'instance' folder is a good place for logs that are instance-specific and not part of version control.
    # You might need to add 'instance/' to your .gitignore.
    if not app.config.get('TESTING'): # Don't create log files during testing by default
        log_dir = os.path.join(app.instance_path, 'logs') # Using instance_path for logs
        
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)

            except OSError as e:
                app.logger.error(f"Could not create log directory {log_dir}: {e}", exc_info=True)
        
        if os.path.exists(log_dir):
            log_file_path = os.path.join(log_dir, 'app.log')
            # RotatingFileHandler allows log files to not grow indefinitely
            file_handler = RotatingFileHandler(
                log_file_path, 
                maxBytes=1024 * 1024 * 5,  # 5 MB per file
                backupCount=5              # Keep 5 backup files
            )

            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            app.logger.addHandler(file_handler)
            app.logger.info(f"File logging enabled. Log file: {log_file_path}")

        else:
            app.logger.warning(f"File logging disabled as log directory could not be created: {log_dir}")


    app.logger.propagate = False 
    
    global _MAIN_APP_LOGGER_NAME
    _MAIN_APP_LOGGER_NAME = app.logger.name 

    app.logger.info(f"Application logger '{_MAIN_APP_LOGGER_NAME}' configured. Level: {log_level_str}.")

    if log_level <= logging.DEBUG:
        app.logger.debug("Debug level logging is enabled for the application.")


def get_logger(name: str = None) -> logging.Logger:
    """
    Retrieves a logger instance.
    If 'name' is None, it returns the current Flask app's configured logger.
    If 'name' is provided, it returns a logger with that specific name, usually
    as a child of the main application logger if named hierarchically (e.g., app_name.module).

    Args:
        name (str, optional): The name of the logger. If None, defaults to the main app logger.

    Returns:
        logging.Logger: The logger instance.
    """

    if name is None:
        if current_app and hasattr(current_app, 'logger'):
            return current_app.logger
        
        return logging.getLogger(_MAIN_APP_LOGGER_NAME) 
    
    # If using hierarchical logging:
    # base_logger_name = _MAIN_APP_LOGGER_NAME
    # if current_app and hasattr(current_app, 'logger'):
    #     base_logger_name = current_app.logger.name
    # return logging.getLogger(f"{base_logger_name}.{name.replace('app.', '')}") # Example of hierarchical naming
    return logging.getLogger(name) # Standard way, will inherit if root logger (app.logger) is parent