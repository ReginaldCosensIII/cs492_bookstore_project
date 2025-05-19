# app/models/order_item.py

class OrderItem:
    def __init__(self, id, order_id, book_id, quantity, unit_price):
        self.id = id
        self.order_id = order_id
        self.book_id = book_id
        self.quantity = quantity
        self.unit_price = unit_price

    # Methods for saving, fetching by order_id, etc.
