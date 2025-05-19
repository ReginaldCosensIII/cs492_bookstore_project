# app/models/customer.py

from app.models.user import User

class Customer(User):
    def __init__(self, id, username, email, password_hash, shipping_address=None):
        super().__init__(id, username, email, password_hash, role='customer')
        self.shipping_address = shipping_address

    # TODO: Implement methods specific to customers (e.g., view_orders())
