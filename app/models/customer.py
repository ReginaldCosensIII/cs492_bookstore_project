# pp/models/customer.py

from .user import User # Use relative import for sibling modules

class Customer(User):
    """
    Represents a Customer user, inheriting from the base User class.
    Differentiation from other user types is primarily through the 'role' attribute.
    This class can be expanded with customer-specific attributes or methods.

    For instance, customer-specific data like loyalty points or order history associations
    might be managed through this class or related services in the future.
    """
    def __init__(self, user_id: int, email: str, password_hash: str, 
                 first_name: str, last_name: str, **kwargs):
        """
        Initializes a new Customer instance, setting the role to 'customer'.

        Args:
            user_id (int): The unique ID of the user.
            email (str): The user's email address.
            password_hash (str): The pre-hashed password.
            first_name (str): User's first name.
            last_name (str): User's last name.
            **kwargs: Additional keyword arguments to pass to the User base class constructor
                      (e.g., phone_number, address details, created_at).
        """
        super().__init__(
            user_id=user_id, 
            email=email, 
            password_hash=password_hash, # Pass hash directly
            first_name=first_name, 
            last_name=last_name, 
            role='customer', # Explicitly set the role for Customer users
            **kwargs # Pass through any other user fields
        )
        # Example: Customer-specific attribute if it existed and wasn't part of the base User
        # self.loyalty_points = kwargs.get('loyalty_points', 0)

    # TODO: Implement methods specific to customers as functionality is developed,
    #       such as managing wishlists, viewing detailed order history (beyond basic list),
    #       or interacting with loyalty programs.
    #       Currently, the 'customer' role on the User object (checked via current_user.is_customer())
    #       is the primary means of differentiation for access control and behavior.

    def __repr__(self) -> str:
        return f"<Customer id={self.id} email='{self.email}'>"