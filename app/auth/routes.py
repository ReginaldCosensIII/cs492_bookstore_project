# app/auth/routes.py

from . import auth_bp                                                               # Import the blueprint instance
from typing import Dict, Any                                                        # For type hinting
from app.services.auth_service import authenticate_user                             # For user authentication
from app.utils import sanitize_form_data, sanitize_form_field_value                 # For input sanitization
from app.logger import get_logger                                                   # Custom application logger
from flask_login import login_user, logout_user, current_user, login_required       # For user seesion management
from app.services.reg_service import register_user, validate_registration_data      # For registration & validation
from flask import render_template, request, redirect, url_for, flash, current_app, session      # For Flask utilities
from app.services.exceptions import ValidationError, AuthenticationError, DatabaseError, AppException # Custom exceptions for error handling

logger = get_logger(__name__) # Logger instance for this module

@auth_bp.route('/')
def index():
    """
    Redirects the base URL of the authentication blueprint
    to the login page.

    Returns:
        Response: A redirect to the login page.
    """
    logger.debug("Auth blueprint index route accessed, redirecting to login.")

    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handles user registration.
    
    For GET requests, it displays the registration form.
    For POST requests, it processes the submitted form data, validates it,
    sanitizes inputs, calls the registration service, and handles success or failure
    by flashing messages and redirecting or re-rendering the form.
    If a user is already authenticated, they are redirected to the home page.

    Returns:
        Response: Renders the registration template or redirects on success/existing session.
    """
    print("***********************************************************************************************")
    if current_user.is_authenticated:
        logger.info(f"Authenticated user {current_user.id} attempted to access /register. Redirecting to home.")

        return redirect(url_for('main.home'))

    # Initialize for potential re-population on validation errors
    form_repopulation_data: Dict[str, Any] = {}
    
    if request.method == 'POST':
        # Initialize registration_payload here to ensure it's always defined for except blocks
        registration_payload: Dict[str, Any] = {}

        try:
            form_data_raw = request.form.to_dict()
            logger.debug(f"Registration attempt with raw form data: { {k:v for k,v in form_data_raw.items() if k != 'password' and k != 'confirm_password'} }") # Log without passwords

            # Define fields for specific sanitization rules
            fields_to_html_escape = {
                'first_name', 'last_name', 'phone_number', 
                'address_line1', 'address_line2', 'city', 'state', 'zip_code'
            }

            fields_to_lowercase = {'email'}

            # Sanitize text fields (excluding passwords which are handled separately)
            # This strips whitespace, lowercases email, and HTML-escapes specified fields.
            sanitized_text_fields = sanitize_form_data(
                form_data_raw, 
                lowercase_fields_set=fields_to_lowercase,
                escape_html_fields=fields_to_html_escape 
            )

            # Construct the final payload for the registration service
            registration_payload.update(sanitized_text_fields)
            # Add raw passwords directly from form_data for hashing by the service
            registration_payload['password'] = form_data_raw.get('password', '')
            registration_payload['confirm_password'] = form_data_raw.get('confirm_password', '')
            # Ensure 'role' is included; it might be from a select and not need escaping other than stripping.
            # If not escaped by sanitize_form_data, it's passed as is (after stripping).
            registration_payload['role'] = form_data_raw.get('role', 'customer') # Default role

            logger.debug(f"Sanitized registration payload (pre-validation): { {k:v for k,v in registration_payload.items() if k != 'password' and k != 'confirm_password'} }")

            # Call the service function to validate registration data
            validation_errors = validate_registration_data(registration_payload)

            if validation_errors:
                # If service returns validation errors, raise a ValidationError
                logger.warning(f"Registration validation failed for email '{registration_payload.get('email')}': {validation_errors}")

                raise ValidationError(
                    message="Registration failed due to validation errors. Please check the form.", 
                    errors={"form_errors": validation_errors} # Structure for template to loop through
                )

            # If validation passes, proceed with user registration service
            logger.info(f"Registration data validated for email '{registration_payload.get('email')}'. Proceeding to register_user service.")
            result_from_service = register_user(registration_payload) # Service handles hashing & DB insert

            # Assuming register_user returns a dict like {"success": True, "message": "...", "user_id": ...}
            # or raises an exception on failure.
            flash(result_from_service.get("message", "Registration successful! Please log in."), "success")

            logger.info(f"User '{registration_payload.get('email')}' registered successfully. ID: {result_from_service.get('user_id')}")

            return redirect(url_for('auth.login'))

        except ValidationError as ve:
            logger.warning(f"Registration ValidationError for '{registration_payload.get('email', 'N/A')}': {ve.user_facing_message} - Errors: {ve.errors}")
            # Flash individual error messages if provided in a structured way by ValidationError
            error_messages_to_flash = []

            if isinstance(ve.errors, dict):\

                for field_errors_list in ve.errors.values(): # Assumes errors is dict of lists

                    if isinstance(field_errors_list, list):
                        error_messages_to_flash.extend(field_errors_list)
            
            if not error_messages_to_flash and ve.user_facing_message != ValidationError.user_message:
                 error_messages_to_flash.append(ve.user_facing_message) # Use the main message if no field errors

            elif not error_messages_to_flash: # Default if no specific messages at all
                 error_messages_to_flash.append(ve.user_message)
            
            for msg in error_messages_to_flash:
                flash(msg, "danger")
            
            # Prepare data to re-populate the form, excluding passwords.
            form_repopulation_data = {k: v for k, v in registration_payload.items() if k not in ['password', 'confirm_password']}
        
        except (DatabaseError, AppException) as app_db_error: # Catch our custom DB or App exceptions
            logger.error(f"Registration failed for '{registration_payload.get('email', 'N/A')}' due to {type(app_db_error).__name__}: {app_db_error.log_message}", exc_info=True)
            flash(app_db_error.user_facing_message, "danger")
            form_repopulation_data = {k: v for k, v in registration_payload.items() if k not in ['password', 'confirm_password']}
        
        except Exception as e: # Catch any other unexpected exceptions
            logger.critical(f"Unexpected error during registration for '{registration_payload.get('email', 'N/A')}': {e}", exc_info=True)
            flash("Registration failed due to an unexpected server error. Please try again later.", "danger")
            form_repopulation_data = {k: v for k, v in registration_payload.items() if k not in ['password', 'confirm_password']}
            
        # Re-render the registration form with errors and repopulated data
        return render_template('register.html', form_data=form_repopulation_data)

    # For GET request, render an empty form
    logger.debug("GET request for /register, rendering registration form.")

    return render_template('register.html', form_data={})


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login.

    For GET requests, it displays the login form.
    For POST requests, it sanitizes inputs, authenticates the user via `auth_service`,
    logs them in using Flask-Login, and redirects them based on their role or to a 
    'next' page if specified. Handles authentication or database errors by flashing messages.
    If a user is already authenticated, they are redirected appropriately.

    Returns:
        Response: Renders the login template or redirects on success/existing session.
    """
    
    if request.method == 'POST':
        # ... (form processing, authentication as in response #81) ...
        try:
            # ... (authenticate_user call) ...
            email_sanitized = request.form.get('email', '').strip().lower()
            password_input = request.form.get('password', '').strip()
            logger.debug(f"Login attempt with sanitized email: {email_sanitized}")
            i = 0
            user = authenticate_user(email_sanitized, password_input)
            login_user(user)

            # ... (flash welcome message) ...
            
            # Role-based redirection after successful login
            user_role = getattr(user, 'role', None)

            if user_role == 'admin':                
                logger.debug("Redirecting admin user to admin.dashboard.")

                return redirect(url_for('admin.dashboard')) # <<< Use new admin endpoint
            
            elif user_role == 'employee':
                logger.debug("Employee role detected. Redirecting to placeholder/home.")
                flash("Employee dashboard is under construction.", "info")
                return redirect(url_for('main.home'))

            logger.debug("Redirecting customer to main.customer.")
            return redirect(url_for('main.customer'))
        # ... (exception handling as in response #81) ...
        except AuthenticationError as ae: 
            logger.warning(f"Authentication failed for email '{email_sanitized}': {ae.user_facing_message}")
            flash(ae.user_facing_message, "danger")
        except DatabaseError as de: 
            logger.error(f"Login database error for email '{email_sanitized}': {de.log_message}", exc_info=True)
            flash(de.user_facing_message, "danger")
        except Exception as e: 
            logger.critical(f"Unexpected error during login for email '{email_sanitized}': {e}", exc_info=True)
            flash("An unexpected server error occurred during login. Please try again.", "danger")

    return render_template('login.html') # Path based on auth_bp template_folder

@auth_bp.route('/logout')
@login_required # Ensures only logged-in users can access this route
def logout():
    """
    Logs out the current authenticated user.
    Clears the user's session using Flask-Login's `logout_user()` function,
    flashes a success message, and redirects to the home page.

    Returns:
        Response: A redirect to the home page.
    """
    user_email_for_log = getattr(current_user, 'email', 'UNKNOWN_USER') 
    user_id_for_log = getattr(current_user, 'id', 'UNKNOWN_ID')
    logger.info(f"User '{user_email_for_log}' (ID: {user_id_for_log}) initiating logout.")
    
    # Clear the shopping cart from the session
    if 'cart' in session:
        session.pop('cart', None)
        logger.info(f"Shopping cart cleared for user '{user_email_for_log}' upon logout.")
    
    # Clear any guest-specific session flags that might persist if user was guest then logged in
    session.pop('guest_checkout_email_prefill', None)
    session.pop('just_placed_order_id', None) 
    session.pop('guest_order_email', None)    
    
    logout_user() # Flask-Login function to log the user out
    
    # Explicitly mark session as modified if items were popped.
    # logout_user() also modifies session, but this ensures our pops are saved.
    session.modified = True 

    flash("You have been successfully logged out. Your cart has been cleared.", "info") 
    logger.info(f"User (formerly '{user_email_for_log}') logged out successfully. Cart cleared. Redirecting to home page.")
    return redirect(url_for('main.home'))