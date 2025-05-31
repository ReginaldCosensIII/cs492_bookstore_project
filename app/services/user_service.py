# app/services/user_service.py

import re
from flask_login import current_user
from typing import List, Optional, Dict, Any # For type hinting
from app.models.db import get_db_connection # For database connections
from app.models.user import User # User model class
from app.services.exceptions import DatabaseError, NotFoundError, ValidationError, AppException # Custom exceptions
from app.logger import get_logger # Custom application logger
from werkzeug.security import generate_password_hash # For admin creating users

# Validation Constants (as you have them in your user_service.py)
PASSWORD_REGEX = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+={}\[\]:;\"'<>,.?/~`\-])[A-Za-z\d!@#$%^&*()_+={}\[\]:;\"'<>,.?/~`\-]{8,128}$"
EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
ALLOWED_ROLES = {'customer', 'admin', 'employee'} 
PHONE_DIGITS_REGEX = r"^\d{10,15}$"
NAME_REGEX = r"^[A-Za-z\s'\-.,]{1,70}$"
ZIP_CODE_REGEX = r"^\d{5}(?:[-\s]\d{4})?$" 
STATE_REGEX = r"^[A-Za-z\s.,'-]{2}$" # Allows for full state names or abbreviations
ADDRESS_REGEX = r"^[A-Za-z0-9\s.,#'\-\/\(\)]{1,100}$"

logger = get_logger(__name__) # Logger instance for this module   

def admin_get_all_users(
    role_filter: Optional[str] = None, 
    search_email: Optional[str] = None,
    sort_by: Optional[str] = None,      # New parameter for sorting column
    sort_order: Optional[str] = 'asc'   # New parameter for sort direction (asc/desc)
) -> List[User]:
    """
    Retrieves all users from the database, with optional filtering, searching, and sorting.
    Intended for use by administrators to view and manage user lists.

    Args:
        role_filter (Optional[str]): Filters users by this role (case-insensitive).
        search_email (Optional[str]): Filters users whose email contains this string (case-insensitive).
        sort_by (Optional[str]): The database column name to sort the results by.
                                 Must be one of the allowed sortable columns.
                                 Defaults to 'last_name' if not specified or invalid.
        sort_order (Optional[str]): The order to sort by ('asc' for ascending, 
                                    'desc' for descending). Defaults to 'asc'.

    Returns:
        List[User]: A list of `User` objects matching the criteria.
    
    Raises:
        DatabaseError: If a critical database error occurs.
        ValueError: If an invalid sort_order is provided.
    """
    logger.debug(f"Service (Admin): admin_get_all_users called with: role_filter='{role_filter}', "
                 f"search_email='{search_email}', sort_by='{sort_by}', sort_order='{sort_order}'")

    params_for_where_clause = []
    
    base_query = """
        SELECT user_id, email, phone_number, password, created_at,
               first_name, last_name, address_line1, address_line2,
               city, state, zip_code, role, is_active 
        FROM users
    """
    where_clauses_list = []

    if role_filter and role_filter.lower() != 'all':
        where_clauses_list.append("LOWER(role) = LOWER(%s)")
        params_for_where_clause.append(role_filter)

    if search_email:
        where_clauses_list.append("email ILIKE %s") 
        params_for_where_clause.append(f"%{search_email}%")

    # Construct the full query string
    full_query = base_query
    if where_clauses_list:
        full_query += " WHERE " + " AND ".join(where_clauses_list)
    
    # --- Sorting Logic ---
    allowed_sort_columns = {
        'id': 'user_id', 
        'name': 'last_name', 
        'email': 'email', 
        'role': 'role', 
        'status': 'is_active', 
        'joined': 'created_at'
    }
    
    db_sort_column_actual = allowed_sort_columns.get(sort_by, 'last_name') 
    logger.debug(f"Service (Admin): Input sort_by: '{sort_by}', Mapped DB sort column: '{db_sort_column_actual}'")

    # Validate and determine SQL sort order
    sort_order_sql_keyword = 'ASC' 
    if sort_order and sort_order.lower() == 'desc':
        sort_order_sql_keyword = 'DESC'
    # ... (logging for sort order) ...
    
    # Add ORDER BY clause
    if db_sort_column_actual == 'last_name': # Specifically for 'name' sort
        full_query += f" ORDER BY last_name {sort_order_sql_keyword}, first_name {sort_order_sql_keyword}, user_id {sort_order_sql_keyword}"
    else:
        full_query += f" ORDER BY {db_sort_column_actual} {sort_order_sql_keyword}, user_id {sort_order_sql_keyword}"
    
    full_query += ";"

    logger.info(f"Service (Admin): Fetching users. Role: '{role_filter}', Email search: '{search_email}', Sort: '{db_sort_column_actual}' {sort_order_sql_keyword}.")
    logger.debug(f"Service (Admin): Final SQL Query to execute: {full_query}")
    logger.debug(f"Service (Admin): Parameters for WHERE clause: {tuple(params_for_where_clause) if params_for_where_clause else 'None'}")

    users_list: List[User] = []
    conn = None

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            print("Full QUERY: ", full_query)
            cur.execute(full_query, tuple(params_for_where_clause) if params_for_where_clause else None)
            user_rows = cur.fetchall()

            for row_dict in user_rows:
                user_obj = User.from_db_row(row_dict)
                if user_obj:
                    users_list.append(user_obj)
            
            logger.info(f"Service (Admin): Retrieved {len(users_list)} users matching criteria.")
            return users_list

    except Exception as e:
        logger.error(f"Service (Admin): Database error while fetching sorted/filtered users: {e}", exc_info=True)
        raise DatabaseError("Could not retrieve user list due to a database problem.", original_exception=e)
    finally:
        if conn:
            conn.close()
            logger.debug("Service (Admin): Database connection closed for admin_get_all_users.")

def admin_get_user_by_id(user_id: int) -> Optional[User]:
    """
    Retrieves a single user from the database by their unique ID.
    Intended for administrator use to fetch user details for viewing or editing.

    Args:
        user_id (int): The ID of the user to retrieve.

    Returns:
        Optional[User]: The `User` object if found, otherwise `None`.
    
    Raises:
        DatabaseError: If an unexpected error occurs during database interaction.
                       (NotFoundError should ideally be handled by the caller if None is returned).
    """
    logger.info(f"Service (Admin): Attempting to fetch user by ID: {user_id}")
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, email, phone_number, password, created_at,
                       first_name, last_name, address_line1, address_line2,
                       city, state, zip_code, role, is_active
                FROM users 
                WHERE user_id = %s;
            """, (user_id,))
            user_data_dict = cur.fetchone()

        if user_data_dict:
            logger.debug(f"Service (Admin): User with ID {user_id} (Email: '{user_data_dict.get('email')}') found.")
            return User.from_db_row(user_data_dict)
        else:
            logger.warning(f"Service (Admin): No user found with ID: {user_id}.")
            return None # Caller (route) should handle this and raise NotFoundError if appropriate for UX
            
    except Exception as e:
        logger.error(f"Service (Admin): Error fetching user by ID {user_id}: {e}", exc_info=True)
        raise DatabaseError(f"Could not retrieve user details for ID {user_id} due to a server error.", original_exception=e)
    finally:
        if conn:
            conn.close()
            logger.debug(f"Service (Admin): Database connection closed for admin_get_user_by_id (user_id: {user_id}).")

def _admin_set_user_active_status(user_id: int, admin_user_id: int, is_active_status: bool) -> bool:
    """
    Internal helper to set the is_active status of a user.
    Prevents an admin from disabling their own account.

    Args:
        user_id (int): The ID of the user whose status is to be changed.
        admin_user_id (int): The ID of the admin performing the action.
        is_active_status (bool): The new active status (True to enable, False to disable).

    Returns:
        bool: True if the status was successfully updated.

    Raises:
        NotFoundError: If the user_id to modify is not found.
        ValidationError: If an admin tries to disable their own account.
        DatabaseError: For other database issues.
    """
    action = "enable" if is_active_status else "disable"
    logger.info(f"Service (Admin): Admin {admin_user_id} attempting to {action} user ID: {user_id}")

    if user_id == admin_user_id and not is_active_status:
        logger.warning(f"Service (Admin): Admin {admin_user_id} attempted to disable their own account. Action denied.")
        raise ValidationError("Administrators cannot disable their own accounts.")

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if user exists before trying to update
            cur.execute("SELECT is_active FROM users WHERE user_id = %s;", (user_id,))
            user_exists_row = cur.fetchone()
            if not user_exists_row:
                raise NotFoundError(f"User with ID {user_id} not found. Cannot {action} account.")

            cur.execute(
                "UPDATE users SET is_active = %s WHERE user_id = %s;",
                (is_active_status, user_id)
            )
            if cur.rowcount == 0:
                # This might happen if the status was already set to the target value,
                # or if the user was deleted concurrently (less likely after the SELECT check).
                logger.warning(f"Service (Admin): No change in active status for user ID {user_id} (was it already {action}d or not found for update?).")
                # Check if current status is already the desired status
                if user_exists_row['is_active'] == is_active_status:
                    logger.info(f"Service (Admin): User ID {user_id} was already {action}d. No database update performed.")
                    return True # Considered success as state matches desired state
                raise DatabaseError(f"Failed to {action} user ID {user_id}. User found but status not updated.")
            
            conn.commit()
            logger.info(f"Service (Admin): User ID {user_id} successfully {action}d by admin {admin_user_id}.")
            return True
    except (NotFoundError, ValidationError) as ve:
        if conn: conn.rollback()
        logger.warning(f"Service (Admin): Failed to {action} user ID {user_id}: {str(ve)}")
        raise
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Service (Admin): Database error trying to {action} user ID {user_id}: {e}", exc_info=True)
        raise DatabaseError(f"Could not {action} user account due to a database problem.", original_exception=e)
    finally:
        if conn: conn.close()

def admin_disable_user(user_id_to_disable: int, current_admin_id: int) -> bool:
    """
    Disables a user account (sets is_active = False).
    An admin cannot disable their own account.

    Args:
        user_id_to_disable (int): The ID of the user to disable.
        current_admin_id (int): The ID of the admin performing the action.

    Returns:
        bool: True if user was successfully disabled.
    
    Raises:
        NotFoundError, ValidationError, DatabaseError (from helper).
    """
    return _admin_set_user_active_status(user_id_to_disable, current_admin_id, False)

def admin_enable_user(user_id_to_enable: int, current_admin_id: int) -> bool:
    """
    Enables a user account (sets is_active = True).

    Args:
        user_id_to_enable (int): The ID of the user to enable.
        current_admin_id (int): The ID of the admin performing the action (for logging).

    Returns:
        bool: True if user was successfully enabled.
    
    Raises:
        NotFoundError, DatabaseError (from helper).
    """
    # No check needed for admin enabling their own account as it's a positive action.
    return _admin_set_user_active_status(user_id_to_enable, current_admin_id, True)

def admin_create_user(user_data: Dict[str, Any], performing_admin_id: int) -> User:
    """
    Creates a new user account by an administrator.
    Validates input data (including optional fields if provided), 
    hashes password, and inserts into the database.
    New users are created as active. `created_at` also serves as last_updated.

    Args:
        user_data (Dict[str, Any]): Data for the new user. Expected keys include
                                     'first_name', 'last_name', 'email', 'role', 'password'.
                                     Optional: 'phone_number', address fields.
                                     Assumes text fields are pre-sanitized (stripped) by caller.
        performing_admin_id (int): ID of the admin performing the action.

    Returns:
        User: The created User object.

    Raises:
        ValidationError: If input data is invalid or email already exists.
        DatabaseError: For database insertion errors.
        AppException: For critical errors like password hashing failure.
    """
    admin_email_log = getattr(current_user, 'email', f"AdminID:{performing_admin_id}")
    logger.info(f"Service (Admin: {admin_email_log}): Attempting to create user. Email: '{user_data.get('email')}'")

    # Extract and normalize main fields (caller should have sanitized for HTML if from form)
    first_name = user_data.get('first_name', '').strip()
    last_name = user_data.get('last_name', '').strip()
    email = user_data.get('email', '').lower().strip()
    role = user_data.get('role', '').lower().strip()
    password = user_data.get('password', '') # Raw password
    
    phone_number = user_data.get('phone_number', '').strip() or None
    address_line1 = user_data.get('address_line1', '').strip() or None
    address_line2 = user_data.get('address_line2', '').strip() or None
    city = user_data.get('city', '').strip() or None
    state = user_data.get('state', '').strip() or None
    zip_code = user_data.get('zip_code', '').strip() or None

    errors_dict: Dict[str, str] = {}
    # Required fields validation
    if not first_name: errors_dict['first_name'] = "First name is required."
    elif not re.match(NAME_REGEX, first_name): errors_dict['first_name'] = "Invalid first name (1-70 chars, letters, spaces, '-,.)."
    
    if not last_name: errors_dict['last_name'] = "Last name is required."
    elif not re.match(NAME_REGEX, last_name): errors_dict['last_name'] = "Invalid last name (1-70 chars, letters, spaces, '-,.)."

    if not email: errors_dict['email'] = "Email is required."
    elif not re.match(EMAIL_REGEX, email): errors_dict['email'] = "Invalid email format (e.g., user@example.com)."
    
    if not role: errors_dict['role'] = "Role is required."
    elif role not in ALLOWED_ROLES: errors_dict['role'] = f"Invalid role. Allowed: {', '.join(ALLOWED_ROLES)}."
    
    if not password: errors_dict['password'] = "An initial password is required."
    elif not re.match(PASSWORD_REGEX, password):
        errors_dict['password'] = "Password: Min 8 chars, with uppercase, lowercase, number, & special char."

    # Optional fields validation (only if provided)
    if phone_number:
        phone_digits = re.sub(r"[^0-9]", "", phone_number)
        if not re.match(PHONE_DIGITS_REGEX, phone_digits):
            errors_dict['phone_number'] = "Phone number: Please enter 10 to 15 digits."
    
    main_address_fields_provided = any([address_line1, city, state, zip_code])
    if main_address_fields_provided:
        if not address_line1: errors_dict['address_line1'] = "Address Line 1 is required if providing partial address."
        elif not re.match(ADDRESS_REGEX, address_line1): errors_dict['address_line1'] = "Invalid Address Line 1 (max 100 chars)."
        
        if address_line2 and not re.match(ADDRESS_REGEX, address_line2): # Optional, but validate if present
             errors_dict['address_line2'] = "Invalid Address Line 2 (max 100 chars)."

        if not city: errors_dict['city'] = "City is required if providing partial address."
        elif not re.match(NAME_REGEX, city): errors_dict['city'] = "Invalid city name." # Using NAME_REGEX for city
        
        if not state: errors_dict['state'] = "State is required if providing partial address."
        elif not re.match(STATE_REGEX, state): errors_dict['state'] = "Invalid state format (e.g., NY or California)."
        
        if not zip_code: errors_dict['zip_code'] = "ZIP Code is required if providing partial address."
        elif not re.match(ZIP_CODE_REGEX, zip_code): errors_dict['zip_code'] = "Invalid ZIP code (e.g., 12345 or 12345-1234)."

    if errors_dict:
        logger.warning(f"Admin create user validation failed for email '{email}': {errors_dict}")
        raise ValidationError("User creation failed due to validation errors.", errors=errors_dict)

    # Check email uniqueness
    conn_check_email = None
    try:
        conn_check_email = get_db_connection()
        with conn_check_email.cursor() as cur_check_email:
            cur_check_email.execute("SELECT user_id FROM users WHERE email = %s FOR UPDATE;", (email,)) # Lock for safety
            if cur_check_email.fetchone():
                logger.warning(f"Admin create user: Email '{email}' already exists.")
                raise ValidationError("This email address is already registered.", errors={'email': 'Email already exists.'})
    except ValidationError:
        raise
    except Exception as e_uniq:
        logger.error(f"DB error checking email uniqueness for '{email}' during admin create: {e_uniq}", exc_info=True)
        raise DatabaseError("Could not verify email uniqueness due to a database issue.", original_exception=e_uniq)
    finally:
        if conn_check_email: conn_check_email.close()
    
    try:
        hashed_password = generate_password_hash(password)
    except Exception as e_hash:
        logger.critical(f"Password hashing error for admin-created user '{email}': {e_hash}", exc_info=True)
        raise AppException("Internal error during user creation (password processing).", original_exception=e_hash)

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # created_at is set by DB default, is_active defaults to TRUE
            insert_query = """
                INSERT INTO users (first_name, last_name, email, phone_number, password,
                                   address_line1, address_line2, city, state, zip_code, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING user_id, email, phone_number, created_at, first_name, last_name, 
                          address_line1, address_line2, city, state, zip_code, role, is_active; 
            """
            cur.execute(insert_query, (
                first_name.title(), last_name.title(), email, phone_number, hashed_password,
                address_line1, address_line2, city.title() if city else None, 
                state.upper() if state else None, zip_code, role
            ))
            created_user_row = cur.fetchone()
            if not created_user_row:
                raise DatabaseError("User creation failed to return new user details after insert.")
            conn.commit()
            
            new_user = User.from_db_row(created_user_row)
            logger.info(f"Service (Admin: {admin_email_log}): User '{new_user.email}' (Role: {new_user.role}) created successfully. ID: {new_user.id}.")
            return new_user
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Service (Admin: {admin_email_log}): DB error creating user '{email}': {e}", exc_info=True)
        raise DatabaseError("User creation failed due to a database error.", original_exception=e)
    finally:
        if conn: conn.close()

def admin_update_user_details(user_id_to_edit: int, update_data: Dict[str, Any], performing_admin_id: int) -> User:
    """
    Updates an existing user's details (excluding password) by an administrator.
    Can update name, email, phone, address fields, and role.

    Args:
        user_id_to_edit (int): The ID of the user to update.
        update_data (Dict[str, Any]): Dictionary of attributes to update.
                                     Supported keys: 'first_name', 'last_name', 'email', 
                                     'phone_number', 'address_line1', 'address_line2', 
                                     'city', 'state', 'zip_code', 'role'.
        performing_admin_id (int): The ID of the admin performing this action.

    Returns:
        User: The updated `User` object.

    Raises:
        NotFoundError: If the user with `user_id_to_edit` is not found.
        ValidationError: If validation of `update_data` fails (e.g., email format/uniqueness, invalid role).
        DatabaseError: If an error occurs during the database update operation.
    """
    admin_email_log = getattr(current_user, 'email', f"AdminID:{performing_admin_id}")
    logger.info(f"Service (Admin: {admin_email_log}): Updating details for user ID: {user_id_to_edit}")

    user_to_update = admin_get_user_by_id(user_id_to_edit)
    if not user_to_update:
        raise NotFoundError(f"User ID {user_id_to_edit} not found for update.")

    fields_to_update_in_db: Dict[str, Any] = {}
    validation_errors_dict: Dict[str, str] = {}
    
    # Validate and prepare each field present in update_data
    # Note: Assumes text values in update_data are already stripped by caller (e.g., sanitize_form_data in route)
    
    if 'first_name' in update_data:
        val = update_data['first_name']
        if not val: validation_errors_dict['first_name'] = "First name cannot be empty."
        elif not re.match(NAME_REGEX, val): validation_errors_dict['first_name'] = "Invalid first name format (1-70 chars, letters, spaces, '-,.)."
        else: fields_to_update_in_db['first_name'] = val.title()
    
    if 'last_name' in update_data:
        val = update_data['last_name']
        if not val: validation_errors_dict['last_name'] = "Last name cannot be empty."
        elif not re.match(NAME_REGEX, val): validation_errors_dict['last_name'] = "Invalid last name format (1-70 chars, letters, spaces, '-,.)."
        else: fields_to_update_in_db['last_name'] = val.title()

    if 'email' in update_data:
        email = update_data['email'].lower() # Already stripped by sanitize_form_data
        if not email: validation_errors_dict['email'] = "Email cannot be empty."
        elif not re.match(EMAIL_REGEX, email): validation_errors_dict['email'] = "Invalid email format."
        elif email != user_to_update.email: 
            conn_check_email = None; existing_user_with_new_email = False
            try:
                conn_check_email = get_db_connection()
                with conn_check_email.cursor() as cur_check_email:
                    cur_check_email.execute("SELECT user_id FROM users WHERE email = %s AND user_id != %s;", (email, user_id_to_edit))
                    if cur_check_email.fetchone(): existing_user_with_new_email = True
            except Exception as e_uniq:
                 logger.error(f"DB error checking email uniqueness for '{email}' in admin update: {e_uniq}", exc_info=True)
                 validation_errors_dict['email'] = "Could not verify email uniqueness (DB error)."
            finally:
                if conn_check_email: conn_check_email.close()
            if existing_user_with_new_email:
                validation_errors_dict['email'] = "This email address is already in use."
            elif 'email' not in validation_errors_dict: fields_to_update_in_db['email'] = email
    
    if 'phone_number' in update_data:
        phone = update_data.get('phone_number', '') # Should be stripped by sanitize_form_data
        if phone:
            phone_digits = re.sub(r"[^0-9]", "", phone)
            if not re.match(PHONE_DIGITS_REGEX, phone_digits): 
                validation_errors_dict['phone_number'] = "Invalid phone (10-15 digits)."
            else: fields_to_update_in_db['phone_number'] = phone
        else: fields_to_update_in_db['phone_number'] = None

    addr_keys_map = {'address_line1': ADDRESS_REGEX, 'address_line2': ADDRESS_REGEX, 
                     'city': NAME_REGEX, 'state': STATE_REGEX, 'zip_code': ZIP_CODE_REGEX}
    for key in addr_keys_map.keys(): # Use .keys() for iterating over dict keys
        if key in update_data:
            value = update_data.get(key, '') # Should be stripped by sanitize_form_data
            if value: # If value is provided (not empty after strip), validate it
                if key == 'address_line2' and not value: # address_line2 is optional, can be empty
                    fields_to_update_in_db[key] = None
                    continue
                if not re.match(addr_keys_map[key], value): # Use addr_keys_map[key] for regex
                    validation_errors_dict[key] = f"Invalid format for {key.replace('_', ' ')}."
                else: 
                    fields_to_update_in_db[key] = value.title() if key == 'city' else (value.upper() if key == 'state' else value)
            else: # Allow clearing optional address fields
                fields_to_update_in_db[key] = None if key != 'address_line1' else fields_to_update_in_db.get(key) # address_line1 might be required if others are set

    if 'role' in update_data:
        role = update_data['role'].lower() # Should be stripped
        if not role: validation_errors_dict['role'] = "Role cannot be empty."
        elif role not in ALLOWED_ROLES: validation_errors_dict['role'] = f"Invalid role. Allowed: {', '.join(ALLOWED_ROLES)}."
        elif user_id_to_edit == performing_admin_id and role != 'admin':
             validation_errors_dict['role'] = "Administrators cannot change their own role from 'admin'."
        else:
            fields_to_update_in_db['role'] = role
            
    if validation_errors_dict:
        logger.warning(f"Admin update user ID {user_id_to_edit} validation failed: {validation_errors_dict}")
        raise ValidationError("User update failed due to validation errors.", errors=validation_errors_dict)

    if not fields_to_update_in_db:
        logger.info(f"Service (Admin: {admin_email_log}): No valid data changes provided to update for user ID: {user_id_to_edit}. Only 'created_at' will be updated.")
        # Even if no other fields change, we update created_at to mark the 'edit' action
        fields_to_update_in_db['created_at'] = "CURRENT_TIMESTAMP_MARKER" 

    set_clauses_sql = []
    update_values_sql = []
    always_update_created_at = True # Flag to ensure created_at is in the SET clause

    for key, value in fields_to_update_in_db.items():
        if key == 'created_at' and value == "CURRENT_TIMESTAMP_MARKER":
            continue # Will be handled by always adding created_at = CURRENT_TIMESTAMP
        set_clauses_sql.append(f"{key} = %s")
        update_values_sql.append(value)
    
    set_clauses_sql.append("created_at = CURRENT_TIMESTAMP") 

    if not set_clauses_sql: # Should not be empty now
        return user_to_update 

    update_query = f"UPDATE users SET {', '.join(set_clauses_sql)} WHERE user_id = %s RETURNING *;"
    final_update_values = list(update_values_sql) 
    final_update_values.append(user_id_to_edit)

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(update_query, tuple(final_update_values))
            updated_user_row = cur.fetchone()
            if not updated_user_row:
                raise DatabaseError(f"User ID {user_id_to_edit} update query affected 0 rows.")
            conn.commit()
        updated_user_object = User.from_db_row(updated_user_row)
        logger.info(f"Service (Admin: {admin_email_log}): User ID {user_id_to_edit} details updated successfully (created_at reflects modification).")
        return updated_user_object
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Service (Admin: {admin_email_log}): DB error updating user ID {user_id_to_edit}: {e}", exc_info=True)
        raise DatabaseError(f"Could not update user details for ID {user_id_to_edit}.", original_exception=e)
    finally:
        if conn: conn.close()