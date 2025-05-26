# app/main/routes.py

from . import main_bp                                                       # Import the blueprint instance
from typing import List                                                     # For type hinting
from app.logger import get_logger                                           # Custom application logger
from app.services.book_service import get_all_books                         # Service to fetch all the books in DB
from flask_login import login_required, current_user 
from app.services.order_service import get_orders_by_user                   # Service to fetch all the order by a user
from app.services.review_service import get_reviews_by_user_id              # Service to fetch all reviews by a user
from app.services.exceptions import AuthorizationError, DatabaseError       # Custom exceptions
from flask import render_template, redirect, url_for, flash, current_app

logger = get_logger(__name__) # Logger instance for this module

def _get_user_context_for_log_main() -> str: # Renamed to avoid conflict if moved to utils
    """
    Helper function to generate a consistent string representation for logging 
    the current user context (authenticated user or guest) within the main blueprint.

    Returns:
        str: A string identifying the user, e.g., "user 123 (user@example.com)" or "guest user".
    """
    if current_user.is_authenticated:
        user_id_log = getattr(current_user, 'id', 'UNKNOWN_ID')
        user_email_log = getattr(current_user, 'email', 'UNKNOWN_EMAIL')

        return f"user {user_id_log} ({user_email_log})"
    
    return "guest user"


@main_bp.route("/")
def home():
    """
    Renders the home page of the bookstore.
    Fetches all books using the book service and passes them to the template.

    Returns:
        Response: Renders the `home.html` template with the list of all books.
    """
    requester_context = _get_user_context_for_log_main()
    logger.info(f"Home page requested by {requester_context}.")

    try:
        books = get_all_books()
        logger.debug(f"Retrieved {len(books)} books for home page display.")

    except DatabaseError as de:
        logger.error(f"Database error fetching books for home page: {de.log_message}", exc_info=True)
        flash("Could not load books at this time due to a database issue. Please try again later.", "danger")
        books = [] # Render page with empty book list on DB error

    except Exception as e:
        logger.error(f"Unexpected error fetching books for home page: {e}", exc_info=True)
        flash("An unexpected error occurred while loading books. Please try again.", "danger")
        books = []

    return render_template("home.html", books=books)


@main_bp.route('/customer')
@login_required # This page is specifically for logged-in customers
def customer():
    """
    Renders the customer-specific dashboard page.
    This page is accessible only to authenticated users. It fetches and displays
    all books, similar to the home page, but within a customer-centric view.
    Further role-specific checks can be added if 'customer' is a distinct role
    with specific permissions beyond general authentication.

    Returns:
        Response: Renders the `customer.html` template with the list of all books.
    
    Raises:
        AuthorizationError: If an authenticated user who is not considered a 'customer'
                            (based on future role definitions) tries to access this page.
                            (Currently, `@login_required` is the primary gate).
    """
    # Perform a more specific role check if 'customer' is a defined role with distinct access.
    # For now, `login_required` ensures an authenticated user.
    # The User model's `is_customer()` method can be used for more fine-grained checks if implemented.
    # Example check (if User model has a `role` attribute and `is_customer` method):
    # if not current_user.is_customer():
    #     logger.warning(f"User {current_user.id} ({current_user.email}) with role '{current_user.role}' "
    #                    f"attempted to access customer dashboard.")
    #     raise AuthorizationError("You do not have permission to access this customer dashboard.")
    
    logger.info(f"Customer dashboard requested by user {current_user.id} ({current_user.email}).")

    try:
        books = get_all_books()
        logger.debug(f"Retrieved {len(books)} books for customer dashboard.")

    except DatabaseError as de:
        logger.error(f"Database error fetching books for customer dashboard (user: {current_user.id}): {de.log_message}", exc_info=True)
        flash("Could not load books due to a database issue. Please try again later.", "danger")
        books = []

    except Exception as e:
        logger.error(f"Unexpected error fetching books for customer dashboard (user: {current_user.id}): {e}", exc_info=True)
        flash("An unexpected error occurred while loading books. Please try again.", "danger")
        books = []
        
    return render_template('customer.html', books=books) 


@main_bp.route('/profile')
@login_required # User must be logged in to view their profile
def profile_page():
    """
    Renders the user's profile page.
    Displays the user's order history and their submitted reviews.
    Data is fetched using `order_service.get_orders_by_user` and 
    `review_service.get_reviews_by_user_id`.

    Returns:
        Response: Renders the `profile.html` template with the user's orders and reviews.
                  Flashes an error message if data cannot be retrieved.
    """
    user_context_log = _get_user_context_for_log_main() # Will always be an authenticated user here
    logger.info(f"Profile page requested for {user_context_log}.")
    
    user_orders: List = []
    user_reviews_list: List[Dict[str, Any]] = []
    
    try:
        logger.debug(f"Fetching order history for {user_context_log}.")
        user_orders = get_orders_by_user(current_user.id)
        logger.info(f"Found {len(user_orders)} orders for {user_context_log}.")
        
        logger.debug(f"Fetching review history for {user_context_log}.")
        user_reviews_list = get_reviews_by_user_id(current_user.id)
        logger.info(f"Found {len(user_reviews_list)} reviews for {user_context_log}.")
        
    except DatabaseError as de:
        logger.error(f"Database error fetching profile data (orders or reviews) for {user_context_log}: {de.log_message}", exc_info=True)
        flash("Could not load your profile data due to a database issue. Please try again later.", "danger")

    except Exception as e: # Catch any other unexpected errors during data fetching
        logger.error(f"Unexpected error fetching profile data for {user_context_log}: {e}", exc_info=True)
        flash("An unexpected error occurred while loading your profile data. Please contact support.", "danger")
        
    return render_template('profile.html', 
                           orders=user_orders,
                           reviews=user_reviews_list 
                           )


@main_bp.route('/admin-dashboard')
@login_required # User must be logged in
def admin_dashboard():
    """
    Renders the administrator dashboard page.
    Access is restricted to users with the 'admin' role.

    Returns:
        Response: Renders the `admin.html` template.
    
    Raises:
        AuthorizationError: If the currently logged-in user is not an admin.
    """
    # Ensure User model has an is_admin() method or role attribute check
    if not (hasattr(current_user, 'is_admin') and current_user.is_admin()): 
        user_email_log = getattr(current_user, 'email', 'N/A')
        user_role_log = getattr(current_user, 'role', 'N/A')
        logger.warning(
            f"User '{user_email_log}' (Role: '{user_role_log}') attempted to access admin dashboard without permission."
        )
        # Raise custom AuthorizationError to be handled by global error handler or app-level handler
        raise AuthorizationError("You do not have permission to access the administrator dashboard.")
    
    user_email_log = getattr(current_user, 'email', 'N/A') # Safe access
    logger.info(f"Admin dashboard accessed by user: {user_email_log}")

    return render_template('admin.html')


@main_bp.route('/employee-dashboard')
@login_required # User must be logged in
def employee_dashboard():
    """
    Renders the employee dashboard page.
    Access is restricted to users with 'employee' or 'admin' roles.

    Returns:
        Response: Renders the `employee.html` template.
    
    Raises:
        AuthorizationError: If the logged-in user is not an employee or admin.
    """
    # Ensure User model has is_employee() and is_admin() methods or role attribute checks
    is_employee = hasattr(current_user, 'is_employee') and current_user.is_employee()
    is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin()

    if not (is_employee or is_admin): 
        user_email_log = getattr(current_user, 'email', 'N/A')
        user_role_log = getattr(current_user, 'role', 'N/A')
        logger.warning(
            f"User '{user_email_log}' (Role: '{user_role_log}') attempted to access employee dashboard without permission."
        )

        raise AuthorizationError("You do not have permission to access the employee dashboard.")
        
    user_email_log = getattr(current_user, 'email', 'N/A')
    logger.info(f"Employee dashboard accessed by user: {user_email_log}")
    
    return render_template('employee.html')