# app/services/auth_service.py

from typing import Optional                                             # For type hinting
from app.models.user import User                                        # User model for creating User objects
from app.logger import get_logger                                       # Custom application logger
from app.models.db import get_db_connection                             # For database connections
from werkzeug.security import check_password_hash                       # For verifying passwords
from app.services.exceptions import AuthenticationError, DatabaseError  # Custom exceptions

# Logger instance for this module, configured by app/logger.py
logger = get_logger(__name__) 

def authenticate_user(email: str, password_input: str) -> Optional[User]:
    """
    Authenticates a user based on their provided email and password.

    This function queries the 'users' table for a user matching the given email.
    If a user is found, it verifies the provided password against the stored
    password hash using `werkzeug.security.check_password_hash`.
    The email input is expected to have been normalized (e.g., stripped of 
    whitespace, lowercased) by the calling route handler before this service
    function is invoked.

    Args:
        email (str): The email address of the user attempting to log in.
        password_input (str): The plain-text password entered by the user for verification.

    Returns:
        Optional[User]: A `User` object populated with data from the database if 
                        authentication is successful. 
    
    Raises:
        AuthenticationError: If the email is not found in the database, or if the provided
                             password does not match the stored hash for the found user.
        DatabaseError: If an unexpected error occurs during database interaction
                       (e.g., connection failure, SQL query execution error).
    """
    logger.info(f"Service: Authentication attempt initiated for email: '{email}'")
    conn = None

    try:
        conn = get_db_connection() # Establishes a new DB connection
        # Cursors from this connection use RealDictCursor by default (as per db.py).

        with conn.cursor() as cur:
            # SQL query to select all necessary fields for User object instantiation.
            cur.execute("""
                SELECT user_id, email, phone_number, password, created_at,
                       first_name, last_name, address_line1, address_line2,
                       city, state, zip_code, role
                FROM users
                WHERE email = %s
            """, (email,))

            user_data_dict = cur.fetchone() # Fetches one row as a dict-like RealDictRow or None

        if user_data_dict:
            # User with the given email was found; now verify the password.
            # user_data_dict["password"] should contain the hashed password from the database.
            if check_password_hash(user_data_dict["password"], password_input):
                logger.info(f"Service: User '{email}' authenticated successfully. Role: {user_data_dict.get('role')}")
                # Create and return a User object using data from the database.
                return User.from_db_row(user_data_dict) 
            else:
                # Password does not match the stored hash.
                logger.warning(f"Service: Authentication failed for email '{email}': Invalid password provided.")
                raise AuthenticationError("Invalid email or password. Please check your credentials and try again.")
            
        else:
            # No user found with the provided email address.
            logger.warning(f"Service: Authentication failed for email '{email}': User not found in the database.")
            # For security, use a generic message for both "user not found" and "wrong password".
            raise AuthenticationError("Invalid email or password. Please check your credentials and try again.")
            
    except AuthenticationError:
        # Re-raise the specific AuthenticationError to be handled by the route or global error handler.
        raise

    except Exception as e:
        # Catch any other unexpected exceptions (e.g., psycopg2.Error, programming errors).
        logger.error(f"Service: Database error or unexpected issue during authentication for email '{email}': {e}", exc_info=True)
        # Wrap other exceptions in a custom DatabaseError for consistent error handling.
        raise DatabaseError(
            message="Could not complete authentication due to a server or database issue. Please try again later.", 
            original_exception=e
        )
    
    finally:
        if conn:
            conn.close() 
            logger.debug(f"Service: Database connection closed after authentication attempt for email '{email}'.")

# Note: The `sanitize_form_input` function, previously associated with auth/reg services,
# has been consolidated into `app/utils.py` (as `sanitize_form_data` and `sanitize_html_text`).
# Input sanitization (like stripping whitespace, lowercasing email) is expected to occur 
# in the route handlers (using functions from app.utils) before data is passed to service functions.
# This service function now expects a pre-processed email.