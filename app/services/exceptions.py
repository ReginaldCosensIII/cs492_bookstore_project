# app/services/exceptions.py

class AppException(Exception):
    """
    Base class for custom application-specific exceptions.
    This allows for consistent error handling throughout the application and enables
    structured error responses, especially for API endpoints.

    Attributes:
        status_code (int): The HTTP status code that should ideally be returned to the client
                           when this exception is caught by a global error handler.
        user_message (str): A user-friendly message describing the error. This message is
                            safe to display to end-users.
        errors (dict): A dictionary that can hold field-specific error messages, particularly
                       useful for validation failures from forms or API inputs.
        log_message (str): A more detailed message intended for server-side logging. This
                           might contain more technical details than the user_message.
        original_exception (Exception): If this custom exception is raised as a wrapper
                                        around another caught exception, this attribute
                                        can store the original exception for better debugging.
    """
    status_code = 500  # Default to Internal Server Error
    user_message = "An application error occurred. Please try again later or contact support."

    def __init__(self, message: str = None, status_code: int = None, 
                 errors: dict = None, log_message: str = None, 
                 original_exception: Exception = None):
        """
        Initializes the AppException instance.

        Args:
            message (str, optional): Overrides the default user_message for this specific
                                     exception instance. This is the message shown to the user.
            status_code (int, optional): Overrides the default status_code for this instance.
            errors (dict, optional): A dictionary of field-specific error messages,
                                     e.g., {"email": "Invalid email format."}.
            log_message (str, optional): A specific message for logging. If None, the user-facing
                                         `message` (or default `user_message`) will be used for logging.
            original_exception (Exception, optional): The original exception that was caught and
                                                      triggered this custom exception. Useful for logging context.
        """
        # The message passed to super().__init__ is what Exception() itself will store.
        super().__init__(message if message is not None else self.user_message)
        
        if status_code is not None:
            self.status_code = status_code
        
        self.user_facing_message = message if message is not None else self.user_message
        self.errors = errors if errors is not None else {} # Ensure errors is a dict
        self.log_message = log_message or self.user_facing_message # Default log_message to user_facing_message
        self.original_exception = original_exception

    def to_dict(self) -> dict:
        """
        Serializes the exception information to a dictionary.
        This is primarily used for generating JSON responses for API error handling.

        Returns:
            dict: A dictionary containing the user-facing error message and any 
                  field-specific errors.
        """
        response = {"error": self.user_facing_message}
        if self.errors and isinstance(self.errors, dict) and self.errors: # Ensure errors is a non-empty dict
            response["errors"] = self.errors
        return response


class DatabaseError(AppException):
    """Custom exception for errors related to database operations (e.g., connection issues, query failures)."""
    user_message = "A database error occurred. Our technical team has been notified. Please try again later."
    status_code = 500


class ValidationError(AppException):
    """Custom exception specifically for input validation failures."""
    user_message = "Your submission contains errors. Please check the details provided and try again."
    status_code = 400 # HTTP Bad Request

    def __init__(self, message: str = None, errors: dict = None, 
                 log_message: str = None, original_exception: Exception = None):
        """
        Initializes ValidationError. Allows overriding the default user message and providing
        a dictionary of field-specific errors.

        Args:
            message (str, optional): A general error message for the validation failure.
            errors (dict, optional): Field-specific error messages, e.g., {"field_name": "Error detail"}.
            log_message (str, optional): Message for server logs.
            original_exception (Exception, optional): Original exception.
        """
        super().__init__(
            message=(message or self.user_message),
            status_code=self.status_code,
            errors=errors,
            log_message=log_message,
            original_exception=original_exception
        )

class AuthenticationError(AppException):
    """Custom exception for authentication failures (e.g., invalid username/password)."""
    user_message = "Authentication failed. Please check your email or password and try again."
    status_code = 401 # HTTP 401 Unauthorized

class AuthorizationError(AppException):
    """Custom exception for authorization failures (e.g., user lacks permission for an action)."""
    user_message = "You are not authorized to perform this action or access this resource."
    status_code = 403 # HTTP 403 Forbidden

class NotFoundError(AppException):
    """Custom exception for when a requested resource (e.g., a book, an order) cannot be found."""
    user_message = "The requested resource could not be found."
    status_code = 404 # HTTP 404 Not Found

    def __init__(self, resource_name: str = "Resource", resource_id = None, 
                 message: str = None, log_message: str = None, original_exception: Exception = None):
        """
        Initializes NotFoundError. Can provide a more specific message if resource_name/id are given.

        Args:
            resource_name (str, optional): The type of resource not found (e.g., "Book", "Order").
            resource_id (optional): The ID or identifier of the resource not found.
            message (str, optional): Overrides the default user_message.
            log_message (str, optional): Message for server logs.
            original_exception (Exception, optional): Original exception.
        """
        final_user_message = message # Use provided message if any
        if final_user_message is None: # Otherwise, construct a default one
            final_user_message = f"{resource_name} not found."
            if resource_id is not None: # Check against None explicitly
                final_user_message = f"{resource_name} with ID '{resource_id}' not found."
        
        super().__init__(
            message=final_user_message,
            status_code=self.status_code, # Uses class-defined 404
            log_message=log_message or final_user_message, # Default log message to user message
            original_exception=original_exception
        )

class CartActionError(AppException):
    """Custom exception for specific errors related to shopping cart actions 
       (e.g., item out of stock during add, invalid quantity)."""
    user_message = "There was an issue with your cart action. Please review your cart or try again."
    status_code = 400 # Typically a Bad Request, but could be context-dependent (e.g., 409 Conflict)

class OrderProcessingError(AppException):
    """Custom exception for failures during the order processing workflow 
       (e.g., stock issues found during final commit, payment gateway failure)."""
    user_message = "We encountered an issue while processing your order. Please contact support if the problem persists."
    status_code = 500 # Default to Internal Server Error if not a direct client input issue