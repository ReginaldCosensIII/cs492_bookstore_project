# app/models/order.py

class Order:
    def __init__(self, id, customer_id, order_date, total_price, status):
        self.id = id
        self.customer_id = customer_id
        self.order_date = order_date
        self.total_price = total_price
        self.status = status

    # Methods like save(), get_by_id(), update_status(), etc. will be added
