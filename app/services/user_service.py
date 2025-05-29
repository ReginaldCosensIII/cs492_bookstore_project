# app/services/user_service.py

import re
from typing import List, Optional, Dict, Any # For type hinting
from app.models.db import get_db_connection # For database connections
from app.models.user import User # User model class
from app.services.exceptions import DatabaseError, NotFoundError, ValidationError, AppException # Custom exceptions
from app.logger import get_logger # Custom application logger
from werkzeug.security import generate_password_hash # For admin creating users

PASSWORD_REGEX = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+={}\[\]:;\"'<>,.?/~`\-])[A-Za-z\d!@#$%^&*()_+={}\[\]:;\"'<>,.?/~`\-]{8,128}$"
EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
ALLOWED_ROLES = {'customer', 'admin', 'employee'} 
PHONE_DIGITS_REGEX = r"^\d{10,15}$" # Example regex

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
    Creates a new user account as an administrator.
    Handles validation, password hashing for an initial password provided by the admin.
    New users are created with `is_active = True` by database default.

    Args:
        user_data (Dict[str, Any]): A dictionary containing the new user's details.
                                     Expected keys: 'first_name', 'last_name', 'email', 
                                     'role', 'password' (initial plain text password).
                                     Optional: 'phone_number', address fields.
                                     Assumes text fields are pre-sanitized (stripped) by caller.
        performing_admin_id (int): The ID of the admin performing this action (for logging).

    Returns:
        User: The newly created and saved `User` object.

    Raises:
        ValidationError: If data validation fails (e.g., missing fields, invalid format, email exists).
        DatabaseError: If an error occurs during the database insert operation.
        AppException: For critical errors like password hashing failure.
    """
    email = user_data.get('email', '').lower().strip() # Ensure lowercase and stripped
    role = user_data.get('role', '').lower().strip()
    first_name = user_data.get('first_name', '').strip()
    last_name = user_data.get('last_name', '').strip()
    password = user_data.get('password', '') # Raw initial password

    logger.info(f"Service (Admin ID: {performing_admin_id}): Attempting to create new user. Email: '{email}', Role: '{role}'")

    # Validation
    errors_dict: Dict[str, str] = {}
    if not first_name: errors_dict['first_name'] = "First name is required."
    if not last_name: errors_dict['last_name'] = "Last name is required."
    if not email: errors_dict['email'] = "Email is required."
    elif not re.match(EMAIL_REGEX, email): errors_dict['email'] = "Invalid email format."
    if not role: errors_dict['role'] = "Role is required."
    elif role not in ALLOWED_ROLES: errors_dict['role'] = f"Invalid role selected. Allowed: {', '.join(ALLOWED_ROLES)}."
    if not password: errors_dict['password'] = "An initial password is required."
    # Basic password complexity check (can reuse PASSWORD_REGEX from reg_service)
    elif not re.match(PASSWORD_REGEX, password):
        errors_dict['password'] = "Password must be at least 8 characters and include an uppercase, lowercase, number, and special character."

    if errors_dict:
        logger.warning(f"Admin create user validation failed for email '{email}': {errors_dict}")
        raise ValidationError("User creation failed due to validation errors.", errors=errors_dict)

    # Check email uniqueness (using get_user_by_email from reg_service or a similar local one)
    # To avoid circular import if reg_service imports user_service, better to have this check here.
    # For this, we can use a simplified version of get_user_by_email from reg_service.
    # Or, rely on database unique constraint for email. For better UX, check first.
    existing_user = None
    try:
        # Re-using the get_user_by_email from reg_service is fine if reg_service doesn't import user_service
        # For now, let's assume a local check or that a get_user_by_email function exists that user_service can call.
        # from app.services.reg_service import get_user_by_email # If it's safe
        # existing_user = get_user_by_email(email)
        # Simplified check directly:
        conn_check = get_db_connection()
        with conn_check.cursor() as cur_check:
            cur_check.execute("SELECT user_id FROM users WHERE email = %s;", (email,))
            if cur_check.fetchone():
                existing_user = True
        conn_check.close()
    except Exception as e:
        logger.error(f"DB error checking email uniqueness for '{email}' during admin create: {e}", exc_info=True)
        raise DatabaseError("Could not verify email uniqueness due to a database issue.")

    if existing_user:
        logger.warning(f"Admin create user: Email '{email}' already exists.")
        raise ValidationError("This email address is already registered.", errors={'email': 'Already in use.'})

    try:
        hashed_password = generate_password_hash(password)
    except Exception as e:
        logger.critical(f"Password hashing error for admin-created user '{email}': {e}", exc_info=True)
        raise AppException("Internal error during user creation (password processing).", original_exception=e)

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # is_active defaults to TRUE in DB schema and User model __init__
            insert_query = """
                INSERT INTO users (first_name, last_name, email, phone_number, password,
                                   address_line1, address_line2, city, state, zip_code, role, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING user_id, email, phone_number, created_at, first_name, last_name, 
                          address_line1, address_line2, city, state, zip_code, role, is_active; 
            """
            cur.execute(insert_query, (
                first_name, last_name, email,
                user_data.get("phone_number") or None, hashed_password,
                user_data.get("address_line1") or None, user_data.get("address_line2") or None,
                user_data.get("city") or None, user_data.get("state") or None,
                user_data.get("zip_code") or None, role
            ))
            created_user_row = cur.fetchone()
            if not created_user_row:
                raise DatabaseError("User creation failed to return user details after insert.")
            conn.commit()
            
            new_user = User.from_db_row(created_user_row)
            logger.info(f"Service (Admin ID: {performing_admin_id}): User '{email}' (Role: {role}) created successfully with ID: {new_user.id}.")
            return new_user
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Service (Admin ID: {performing_admin_id}): DB error creating user '{email}': {e}", exc_info=True)
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
    logger.info(f"Service (Admin ID: {performing_admin_id}): Attempting to update details for user ID: {user_id_to_edit}")

    user_to_update = admin_get_user_by_id(user_id_to_edit)
    if not user_to_update:
        raise NotFoundError(f"User with ID {user_id_to_edit} not found for update.")

    # Validate and prepare fields for update
    fields_to_update: Dict[str, Any] = {}
    errors_dict: Dict[str, str] = {}

    if 'first_name' in update_data:
        first_name = str(update_data['first_name']).strip()
        if not first_name: errors_dict['first_name'] = "First name cannot be empty."
        else: fields_to_update['first_name'] = first_name.title()
    
    if 'last_name' in update_data:
        last_name = str(update_data['last_name']).strip()
        if not last_name: errors_dict['last_name'] = "Last name cannot be empty."
        else: fields_to_update['last_name'] = last_name.title()

    if 'email' in update_data:
        email = str(update_data['email']).lower().strip()
        if not email: errors_dict['email'] = "Email cannot be empty."
        elif not re.match(EMAIL_REGEX, email): errors_dict['email'] = "Invalid email format."
        elif email != user_to_update.email: # Check uniqueness only if email is changing
            # existing_user_with_new_email = get_user_by_email(email) # From reg_service or local
            conn_check = get_db_connection(); existing_user_with_new_email = None
            with conn_check.cursor() as cur_check:
                cur_check.execute("SELECT user_id FROM users WHERE email = %s;", (email,))
                if cur_check.fetchone(): existing_user_with_new_email = True
            conn_check.close()
            if existing_user_with_new_email:
                errors_dict['email'] = "This email address is already in use by another account."
            else:
                fields_to_update['email'] = email
    
    if 'phone_number' in update_data:
        phone = str(update_data['phone_number']).strip()
        if phone: # Optional, but validate if provided
            phone_digits = re.sub(r"[^0-9]", "", phone)
            if not re.match(PHONE_DIGITS_REGEX, phone_digits): errors_dict['phone_number'] = "Invalid phone number (10-15 digits)."
            else: fields_to_update['phone_number'] = phone # Store original formatted if desired, or phone_digits
        else: # Allow clearing phone number
            fields_to_update['phone_number'] = None

    # Address fields (optional, validate if provided)
    addr_fields = ['address_line1', 'address_line2', 'city', 'state', 'zip_code']
    for field in addr_fields:
        if field in update_data:
            value = str(update_data[field]).strip()
            if value: fields_to_update[field] = value
            else: fields_to_update[field] = None # Allow clearing optional address fields

    if 'role' in update_data:
        role = str(update_data['role']).lower().strip()
        if not role: errors_dict['role'] = "Role cannot be empty."
        elif role not in ALLOWED_ROLES: errors_dict['role'] = f"Invalid role. Allowed: {', '.join(ALLOWED_ROLES)}."
        elif user_id_to_edit == performing_admin_id and role != 'admin':
             errors_dict['role'] = "Administrators cannot change their own role from 'admin'."
        else:
            fields_to_update['role'] = role
            
    if errors_dict:
        logger.warning(f"Admin update user ID {user_id_to_edit} validation failed: {errors_dict}")
        raise ValidationError("User update failed due to validation errors.", errors=errors_dict)

    if not fields_to_update:
        logger.info(f"Service (Admin ID: {performing_admin_id}): No changes provided to update for user ID: {user_id_to_edit}")
        return user_to_update # No actual update needed, return existing user

    # Construct SQL UPDATE statement dynamically
    set_clauses = []
    update_values = []
    for key, value in fields_to_update.items():
        set_clauses.append(f"{key} = %s")
        update_values.append(value)
    
    if not set_clauses: # Should be caught by "no changes" above, but defensive
        return user_to_update

    update_query = f"UPDATE users SET {', '.join(set_clauses)}, created_at = CURRENT_TIMESTAMP WHERE user_id = %s RETURNING *;"
    update_values.append(user_id_to_edit)

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(update_query, tuple(update_values))
            updated_user_row = cur.fetchone()
            if not updated_user_row:
                # This could happen if user_id was valid but somehow update affected 0 rows
                raise DatabaseError(f"User ID {user_id_to_edit} found but update failed to apply.")
            conn.commit()
        
        updated_user = User.from_db_row(updated_user_row)
        logger.info(f"Service (Admin ID: {performing_admin_id}): User ID {user_id_to_edit} details updated successfully.")
        return updated_user
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Service (Admin ID: {performing_admin_id}): DB error updating user ID {user_id_to_edit}: {e}", exc_info=True)
        raise DatabaseError(f"Could not update user details for ID {user_id_to_edit}.", original_exception=e)
    finally:
        if conn: conn.close()

def admin_create_user(user_data: Dict[str, Any], performing_admin_id: int) -> User:
    """
    Creates a new user account as an administrator.
    Handles validation, password hashing for an initial password provided by the admin.
    New users are created with `is_active = True` by database default.

    Args:
        user_data (Dict[str, Any]): A dictionary containing the new user's details.
                                     Expected keys: 'first_name', 'last_name', 'email', 
                                     'role', 'password' (initial plain text password).
                                     Optional: 'phone_number', address fields.
                                     Assumes text fields are pre-sanitized (stripped) by caller.
        performing_admin_id (int): The ID of the admin performing this action (for logging).

    Returns:
        User: The newly created and saved `User` object.

    Raises:
        ValidationError: If data validation fails (e.g., missing fields, invalid format, email exists).
        DatabaseError: If an error occurs during the database insert operation.
        AppException: For critical errors like password hashing failure.
    """
    email = user_data.get('email', '').lower().strip()
    role = user_data.get('role', '').lower().strip()
    first_name = user_data.get('first_name', '').strip()
    last_name = user_data.get('last_name', '').strip()
    password = user_data.get('password', '') # Raw initial password from admin form

    logger.info(f"Service (Admin ID: {performing_admin_id}): Attempting to create new user. Email: '{email}', Role: '{role}'")

    errors_dict: Dict[str, str] = {}
    if not first_name: errors_dict['first_name'] = "First name is required."
    if not last_name: errors_dict['last_name'] = "Last name is required."
    if not email: errors_dict['email'] = "Email is required."
    elif not re.match(EMAIL_REGEX, email): errors_dict['email'] = "Invalid email format."
    if not role: errors_dict['role'] = "Role is required."
    elif role not in ALLOWED_ROLES: errors_dict['role'] = f"Invalid role. Allowed: {', '.join(ALLOWED_ROLES)}."
    if not password: errors_dict['password'] = "An initial password is required."
    elif not re.match(PASSWORD_REGEX, password): # Validate initial password complexity
        errors_dict['password'] = "Password: Min 8 chars, with uppercase, lowercase, number, & special char."

    if errors_dict:
        logger.warning(f"Admin create user validation failed for email '{email}': {errors_dict}")
        raise ValidationError("User creation failed due to validation errors.", errors=errors_dict)

    # Check email uniqueness
    conn_check = None
    try:
        conn_check = get_db_connection()
        with conn_check.cursor() as cur_check:
            cur_check.execute("SELECT user_id FROM users WHERE email = %s;", (email,))
            if cur_check.fetchone():
                logger.warning(f"Admin create user: Email '{email}' already exists.")
                raise ValidationError("This email address is already registered.", errors={'email': 'Already in use.'})
    except ValidationError:
        raise # Re-raise validation error if email exists
    except Exception as e:
        logger.error(f"DB error checking email uniqueness for '{email}' during admin create: {e}", exc_info=True)
        raise DatabaseError("Could not verify email uniqueness.", original_exception=e)
    finally:
        if conn_check: conn_check.close()

    try:
        hashed_password = generate_password_hash(password)
    except Exception as e:
        logger.critical(f"Password hashing error for admin-created user '{email}': {e}", exc_info=True)
        raise AppException("Internal error during user creation (password processing).", original_exception=e)

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # is_active defaults to TRUE in DB schema. created_at also acts as an updated_at field so if a user is updated the created_at is changed to the CURRENT_TIMESTAMP
            insert_query = """
                INSERT INTO users (first_name, last_name, email, phone_number, password,
                                   address_line1, address_line2, city, state, zip_code, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING user_id, email, phone_number, created_at, first_name, last_name, 
                          address_line1, address_line2, city, state, zip_code, role, is_active; 
            """
            cur.execute(insert_query, (
                first_name, last_name, email,
                user_data.get("phone_number") or None, hashed_password,
                user_data.get("address_line1") or None, user_data.get("address_line2") or None,
                user_data.get("city") or None, user_data.get("state") or None,
                user_data.get("zip_code") or None, role
            ))
            created_user_row = cur.fetchone()
            if not created_user_row:
                raise DatabaseError("User creation failed to return user details after insert.")
            conn.commit()
            
            new_user = User.from_db_row(created_user_row) # Create User object from the returned row
            logger.info(f"Service (Admin ID: {performing_admin_id}): User '{email}' (Role: {role}) created successfully with ID: {new_user.id}.")
            return new_user
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Service (Admin ID: {performing_admin_id}): DB error creating user '{email}': {e}", exc_info=True)
        raise DatabaseError("User creation failed due to a database error.", original_exception=e)
    finally:
        if conn: conn.close()

# --- NEW Admin User Update Function ---
def admin_update_user_details(user_id_to_edit: int, update_data: Dict[str, Any], performing_admin_id: int) -> User:
    """
    Updates an existing user's details (excluding password) by an administrator.
    Can update name, email, phone, address fields, and role.
    The 'is_active' status is handled by admin_enable_user/admin_disable_user functions.

    Args:
        user_id_to_edit (int): The ID of the user to update.
        update_data (Dict[str, Any]): Dictionary of attributes to update.
                                     Supported keys: 'first_name', 'last_name', 'email', 
                                     'phone_number', 'address_line1', 'address_line2', 
                                     'city', 'state', 'zip_code', 'role'.
                                     Assumes text fields are pre-sanitized by caller.
        performing_admin_id (int): The ID of the admin performing this action.

    Returns:
        User: The updated `User` object.

    Raises:
        NotFoundError: If the user with `user_id_to_edit` is not found.
        ValidationError: If validation of `update_data` fails (e.g., email format/uniqueness, invalid role).
        DatabaseError: If an error occurs during the database update operation.
    """
    logger.info(f"Service (Admin ID: {performing_admin_id}): Attempting to update details for user ID: {user_id_to_edit}")

    user_to_update = admin_get_user_by_id(user_id_to_edit)
    if not user_to_update: # admin_get_user_by_id returns None if not found
        logger.warning(f"Service (Admin ID: {performing_admin_id}): User ID {user_id_to_edit} not found for update.")
        raise NotFoundError(f"User with ID {user_id_to_edit} not found. Cannot update details.")

    # Validate and prepare fields for update
    fields_to_update_in_db: Dict[str, Any] = {} # Actual DB column updates
    errors_dict: Dict[str, str] = {}

    # Note: Assumes update_data values are already stripped by the caller (e.g., route using sanitize_form_data)
    if 'first_name' in update_data:
        first_name = str(update_data['first_name']).strip()
        if not first_name: errors_dict['first_name'] = "First name cannot be empty."
        else: fields_to_update_in_db['first_name'] = first_name.title()
    
    if 'last_name' in update_data:
        last_name = str(update_data['last_name']).strip()
        if not last_name: errors_dict['last_name'] = "Last name cannot be empty."
        else: fields_to_update_in_db['last_name'] = last_name.title()

    if 'email' in update_data:
        email = str(update_data['email']).lower().strip()
        if not email: errors_dict['email'] = "Email cannot be empty."
        elif not re.match(EMAIL_REGEX, email): errors_dict['email'] = "Invalid email format."
        elif email != user_to_update.email: # Check uniqueness only if email is changing
            existing_user_with_new_email = None
            conn_check_email = None
            try:
                conn_check_email = get_db_connection()
                with conn_check_email.cursor() as cur_check_email:
                    cur_check_email.execute("SELECT user_id FROM users WHERE email = %s;", (email,))
                    if cur_check_email.fetchone(): existing_user_with_new_email = True
            except Exception as e_uniq:
                 logger.error(f"DB error checking email uniqueness for '{email}' during admin update: {e_uniq}", exc_info=True)
                 errors_dict['email'] = "Could not verify email uniqueness. DB error." # Add to field errors
            finally:
                if conn_check_email: conn_check_email.close()

            if existing_user_with_new_email:
                errors_dict['email'] = "This email address is already in use by another account."
            else:
                fields_to_update_in_db['email'] = email
    
    if 'phone_number' in update_data: # Optional field
        phone = str(update_data['phone_number']).strip()
        if phone: 
            phone_digits = re.sub(r"[^0-9]", "", phone)
            if not re.match(PHONE_DIGITS_REGEX, phone_digits): errors_dict['phone_number'] = "Invalid phone (10-15 digits)."
            else: fields_to_update_in_db['phone_number'] = phone 
        else: 
            fields_to_update_in_db['phone_number'] = None # Allow clearing

    # Address fields are optional, validate if provided
    addr_keys = ['address_line1', 'address_line2', 'city', 'state', 'zip_code']
    for key in addr_keys:
        if key in update_data:
            value = str(update_data[key]).strip()
            if value: fields_to_update_in_db[key] = value
            else: fields_to_update_in_db[key] = None # Allow clearing

    if 'role' in update_data:
        role = str(update_data['role']).lower().strip()
        if not role: errors_dict['role'] = "Role cannot be empty."
        elif role not in ALLOWED_ROLES: errors_dict['role'] = f"Invalid role. Allowed: {', '.join(ALLOWED_ROLES)}."
        # Prevent admin from changing their own role away from 'admin' if they are the one being edited
        elif user_id_to_edit == performing_admin_id and role != 'admin':
             errors_dict['role'] = "Administrators cannot change their own role from 'admin' via this form."
        else:
            fields_to_update_in_db['role'] = role
            
    if errors_dict: # If any validation errors occurred
        logger.warning(f"Admin update user ID {user_id_to_edit} validation failed: {errors_dict}")
        raise ValidationError("User update failed due to validation errors.", errors=errors_dict)

    if not fields_to_update_in_db: # No actual changes to commit
        logger.info(f"Service (Admin ID: {performing_admin_id}): No changes provided to update for user ID: {user_id_to_edit}")
        return user_to_update # Return the unchanged user object

    # Construct SQL UPDATE statement dynamically based on fields_to_update_in_db
    set_clauses_sql = []
    update_values_sql = []
    for key, value in fields_to_update_in_db.items():
        set_clauses_sql.append(f"{key} = %s")
        update_values_sql.append(value)
    
    update_query = f"UPDATE users SET {', '.join(set_clauses_sql)}, created_at = CURRENT_TIMESTAMP WHERE user_id = %s RETURNING *;"
    update_values_sql.append(user_id_to_edit)

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(update_query, tuple(update_values_sql))
            updated_user_row = cur.fetchone()
            if not updated_user_row:
                # This could happen if user_id was valid but update affected 0 rows (e.g., race condition where user deleted)
                logger.error(f"User ID {user_id_to_edit} was found but update query affected 0 rows.")
                raise DatabaseError(f"User ID {user_id_to_edit} found but update failed to apply in database.")
            conn.commit()
        
        updated_user_object = User.from_db_row(updated_user_row)
        logger.info(f"Service (Admin ID: {performing_admin_id}): User ID {user_id_to_edit} details updated successfully.")
        return updated_user_object
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Service (Admin ID: {performing_admin_id}): DB error updating user ID {user_id_to_edit}: {e}", exc_info=True)
        raise DatabaseError(f"Could not update user details for ID {user_id_to_edit}.", original_exception=e)
    finally:
        if conn: conn.close()
