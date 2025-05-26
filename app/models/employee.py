# app/models/employee.py
from .user import User # Use relative import for sibling modules

class Employee(User):
    """
    Represents an Employee user, inheriting from the base User class.
    The 'role' attribute is set to 'employee' to distinguish this user type.
    This class can be extended with employee-specific attributes (e.g., department,
    employee ID if different from user_id) and methods related to employee tasks.
    """
    def __init__(self, user_id: int, email: str, password_hash: str, 
                 first_name: str, last_name: str, **kwargs):
        """
        Initializes a new Employee instance, setting the role to 'employee'.

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
            role='employee', # Explicitly set the role for Employee users
            **kwargs # Pass through any other user fields
        )
        # Example: Employee-specific attributes if needed later
        # self.department = kwargs.get('department')
        # self.employee_internal_id = kwargs.get('employee_internal_id')

    # TODO: Add methods specific to employees as their functionalities are implemented,
    #       such as managing inventory, processing orders, or accessing internal tools.
    #       Currently, the 'employee' role on the User object (checked via current_user.is_employee())
    #       is the primary means of differentiation for access control.

    def __repr__(self) -> str:
        return f"<Employee id={self.id} email='{self.email}'>"