# app/models/employee.py

from app.models.user import User

class Employee(User):
    def __init__(self, id, username, email, password_hash):
        super().__init__(id, username, email, password_hash, role='employee')

    # TODO: Add methods for managing inventory, orders, etc.
