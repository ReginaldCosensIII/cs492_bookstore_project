# cs492_bookstore_project/app/main/routes.py
from flask import render_template, redirect, url_for, flash, current_app, request
from flask_login import login_required, current_user
from typing import List, Dict, Any # For type hinting

from . import main_bp # Import the blueprint instance from app/main/__init__.py
from app.services.book_service import get_all_books, get_all_distinct_genres
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

def _get_book_display_params_from_request() -> Dict[str, Any]:
    """
    Helper to extract and normalize book display parameters (filter, search, sort)
    from the current request's query arguments.

    Returns:
        Dict[str, Any]: A dictionary containing 'genre_filter', 'search_term',
                        'sort_by', and 'sort_order'.
    """
    genre_filter = request.args.get('genre', 'all', type=str).strip().lower()
    search_term = request.args.get('search', '', type=str).strip()
    sort_by = request.args.get('sort_by', 'title', type=str).strip().lower() # Default sort by title
    sort_order = request.args.get('sort_order', 'asc', type=str).strip().lower()
    if sort_order not in ['asc', 'desc']:
        sort_order = 'asc' # Default to ascending if invalid value

    return {
        "genre_filter": genre_filter if genre_filter != 'all' else None, # Pass None if 'all'
        "search_term": search_term,
        "sort_by": sort_by,
        "sort_order": sort_order,
        # For repopulating the form, pass back the original values
        "current_genre_filter": genre_filter, 
        "current_search_term": search_term,
        "current_sort_by": sort_by,
        "current_sort_order": sort_order
    }

@main_bp.route("/")
def home():
    """
    Renders the home page of the bookstore (`home.html`).
    Fetches books based on optional query parameters for filtering by genre,
    searching by title/author, and sorting. Also fetches a list of distinct genres
    for the filter dropdown.

    Query Parameters:
        - `genre` (str, optional): Filter books by this genre.
        - `search` (str, optional): Search term for book titles or authors.
        - `sort_by` (str, optional): Column to sort books by ('title', 'author', 'price', 'newest').
                                     Defaults to 'title'.
        - `sort_order` (str, optional): Sort direction ('asc' or 'desc'). Defaults to 'asc'.

    Returns:
        Response: Renders `home.html` with the list of books, available genres,
                  and current filter/sort parameters.
    """
    requester_context = _get_user_context_for_log_main()
    display_params = _get_book_display_params_from_request()
    logger.info(f"Route: Home page requested by {requester_context} with params: {display_params}")

    books_objects: List[Book] = [] # List of Book objects
    books_for_template: List[Dict[str, Any]] = [] # List of dictionaries for JSON
    genres: List[str] = []
    try:
        books_objects = get_all_books(
            genre_filter=display_params["genre_filter"],
            search_term=display_params["search_term"],
            sort_by=display_params["sort_by"],
            sort_order=display_params["sort_order"]
        )
        # Convert Book objects to dictionaries for the template/JSON
        for book_obj in books_objects:
            if hasattr(book_obj, 'to_dict') and callable(book_obj.to_dict):
                books_for_template.append(book_obj.to_dict()) 
            else:
                # Fallback or log error if to_dict is missing, though it should be there
                logger.warning(f"Book object (ID: {getattr(book_obj, 'book_id', 'N/A')}) missing to_dict method.")

        genres = get_all_distinct_genres()
        logger.debug(f"Route: Retrieved {len(books_for_template)} books and {len(genres)} genres for home page.")
    except DatabaseError as de:
        logger.error(f"Route: Database error fetching data for home page: {de.log_message}", exc_info=True)
        flash("Could not load book data due to a database issue. Please try again later.", "danger")
    except Exception as e:
        logger.error(f"Route: Unexpected error fetching data for home page: {e}", exc_info=True)
        flash("An unexpected error occurred while loading book data. Please try again.", "danger")

    return render_template("home.html", 
                           books=books_for_template, # Pass the list of dictionaries
                           genres=genres,
                           current_filters=display_params,
                           action_url=url_for('main.home')
                           )

@main_bp.route('/customer')
@login_required 
def customer():
    """
    Renders the customer-specific dashboard page (`customer.html`).
    Fetches books based on optional query parameters for filtering by genre,
    searching by title/author, and sorting. Also fetches distinct genres for filters.
    Accessible only to authenticated users.

    Query Parameters: (Same as home route)
        - `genre`, `search`, `sort_by`, `sort_order`

    Returns:
        Response: Renders `customer.html` with books, genres, and filter/sort parameters.
    """
    user_context_log = _get_user_context_for_log_main() 
    display_params = _get_book_display_params_from_request()
    logger.info(f"Route: Customer dashboard requested by {user_context_log} with params: {display_params}")

    books_objects: List[Book] = []
    books_for_template: List[Dict[str, Any]] = []
    genres: List[str] = []
    try:
        books_objects = get_all_books(
            genre_filter=display_params["genre_filter"],
            search_term=display_params["search_term"],
            sort_by=display_params["sort_by"],
            sort_order=display_params["sort_order"]
        )
        for book_obj in books_objects:
            if hasattr(book_obj, 'to_dict') and callable(book_obj.to_dict):
                books_for_template.append(book_obj.to_dict())
            else:
                logger.warning(f"Book object (ID: {getattr(book_obj, 'book_id', 'N/A')}) missing to_dict method.")

        genres = get_all_distinct_genres()
        logger.debug(f"Route: Retrieved {len(books_for_template)} books and {len(genres)} for customer dashboard ({user_context_log}).")
    # ... (error handling as before) ...
    except DatabaseError as de:
        logger.error(f"Route: Database error fetching data for home page: {de.log_message}", exc_info=True)
        flash("Could not load book data due to a database issue. Please try again later.", "danger")
    except Exception as e:
        logger.error(f"Route: Unexpected error fetching data for home page: {e}", exc_info=True)
        flash("An unexpected error occurred while loading book data. Please try again.", "danger")

    return render_template('customer.html', 
                           books=books_for_template, # Pass the list of dictionaries
                           genres=genres,
                           current_filters=display_params,
                           action_url=url_for('main.customer')
                           ) 

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

@main_bp.route('/about')
def about_page():
    """Renders the About Us page."""
    logger.info("Route: About Us page requested.")
    return render_template('about.html')

@main_bp.route('/faq')
def faq_page():
    """Renders the FAQ page."""
    logger.info("Route: FAQ page requested.")
    return render_template('faq.html')

@main_bp.route('/contact')
def contact_page():
    """Renders the Contact Us page."""
    logger.info("Route: Contact Us page requested.")
    return render_template('contact.html')

@main_bp.route('/privacy-policy')
def privacy_policy_page():
    """Renders the Privacy Policy page."""
    logger.info("Route: Privacy Policy page requested.")
    return render_template('privacy_policy.html')

@main_bp.route('/terms-of-service')
def terms_of_service_page():
    """Renders the Terms of Service page."""
    logger.info("Route: Terms of Service page requested.")
    return render_template('terms_of_service.html')

# Note: The routes for /admin-dashboard and /employee-dashboard have been removed.
# They will be handled by their own dedicated blueprints (e.g., app.admin).