# app/reviews/routes.py

from typing import Dict, Any                            # For type hinting
from . import reviews_api_bp                            # Import the blueprint instance from app/reviews/__init__.py
from app.logger import get_logger                       # Custom application logger
from app.utils import sanitize_html_text                # For sanitizing review comments
from flask import request, jsonify, current_app         
from flask_login import login_required, current_user
from app.services.review_service import (               # Service used to for Reviews(add,update,delete etc)
    add_review, 
    update_review, 
    delete_review_if_owner, 
    get_reviews_by_book, 
    get_user_review_for_book
)
from app.services.exceptions import (                   # Custom exceptions used for exception and error handling
    ValidationError, 
    AuthorizationError, 
    NotFoundError, 
    DatabaseError, 
    AppException
)

logger = get_logger(__name__) # Logger instance for this module

@reviews_api_bp.route('/reviews/<int:book_id>', methods=['GET'])
def api_get_reviews_for_book_route(book_id: int):
    """
    API endpoint to fetch all reviews for a specific book.
    
    Optionally includes an 'is_owner' flag for each review if a user is authenticated,
    indicating if the current user is the author of the review. This helps the
    frontend decide whether to show edit/delete controls.

    Args:
        book_id (int): The ID of the book for which to fetch reviews.

    Returns:
        JSON: A JSON list of review dictionaries, or a JSON error object.
              Each review dictionary includes review details, user information 
              (first name, last name, user_id), and the 'is_owner' flag.
    """
    # Determine user context for logging and ownership check
    user_id_for_ownership_check: int | None = None
    log_user_context = "guest user"

    if current_user.is_authenticated:
        user_id_for_ownership_check = getattr(current_user, 'id', None)
        user_email_log = getattr(current_user, 'email', 'N/A')
        log_user_context = f"user {user_id_for_ownership_check} ({user_email_log})"
        
    logger.info(f"API: Request for reviews for book_id: {book_id} by {log_user_context}.")

    try:
        # Pass current_user.id (if authenticated) to the service to determine 'is_owner' flag
        reviews = get_reviews_by_book(book_id, current_user_id_for_ownership=user_id_for_ownership_check)
        logger.debug(f"API: Found {len(reviews)} reviews for book_id: {book_id}.")

        return jsonify(reviews), 200
    
    except DatabaseError as de:
        logger.error(f"API: Database error fetching reviews for book {book_id}: {de.log_message}", exc_info=True)

        return jsonify({"error": de.user_facing_message, "details": str(de)}), de.status_code
    
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"API: Unexpected error fetching reviews for book {book_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch reviews due to an internal server error."}), 500
    


@reviews_api_bp.route('/reviews', methods=['POST'])
@login_required # User must be logged in to submit or update a review
def api_submit_or_update_review_route():
    """
    API endpoint for an authenticated user to submit a new review or update their existing review for a book.
    The backend service layer determines if it's an add or update based on whether the user
    already has a review for the specified book.
    Expects 'book_id', 'rating' (1-5), and 'comment' (optional) in the form data.

    Returns:
        JSON: A JSON response indicating success or failure, with a message.
    """
    # current_user is guaranteed to be authenticated due to @login_required
    user_id_log = getattr(current_user, 'id', 'UNKNOWN_ID')
    user_email_log = getattr(current_user, 'email', 'UNKNOWN_EMAIL')
    log_user_context = f"user {user_id_log} ({user_email_log})"

    book_id_str = request.form.get('book_id')
    rating_str = request.form.get('rating')
    comment_text_raw = request.form.get('comment', '') # Raw comment from user
    
    logger.info(f"API: {log_user_context} attempting to submit/update review for book_id: {book_id_str}.")

    try:
        # Basic validation for presence and type (more detailed validation in service if needed)
        if not book_id_str or not rating_str:
            logger.warning(f"API Review Submit/Update by {log_user_context}: Missing book_id or rating.")

            raise ValidationError("Book ID and rating are required fields.", 
                                  errors={"form": "Book ID and rating are required."})
        
        try:
            rating_int = int(rating_str)
            book_id_int = int(book_id_str)

        except ValueError:
            logger.warning(f"API Review Submit/Update by {log_user_context}: Invalid integer format for book_id '{book_id_str}' or rating '{rating_str}'.")

            raise ValidationError("Book ID and rating must be valid numbers.", 
                                  errors={"rating": "Invalid rating format.", "book_id": "Invalid book ID format."})

        if not (1 <= rating_int <= 5): # Rating range validation
            logger.warning(f"API Review Submit/Update by {log_user_context}: Invalid rating value '{rating_int}'.")

            raise ValidationError("Rating must be an integer between 1 and 5.", 
                                  errors={"rating": "Rating must be between 1 and 5."})

        # Sanitize comment text before passing to service layer
        sanitized_comment = sanitize_html_text(comment_text_raw)
        logger.debug(f"API Review Submit/Update by {log_user_context}: Sanitized comment length: {len(sanitized_comment if sanitized_comment else '')}")

        # Service layer handles checking for existing review and decides to add or update
        existing_review = get_user_review_for_book(book_id_int, current_user.id)

        if existing_review and existing_review.get('review_id') is not None:
            review_id_to_update = existing_review['review_id']
            logger.info(f"API: {log_user_context} attempting to update existing review_id: {review_id_to_update} for book_id: {book_id_int}")
            update_review(review_id_to_update, rating_int, sanitized_comment, current_user.id)
            message = "Your review has been updated successfully."
            
        else:
            logger.info(f"API: {log_user_context} attempting to add new review for book_id: {book_id_int}")
            add_review(book_id_int, current_user.id, rating_int, sanitized_comment)
            message = "Your review has been added successfully."
        
        return jsonify({"success": True, "message": message}), 200

    except (ValidationError, AuthorizationError, NotFoundError, DatabaseError) as app_error:
        # Log specific application exceptions raised by services or this route
        log_msg_detail = getattr(app_error, 'log_message', str(app_error))
        logger.warning(f"API Review Submit/Update by {log_user_context} for book {book_id_str} failed: {type(app_error).__name__} - {log_msg_detail}", exc_info=True)
        # Return JSON response using the exception's to_dict() method and status_code
        return jsonify(app_error.to_dict()), app_error.status_code
    
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"API: Unexpected error saving review for book_id {book_id_str} by {log_user_context}: {e}", exc_info=True)
        # Return a generic 500 error response
        return jsonify({"error": "An unexpected error occurred while processing your review. Please try again."}), 500


@reviews_api_bp.route('/reviews/<int:review_id>', methods=['DELETE'])
@login_required # User must be logged in to delete a review
def api_delete_review_route(review_id: int):
    """
    API endpoint for an authenticated user to delete their own review.
    The service layer (`delete_review_if_owner`) handles the ownership check
    to ensure a user can only delete reviews they authored.

    Args:
        review_id (int): The ID of the review to be deleted.

    Returns:
        JSON: A JSON response indicating success or failure, with a message.
    """
    # current_user is guaranteed to be authenticated due to @login_required
    user_id_log = getattr(current_user, 'id', 'UNKNOWN_ID')
    user_email_log = getattr(current_user, 'email', 'UNKNOWN_EMAIL')
    log_user_context = f"user {user_id_log} ({user_email_log})"
    logger.info(f"API: Request from {log_user_context} to delete review_id: {review_id}")

    try:
        # delete_review_if_owner service function handles ownership check and deletion
        delete_review_if_owner(review_id, current_user.id) 
        logger.info(f"API: Review {review_id} successfully deleted by {log_user_context}.")

        return jsonify({"success": True, "message": "Review deleted successfully."}), 200
    
    except NotFoundError as nfe:
        logger.warning(f"API Review Deletion by {log_user_context} for review {review_id} failed: {nfe.log_message}")

        return jsonify({"success": False, "error": nfe.user_facing_message}), nfe.status_code
    
    except AuthorizationError as ae:
        logger.warning(f"API Review Deletion by {log_user_context} for review {review_id} unauthorized: {ae.log_message}")

        return jsonify({"success": False, "error": ae.user_facing_message}), ae.status_code
    
    except DatabaseError as de:
        logger.error(f"API Database Error deleting review {review_id} by {log_user_context}: {de.log_message}", exc_info=True)

        return jsonify({"success": False, "error": de.user_facing_message}), de.status_code
    
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"API: Unexpected error deleting review {review_id} by {log_user_context}: {e}", exc_info=True)
        
        return jsonify({"success": False, "error": "Failed to delete review due to an internal server error."}), 500