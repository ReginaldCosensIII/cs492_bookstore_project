# app/models/review.py

from datetime import datetime # For type hinting if needed
from app.logger import get_logger # Use the app's configured logger

# Use the app's configured logger
logger = get_logger(__name__)

class Review:
    """
    Represents a customer review for a book.

    Attributes:
        review_id (int, optional): The unique identifier for the review.
        id (int, optional): Alias for review_id.
        book_id (int): The ID of the book being reviewed.
        user_id (int): The ID of the user who wrote the review.
        rating (int): The star rating given by the user (e.g., 1-5).
        comment (str, optional): The text content of the review. Expected to be
                                 HTML-sanitized by the service layer before being
                                 set on this object if from user input.
        created_at (datetime, optional): Timestamp of when the review was created.
                                         Typically set by the database.
        user_first_name (str, optional): Denormalized first name of the reviewer for display.
        user_last_name (str, optional): Denormalized last name of the reviewer for display.
    """
    def __init__(self, book_id: int, user_id: int, rating: int, comment: str | None, 
                 review_id: int = None, created_at: datetime = None, 
                 user_first_name: str = None, user_last_name: str = None):
        """
        Initializes a new Review instance.

        Args:
            book_id (int): The ID of the reviewed book.
            user_id (int): The ID of the user submitting the review.
            rating (int): The rating score (e.g., 1 to 5).
            comment (str | None): The text of the review. Assumed to be sanitized 
                                  if coming from user input before this point.
            review_id (int, optional): The ID of the review if it already exists. Defaults to None.
            created_at (datetime, optional): The creation timestamp from the database. Defaults to None.
            user_first_name (str, optional): First name of the reviewer (denormalized). Defaults to None.
            user_last_name (str, optional): Last name of the reviewer (denormalized). Defaults to None.
        """
        self.review_id = review_id
        self.id = review_id # Common alias
        self.book_id = book_id
        self.user_id = user_id

        try:
            self.rating = int(rating) if rating is not None else 0

        except ValueError:
            logger.warning(f"Invalid rating value '{rating}' for review on book {book_id}. Defaulting to 0.")
            self.rating = 0

        self.comment = comment # Assumed sanitized (e.g., by sanitize_html_text) if from user input
        self.created_at = created_at # This will be a datetime object from DB or service

        # Denormalized user data, typically populated when fetching reviews with a JOIN
        self.user_first_name = user_first_name
        self.user_last_name = user_last_name

    @classmethod
    def from_row(cls, row_dict: dict):
        """
        Class method to create a Review instance from a database row dictionary.
        Assumes `row_dict` keys match database column names or aliased names from a JOIN.

        Args:
            row_dict (dict): A dictionary representing a row, typically from `RealDictCursor`.
                             It should contain review fields and may contain joined user fields
                             like 'first_name', 'last_name'.
        Returns:
            Review | None: A Review object if row_dict is valid, otherwise None.
        """
        if not row_dict:
            logger.debug("Review.from_row received empty or None row_dict, returning None.")
            return None
        
        return cls(
            review_id=row_dict.get('review_id'),
            book_id=row_dict.get('book_id'),
            user_id=row_dict.get('user_id'),
            rating=row_dict.get('rating'),
            comment=row_dict.get('comment'),
            created_at=row_dict.get('created_at'),
            # Assumes 'first_name' and 'last_name' are column names (or aliases)
            # from the 'users' table if a JOIN was performed.
            user_first_name=row_dict.get('first_name'), 
            user_last_name=row_dict.get('last_name')    
        )

    def to_dict(self, include_user_details: bool = True, is_owner: bool = False) -> dict:
        """
        Returns a dictionary representation of the review, suitable for JSON serialization.
        Optionally includes denormalized user details.

        Args:
            include_user_details (bool): If True, includes a nested 'user' object with
                                         first and last name. Defaults to True.
            is_owner (bool): Flag indicating if the current viewer is the owner of the review.
                             This is typically determined by the route/service and passed here.
                             Defaults to False.
        Returns:
            dict: A dictionary containing the review's attributes.
        """
        data = {
            'id': self.review_id,
            'review_id': self.review_id,
            'book_id': self.book_id,
            'user_id': self.user_id, 
            'rating': self.rating,
            'comment': self.comment, 
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_owner': is_owner # Include ownership flag for frontend logic
        }

        if include_user_details:
            # Nested user object is cleaner for JS if multiple user fields are needed
            data['user'] = {
                'id': self.user_id, # Can be useful for client-side checks too
                'first_name': self.user_first_name,
                'last_name': self.user_last_name
            }

            # Keep flat versions if some parts of JS expect them directly on the review object
            data['user_first_name'] = self.user_first_name
            data['user_last_name'] = self.user_last_name
            
        return data

    def __repr__(self) -> str:
        """String representation of the Review object, useful for debugging."""
        return (f"<Review id={self.review_id} book_id={self.book_id} user_id={self.user_id} "
                f"rating={self.rating}>")

    # Note: Persistence methods (save, update, delete) for Review instances
    # are handled by the review_service.py to encapsulate business logic,
    # sanitization, and ownership checks.