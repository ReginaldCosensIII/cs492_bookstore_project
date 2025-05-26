# app/services/review_service.py

from datetime import datetime
from app.logger import get_logger # Custom application logger
from typing import List, Dict, Any, Optional # For type hinting
from app.models.db import get_db_connection # For database connections
from psycopg2.extras import RealDictCursor # To get rows as dictionaries
from app.utils import sanitize_html_text # For sanitizing review comments
from app.services.exceptions import (         # Customer exceptions for error handling
    DatabaseError, NotFoundError, AuthorizationError, ValidationError
)

logger = get_logger(__name__) # Logger instance for this module

def get_reviews_by_user_id(user_id: int) -> List[Dict[str, Any]]:
    """
    Fetches all reviews written by a specific user, joined with book titles.
    'created_at' in the returned dictionaries will be a `datetime` object, suitable
    for direct use in Jinja templates with filters like `strftime`.

    Args:
        user_id (int): The ID of the user whose reviews are to be fetched.

    Returns:
        List[Dict[str, Any]]: A list of review dictionaries. Each dictionary includes
                              review details and the 'book_title'. Returns an empty list
                              if no reviews are found or in case of a database error.
    Raises:
        DatabaseError: If an underlying database error occurs during the fetch operation.
                       (This function currently returns [] on error after logging).
    """

    logger.info(f"Service: Fetching all reviews for user_id: {user_id}")
    query = """
        SELECT 
            r.review_id, r.book_id, r.user_id, r.rating, r.comment, r.created_at,
            b.title AS book_title  -- Alias for clarity, matches what model/template might expect
        FROM reviews r
        JOIN books b ON r.book_id = b.book_id
        WHERE r.user_id = %s
        ORDER BY r.created_at DESC;
    """

    conn = None
    user_reviews_list: List[Dict[str, Any]] = []

    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur: # Explicitly ensure RealDictCursor
            cur.execute(query, (user_id,))
            results = cur.fetchall() # List of RealDictRow

            for row_dict in results:
                # For profile page display, keeping created_at as datetime object is fine
                # as Jinja's strftime can be used.
                user_reviews_list.append({
                    "id": row_dict['review_id'], # Common alias
                    "review_id": row_dict['review_id'],
                    "book_id": row_dict['book_id'],
                    "user_id": row_dict['user_id'],
                    "rating": row_dict['rating'],
                    "comment": row_dict['comment'], # Comment from DB is assumed safe or will be escaped at render
                    "created_at": row_dict['created_at'], # Keep as datetime object for template use
                    "book_title": row_dict.get('book_title', 'N/A')
                })

        logger.info(f"Service: Found {len(user_reviews_list)} reviews for user_id: {user_id}")

        return user_reviews_list
    
    except Exception as e:
        logger.error(f"Service: Error fetching reviews for user_id {user_id}: {e}", exc_info=True)
        # Return empty list on error to prevent page crash, consistent with other "get_all" type functions.
        # Route can decide if this should be a user-facing error.
        return [] 
    
    finally:
        if conn:
            conn.close()
            logger.debug(f"Database connection closed for get_reviews_by_user_id (user_id: {user_id}).")


def add_review(book_id: int, user_id: int, rating: int, raw_comment: str) -> Dict[str, Any]:
    """
    Adds a new review to the database for a given book by a specific user.
    The comment text is sanitized before insertion.

    Args:
        book_id (int): The ID of the book being reviewed.
        user_id (int): The ID of the user submitting the review.
        rating (int): The star rating (e.g., 1-5).
        raw_comment (str): The raw comment text from the user. This will be sanitized.

    Returns:
        Dict[str, Any]: A dictionary containing the 'review_id' and 'created_at' (as ISO string)
                        of the newly created review.

    Raises:
        DatabaseError: If the review cannot be added due to a database issue.
        ValidationError: If input data (e.g. rating) is invalid (though often checked by route).
    """

    logger.info(f"Service: Attempting to add review for book_id: {book_id} by user_id: {user_id}")
    
    # Sanitize the comment text to prevent XSS if it's displayed as HTML later.
    sanitized_comment = sanitize_html_text(raw_comment)
    
    # Basic validation for rating (can be expanded)
    if not (1 <= rating <= 5):
        logger.warning(f"Invalid rating '{rating}' for review by user {user_id} on book {book_id}.")
        raise ValidationError("Rating must be between 1 and 5.", errors={"rating": "Invalid rating value."})

    query = """
        INSERT INTO reviews (book_id, user_id, rating, comment)
        VALUES (%s, %s, %s, %s)
        RETURNING review_id, created_at;
    """
    conn = None

    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur: 
            cur.execute(query, (book_id, user_id, rating, sanitized_comment))
            result_row = cur.fetchone() # dict-like RealDictRow
            conn.commit()

            if result_row and 'review_id' in result_row:
                logger.info(f"Review added with ID {result_row['review_id']} for book {book_id} by user {user_id}")
                return {
                    "review_id": result_row['review_id'],
                    "created_at": result_row['created_at'].isoformat() if result_row.get('created_at') else None
                }
            
            else:
                # This case should ideally not be reached if RETURNING is used and insert is successful.
                logger.error(f"Failed to retrieve review details after adding for book {book_id}, user {user_id}.")
                raise DatabaseError("Failed to confirm review creation after database insert.")
            
    except Exception as e:

        if conn:
            conn.rollback()

        logger.error(f"Error adding review for book {book_id} by user {user_id}: {e}", exc_info=True)

        raise DatabaseError("Could not add your review due to a database issue. Please try again.", original_exception=e)
    
    finally:
        if conn:
            conn.close()
            logger.debug(f"Database connection closed for add_review (book_id: {book_id}, user_id: {user_id}).")


def update_review(review_id: int, rating: int, raw_comment: str, current_user_id: int) -> bool:
    """
    Updates an existing review in the database.
    Performs an ownership check to ensure only the user who wrote the review can update it.
    The comment text is sanitized before updating.

    Args:
        review_id (int): The ID of the review to be updated.
        rating (int): The new star rating (e.g., 1-5).
        raw_comment (str): The new raw comment text from the user. This will be sanitized.
        current_user_id (int): The ID of the user attempting to update the review, for ownership verification.

    Returns:
        bool: True if the review was successfully updated.

    Raises:
        NotFoundError: If the review with the given `review_id` is not found.
        AuthorizationError: If `current_user_id` does not match the `user_id` of the review.
        DatabaseError: If an unexpected database error occurs.
        ValidationError: If input data (e.g. rating) is invalid.
    """

    logger.info(f"Service: User {current_user_id} attempting to update review_id: {review_id}")
    
    sanitized_comment = sanitize_html_text(raw_comment)

    if not (1 <= rating <= 5):
        logger.warning(f"Invalid rating '{rating}' for update attempt on review {review_id}.")
        raise ValidationError("Rating must be between 1 and 5.", errors={"rating": "Invalid rating value."})

    # The UPDATE query includes `AND user_id = %s` for an atomic ownership check and update.
    # If rowcount is 0, we then check if it was due to not found or not owned.
    query_update = """
        UPDATE reviews
        SET rating = %s, comment = %s, created_at = CURRENT_TIMESTAMP
        WHERE review_id = %s AND user_id = %s; 
    """

    conn = None

    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query_update, (rating, sanitized_comment, review_id, current_user_id))
            
            if cur.rowcount == 0: # No rows updated
                # Check if the review exists at all to differentiate "not found" vs "not owned"
                cur.execute("SELECT user_id FROM reviews WHERE review_id = %s", (review_id,))
                review_owner_row = cur.fetchone()

                if not review_owner_row:
                    logger.warning(f"Update failed: Review {review_id} not found in database.")
                    raise NotFoundError(resource_name="Review", resource_id=review_id)
                
                else: 
                    # Review exists, but user_id didn't match (or other concurrent update issue)
                    logger.warning(f"Update failed: User {current_user_id} not authorized to update review {review_id} (owned by {review_owner_row.get('user_id')}), or review already matched update content.")
                    raise AuthorizationError("You are not authorized to update this review, or no changes were detected.")
            
            conn.commit()
            logger.info(f"Review {review_id} updated successfully by user {current_user_id}.")

            return True
            
    except (NotFoundError, AuthorizationError, ValidationError): # Re-raise specific known exceptions
        if conn: conn.rollback() # Rollback if transaction started and a business error occurred

        raise

    except Exception as e:
        if conn: conn.rollback()

        logger.error(f"Error updating review {review_id} by user {current_user_id}: {e}", exc_info=True)

        raise DatabaseError("Could not update your review due to a database issue.", original_exception=e)
    
    finally:
        if conn:
            conn.close()
            logger.debug(f"Database connection closed for update_review (review_id: {review_id}).")


def delete_review_if_owner(review_id: int, current_user_id: int) -> bool:
    """
    Deletes a review from the database if the `current_user_id` matches the review's `user_id`.
    This function ensures that users can only delete their own reviews.

    Args:
        review_id (int): The ID of the review to be deleted.
        current_user_id (int): The ID of the user attempting the deletion.

    Returns:
        bool: True if the review was successfully deleted.

    Raises:
        NotFoundError: If the review with the given `review_id` is not found.
        AuthorizationError: If the `current_user_id` does not match the `user_id` of the review
                            (i.e., user is not the owner).
        DatabaseError: If an unexpected database error occurs during the deletion process.
    """
    logger.info(f"Service: User {current_user_id} attempting to delete review_id: {review_id}")
    conn = None

    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # First, fetch the review to verify existence and ownership.
            cur.execute("SELECT user_id FROM reviews WHERE review_id = %s;", (review_id,))
            review_data_row = cur.fetchone()

            if not review_data_row:
                logger.warning(f"Delete review failed: Review with ID {review_id} not found.")
                raise NotFoundError(resource_name="Review", resource_id=review_id)

            if review_data_row['user_id'] != current_user_id:
                # Future: Add a check here if current_user.is_admin() to allow admin override.
                logger.warning(
                    f"Authorization failed: User {current_user_id} attempted to delete review {review_id} "
                    f"owned by user {review_data_row['user_id']}."
                )

                raise AuthorizationError("You are not authorized to delete this review as you are not its author.")

            # If ownership is confirmed, proceed with deletion.
            cur.execute("DELETE FROM reviews WHERE review_id = %s AND user_id = %s;", (review_id, current_user_id))
            conn.commit()
            
            if cur.rowcount == 0:
                # This case should ideally be caught by the SELECT and ownership check above.
                # However, it could happen in a rare race condition if the review was deleted 
                # by another process between the SELECT and DELETE.
                logger.warning(
                    f"Review {review_id} was found but not deleted (rowcount 0 during DELETE). "
                    "This might indicate it was deleted concurrently or an issue with the delete query."
                )

                # Consider if this should be NotFoundError or a specific DatabaseError.
                # If select confirmed it exists and belongs to user, then 0 rows on delete is odd.
                raise DatabaseError("Review was found but could not be deleted unexpectedly. It might have been removed by another process.")
            
            logger.info(f"Review {review_id} deleted successfully by owner {current_user_id}.")

            return True
            
    except (NotFoundError, AuthorizationError): # Re-raise specific known exceptions
        # No explicit rollback needed here as these errors typically occur before DML or are checks.
        raise

    except Exception as e:
        if conn: conn.rollback() # Rollback on unexpected errors during DML phase

        logger.error(f"Error deleting review {review_id} by user {current_user_id}: {e}", exc_info=True)

        raise DatabaseError("Could not delete the review due to a database issue.", original_exception=e)
    
    finally:
        if conn:
            conn.close()
            logger.debug(f"Database connection closed for delete_review_if_owner (review_id: {review_id}).")


def get_reviews_by_book(book_id: int, current_user_id_for_ownership: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetches all reviews for a specific book, joined with the reviewer's first and last names.
    If `current_user_id_for_ownership` is provided, an 'is_owner' boolean flag is added
    to each review dictionary indicating if the current viewer is the author of that review.
    `created_at` is returned as an ISO 8601 formatted string, suitable for JSON responses.

    Args:
        book_id (int): The ID of the book for which to fetch reviews.
        current_user_id_for_ownership (Optional[int]): The ID of the currently authenticated user,
                                                       used to determine review ownership.
                                                       If None (e.g., for a guest), 'is_owner' will be False.
    Returns:
        List[Dict[str, Any]]: A list of review dictionaries. Each dictionary includes review details,
                              user information (first name, last name, user_id), and an 'is_owner' flag.
                              Returns an empty list if no reviews are found or on database error.
    """
    logger.debug(f"Service: Fetching reviews for book_id: {book_id}. Ownership check for user: {current_user_id_for_ownership}")

    query = """
        SELECT r.review_id, r.user_id, r.book_id, r.rating, r.comment, r.created_at,
               u.first_name, u.last_name
        FROM reviews r
        JOIN users u ON r.user_id = u.user_id
        WHERE r.book_id = %s
        ORDER BY r.created_at DESC;
    """

    conn = None
    reviews_list: List[Dict[str, Any]] = []

    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur: # Ensure RealDictCursor
            cur.execute(query, (book_id,))
            results = cur.fetchall() # List of RealDictRow

            for r_dict in results:
                created_at_iso_string = r_dict['created_at'].isoformat() if r_dict.get('created_at') else None
                
                is_owner = False # Default to False

                if current_user_id_for_ownership is not None and r_dict.get('user_id') == current_user_id_for_ownership:
                    is_owner = True
                
                reviews_list.append({
                    "id": r_dict['review_id'], # Alias for review_id, often used in frontend
                    "review_id": r_dict['review_id'],
                    "book_id": r_dict['book_id'],
                    "rating": r_dict['rating'],
                    "comment": r_dict['comment'], # Assumed sanitized if stored this way, or escape at render
                    "created_at": created_at_iso_string, # ISO format for JSON/JavaScript
                    "user": { # Nested user object can be convenient for frontend
                        "id": r_dict['user_id'],
                        "first_name": r_dict.get('first_name'),
                        "last_name": r_dict.get('last_name')
                    },
                    # Keep flat versions for compatibility if any part of JS expects them directly
                    "user_first_name": r_dict.get('first_name'), 
                    "user_last_name": r_dict.get('last_name'),
                    "user_id": r_dict['user_id'], # Explicit user_id of the reviewer
                    "is_owner": is_owner # Crucial flag for frontend to show/hide edit/delete buttons
                })

        logger.debug(f"Service: Found {len(reviews_list)} reviews for book_id: {book_id}")
        return reviews_list
    
    except Exception as e:
        logger.error(f"Service: Error fetching reviews for book {book_id}: {e}", exc_info=True)
        # For API calls, route handler might convert this to a 500 error response.
        # Returning empty list here can simplify route handler logic if no reviews is not an error.
        return [] 
    
    finally:
        if conn:
            conn.close()
            logger.debug(f"Database connection closed for get_reviews_by_book (book_id: {book_id}).")


def get_user_review_for_book(book_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetches a specific user's review for a specific book, if one exists.
    This is often used to check if a user has already reviewed a book before allowing
    them to submit a new review (they should update instead).
    'created_at' is returned as an ISO 8601 string if present.

    Args:
        book_id (int): The ID of the book.
        user_id (int): The ID of the user.

    Returns:
        Optional[Dict[str, Any]]: A dictionary representing the review if found, 
                                  otherwise `None`.
    
    Raises:
        DatabaseError: If an unexpected error occurs during database interaction.
    """
    logger.debug(f"Service: Fetching review for book_id: {book_id} by user_id: {user_id}")
    query = """
        SELECT review_id, book_id, user_id, rating, comment, created_at 
        FROM reviews 
        WHERE book_id = %s AND user_id = %s;
    """

    conn = None

    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur: # Ensure RealDictCursor
            cur.execute(query, (book_id, user_id))
            review_data_row = cur.fetchone() # dict-like RealDictRow or None
        
        if review_data_row:
            # Convert datetime to ISO string if it's to be passed directly to jsonify later by a route

            if review_data_row.get('created_at'):
                review_data_row['created_at'] = review_data_row['created_at'].isoformat()

            logger.debug(f"Found existing review for book {book_id} by user {user_id}: {review_data_row['review_id']}")

            return dict(review_data_row) # Convert RealDictRow to plain dict
        
        else:
            logger.debug(f"No existing review found for book {book_id} by user {user_id}.")
            return None
            
    except Exception as e:
        logger.error(f"Service: Error fetching user's specific review for book {book_id}, user {user_id}: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Could not retrieve your existing review for this book.", 
            original_exception=e
        )
    
    finally:
        if conn:
            conn.close()
            logger.debug(f"Database connection closed for get_user_review_for_book (book_id: {book_id}, user_id: {user_id}).")