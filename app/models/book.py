# app/models/book.py

from app.logger import get_logger # Use the custom application logger
from decimal import Decimal, InvalidOperation # For handling price conversion
from app.models.db import get_db_connection # For database connection management
from app.services.exceptions import DatabaseError # Custom exception for database errors

logger = get_logger(__name__)

class Book:
    """
    Represents a book in the bookstore.

    This class encapsulates the properties and database interactions for book entities,
    including saving, updating, deleting, and retrieving book information.

    Attributes:
        book_id (int, optional): The unique identifier for the book.
        title (str): The title of the book. Stored in lowercase but displayed in title case.
        author (str): The author(s) of the book.
        genre (str): The genre of the book.
        price (Decimal): The price of the book. Stored and handled as Decimal for precision.
        stock_quantity (int): The current number of copies in stock.
        image_url (str): URL for the book's cover image. Defaults to a placeholder.
        description (str): A description of the book. Defaults to a generic message.
        created_at (datetime, optional): Timestamp of when the book record was created in the DB.
        updated_at (datetime, optional): Timestamp of when the book record was last updated in the DB.
    """
    def __init__(self, title: str, author: str, genre: str, price, stock_quantity: int, 
                 image_url: str = None, description: str = None, book_id: int = None, 
                 created_at=None, updated_at=None):
        """
        Initializes a new Book instance.

        Args:
            title (str): The title of the book.
            author (str): The author(s) of the book.
            genre (str): The genre of the book.
            price (str | float | int | Decimal): The price of the book. Will be converted to Decimal.
            stock_quantity (int): The number of copies currently in stock.
            image_url (str, optional): URL for the book's cover image. 
                                       Defaults to a placeholder if not provided.
            description (str, optional): A description of the book. 
                                         Defaults to "No description available." if not provided.
            book_id (int, optional): The unique ID of the book (if it already exists in the database).
                                     Defaults to None for new books.
            created_at (datetime, optional): The creation timestamp from the database.
            updated_at (datetime, optional): The last update timestamp from the database.
        """
        self.book_id = book_id
        # self.id = book_id # Alias for 'id' can be added if consistently needed by other systems
        self.title = str(title).lower() if title else "untitled" # Store title in lowercase for consistent search/sort
        self.author = author
        self.genre = genre

        try:
            self.price = Decimal(str(price)) if price is not None else Decimal('0.00')

        except InvalidOperation:
            logger.warning(f"Invalid price value '{price}' for book '{title}'. Defaulting to 0.00.")
            self.price = Decimal('0.00')

        self.stock_quantity = int(stock_quantity) if stock_quantity is not None else 0
        self.image_url = image_url or 'https://via.placeholder.com/150x220.png?text=No+Image+Available'
        self.description = description or "No description available for this book."
        self.created_at = created_at # Typically set by the database on insert
        self.updated_at = updated_at # Typically set by the database on insert/update

    def to_dict(self, include_timestamps: bool = False) -> dict:
        """
        Returns a dictionary representation of the Book object.
        Useful for JSON serialization or when a dictionary format is needed.

        Args:
            include_timestamps (bool): If True, includes 'created_at' and 'updated_at' 
                                       fields (as ISO strings) in the dictionary.
                                       Defaults to False.
        Returns:
            dict: A dictionary containing the book's attributes.
        """
        data = {
            'book_id': self.book_id,
            'id': self.book_id, # Common alias
            'title': self.title.title() if self.title else "Untitled", # Display in Title Case
            'author': self.author,
            'genre': self.genre,
            'price': str(self.price.quantize(Decimal('0.01'))), # Serialize Decimal as string
            'stock_quantity': self.stock_quantity,
            'image_url': self.image_url,
            'description': self.description
        }

        if include_timestamps:
            data['created_at'] = self.created_at.isoformat() if self.created_at else None
            data['updated_at'] = self.updated_at.isoformat() if self.updated_at else None

        return data

    @classmethod
    def from_row(cls, row_dict: dict):
        """
        Class method to create a Book instance from a database row dictionary.
        This assumes the row_dict keys match the database column names and
        can be mapped to the __init__ parameters of the Book class.

        Args:
            row_dict (dict): A dictionary representing a row from the 'books' table,
                             typically obtained using RealDictCursor.
        Returns:
            Book | None: A Book object if row_dict is valid, otherwise None.
        """
        if not row_dict:
            logger.debug("from_row received empty or None row_dict, returning None.")
            return None
        
        # Ensure keys match __init__ parameters or handle missing keys gracefully.
        # The __init__ method itself handles defaults for image_url and description.
        return cls(
            book_id=row_dict.get('book_id'),
            title=row_dict.get('title'),
            author=row_dict.get('author'),
            genre=row_dict.get('genre'),
            price=row_dict.get('price'), # Handled as Decimal in __init__
            stock_quantity=row_dict.get('stock_quantity'),
            image_url=row_dict.get('image_url'),
            description=row_dict.get('description'),
            created_at=row_dict.get('created_at'), # Assuming 'books' table has these
            updated_at=row_dict.get('updated_at')  # Assuming 'books' table has these
        )

    def save(self):
        """
        Saves a new book to the database or updates an existing book if book_id is set.
        Manages its own database connection and transaction.

        Raises:
            DatabaseError: If any database operation fails.
        """
        conn = None
        action = "update" if self.book_id else "insert"
        log_identifier = f"book ID {self.book_id}" if self.book_id else f"new book '{self.title}'"
        logger.debug(f"Attempting to {action} {log_identifier}.")

        try:
            conn = get_db_connection()
            with conn.cursor() as cur: # RealDictCursor is default from get_db_connection
                if self.book_id: # Update existing book
                    # Assuming 'updated_at' is handled by a DB trigger or default
                    query = """
                        UPDATE books
                        SET title = %s, author = %s, genre = %s, price = %s, 
                            stock_quantity = %s, image_url = %s, description = %s
                            -- updated_at = CURRENT_TIMESTAMP (If not using DB trigger)
                        WHERE book_id = %s;
                    """

                    values = (self.title, self.author, self.genre, self.price,
                              self.stock_quantity, self.image_url, self.description, self.book_id)
                    cur.execute(query, values)

                    if cur.rowcount == 0:
                        logger.warning(f"No rows updated for book ID {self.book_id}. Book may not exist.")
                        # Consider raising an error if update affected 0 rows for existing ID

                else: # Insert new book
                    # Assuming 'created_at' and 'updated_at' are handled by DB defaults (e.g., CURRENT_TIMESTAMP)
                    query = """
                        INSERT INTO books (title, author, genre, price, stock_quantity, image_url, description)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING book_id, created_at, updated_at; 
                    """
                    values = (self.title, self.author, self.genre, self.price, 
                              self.stock_quantity, self.image_url, self.description)
                    
                    cur.execute(query, values)
                    result_row = cur.fetchone() # dict-like row due to RealDictCursor

                    if result_row:
                        self.book_id = result_row['book_id']
                        self.created_at = result_row.get('created_at') # Get if returned by DB
                        self.updated_at = result_row.get('updated_at') # Get if returned by DB
                    else:
                        logger.error("Failed to retrieve book_id and timestamps after insert.")
                        raise DatabaseError("Book insert failed to return generated ID and timestamps.")
                conn.commit()
                logger.info(f"Book '{self.title}' (ID: {self.book_id}) saved successfully (action: {action}).")

        except Exception as e:
            if conn:
                conn.rollback()

            logger.error(f"Error saving book (ID: {self.book_id}, Title: {self.title}): {e}", exc_info=True)

            raise DatabaseError(f"Could not save book '{self.title}'.", original_exception=e)
        
        finally:
            if conn:
                conn.close()

    # decrease_stock method would be better in book_service.py to handle transactions
    # with other operations like order creation. If kept here, it must manage its own transaction carefully.
    # For this refactor, assuming decrease_stock is primarily handled by book_service.

    @staticmethod
    def delete(book_id: int) -> bool:
        """
        Deletes a book from the database by its ID.

        Args:
            book_id (int): The ID of the book to delete.
        
        Returns:
            bool: True if deletion was successful (1 row affected), False otherwise.
        
        Raises:
            DatabaseError: If any database operation fails.
        """
        conn = None
        logger.debug(f"Attempting to delete book with ID: {book_id}.")

        try:
            conn = get_db_connection()

            with conn.cursor() as cur:
                cur.execute("DELETE FROM books WHERE book_id = %s;", (book_id,))
                conn.commit()

                if cur.rowcount == 0:
                    logger.warning(f"Attempted to delete book ID {book_id}, but it was not found or not deleted.")
                    return False 
                
                logger.info(f"Book with ID {book_id} deleted successfully.")
                return True
            
        except Exception as e:
            if conn:
                conn.rollback()

            logger.error(f"Error deleting book ID {book_id}: {e}", exc_info=True)
            raise DatabaseError(f"Could not delete book with ID {book_id}.", original_exception=e)
        
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_by_id(book_id: int): # -> Book | None: (Python 3.10+)
        """
        Retrieves a single book from the database by its ID.

        Args:
            book_id (int): The ID of the book to retrieve.
        
        Returns:
            Book | None: A Book object if found, otherwise None.
        
        Raises:
            DatabaseError: If any database operation fails.
        """
        logger.debug(f"Fetching book by ID: {book_id}.")
        query = "SELECT * FROM books WHERE book_id = %s;"
        conn = None

        try:
            conn = get_db_connection()
            with conn.cursor() as cur: # RealDictCursor is default from get_db_connection
                cur.execute(query, (book_id,))
                result_dict = cur.fetchone() 
            
            if result_dict:
                logger.debug(f"Book found for ID {book_id}: '{result_dict.get('title')}'")
                return Book.from_row(result_dict)
            
            else:
                logger.info(f"No book found with ID {book_id}.")
                return None
            
        except Exception as e:
            logger.error(f"Error retrieving book by ID {book_id}: {e}", exc_info=True)
            raise DatabaseError(f"Could not retrieve book with ID {book_id}.", original_exception=e)
        
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_all() -> list: # list[Book] for Python 3.9+
        """
        Retrieves all books from the database, ordered by title.
        This method is now designed to be called by book_service.get_all_books(),
        which will return Book objects.

        Returns:
            list[Book]: A list of Book objects. Returns an empty list if no books are found or on error.
        
        Raises:
            DatabaseError: If any database operation fails.
        """
        logger.info("Fetching all books.")
        query = "SELECT * FROM books ORDER BY title ASC;"
        conn = None
        book_objects = []

        try:
            conn = get_db_connection()
            with conn.cursor() as cur: # RealDictCursor by default
                cur.execute(query)
                results_as_dicts = cur.fetchall()
            
            for row_dict in results_as_dicts:
                book_objects.append(Book.from_row(row_dict))

            logger.info(f"Retrieved {len(book_objects)} books from database.")
            return book_objects
        
        except Exception as e:
            logger.error(f"Error fetching all books: {e}", exc_info=True)
            # Return empty list as a fallback, service layer can decide to raise further.
            # This matches the user's specialized prompt: "return empty list on error or if no books" for service.
            raise DatabaseError("Could not retrieve all books.", original_exception=e)
        
        finally:
            if conn:
                conn.close()