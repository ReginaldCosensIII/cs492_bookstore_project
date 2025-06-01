# app/models/order_item.py

from app.logger import get_logger # Use the app's configured logger
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation # For price handling

logger = get_logger(__name__)

class OrderItem:
    """
    Represents an individual item within an order.

    Each OrderItem links a specific book to an order, along with the quantity
    ordered and the price of the book at the time the order was placed.

    Attributes:
        order_item_id (int, optional): The unique identifier for this order item.
        id (int, optional): Alias for order_item_id.
        order_id (int): The ID of the order this item belongs to.
        book_id (int): The ID of the book ordered.
        quantity (int): The number of units of this book ordered.
        unit_price_at_purchase (Decimal): The price of a single unit of the book 
                                          at the time the order was placed.
        book_title (str, optional): Denormalized book title for display convenience.
        book_image_url (str, optional): Denormalized book image URL for display convenience.
    """
    def __init__(self, order_id: int, book_id: int, quantity: int, 
                 unit_price_at_purchase, order_item_id: int = None,
                 book_title: str = None, book_image_url: str = None): # Added denormalized fields
        """
        Initializes a new OrderItem instance.

        Args:
            order_id (int): The ID of the parent order.
            book_id (int): The ID of the book.
            quantity (int): The quantity of this book ordered.
            unit_price_at_purchase (str | float | int | Decimal): The price of one unit of the book
                                                                  at the time of purchase. Will be
                                                                  converted to Decimal.
            order_item_id (int, optional): The unique ID of this order item (if it already exists).
                                           Defaults to None for new items.
            book_title (str, optional): The title of the book (denormalized for display).
            book_image_url (str, optional): The image URL of the book (denormalized for display).
        """
        self.order_item_id = order_item_id
        self.id = order_item_id # Common alias
        self.order_id = order_id
        self.book_id = book_id
        try:
            self.quantity = int(quantity) if quantity is not None else 0
        except ValueError:
            logger.warning(f"Invalid quantity value '{quantity}' for order item with book_id {book_id}. Defaulting to 0.")
            self.quantity = 0
            
        try:
            self.unit_price_at_purchase = Decimal(str(unit_price_at_purchase)) if unit_price_at_purchase is not None else Decimal('0.00')
        except InvalidOperation:
            logger.warning(f"Invalid unit_price_at_purchase value '{unit_price_at_purchase}' for order item with book_id {book_id}. Defaulting to 0.00.")
            self.unit_price_at_purchase = Decimal('0.00')

        # Optional denormalized fields, typically populated when fetching order details with joins
        self.book_title = book_title 
        self.book_image_url = book_image_url

    @classmethod
    def from_row(cls, row_dict: dict):
        """
        Class method to create an OrderItem instance from a database row dictionary.

        Args:
            row_dict (dict): A dictionary representing a row from the 'order_items' table.
                             Expected keys match database column names. It may also contain
                             joined data like 'book_title' or 'book_image_url'.
        Returns:
            OrderItem | None: An OrderItem object if row_dict is valid, otherwise None.
        """
        if not row_dict:
            logger.debug("OrderItem.from_row received empty or None row_dict, returning None.")
            return None
        
        return cls(
            order_item_id=row_dict.get('order_item_id'), # Matches DB schema if it's order_item_id
            order_id=row_dict.get('order_id'),
            book_id=row_dict.get('book_id'),
            quantity=row_dict.get('quantity'),
            unit_price_at_purchase=row_dict.get('unit_price_at_purchase'), # Matches DB schema
            # Denormalized fields from JOINs, if present in row_dict
            book_title=row_dict.get('book_title'),
            book_image_url=row_dict.get('book_image_url')
        )

    def to_dict(self) -> dict:
        """
        Returns a dictionary representation of the order item, suitable for JSON serialization.
        Calculates the total price for this item.

        Returns:
            dict: A dictionary containing the order item's attributes.
        """
        item_total = (self.unit_price_at_purchase * Decimal(self.quantity)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        data = {
            'order_item_id': self.order_item_id,
            'id': self.id, # Alias
            'order_id': self.order_id,
            'book_id': self.book_id,
            'quantity': self.quantity,
            'unit_price_at_purchase': str(self.unit_price_at_purchase.quantize(Decimal("0.01"))) if self.unit_price_at_purchase is not None else "0.00", # String
            'item_total': str(item_total) # Already rounded
        }
        # Include denormalized book details if they were populated
        if self.book_title:
            data['book_title'] = self.book_title

        if self.book_image_url:
            data['book_image_url'] = self.book_image_url

        return data

    def __repr__(self):
        return (f"<OrderItem id={self.order_item_id} order_id={self.order_id} book_id={self.book_id} "
                f"qty={self.quantity} price_each={self.unit_price_at_purchase}>")

    # Note: Persistence methods (save, update, delete) for OrderItem instances
    # are typically handled by the order_service.py as part of a larger transaction
    # when an order is created or modified, rather than on the OrderItem model itself.