# app/services/book_service.py

import psycopg2                                                       # For database errors
from decimal import Decimal                                                         # For type hinting
from app.models.book import Book                                                    # Book model class
from app.logger import get_logger                                                   # Custom application logger
from typing import List, Optional                                                   # For type hinting
from app.models.db import get_db_connection                                         # For database connections
from app.services.exceptions import DatabaseError, NotFoundError, ValidationError   # Custom exceptions

# cs492_bookstore_project/app/services/book_service.py
from typing import List, Optional # For type hinting

from app.models.book import Book  # Book model class
from app.models.db import get_db_connection # For database connections
from app.services.exceptions import DatabaseError, NotFoundError, ValidationError # Custom exceptions
from app.logger import get_logger # Custom application logger
# from decimal import Decimal # Not directly used here, Book model handles it
 
logger = get_logger(__name__) # Logger instance for this module

def get_all_books() -> List[Book]:
    """
    Retrieves all books from the database, ordered by title.

    This service function delegates the database query to the `Book.get_all()`
    static method from the `Book` model. It's expected that `Book.get_all()`
    returns a list of `Book` instances. This service function provides a consistent
    interface for fetching all books and includes standardized logging and error handling.

    Returns:
        List[Book]: A list of `Book` objects. Returns an empty list if no books are
                    found.
    
    Raises:
        DatabaseError: If an underlying database error occurs during the fetch operation
                       that is not handled within `Book.get_all()` by returning an empty list.
    """
    logger.info("Service: Request received to fetch all books from the database.")

    try:
        # Delegate to the Book model's static method.
        # Book.get_all() is expected to handle its own DB connection, cursor, and data mapping to Book objects.
        all_book_objects = Book.get_all() 
        logger.info(f"Service: Successfully retrieved {len(all_book_objects)} books from the database.")

        return all_book_objects
    
    except DatabaseError as de:
        # Log the specific DatabaseError if it was raised from the model layer.
        logger.error(f"Service: A database error occurred in Book.get_all() while fetching all books: {de.log_message}", exc_info=True)

        raise # Re-raise to be handled by the calling route or global error handler.

    except Exception as e:
        # Catch any other unexpected errors not specifically caught as DatabaseError by the model.
        logger.error(f"Service: An unexpected error occurred while fetching all books: {e}", exc_info=True)
        # Wrap in a custom DatabaseError for consistent error type from the service layer.
        raise DatabaseError("An unexpected error occurred while retrieving book data from the database.", original_exception=e)

def get_book_by_id(book_id: int) -> Book: 
    """
    Retrieves a single book from the database by its unique ID.

    This service function calls the static `Book.get_by_id(book_id)` method.
    If the book is not found by the model method (which should return `None` in that case),
    this service function raises a `NotFoundError`. Other database issues are
    wrapped in or propagated as `DatabaseError`.

    Args:
        book_id (int): The ID of the book to retrieve.

    Returns:
        Book: The `Book` object if found.
    
    Raises:
        NotFoundError: If no book with the given ID is found in the database.
        DatabaseError: If an unexpected error occurs during database interaction.
    """
    logger.info(f"Service: Attempting to fetch book with ID: {book_id}")

    try:
        # Delegate to the Book model's static method.
        book = Book.get_by_id(book_id) 

        if book:
            logger.debug(f"Service: Book with ID {book_id} (Title: '{book.title}') found successfully.")

            return book
        
        else:
            # If Book.get_by_id returns None, it signifies the book was not found.
            logger.warning(f"Service: Book with ID {book_id} not found in the database (Book.get_by_id returned None).")

            raise NotFoundError(resource_name="Book", resource_id=book_id)
        
    except NotFoundError:
        # Log and re-raise the specific NotFoundError if it came from Book.get_by_id or was raised here.
        logger.warning(f"Service: NotFoundError confirmed for book ID {book_id}.")

        raise

    except DatabaseError as de: 
        # Catch specific DatabaseError if it was raised from the model layer.
        logger.error(f"Service: A database error occurred while fetching book ID {book_id}: {de.log_message}", exc_info=True)

        raise

    except Exception as e:
        # Catch any other unexpected errors.
        logger.error(f"Service: An unexpected error occurred while fetching book by ID {book_id}: {e}", exc_info=True)

        raise DatabaseError(message=f"Could not retrieve book with ID {book_id} due to a server error.", original_exception=e)


def decrease_book_stock(book_id: int, quantity_to_decrease: int, db_conn=None) -> bool:
    """
    Decreases the stock quantity for a given book ID by the specified amount.

    This function is designed to be robust and can participate in an existing 
    database transaction if an active `db_conn` (database connection) is provided. 
    It performs critical checks for valid quantity, book existence, and sufficient 
    stock before attempting the update. It uses `SELECT FOR UPDATE` to lock the 
    book row during the check-and-update operation to prevent race conditions
    within a transaction.

    Args:
        book_id (int): The ID of the book whose stock needs to be decreased.
        quantity_to_decrease (int): The number of units to decrease the stock by. 
                                    Must be a positive integer.
        db_conn (psycopg2.connection, optional): 
            An existing database connection. If `None` (default), a new connection 
            is created, and the transaction (commit/rollback) is managed locally 
            within this function. If a connection is provided, this function will use 
            it and will NOT commit, rollback, or close it, assuming it's part of a 
            larger, externally managed transaction (e.g., order creation).

    Returns:
        bool: True if the stock was successfully updated in the database (this indicates
              the DML executed; actual commit depends on `manage_conn_locally`). 
              The function raises exceptions on failure rather than returning False 
              for business logic errors like insufficient stock or item not found.

    Raises:
        ValidationError: If `quantity_to_decrease` is not a positive integer, or if
                         the available stock is insufficient for the requested decrease.
        NotFoundError: If the book with the specified `book_id` is not found in the database.
        DatabaseError: For other underlying database errors during the stock update operation.
    """
    logger.info(f"Service: Attempting to decrease stock for book_id {book_id} by quantity {quantity_to_decrease}.")
    
    if not isinstance(quantity_to_decrease, int) or quantity_to_decrease <= 0:
        logger.warning(f"Invalid quantity for stock decrease: {quantity_to_decrease}. Must be a positive integer.")

        raise ValidationError(
            message="Quantity to decrease must be a positive integer.",
            errors={"quantity": "Quantity must be greater than zero."}
        )

    manage_conn_locally = db_conn is None
    conn_to_use = db_conn 
    
    try:

        if manage_conn_locally:
            logger.debug(f"decrease_book_stock for book {book_id}: Managing database connection locally.")
            conn_to_use = get_db_connection()
            conn_to_use.autocommit = False # Manage transaction explicitly if local

        if conn_to_use is None: # Should only happen if db_conn was None and get_db_connection failed
             logger.critical("Database connection is None in decrease_book_stock. Cannot proceed.")
             
             raise DatabaseError("Database connection not available for stock decrease operation.")

        with conn_to_use.cursor() as cur: # Assumes RealDictCursor from get_db_connection
            logger.debug(f"Executing SELECT FOR UPDATE to lock stock for book_id {book_id}.")
            cur.execute("SELECT stock_quantity FROM books WHERE book_id = %s FOR UPDATE;", (book_id,))
            book_stock_row = cur.fetchone()

            if not book_stock_row:
                logger.warning(f"Book with ID {book_id} not found during stock decrease attempt (after lock).")

                raise NotFoundError(
                    resource_name="Book", 
                    resource_id=book_id, 
                    message=f"Book (ID: {book_id}) not found, cannot update stock."
                )
            
            current_stock = book_stock_row['stock_quantity']
            logger.debug(f"Current stock for book_id {book_id} is {current_stock} (read under lock).")

            if quantity_to_decrease > current_stock:
                logger.warning(
                    f"Insufficient stock for book ID {book_id} to decrease by {quantity_to_decrease}. "
                    f"Available: {current_stock}."
                )

                raise ValidationError(
                    message=(f"Not enough stock for book ID {book_id}. "
                             f"Only {current_stock} items available, but a decrease of {quantity_to_decrease} was requested."),
                    errors={"quantity": f"Insufficient stock. Only {current_stock} available."}
                )

            new_stock_quantity = current_stock - quantity_to_decrease
            logger.debug(f"Attempting to update stock for book_id {book_id} from {current_stock} to {new_stock_quantity}.")
            cur.execute("UPDATE books SET stock_quantity = %s WHERE book_id = %s;", 
                        (new_stock_quantity, book_id))
            
            if cur.rowcount == 0:
                logger.error(f"Stock update for book_id {book_id} affected 0 rows unexpectedly after lock. Potential issue.")

                raise DatabaseError(f"Stock update for book {book_id} failed to apply (0 rows affected after lock).")

            if manage_conn_locally:
                conn_to_use.commit()
                logger.info(f"Stock for book_id {book_id} successfully decreased to {new_stock_quantity}. Local transaction committed.")

            else:
                logger.info(f"Stock for book_id {book_id} successfully updated to {new_stock_quantity} (part of an external transaction).")

            return True
            
    except (NotFoundError, ValidationError) as business_error: 
        if manage_conn_locally and conn_to_use and not conn_to_use.closed: 

            try: conn_to_use.rollback()

            except Exception as rb_ex: logger.error(f"Rollback error in decrease_book_stock for book {book_id}: {rb_ex}", exc_info=True)

            logger.debug(f"Local transaction rolled back for stock decrease of book_id {book_id} due to: {type(business_error).__name__} - {str(business_error)}")

        logger.warning(f"Stock update for book_id {book_id} failed: {getattr(business_error, 'log_message', str(business_error))}")

        raise 

    except Exception as e:
        if manage_conn_locally and conn_to_use and not conn_to_use.closed: 

            try: conn_to_use.rollback()

            except Exception as rb_ex: logger.error(f"Rollback error in decrease_book_stock for book {book_id}: {rb_ex}", exc_info=True)

            logger.debug(f"Local transaction rolled back for stock decrease of book_id {book_id} due to unexpected error.")

        logger.error(f"Database error or unexpected issue during stock decrease for book_id {book_id}: {e}", exc_info=True)

        raise DatabaseError("Could not update book stock due to an unexpected database issue.", original_exception=e)
    
    finally:
        if manage_conn_locally and conn_to_use and not conn_to_use.closed:

            try: conn_to_use.autocommit = True # Reset autocommit if it was changed

            except psycopg2.Error as conn_err: logger.debug(f"Error resetting autocommit for book_id {book_id} during close: {conn_err}")

            except Exception as e: logger.error(f"Unexpected error resetting autocommit for book_id {book_id}: {e}", exc_info=True)

            conn_to_use.close()
            logger.debug(f"Locally managed database connection closed after stock decrease attempt for book_id {book_id}.")