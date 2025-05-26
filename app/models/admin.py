# cs492_bookstore_project/app/models/admin.py
from .user import User # Use relative import

class Admin(User):
    def __init__(self, user_id, email, password, first_name, last_name, **kwargs):
        # Pass all necessary User fields to super().__init__
        # Assuming User.__init__ takes all these.
        super().__init__(
            user_id=user_id, email=email, password=password,
            first_name=first_name, last_name=last_name, 
            role='admin', # Role is set here
            **kwargs # Pass through any other user fields like phone, address etc.
        )
        # Admin-specific attributes can be added here if any

    # TODO: Add admin-only methods or properties if Admin model becomes more distinct
    # For now, role 'admin' on User object is primary differentiator.