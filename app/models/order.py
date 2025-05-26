# app/models/order.py

import logging
from datetime import datetime
from app.logger import get_logger
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import List, TYPE_CHECKING # For type hinting items

# Use the app's configured logger
logger = get_logger(__name__)

# Forward declaration for OrderItem to avoid circular import issues if OrderItem imports Order
if TYPE_CHECKING:
    from .order_item import OrderItem


class Order:
    """
    Represents an order placed by a user or a guest in the bookstore.

    Attributes:
        order_id (int, optional): The unique identifier for the order.
        id (int, optional): An alias for `order_id`.
        user_id (int, optional): The ID of the registered user who placed the order. 
                                 This will be `None` for orders placed by guests.
        guest_email (str, optional): The email address provided by a guest during checkout.
        order_date (datetime): The date and time when the order was placed. This effectively
                               serves as the creation timestamp for the order.
        total_amount (Decimal): The total monetary value of the order.
        status (str): The current processing status of the order.
        shipping_address_line1 (str, optional): The first line of the shipping address.
        shipping_address_line2 (str, optional): The second line of the shipping address.
        shipping_city (str, optional): The city for shipping.
        shipping_state (str, optional): The state or region for shipping.
        shipping_zip_code (str, optional): The postal or ZIP code for shipping.
        updated_at (datetime, optional): Timestamp of when the order record was last updated in the database.
        items (List['OrderItem']): A list of `OrderItem` objects associated with this order.
    """
    def __init__(self, 
                 user_id: int | None, 
                 order_date: datetime, 
                 total_amount, 
                 status: str, 
                 order_id: int | None = None, 
                 shipping_address_line1: str | None = None, 
                 shipping_address_line2: str | None = None, 
                 shipping_city: str | None = None, 
                 shipping_state: str | None = None, 
                 shipping_zip_code: str | None = None,
                 guest_email: str | None = None,
                 updated_at: datetime | None = None): # order_date handles creation time
        """
        Initializes a new Order instance.

        Args:
            user_id (int | None): ID of the registered user, or None for a guest.
            order_date (datetime): The date/time the order was placed.
            total_amount (str | float | int | Decimal): The total value of the order.
            status (str): The initial status of the order.
            order_id (int, optional): The order's unique ID if it already exists.
            shipping_address_line1 (str, optional): Primary shipping address line.
            shipping_address_line2 (str, optional): Secondary shipping address line.
            shipping_city (str, optional): Shipping city.
            shipping_state (str, optional): Shipping state/region.
            shipping_zip_code (str, optional): Shipping postal/ZIP code.
            guest_email (str, optional): Email address for guest orders.
            updated_at (datetime, optional): Timestamp of the last update from the database.
        """
        self.order_id = order_id
        self.id = order_id 
        self.user_id = user_id 
        self.guest_email = guest_email if not user_id else None        
        self.order_date = order_date if isinstance(order_date, datetime) else datetime.utcnow()
        
        try:
            self.total_amount = Decimal(str(total_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) \
                if total_amount is not None else Decimal('0.00')
            
        except InvalidOperation:
            self.total_amount = Decimal('0.00')
            logger.warning(
                f"Invalid value for total_amount during Order init: '{total_amount}'. Defaulting to 0.00 for order_id {order_id if order_id else 'NEW'}."
            )
                        
        self.status = status 
        self.shipping_address_line1 = shipping_address_line1
        self.shipping_address_line2 = shipping_address_line2
        self.shipping_city = shipping_city
        self.shipping_state = shipping_state
        self.shipping_zip_code = shipping_zip_code
        
        self.updated_at = updated_at or self.order_date 

        self.items: List[OrderItem] = []

    @classmethod
    def from_row(cls, row_dict: dict) -> 'Order | None':
        """
        Class method to create an Order instance from a database row dictionary.
        Assumes `row_dict` keys match database column names from the 'orders' table.
        Uses `order_date` as the creation timestamp if a separate `created_at` column
        is not present in the row_dict or database schema for orders.

        Args:
            row_dict (dict): A dictionary representing a row from the 'orders' table.
        
        Returns:
            Order | None: An Order object if `row_dict` is valid, otherwise None.
        """
        if not row_dict:
            logger.debug("Order.from_row received empty or None row_dict.")
            return None
        
        return cls(
            order_id=row_dict.get('order_id'),
            user_id=row_dict.get('user_id'), 
            guest_email=row_dict.get('guest_email'),
            order_date=row_dict.get('order_date'), # This serves as the creation date
            total_amount=row_dict.get('total_amount'),
            status=row_dict.get('status'), 
            shipping_address_line1=row_dict.get('shipping_address_line1'),
            shipping_address_line2=row_dict.get('shipping_address_line2'),
            shipping_city=row_dict.get('shipping_city'),
            shipping_state=row_dict.get('shipping_state'),
            shipping_zip_code=row_dict.get('shipping_zip_code'),
            updated_at=row_dict.get('updated_at')
            # 'created_at' parameter in __init__ will default to order_date if not explicitly passed from here.
        )

    def to_dict(self, include_items: bool = False) -> dict:
        """
        Returns a dictionary representation of the order, suitable for JSON serialization.

        Args:
            include_items (bool): If True, includes a list of item dictionaries. 
                                  Defaults to False.
        Returns:
            dict: A dictionary representing the order.
        """
        data = {
            'order_id': self.order_id,
            'id': self.id,
            'user_id': self.user_id,
            'guest_email': self.guest_email,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            # Using self.order_date as the 'created_at' value in the dictionary output for clarity
            'created_at': self.order_date.isoformat() if self.order_date else None, 
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'total_amount': str(self.total_amount), 
            'status': self.status,
            'shipping_address_line1': self.shipping_address_line1,
            'shipping_address_line2': self.shipping_address_line2,
            'shipping_city': self.shipping_city,
            'shipping_state': self.shipping_state,
            'shipping_zip_code': self.shipping_zip_code,
        }

        if include_items and self.items:
            data['items'] = [item.to_dict() for item in self.items]
            
        return data

    def __repr__(self) -> str:
        """String representation of the Order object, useful for debugging."""
        user_identifier = f"user_id={self.user_id}" if self.user_id else f"guest_email='{self.guest_email}'"
        return (f"<Order id={self.order_id} {user_identifier} status='{self.status}' "
                f"total_amount={self.total_amount:.2f}>")