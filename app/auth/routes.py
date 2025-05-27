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
    if current_user.is_authenticated:
        logger.info(f"User {current_user.id} already authenticated, attempting to access /login. Redirecting.")

        if hasattr(current_user, 'role'): # Check if role attribute exists

            if current_user.role == 'admin':
                return redirect(url_for('main.admin_dashboard'))
            
            elif current_user.role == 'employee':
                return redirect(url_for('main.employee_dashboard'))
            
        return redirect(url_for('main.customer')) # Default redirect for authenticated customer or unknown role

    if request.method == 'POST':
        form_data = request.form.to_dict()
        email_raw = form_data.get('email', '')
        password_input = form_data.get('password', '') # Raw password

        # Sanitize email: strip whitespace and lowercase. HTML escaping is not needed for email.
        email_sanitized = sanitize_form_field_value(email_raw, key_name='email', should_escape_html=False)
        logger.debug(f"Login attempt for sanitized email: '{email_sanitized}'")

        try:
            user = authenticate_user(email_sanitized, password_input) # auth_service handles actual authentication            
            login_user(user) # Flask-Login handles setting up the user session
            user_name_for_flash = getattr(user, 'first_name', 'User').title()
            logger.info(f"User '{user.email}' (ID: {user.id}, Role: {user.role}) logged in successfully.")
            flash(f"Welcome back, {user_name_for_flash}!", "success")

            # Redirect to 'next' page if provided (e.g., after being redirected by @login_required)
            next_page = request.args.get('next')
            # Basic security check for open redirect vulnerability
            if next_page and next_page.startswith('/') and not next_page.startswith('//'):
                logger.debug(f"Redirecting logged-in user to 'next' page: {next_page}")

                return redirect(next_page)
            
            # Role-based redirection if no 'next' page
            if hasattr(user, 'role'):
                if user.role == 'admin':
                    logger.debug("Redirecting admin user to admin_dashboard.")

                    return redirect(url_for('main.admin_dashboard'))
                
                elif user.role == 'employee':
                    logger.debug("Redirecting employee user to employee_dashboard.")

                    return redirect(url_for('main.employee_dashboard'))
            
            logger.debug("Redirecting customer or user with default role to customer dashboard.")

            return redirect(url_for('main.customer')) # Default redirect

        except AuthenticationError as ae: # Custom exception from auth_service
            logger.warning(f"Authentication failed for email '{email_sanitized}': {ae.user_facing_message}")
            flash(ae.user_facing_message, "danger")

        except DatabaseError as de: # Custom exception from auth_service
            logger.error(f"Login database error for email '{email_sanitized}': {de.log_message}", exc_info=True)
            flash(de.user_facing_message, "danger")

        except Exception as e: # Catch any other unexpected exceptions
            logger.critical(f"Unexpected error during login process for email '{email_sanitized}': {e}", exc_info=True)
            flash("An unexpected server error occurred during login. Please try again later.", "danger")

    # For GET request or if POST fails and needs to re-render form
    logger.debug("GET request for /login or re-rendering login form after POST error.")
    return render_template('login.html')


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