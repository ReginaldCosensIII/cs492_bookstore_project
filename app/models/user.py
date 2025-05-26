# app/models/user.py

from app.models.db import get_db_connection
from datetime import datetime # For type hinting
from app.logger import get_logger # Use the app's configured logger
from flask_login import UserMixin # Provides default implementations for Flask-Login User methods

# Use the app's configured logger
logger = get_logger(__name__)

class User(UserMixin):
    """
    Represents a user in the bookstore system.
    This class implements the `UserMixin` from Flask-Login for session management.
    It includes common user attributes and methods for role checking.

    Attributes:
        id (int): The unique identifier for the user, used by Flask-Login. Alias for user_id.
        user_id (int): The primary key from the 'users' database table.
        email (str): The user's email address (unique).
        phone_number (str, optional): The user's phone number.
        password_hash (str): The hashed password for the user. NEVER store plain text passwords.
        created_at (datetime, optional): Timestamp of when the user account was created.
        first_name (str, optional): The user's first name.
        last_name (str, optional): The user's last name.
        address_line1 (str, optional): User's primary shipping address line.
        address_line2 (str, optional): User's secondary shipping address line.
        city (str, optional): User's shipping city.
        state (str, optional): User's shipping state.
        zip_code (str, optional): User's shipping ZIP code.
        role (str): The role of the user (e.g., 'customer', 'admin', 'employee').
    """
    def __init__(self, user_id: int, email: str, password_hash: str, 
                 first_name: str, last_name: str, role: str,
                 phone_number: str = None, created_at: datetime = None, 
                 address_line1: str = None, address_line2: str = None,
                 city: str = None, state: str = None, zip_code: str = None):
        """
        Initializes a new User instance.

        Args:
            user_id (int): The unique ID of the user.
            email (str): The user's email address.
            password_hash (str): The pre-hashed password. This __init__ expects the hash.
            first_name (str): User's first name.
            last_name (str): User's last name.
            role (str): User's role (e.g., 'customer', 'admin').
            phone_number (str, optional): User's phone number. Defaults to None.
            created_at (datetime, optional): Account creation timestamp. Defaults to None (DB might set it).
            address_line1 (str, optional): Address line 1. Defaults to None.
            address_line2 (str, optional): Address line 2. Defaults to None.
            city (str, optional): City. Defaults to None.
            state (str, optional): State. Defaults to None.
            zip_code (str, optional): ZIP code. Defaults to None.
        """
        self.id = int(user_id) # Flask-Login expects 'id' attribute, ensure it's correct type
        self.user_id = int(user_id) 
        self.email = email
        self.phone_number = phone_number
        self.password_hash = password_hash # Store the hash directly
        self.created_at = created_at
        self.first_name = first_name
        self.last_name = last_name
        self.address_line1 = address_line1
        self.address_line2 = address_line2
        self.city = city
        self.state = state
        self.zip_code = zip_code
        self.role = role if role else 'customer' # Default role to customer if not specified

        logger.debug(f"User object initialized: ID={self.id}, Email='{self.email}', Role='{self.role}'")

    # get_id() is required by Flask-Login and should return a string representation of the user's unique ID.
    # UserMixin provides a default implementation that uses self.id.
    # def get_id(self):
    #     return str(self.id)
    
    # Role checking helper methods for convenience in templates and routes
    def is_admin(self) -> bool:
        """Checks if the user has the 'admin' role."""
        return self.role == 'admin'

    def is_employee(self) -> bool:
        """Checks if the user has the 'employee' role."""
        return self.role == 'employee'

    def is_customer(self) -> bool:
        """Checks if the user has the 'customer' role."""
        return self.role == 'customer'
    
    def __repr__(self) -> str:
        """String representation of the User object, useful for debugging."""
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"

    @classmethod
    def from_db_row(cls, row_dict: dict):
        """
        Class method to create a User instance from a database row dictionary.
        This assumes `row_dict` keys match database column names and can be mapped
        to the `__init__` parameters of the User class.

        Args:
            row_dict (dict): A dictionary representing a row from the 'users' table,
                             typically obtained using RealDictCursor.
        Returns:
            User | None: A User object if row_dict is valid, otherwise None.
        """
        if not row_dict:
            logger.debug("User.from_db_row received empty or None row_dict.")
            return None
        
        # Ensure all required __init__ params are present in row_dict or have defaults
        return cls(
            user_id=row_dict.get('user_id'),
            email=row_dict.get('email'),
            password_hash=row_dict.get('password'), # Assumes DB column is 'password' (storing the hash)
            created_at=row_dict.get('created_at'),
            first_name=row_dict.get('first_name'),
            last_name=row_dict.get('last_name'),
            address_line1=row_dict.get('address_line1'),
            address_line2=row_dict.get('address_line2'),
            city=row_dict.get('city'),
            state=row_dict.get('state'),
            zip_code=row_dict.get('zip_code'),
            role=row_dict.get('role', 'customer'), # Default to 'customer' if role is missing
            phone_number=row_dict.get('phone_number')
        )

def load_user(user_id_str: str): # Renamed in app/__init__ to _flask_login_user_loader for clarity
    """
    Loads a user from the database by user_id.
    This function is typically registered with Flask-Login's `user_loader` decorator.

    Args:
        user_id_str (str): The ID of the user to load (as a string from the session).
    
    Returns:
        User | None: The User object if found, otherwise None.
    
    Raises:
        DatabaseError: If a database issue occurs during fetching.
    """
    if not user_id_str:
        return None
    
    conn = None
    try:
        user_id_int = int(user_id_str) # User IDs are integers in the database
    except ValueError:
        logger.warning(f"load_user called with non-integer user_id_str: '{user_id_str}'")
        return None

    try:
        conn = get_db_connection()
        # RealDictCursor is the default for cursors from get_db_connection
        with conn.cursor() as cur:
            # Select all fields needed by User.from_db_row
            cur.execute("""
                SELECT user_id, email, phone_number, password, created_at,
                       first_name, last_name, address_line1, address_line2,
                       city, state, zip_code, role
                FROM users
                WHERE user_id = %s
            """, (user_id_int,))
            user_data_dict = cur.fetchone() # Returns a RealDictRow (dict-like) or None
        
        if user_data_dict:
            logger.debug(f"Data for user_id {user_id_int} found in DB: {dict(user_data_dict)}") # Log as dict
            return User.from_db_row(user_data_dict)
        else:
            logger.info(f"No user found in DB with user_id: {user_id_int}")
            return None
            
    except Exception as e:
        # Log the full exception details for debugging.
        logger.error(f"Error loading user {user_id_int}: {e}", exc_info=True)
        # For Flask-Login, it's important to return None on error to indicate user couldn't be loaded.
        # Raising a custom DatabaseError here might be caught by a global error handler
        # which might not be what Flask-Login expects for user loading failures.
        # However, if you want to signal a critical DB issue, raising is an option.
        # For now, adhering to Flask-Login's expectation of None on failure.
        return None 
    finally:
        if conn:
            conn.close()