# app/models/admin.py

from app.models.employee import Employee

class Admin(Employee):
    def __init__(self, id, username, email, password_hash):
        super().__init__(id, username, email, password_hash)
        self.role = 'admin'

    # TODO: Add admin-only methods like manage_users()
