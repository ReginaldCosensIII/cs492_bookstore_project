# app/services/order_service.py

from datetime import datetime                                               # For handling order dates and timestamps
from app.models.order import Order                                          # Order model class
from app.logger import get_logger                                           # Custom application logger
from decimal import Decimal, ROUND_HALF_UP                                  # For precise financial calculations
from app.models.order_item import OrderItem                                 # OrderItem model class
from app.models.db import get_db_connection                                 # For database connections
from typing import List, Dict, Any, Optional                                # For type hinting
from app.services.book_service import get_book_by_id, decrease_book_stock   # To interact with book data and stock
from app.services.exceptions import (                                       # Custom exceptions for error handling
    OrderProcessingError, ValidationError, NotFoundError, DatabaseError, AuthorizationError
)

logger = get_logger(__name__) 

def create_order_from_cart(user_id: Optional[int], 
                           cart_items_session: Dict[str, int], 
                           shipping_details: Dict[str, Any], 
                           guest_email_for_order: Optional[str] = None) -> Order:
    """
    Creates a new order from items in the user's session cart and provided shipping details.

    This service orchestrates the order creation process, including validation,
    total calculation, stock checking, database transaction management for inserting
    order and order item records, and updating book stock.

    Args:
        user_id (Optional[int]): ID of the authenticated user, or `None` for guest orders.
        cart_items_session (Dict[str, int]): Cart items (book_id str -> quantity int).
        shipping_details (Dict[str, Any]): Shipping address details. Expected keys match
                                           Order model: 'shipping_address_line1', 'shipping_city', 
                                           'shipping_state', 'shipping_zip_code', and 
                                           optionally 'shipping_address_line2'. Assumed pre-sanitized.
        guest_email_for_order (Optional[str]): Email for guest orders.

    Returns:
        Order: The created `Order` object with its associated `OrderItem` list.

    Raises:
        ValidationError: If cart is empty, shipping details invalid, or cart item data malformed.
        OrderProcessingError: For issues preventing order completion (e.g., insufficient stock).
        NotFoundError: If a book in the cart is not found.
        DatabaseError: For underlying database errors.
    """
    log_user_context = f"user_id: {user_id}" if user_id else f"guest_email: {guest_email_for_order or 'N/A'}"
    logger.info(f"Service: Initiating order creation for {log_user_context} with {len(cart_items_session)} distinct item types.")

    if not cart_items_session:
        logger.warning(f"Order creation attempt by {log_user_context} with an empty cart.")

        raise ValidationError("Cannot place an order: your shopping cart is currently empty.")

    required_shipping_fields = ['shipping_address_line1', 'shipping_city', 'shipping_state', 'shipping_zip_code']

    for field_key in required_shipping_fields:

        if not shipping_details.get(field_key,"").strip():
            logger.warning(f"Order creation for {log_user_context} failed: Missing required shipping field '{field_key}'.")

            raise ValidationError(
                message=f"The shipping field '{field_key.replace('shipping_', '').replace('_', ' ').title()}' is required.",
                errors={field_key: "This field is required."}
            )
    
    conn = None
    order_items_to_process_for_db: List[Dict[str, Any]] = []
    calculated_total_amount = Decimal('0.00')

    try:
        logger.debug(f"Service: Pre-validating cart items and calculating total for {log_user_context}...")

        for book_id_str, quantity_in_cart_str in cart_items_session.items():

            try:
                book_id = int(book_id_str)
                quantity = int(quantity_in_cart_str)

                if quantity <= 0: raise ValueError("Item quantity in cart must be positive.")
                
                book = get_book_by_id(book_id) # Raises NotFoundError if not found
                
                if quantity > book.stock_quantity:
                    logger.warning(f"Order Processing (Pre-check): Insufficient stock for '{book.title}' (ID: {book_id}). Req: {quantity}, Avail: {book.stock_quantity}.")

                    raise OrderProcessingError(
                        f"Not enough stock for '{book.title.title()}'. Only {book.stock_quantity} available. Please update your cart.",
                        errors={'cart_item_stock': f"Insufficient stock for {book.title.title()}"}
                    )
                
                price_at_purchase = book.price 
                item_total = price_at_purchase * Decimal(quantity)
                calculated_total_amount += item_total
                order_items_to_process_for_db.append({
                    'book_id': book_id, 'quantity': quantity, 
                    'unit_price_at_purchase': price_at_purchase, 'book_title': book.title
                })

            except ValueError as ve:

                logger.error(f"Invalid book_id ('{book_id_str}') or quantity ('{quantity_in_cart_str}') in cart for {log_user_context}: {ve}", exc_info=True)
                raise ValidationError(f"Invalid data for book ID '{book_id_str}' or quantity '{quantity_in_cart_str}' in your cart.")
            
            # NotFoundError from get_book_by_id propagates

        if not order_items_to_process_for_db:
             raise ValidationError("No valid items to order after validation.")
        
        calculated_total_amount = calculated_total_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        logger.info(f"Order pre-calculation for {log_user_context}: Total amount ${calculated_total_amount:.2f}, Items: {len(order_items_to_process_for_db)}")

        conn = get_db_connection()
        conn.autocommit = False 

        order_status = "Pending Payment" 
        order_date_db = datetime.utcnow()
        
        # SQL query for inserting into 'orders' table.
        # Your 'orders' schema has order_date and updated_at. No separate created_at.
        # guest_email column is assumed to exist and be nullable.
        order_insert_query = """
            INSERT INTO orders (user_id, order_date, total_amount, status, 
                                shipping_address_line1, shipping_address_line2, 
                                shipping_city, shipping_state, shipping_zip_code,
                                guest_email, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
            RETURNING order_id, order_date, status, updated_at; 
        """ 
        
        with conn.cursor() as cur:
            cur.execute(order_insert_query, (
                user_id, order_date_db, calculated_total_amount, order_status,
                shipping_details.get('shipping_address_line1'),
                shipping_details.get('shipping_address_line2'),
                shipping_details.get('shipping_city'), 
                shipping_details.get('shipping_state'), 
                shipping_details.get('shipping_zip_code'),
                guest_email_for_order if not user_id else None,
                order_date_db # Set updated_at initially to order_date
            ))

            created_order_data_row = cur.fetchone()

            if not created_order_data_row or 'order_id' not in created_order_data_row:
                raise DatabaseError("Order creation failed: Could not retrieve order details post-insert.")
            
            new_order_id = created_order_data_row['order_id']
            db_order_date_returned = created_order_data_row['order_date'] 
            db_order_status_returned = created_order_data_row['status']
            db_updated_at_returned = created_order_data_row.get('updated_at', db_order_date_returned)

            logger.info(f"Order record {new_order_id} inserted into DB for {log_user_context}")

            order_item_insert_query = """
                INSERT INTO order_items (order_id, book_id, quantity, unit_price_at_purchase)
                VALUES (%s, %s, %s, %s)
                RETURNING order_item_id;
            """
            created_order_item_models: List[OrderItem] = []
            
            for item_data in order_items_to_process_for_db:
                decrease_book_stock(item_data['book_id'], item_data['quantity'], db_conn=conn) 
                cur.execute(order_item_insert_query, (
                    new_order_id, item_data['book_id'], 
                    item_data['quantity'], item_data['unit_price_at_purchase']
                ))

                order_item_result_row = cur.fetchone()

                if not order_item_result_row or 'order_item_id' not in order_item_result_row:
                    raise DatabaseError(f"Failed to create order item for book ID {item_data['book_id']} in order {new_order_id}")
                
                item_instance_data = {**item_data, **order_item_result_row, 'order_id': new_order_id}
                created_order_item_models.append(OrderItem.from_row(item_instance_data))
            
            conn.commit()
            logger.info(f"Order {new_order_id} fully committed for {log_user_context}.")

            # Construct Order object using data confirmed from DB and inputs
            final_order = Order(
                order_id=new_order_id, 
                user_id=user_id, 
                order_date=db_order_date_returned, # This serves as creation time
                total_amount=calculated_total_amount, 
                status=db_order_status_returned,
                shipping_address_line1=shipping_details.get('shipping_address_line1'),
                shipping_address_line2=shipping_details.get('shipping_address_line2'),
                shipping_city=shipping_details.get('shipping_city'),
                shipping_state=shipping_details.get('shipping_state'),
                shipping_zip_code=shipping_details.get('shipping_zip_code'),
                guest_email=guest_email_for_order if not user_id else None,
                updated_at=db_updated_at_returned 
                # Order model's __init__ uses order_date for its internal `created_at` logic
            )

            final_order.items = created_order_item_models

            return final_order

    except (ValidationError, NotFoundError, OrderProcessingError, DatabaseError) as business_error:
        if conn: conn.rollback()

        logger.warning(f"Order creation for {log_user_context} failed: {getattr(business_error, 'log_message', str(business_error))}")
        
        raise 

    except Exception as e: 
        if conn: conn.rollback()

        logger.error(f"Critical unexpected error during order creation for {log_user_context}: {e}", exc_info=True)

        raise OrderProcessingError(message="Could not process your order due to an unexpected internal error.", original_exception=e)
    
    finally:
        if conn:
            conn.autocommit = True 
            conn.close()
            logger.debug(f"Database connection closed for order creation attempt by {log_user_context}.")


def get_orders_by_user(user_id: int) -> List[Order]:
    """
    Retrieves a summary list of all orders placed by a specific registered user.
    Orders are returned newest first. Does not load order items for performance.

    Args:
        user_id (int): The ID of the user whose orders are to be fetched.

    Returns:
        List[Order]: A list of `Order` objects. Returns empty if no orders found.
    
    Raises:
        DatabaseError: If an underlying database error occurs.
    """
    logger.info(f"Service: Fetching order history summary for user_id: {user_id}")
    # Your 'orders' table has 'order_date' and 'updated_at', but no separate 'created_at'.
    # Order.from_row should handle mapping 'order_date' to the object's creation time aspect.
    query = """
        SELECT order_id, user_id, guest_email, order_date, total_amount, status,
               shipping_address_line1, shipping_address_line2, 
               shipping_city, shipping_state, shipping_zip_code,
               updated_at 
        FROM orders 
        WHERE user_id = %s 
        ORDER BY order_date DESC;
    """ 

    conn = None
    orders_list: List[Order] = []

    try:
        conn = get_db_connection()

        with conn.cursor() as cur:
            cur.execute(query, (user_id,))
            order_rows = cur.fetchall()

            for row_dict in order_rows:
                orders_list.append(Order.from_row(row_dict))

        logger.info(f"Service: Found {len(orders_list)} orders for user_id: {user_id}")

        return orders_list
    
    except Exception as e:
        logger.error(f"Service: Error fetching orders for user {user_id}: {e}", exc_info=True)

        raise DatabaseError("Could not retrieve your order history due to a database problem.", original_exception=e)
    
    finally:
        if conn: conn.close()


def get_order_details(order_id: int, user_id_for_auth: Optional[int] = None, 
                      guest_email_for_auth: Optional[str] = None) -> Optional[Order]:
    """
    Retrieves full details for a specific order, including line items and book information.
    Performs authorization checks based on `user_id_for_auth` or `guest_email_for_auth`.

    Args:
        order_id (int): ID of the order.
        user_id_for_auth (Optional[int]): ID of authenticated user for ownership check.
        guest_email_for_auth (Optional[str]): Email of guest for guest order verification.

    Returns:
        Optional[Order]: The `Order` object with items if found and authorized.

    Raises:
        NotFoundError: If no order with `order_id` is found.
        AuthorizationError: If the requester is not authorized.
        DatabaseError: For underlying database errors.
    """
    auth_context_parts = []

    if user_id_for_auth: auth_context_parts.append(f"user_id {user_id_for_auth}")

    if guest_email_for_auth: auth_context_parts.append(f"guest_email {guest_email_for_auth}")

    auth_context = " or ".join(auth_context_parts) if auth_context_parts else "unknown requester"
    logger.info(f"Service: Fetching full details for order_id: {order_id}, requested by: {auth_context}")
    
    # Your 'orders' table has 'order_date' and 'updated_at', no separate 'created_at'.
    order_query = """
        SELECT order_id, user_id, guest_email, order_date, total_amount, status,
               shipping_address_line1, shipping_address_line2, 
               shipping_city, shipping_state, shipping_zip_code,
               updated_at 
        FROM orders WHERE order_id = %s;
    """

    items_query = """
        SELECT oi.order_item_id, oi.order_id, oi.book_id, oi.quantity, oi.unit_price_at_purchase,
               b.title AS book_title, b.image_url AS book_image_url 
        FROM order_items oi
        JOIN books b ON oi.book_id = b.book_id
        WHERE oi.order_id = %s ORDER BY oi.order_item_id ASC;
    """

    conn = None

    try:
        conn = get_db_connection()

        with conn.cursor() as cur: 
            cur.execute(order_query, (order_id,))
            order_row = cur.fetchone() 

            if not order_row:
                raise NotFoundError(resource_name="Order", resource_id=order_id)

            # Authorization
            if user_id_for_auth is not None: 

                if order_row.get('user_id') != user_id_for_auth:
                    raise AuthorizationError("You are not authorized to view this order's details.")
                
            elif guest_email_for_auth is not None: 

                if order_row.get('user_id') is not None or \
                   (order_row.get('guest_email') or '').strip().lower() != guest_email_for_auth.strip().lower():
                    
                    raise AuthorizationError("Cannot view this order with the provided guest email.")
                
            else: 
                raise AuthorizationError("Authentication details required to view this order.")

            order = Order.from_row(order_row)
            cur.execute(items_query, (order_id,))
            item_rows = cur.fetchall()

            for item_row_dict in item_rows:
                item = OrderItem.from_row(item_row_dict)
                order.items.append(item)
        
        logger.info(f"Service: Successfully fetched order {order_id} details with {len(order.items)} for {auth_context}.")

        return order
    
    except (NotFoundError, AuthorizationError) as specific_error:
        logger.warning(f"Access/retrieval issue for order {order_id} ({auth_context}): {getattr(specific_error, 'log_message', str(specific_error))}")

        raise

    except Exception as e:
        logger.error(f"Service: Unexpected error fetching details for order {order_id} ({auth_context}): {e}", exc_info=True)

        raise DatabaseError("Could not retrieve the details for this order.", original_exception=e)
    
    finally:
        if conn: conn.close()