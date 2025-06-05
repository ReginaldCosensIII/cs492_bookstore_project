# cs492_bookstore_project/app/utils.py

import re
from typing import Dict, List                                           # Added List for type hinting
from flask import current_app                                           # For accessing app.logger and mail instance
from flask_mail import Message                                          # For creating email messages
from app.logger import get_logger                                       # Your custom logger
from app.models.db import get_db_connection                             # For database interaction
from app.services.exceptions import DatabaseError                       # For error handling
from markupsafe import escape as markupsafe_escape 

logger = get_logger(__name__) # Logger for this module

DEFAULT_LOWERCASE_FIELDS = {'email', 'username'}

def sanitize_html_text(text_input):
    """
    Sanitizes a single string input by stripping whitespace and then escaping HTML characters.
    """
    if not isinstance(text_input, str):
        return text_input
    return markupsafe_escape(text_input.strip())


def sanitize_form_field_value(value, key_name=None, lowercase_fields_set=None, should_escape_html=True): # CHANGED HERE
    """
    Sanitizes a single form field value.
    - Strips whitespace if it's a string.
    - Converts to lowercase if it's a string and key_name is in lowercase_fields_set.
    - HTML-escapes the string if should_escape_html is True.
    """
    if lowercase_fields_set is None:
        lowercase_fields_set = DEFAULT_LOWERCASE_FIELDS

    if isinstance(value, str):
        processed_value = value.strip()
        if key_name and key_name in lowercase_fields_set:
            processed_value = processed_value.lower()
        
        if should_escape_html: # CHANGED HERE
            processed_value = markupsafe_escape(processed_value)
        return processed_value
    return value


def sanitize_form_data(form_data_dict, lowercase_fields_set=None, escape_html_fields=None):
    """
    Sanitizes string values within a dictionary (typically from flat form data).
    """
    if not isinstance(form_data_dict, dict):
        return form_data_dict 

    if lowercase_fields_set is None:
        lowercase_fields_set = DEFAULT_LOWERCASE_FIELDS
    if escape_html_fields is None:
        escape_html_fields = set() 
    
    sanitized_data = {}
    for key, value in form_data_dict.items():
        should_escape = key in escape_html_fields
        sanitized_data[key] = sanitize_form_field_value(
            value, 
            key_name=key, 
            lowercase_fields_set=lowercase_fields_set, 
            should_escape_html=should_escape # This call is now correct
        )
    return sanitized_data

def normalize_whitespace(text):
    """
    Normalizes all whitespace in a string.
    """
    if not isinstance(text, str):
        return text
    normalized_text = re.sub(r'\s+', ' ', text)
    return normalized_text.strip()

def get_admin_emails_dict() -> Dict[int, str]:
    """
    Retrieves a dictionary of all admin users' email addresses from the database.

    The role comparison is case-insensitive (e.g., 'admin', 'Admin', 'ADMIN').
    The emails are returned as stored in the database (typically lowercase).

    Returns:
        Dict[int, str]: A dictionary where keys are user_ids (int) and values 
                        are email addresses (str) of admin users.
                        Returns an empty dictionary if no admins are found or in case of an error.
    
    Raises:
        DatabaseError: Propagates DatabaseError if a significant database issue occurs
                       that prevents query execution or connection.
    """
    logger.info("Attempting to fetch email addresses for all admin users.")
    admin_emails: Dict[int, str] = {}
    conn = None
    try:
        conn = get_db_connection()
        # Assumes your db.get_db_connection() uses RealDictCursor or similar
        # to get results as dictionaries.
        with conn.cursor() as cur:
            # Query for users with the role 'admin' (case-insensitive)
            # It's good practice to ensure 'role' is stored consistently (e.g., all lowercase)
            # or use LOWER() in the query if case might vary.
            cur.execute("SELECT user_id, email FROM users WHERE LOWER(role) = 'admin';")
            admin_users_rows = cur.fetchall() # Returns a list of dict-like rows

            if admin_users_rows:
                for row in admin_users_rows:
                    user_id = row.get('user_id')
                    email = row.get('email')
                    if user_id is not None and email is not None:
                        admin_emails[user_id] = email
                logger.info(f"Successfully fetched {len(admin_emails)} admin email addresses.")
            else:
                logger.info("No users with role 'admin' found in the database.")
        
        return admin_emails

    except DatabaseError as de: # Catch specific DatabaseError if raised by get_db_connection or cursor execution
        logger.error(f"A known database error occurred while fetching admin emails: {de.log_message}", exc_info=True)
        raise # Re-raise the specific DatabaseError to be handled by the caller
    except Exception as e:
        # Catch any other unexpected errors (e.g., psycopg2.Error if not wrapped, programming errors)
        logger.error(f"An unexpected error occurred while fetching admin emails: {e}", exc_info=True)
        # Wrap other exceptions in a custom DatabaseError for consistent error handling upstream.
        raise DatabaseError(
            message="Could not retrieve admin email addresses due to an unexpected server issue.",
            original_exception=e
        )
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed after fetching admin emails.")