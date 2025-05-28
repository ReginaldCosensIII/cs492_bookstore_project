# cs492_bookstore_project/app/main/routes.py
from flask import render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from typing import List, Dict, Any # For type hinting

from . import main_bp # Import the blueprint instance from app/main/__init__.py
from app.services.book_service import get_all_books
from app.services.order_service import get_orders_by_user 
from app.services.review_service import get_reviews_by_user_id 
from app.services.exceptions import AuthorizationError, DatabaseError # Custom exceptions
from app.logger import get_logger # Custom application logger

logger = get_logger(__name__) # Logger instance for this module

def _get_user_context_for_log_main() -> str:
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
    Fetches all books using the book service and passes them to the `home.html` template
    for display. Handles potential database errors gracefully.

    Returns:
        Response: Renders the `home.html` template with a list of all available books.
    """
    requester_context = _get_user_context_for_log_main()
    logger.info(f"Route: Home page requested by {requester_context}.")
    books: List[Any] = [] 

    try:
        books = get_all_books()
        logger.debug(f"Route: Retrieved {len(books)} books for home page display.")

    except DatabaseError as de:
        logger.error(f"Route: Database error fetching books for home page: {de.log_message}", exc_info=True)
        flash("Could not load books at this time due to a database issue. Please try again later.", "danger")

    except Exception as e:
        logger.error(f"Route: Unexpected error fetching books for home page: {e}", exc_info=True)
        flash("An unexpected error occurred while loading books. Please try again.", "danger")

    return render_template("home.html", books=books)


@main_bp.route('/customer')
@login_required 
def customer():
    """
    Renders the customer-specific dashboard page (`customer.html`).
    Accessible only to authenticated users. Currently displays all books.
    Future enhancements could include more role-specific checks if 'customer'
    becomes a more distinct role beyond general authentication.

    Returns:
        Response: Renders the `customer.html` template with a list of all available books.
    """
    user_context_log = _get_user_context_for_log_main()
    # Role check example (currently, @login_required is the main gate)
    # if not (hasattr(current_user, 'role') and current_user.role == 'customer'):
    #     logger.warning(f"{user_context_log} (role: {getattr(current_user, 'role', 'N/A')}) "
    #                    f"attempted to access customer dashboard without specific customer role.")
    #     # Depending on policy, could raise AuthorizationError or just proceed if any logged-in user is okay
    #     pass # For now, allow any authenticated user

    logger.info(f"Route: Customer dashboard requested by {user_context_log}")
    books: List[Any] = []

    try:
        books = get_all_books()
        logger.debug(f"Route: Retrieved {len(books)} books for customer dashboard for {user_context_log}.")

    except DatabaseError as de:
        logger.error(f"Route: Database error fetching books for customer dashboard ({user_context_log}): {de.log_message}", exc_info=True)
        flash("Could not load books due to a database issue. Please try again later.", "danger")

    except Exception as e:
        logger.error(f"Route: Unexpected error fetching books for customer dashboard ({user_context_log}): {e}", exc_info=True)
        flash("An unexpected error occurred while loading books. Please try again.", "danger")
        
    return render_template('customer.html', books=books) 


@main_bp.route('/profile')
@login_required 
def profile_page():
    """
    Renders the user's profile page (`profile.html`).
    Displays the authenticated user's order history and their submitted reviews.
    Data is fetched using `order_service.get_orders_by_user` and 
    `review_service.get_reviews_by_user_id`.

    Returns:
        Response: Renders `profile.html` with user's orders and reviews.
                  Flashes an error if data retrieval fails.
    """
    user_context_log = _get_user_context_for_log_main() 
    logger.info(f"Route: Profile page requested for {user_context_log}")
    
    user_orders: List[Any] = []
    user_reviews_list: List[Dict[str, Any]] = [] 
    
    try:
        logger.debug(f"Route: Fetching order history for {user_context_log}.")
        user_orders = get_orders_by_user(current_user.id) # type: ignore
        logger.info(f"Route: Found {len(user_orders)} orders for {user_context_log}.")
        
        logger.debug(f"Route: Fetching review history for {user_context_log}.")
        user_reviews_list = get_reviews_by_user_id(current_user.id) # type: ignore
        logger.info(f"Route: Found {len(user_reviews_list)} reviews for {user_context_log}.")
        
    except DatabaseError as de:
        logger.error(f"Route: Database error fetching profile data for {user_context_log}: {de.log_message}", exc_info=True)
        flash("Could not load your profile data due to a database issue. Please try again later.", "danger")

    except Exception as e: 
        logger.error(f"Route: Unexpected error fetching profile data for {user_context_log}: {e}", exc_info=True)
        flash("An unexpected error occurred while loading your profile data. Please contact support.", "danger")
        
    return render_template('profile.html', 
                           orders=user_orders,
                           reviews=user_reviews_list 
                           )

# Removed old /admin-dashboard and /employee-dashboard routes from main_bp.
# These will now be handled by their own dedicated blueprints (e.g., app.admin).