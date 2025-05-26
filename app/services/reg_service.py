# app/services/reg_service.py

import re
from app.models.user import User                                            # Import the User model type hinting and retrun type
from app.logger import get_logger                                           # Use the application's configured logger
from app.models.db import get_db_connection                                 # Import the database connection utility
from typing import Dict, Any, List, Optional                                # Type hints for function parameters & return types
from werkzeug.security import generate_password_hash                        # For password hashing
from app.services.exceptions import ValidationError, DatabaseError, AppException    # Custome exceptions & error handling

logger = get_logger(__name__)

# --- Validation Constants ---
EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
PASSWORD_REGEX = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+={}\[\]:;\"'<>,.?/~`\-])[A-Za-z\d!@#$%^&*()_+={}\[\]:;\"'<>,.?/~`\-]{8,128}$"
NAME_REGEX = r"^[A-Za-z\s'\-.,]{1,70}$"
PHONE_DIGITS_REGEX = r"^\d{10,15}$"
ZIP_CODE_REGEX = r"^\d{5}(?:[-\s]\d{4})?$"
STATE_REGEX = r"^[A-Za-z\s.,'-]{2,50}$"
ADDRESS_REGEX = r"^[A-Za-z0-9\s.,#'\-\/\(\)]{1,100}$"
ALLOWED_ROLES = {'customer', 'admin', 'employee'}

def validate_registration_data(form_data: Dict[str, Any]) -> List[str]:
    """
    Validates user registration data against predefined rules and checks for email uniqueness.

    This function is typically called by the registration route handler after initial
    data sanitization (e.g., stripping whitespace, lowercasing email via `app/utils.py`).
    It accumulates all validation errors into a list.

    Args:
        form_data (Dict[str, Any]): A dictionary containing the user-submitted registration data.
                                     Expected keys: 'first_name', 'last_name', 'email',
                                     'password' (raw), 'confirm_password', 'role', and optional
                                     address/phone fields.

    Returns:
        List[str]: A list of human-readable error messages. An empty list indicates 
                   that all validations passed.
    """
    email_for_log = form_data.get('email', 'N/A')
    logger.debug(f"Service: Validating registration data for potential user: {email_for_log}")
    errors: List[str] = []
    
    required_fields = ['first_name', 'last_name', 'email', 'password', 'confirm_password', 'role']

    for field in required_fields:
        if not form_data.get(field,"").strip():
            errors.append(f"{field.replace('_', ' ').title()} is required.")
    
    if errors: # Early exit if core required fields are missing
        logger.warning(f"Initial validation failed for registration (email: {email_for_log}): Missing required fields - {errors}")

        return errors

    # Field-specific Validations
    if not re.match(NAME_REGEX, form_data['first_name']):
        errors.append("First name: 1-70 characters, letters, spaces, and '-,.")

    if not re.match(NAME_REGEX, form_data['last_name']):
        errors.append("Last name: 1-70 characters, letters, spaces, and '-,.")

    email = form_data.get('email', '') # Assumed already lowercased by route

    if not re.match(EMAIL_REGEX, email):
        errors.append("Invalid email address format (e.g., user@example.com).")
        
    else:
        try:
            if get_user_by_email(email): 
                errors.append("This email address is already registered. Please log in or use a different email.")

        except DatabaseError: 
            errors.append("Could not verify email uniqueness at this time. Please try again.")

    if form_data.get('phone_number',"").strip():
        phone_digits = re.sub(r"[^0-9]", "", form_data['phone_number']) 

        if not re.match(PHONE_DIGITS_REGEX, phone_digits):
            errors.append("Phone number: Please enter 10 to 15 digits.")

    password = form_data.get('password', '')
    confirm_password = form_data.get('confirm_password', '')

    if password and not re.match(PASSWORD_REGEX, password):
        errors.append("Password: Min 8 chars, with uppercase, lowercase, number, and special character.")

    elif password != confirm_password:
        errors.append("Passwords do not match.")

    if form_data.get('role') not in ALLOWED_ROLES:
        errors.append(f"Invalid role. Please choose from: {', '.join(ALLOWED_ROLES)}.")

    # Address fields (conditionally required or format-checked if provided)
    main_address_fields_provided = any(form_data.get(f,"").strip() for f in ['address_line1', 'city', 'state', 'zip_code'])

    if main_address_fields_provided:
        # You might enforce these if main_address_fields_provided is true, or based on role
        address_fields_to_check = {
            'address_line1': ("Address Line 1", ADDRESS_REGEX, "Invalid Address Line 1 (max 100 chars)."),
            'city': ("City", NAME_REGEX, "Invalid city name."),
            'state': ("State", STATE_REGEX, "Invalid state (e.g., NY or California, max 50 chars)."),
            'zip_code': ("ZIP Code", ZIP_CODE_REGEX, "Invalid ZIP code (e.g., 12345 or 12345-1234).")
        }

        for field_key, (field_name, regex, msg) in address_fields_to_check.items():
            value = form_data.get(field_key,"").strip()

            if not value: # If any main address part is given, these become required
                errors.append(f"{field_name} is required when providing an address.")

            elif not re.match(regex, value):
                errors.append(msg)
        
        if form_data.get('address_line2',"").strip() and not re.match(ADDRESS_REGEX, form_data['address_line2']):
            errors.append("Invalid Address Line 2 (max 100 chars).")
            
    if errors:
        logger.warning(f"Registration data validation failed for email '{email_for_log}': {errors}")

    else:
        logger.debug(f"Registration data for email '{email_for_log}' passed all service-level validations.")

    return errors


def register_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Registers a new user in the database.
    Assumes `user_data` has passed preliminary validation via `validate_registration_data`.
    Handles password hashing and database insertion for the new user.

    Args:
        user_data (Dict[str, Any]): Validated user registration data. Required keys: 
                                     'first_name', 'last_name', 'email', 'password' (raw), 'role'.
                                     Optional address/phone fields default to None if not present.
                                     Text fields (except password) expected to be stripped, email lowercased.

    Returns:
        Dict[str, Any]: Dict with 'success' (bool), 'message' (str), and 'user_id' (int) on success.
    
    Raises:
        ValidationError: If final email uniqueness check fails within transaction.
        DatabaseError: For unexpected database interaction errors.
        AppException: For critical errors like password hashing failure.
    """
    email_to_register = user_data.get('email')
    logger.info(f"Service: Attempting to register new user with email: '{email_to_register}'")

    try:
        password_to_hash = user_data.get('password')
        if not isinstance(password_to_hash, str) or not password_to_hash:
            raise ValidationError("Password is required.", errors={"password": "A password is required."})
        
        hashed_password = generate_password_hash(password_to_hash)

    except Exception as e: 
        logger.critical(f"Critical error hashing password for user '{email_to_register}': {e}", exc_info=True)

        raise AppException("Internal error during registration (password processing).", original_exception=e)

    conn = None

    try:
        conn = get_db_connection()
        conn.autocommit = False # Manage transaction explicitly

        with conn.cursor() as cur: 
            cur.execute("SELECT user_id FROM users WHERE email = %s FOR UPDATE;", (email_to_register,))

            if cur.fetchone():
                raise ValidationError("This email address is already registered.", errors={'email': 'Already in use.'})

            insert_query = """
                INSERT INTO users (first_name, last_name, email, phone_number, password,
                                   address_line1, address_line2, city, state, zip_code, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING user_id, created_at; 
            """

            values = (
                user_data.get("first_name"), user_data.get("last_name"), email_to_register,
                user_data.get("phone_number") or None, hashed_password,
                user_data.get("address_line1") or None, user_data.get("address_line2") or None,
                user_data.get("city") or None, user_data.get("state") or None,
                user_data.get("zip_code") or None, user_data.get("role", "customer")
            )

            cur.execute(insert_query, values)
            result_row = cur.fetchone()
            
            if not result_row or 'user_id' not in result_row:
                raise DatabaseError("User registration insert failed to return new user ID.")

            new_user_id = result_row['user_id']
            conn.commit()
            
            logger.info(f"User '{email_to_register}' registered successfully with new user_id: {new_user_id}.")

            return {"success": True, "message": "Registration successful! Please log in.", "user_id": new_user_id}

    except ValidationError as ve: 
        if conn: conn.rollback()

        logger.warning(f"Validation error during user registration for '{email_to_register}': {ve.user_facing_message}, Errors: {ve.errors}")

        raise

    except Exception as e: 
        if conn: conn.rollback()

        logger.error(f"Database error or unexpected issue during registration for '{email_to_register}': {e}", exc_info=True)

        raise DatabaseError("Registration could not be completed due to a database error.", original_exception=e)
    
    finally:
        if conn:
            conn.autocommit = True # Reset for connection pooling if applicable
            conn.close()
            logger.debug(f"Database connection closed for registration attempt of '{email_to_register}'.")


def get_user_by_email(email: str) -> Optional[User]:
    """
    Retrieves a user from the database by their email address.
    Email search is case-insensitive (assumes DB index on LOWER(email) or email stored lowercase).

    Args:
        email (str): User's email address. Expected to be normalized (stripped, lowercased) by caller.

    Returns:
        Optional[User]: A `User` object if found, otherwise `None`.
    
    Raises:
        DatabaseError: If an unexpected database error occurs.
    """
    logger.debug(f"Service: Attempting to fetch user by email: '{email}'")
    conn = None

    try:
        conn = get_db_connection()

        with conn.cursor() as cur: 
            cur.execute("""
                SELECT user_id, email, phone_number, password, created_at,
                       first_name, last_name, address_line1, address_line2,
                       city, state, zip_code, role
                FROM users WHERE email = %s 
            """, (email,))

            user_row_dict = cur.fetchone()
        
        if user_row_dict:
            logger.debug(f"User found by email '{email}': ID {user_row_dict.get('user_id')}")

            return User.from_db_row(user_row_dict)
        
        else:
            logger.debug(f"No user found with email '{email}'.")

            return None
        
    except Exception as e:
        logger.error(f"Service: Error fetching user by email '{email}': {e}", exc_info=True)

        raise DatabaseError(message=f"Could not retrieve user data for email '{email}'.", original_exception=e)
    
    finally:
        if conn:
            conn.close()
            logger.debug(f"Database connection closed for get_user_by_email (email: '{email}').")