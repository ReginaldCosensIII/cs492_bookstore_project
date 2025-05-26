# cs492_bookstore_project/app/cart/routes.py

import re                                                                               # For EMAIL_REGEX validation
from . import cart_bp                                                                   # Import the BP instance
from app.logger import get_logger                                                       # Custom application logger
from flask_login import current_user                                                    # login_required is used selectively
from typing import Dict, Tuple, List, Any                                               # For type hinting
from decimal import Decimal, ROUND_HALF_UP                                              # For precise $$ calculations
from app.services.book_service import get_book_by_id                                    # Service to fetch book details
from app.services.order_service import create_order_from_cart                           # Service to create orders
from app.utils import sanitize_html_text, normalize_whitespace                          # For input sanitization
from flask import request, session, jsonify, render_template, flash, redirect, url_for
from app.services.exceptions import (                                                   # Custom exceptions for error handling
    NotFoundError, 
    CartActionError, 
    ValidationError, 
    OrderProcessingError,
    DatabaseError
)

logger = get_logger(__name__) # Logger instance for this module

# Regular expression for validating email format, used for guest checkout.
EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

def _get_user_context_for_log() -> str:
    """
    Helper function to generate a consistent string representation for logging 
    the current user context (authenticated user or guest).

    Returns:
        str: A string identifying the user, e.g., "user 123 (user@example.com)" or "guest user".
    """
    if current_user.is_authenticated:
        user_id_log = getattr(current_user, 'id', 'UNKNOWN_ID')
        user_email_log = getattr(current_user, 'email', 'UNKNOWN_EMAIL')

        return f"user {user_id_log} ({user_email_log})"
    
    return "guest user"

def _calculate_current_cart_total_and_items(cart_session: Dict[str, int]) -> Tuple[List[Dict[str, Any]], Decimal, bool]:
    """
    Calculates the detailed list of items in the cart, the grand total amount,
    and an emptiness flag based on the provided session cart data.

    This helper iterates through the cart items, fetches current book details (price, stock)
    using `book_service.get_book_by_id`, and performs calculations using `Decimal` for precision.
    It prepares a list of dictionaries, each representing a cart item with details suitable
    for display in templates (e.g., `cart.html`, `checkout.html`).

    Args:
        cart_session (Dict[str, int]): The cart data from the session, where keys are 
                                       book IDs (as strings) and values are quantities.

    Returns:
        Tuple[List[Dict[str, Any]], Decimal, bool]: A tuple containing:
            - `cart_items_detailed` (List[Dict[str, Any]]): A list of dictionaries,
              each detailing a cart item (book_id, title, quantity, unit_price, image_url,
              total_price, stock_quantity).
            - `grand_total` (Decimal): The calculated total amount for all items in the cart,
              rounded to two decimal places.
            - `is_empty` (bool): True if the cart is effectively empty after validation 
              (no valid items), False otherwise.
    """
    cart_items_detailed: List[Dict[str, Any]] = []
    grand_total = Decimal('0.00')
    user_context_for_log = _get_user_context_for_log() # For logging context

    if not cart_session:
        logger.debug(f"_calculate_current_cart_total_and_items: Cart session is empty for {user_context_for_log}.")
        
        return cart_items_detailed, grand_total, True # True for is_empty

    processed_book_ids = set() # Avoid processing duplicates if session data were malformed

    for book_id_str, quantity_in_cart in cart_session.items():
        
        if book_id_str in processed_book_ids: continue # Should not happen with dict keys
        processed_book_ids.add(book_id_str)
        
        try:
            book_id_int = int(book_id_str)
            current_quantity = int(quantity_in_cart)

            if current_quantity <= 0:
                logger.info(f"_calculate_cart: Skipping item {book_id_str} (qty: {current_quantity}) for {user_context_for_log}.")
                continue

            book = get_book_by_id(book_id_int) # Service function raises NotFoundError if not found

            if not book: # Should be caught by NotFoundError from service, but defensive
                logger.warning(f"_calculate_cart: Book ID {book_id_str} not found for {user_context_for_log}. Skipping.")
                continue 
            
            # Ensure book.price is a Decimal for calculations
            book_price_decimal = book.price

            if not isinstance(book_price_decimal, Decimal):
                try:
                    book_price_decimal = Decimal(str(book.price))

                except Exception: # Catch broad error for Decimal conversion
                    logger.error(f"_calculate_cart: Invalid price type for book ID {book.book_id} ('{book.price}'). Skipping for {user_context_for_log}.")

                    continue
            
            item_total = book_price_decimal * Decimal(current_quantity) # Decimal arithmetic
            item_total_rounded = item_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            cart_items_detailed.append({
                "book_id": book.book_id, 
                "title": book.title.title(), # Display title case
                "quantity": current_quantity, 
                "unit_price": book_price_decimal, # Store as Decimal
                "image_url": book.image_url, 
                "total_price": item_total_rounded, # Store rounded Decimal
                "stock_quantity": book.stock_quantity 
            })
            grand_total += item_total # Accumulate exact item_total

        except ValueError:
            logger.warning(f"_calculate_cart: Invalid format for book_id '{book_id_str}' or quantity '{quantity_in_cart}' for {user_context_for_log}. Skipping.")

        except NotFoundError:
             logger.warning(f"_calculate_cart: Book ID {book_id_str} from cart not found for {user_context_for_log}. Skipping.")

        except Exception as e: # Catch-all for unexpected issues with a single item
            logger.error(f"_calculate_cart: Unexpected error processing cart item {book_id_str} for {user_context_for_log}: {e}", exc_info=True)
            
    grand_total = grand_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    is_empty = not bool(cart_items_detailed) # True if list is empty
    logger.debug(f"_calculate_cart for {user_context_for_log}: {len(cart_items_detailed)} items, Total: {grand_total}")

    return cart_items_detailed, grand_total, is_empty


@cart_bp.route("/add_to_cart", methods=["POST"])
# No @login_required decorator - allows guests to add items to their session cart.
def add_to_cart_route():
    """
    Handles AJAX requests to add a book to the shopping cart stored in the session.
    It checks for available stock and caps the quantity if the request exceeds stock.
    Provides informative JSON responses about the outcome of the action.

    Request JSON Payload:
        {
            "book_id": "string_or_int", 
            "quantity": int 
        }

    Returns:
        JSON: A JSON response indicating success or failure, with a message,
              current cart item count, total cart value, and the actual quantity
              of the item now in the cart.
    """
    user_context_for_log = _get_user_context_for_log()
    data = None 
    
    try:
        data = request.get_json()

        if not data: 
            logger.warning(f"Add to cart attempt by {user_context_for_log} - Invalid request: No JSON data.")

            raise CartActionError("Invalid request data: Expected JSON payload.")
            
        book_id_str = str(data.get("book_id"))
        requested_quantity_to_add = int(data.get("quantity", 1)) # Default to adding 1 if not specified

        if not book_id_str or requested_quantity_to_add < 1:
            logger.warning(f"Add to cart by {user_context_for_log} - Invalid input: book_id='{book_id_str}', quantity='{requested_quantity_to_add}'.")

            raise CartActionError("Book ID and a valid positive quantity are required.")

        book_id_int = int(book_id_str)
        book = get_book_by_id(book_id_int) # Raises NotFoundError if book doesn't exist
        
        cart = session.get("cart", {}) # Retrieve current cart from session
        current_quantity_in_cart_for_item = cart.get(book_id_str, 0)
        
        message = ""
        final_quantity_for_item_in_cart = current_quantity_in_cart_for_item
        quantity_actually_added_this_time = 0
        operation_status_success = True # Tracks if user's primary intent (add quantity) was met

        if book.stock_quantity == 0 and current_quantity_in_cart_for_item == 0 : # Book is out of stock
            message = f"Sorry, '{book.title.title()}' is currently out of stock. Cannot add to cart."
            operation_status_success = False # Nothing could be added

        else:
            # Calculate how many more can be added before hitting total stock limit
            available_to_add_now = book.stock_quantity - current_quantity_in_cart_for_item
            
            if available_to_add_now <= 0: # Cart already has max stock or more (should be rare)
                message = f"Cannot add more of '{book.title.title()}'. Your cart already contains the maximum available stock ({book.stock_quantity})."

                if requested_quantity_to_add > 0 : operation_status_success = False # User tried to add but couldn't

            elif requested_quantity_to_add <= available_to_add_now:
                # Can add the full requested quantity without exceeding stock
                final_quantity_for_item_in_cart = current_quantity_in_cart_for_item + requested_quantity_to_add
                quantity_actually_added_this_time = requested_quantity_to_add
                message = f"Successfully added {quantity_actually_added_this_time} of '{book.title.title()}' to your cart. Cart now has {final_quantity_for_item_in_cart}."

            else: # requested_quantity_to_add > available_to_add_now (and available_to_add_now > 0)
                # Can only add some (up to stock limit)
                final_quantity_for_item_in_cart = book.stock_quantity # Cap at total stock
                quantity_actually_added_this_time = available_to_add_now 
                message = (f"You requested to add {requested_quantity_to_add}, but only {quantity_actually_added_this_time} more of '{book.title.title()}' "
                           f"could be added due to stock limits. Cart now contains {final_quantity_for_item_in_cart} (max available stock).")
        
        # Update cart session only if the final quantity is positive
        if final_quantity_for_item_in_cart > 0:
            cart[book_id_str] = final_quantity_for_item_in_cart

        elif book_id_str in cart: # If final quantity is 0 and item was in cart, remove it
            del cart[book_id_str]
        
        session["cart"] = cart
        session.modified = True

        _, current_cart_total, _ = _calculate_current_cart_total_and_items(cart)
        logger.info(
            f"Add to cart: Book {book_id_str}, by {user_context_for_log}. "
            f"Req add: {requested_quantity_to_add}, Actually added: {quantity_actually_added_this_time}. "
            f"Final cart item qty: {cart.get(book_id_str, 0)}. Message: {message}"
        )
        
        response_payload = {
            "success": operation_status_success, 
            "message": message,
            "cart_item_count": sum(v for v in cart.values() if isinstance(v, int)),
            "cart_total_str": f"{current_cart_total:.2f}",
            "actual_quantity_in_cart_for_item": cart.get(book_id_str, 0) 
        }
        # If operation_status_success is False, JS might use 'error' key if present
        if not operation_status_success:
             response_payload["error"] = message 

        return jsonify(response_payload), 200

    except NotFoundError as nfe:
        book_id_attempt = data.get('book_id') if data and isinstance(data,dict) else 'N/A'
        logger.warning(f"Add to cart by {user_context_for_log} failed: {nfe.user_facing_message} (Book ID attempt: {book_id_attempt})")

        return jsonify({"success": False, "error": nfe.user_facing_message}), nfe.status_code
    
    except CartActionError as cae:
        logger.warning(f"Add to cart by {user_context_for_log} failed with CartActionError: {cae.user_facing_message}")

        return jsonify({"success": False, "error": cae.user_facing_message}), cae.status_code
    
    except ValueError: # For int conversion errors
        data_log = data if data and isinstance(data, dict) else 'N/A'
        logger.warning(f"Add to cart by {user_context_for_log} failed: Invalid book ID or quantity format. Data: {data_log}")

        return jsonify({"success": False, "error": "Invalid book ID or quantity format."}), 400
    
    except Exception as e:
        logger.error(f"Unexpected error adding to cart for {user_context_for_log}: {e}", exc_info=True)
        
        return jsonify({"success": False, "error": "Could not add item to cart due to an internal server error."}), 500


@cart_bp.route("/") 
# No @login_required - guests can view their session cart
def view_cart_route():
    """
    Displays the shopping cart page (`cart.html`).
    It retrieves cart items from the session, fetches current book details for each
    item (including price and stock), adjusts quantities in the session if necessary
    (e.g., if stock has changed or items are invalid), and calculates the total.
    Guests and logged-in users can view their respective session carts.

    Returns:
        Response: Renders the cart template with cart items and total.
    """
    user_context_for_log = _get_user_context_for_log()
    cart_session = session.get("cart", {}) # Get current cart from session
    logger.info(f"Viewing cart for {user_context_for_log}. Initial session cart: {cart_session}")
    
    # Calculate detailed items and total based on the current session cart
    # This helper does not modify the session itself but reflects current data.
    cart_items_for_display, grand_total_for_display, cart_is_empty_for_display = \
        _calculate_current_cart_total_and_items(cart_session)
    
    # Perform a session clean-up pass:
    # Adjust quantities in the *session* if stock has changed or items are invalid.
    # This ensures the session is accurate for subsequent actions (like checkout).
    current_cart_in_session = session.get("cart", {}).copy() # Work on a copy for modifications
    session_was_modified = False
    
    for book_id_str, quantity_in_session_cart in list(current_cart_in_session.items()):
        try:
            book_id_int = int(book_id_str)
            current_session_quantity = int(quantity_in_session_cart)

            if current_session_quantity <= 0: # Item has invalid quantity in session
                del current_cart_in_session[book_id_str]
                session_was_modified = True
                logger.info(f"Removed book ID {book_id_str} from session (quantity <= 0) during cart view for {user_context_for_log}")
                flash(f"Item with ID {book_id_str} was removed from your cart due to invalid quantity.", "info")

                continue

            book = get_book_by_id(book_id_int) # May raise NotFoundError
            if not book: # Should be caught by NotFoundError, but defensive
                del current_cart_in_session[book_id_str]
                session_was_modified = True
                logger.warning(f"Removed non-existent book ID {book_id_str} from session for {user_context_for_log}")
                flash(f"A book (ID: {book_id_str}) in your cart is no longer available and has been removed.", "warning")

                continue

            # Check if quantity in session exceeds current available stock
            if current_session_quantity > book.stock_quantity:
                new_valid_quantity_for_session = book.stock_quantity

                if new_valid_quantity_for_session > 0:
                    current_cart_in_session[book_id_str] = new_valid_quantity_for_session
                    flash(f"Quantity for '{book.title.title()}' was automatically adjusted in your cart to available stock: {new_valid_quantity_for_session}.", "warning")

                else: # Stock is now 0, remove item from session cart
                    del current_cart_in_session[book_id_str]
                    flash(f"'{book.title.title()}' was removed from your cart as it's now out of stock.", "warning")

                session_was_modified = True
                logger.info(f"Adjusted/removed quantity in session for book ID {book_id_str} (stock: {book.stock_quantity}) for {user_context_for_log}")

        except (ValueError, NotFoundError): # If book_id is bad or book no longer exists
            if book_id_str in current_cart_in_session:
                del current_cart_in_session[book_id_str]
                session_was_modified = True

            logger.warning(f"Removed invalid or non-existent book ID {book_id_str} from session during cart view validation for {user_context_for_log}")
            flash(f"An item (ID: {book_id_str}) in your cart was invalid or no longer available and has been removed.", "warning")

        except Exception as e: # Catch-all for other issues with an item during session clean
            logger.error(f"Unexpected error during cart session clean for item {book_id_str} ({user_context_for_log}): {e}", exc_info=True)

            if book_id_str in current_cart_in_session: # Attempt to remove problematic item
                del current_cart_in_session[book_id_str]
                session_was_modified = True

    if session_was_modified:
        session["cart"] = current_cart_in_session # Save the cleaned cart back to session
        session.modified = True
        logger.info(f"Cart session updated for {user_context_for_log} after validation. Re-calculating display items based on cleaned session.")
        # Re-calculate display items and total with the cleaned session data
        cart_items_for_template, grand_total_for_template, cart_is_empty = \
            _calculate_current_cart_total_and_items(current_cart_in_session)
        
    else:
        # If session wasn't modified, the initial calculation is still valid
        cart_items_for_template = cart_items_for_display
        grand_total_for_template = grand_total_for_display
        cart_is_empty = cart_is_empty_for_display


    logger.info(f"Rendering cart page for {user_context_for_log}. Items to display: {len(cart_items_for_template)}, Calculated Total: ${grand_total_for_template:.2f}, IsEmpty: {cart_is_empty}")

    return render_template("cart.html", 
                           cart_items=cart_items_for_template, 
                           cart_total=grand_total_for_template, 
                           is_empty=cart_is_empty)


@cart_bp.route("/remove", methods=["POST"])
# No @login_required - guests can modify their session cart
def remove_from_cart_route():
    """
    Handles AJAX requests to remove a book item completely from the session cart.

    Request JSON Payload:
        { "book_id": "string_or_int" }

    Returns:
        JSON: A JSON response indicating success or failure, with a message,
              updated cart item count, and new cart total.
    """
    user_context_for_log = _get_user_context_for_log()
    data = None

    try:
        data = request.get_json()

        if not data: raise CartActionError("Invalid request: Expected JSON payload.")

        book_id_str = str(data.get("book_id"))

        if not book_id_str: raise CartActionError("Book ID is required for removal.")

        cart = session.get("cart", {})
        book_title_for_msg = "The item" # Default title for message

        if book_id_str in cart:
            try: # Attempt to get book title for a nicer message
                book = get_book_by_id(int(book_id_str))

                if book: book_title_for_msg = f"'{book.title.title()}'"

            except NotFoundError: pass # Book might be deleted, use default title
            except ValueError: pass # book_id_str might be invalid format

            del cart[book_id_str]
            session["cart"] = cart
            session.modified = True
            logger.info(f"Book ID {book_id_str} removed from cart for {user_context_for_log}.")
            
            _, new_total, _ = _calculate_current_cart_total_and_items(cart)

            return jsonify({
                "success": True, "message": f"{book_title_for_msg} has been removed from your cart.",
                "cart_item_count": sum(v for v in cart.values() if isinstance(v, int)),
                "new_cart_total_str": f"{new_total:.2f}" 
            }), 200
        
        else:
            logger.warning(f"Attempt to remove non-existent book ID {book_id_str} from cart by {user_context_for_log}.")

            raise CartActionError("Item was not found in your cart to remove.", status_code=404) # 404 if item not in cart
            
    except CartActionError as cae:
        logger.warning(f"Remove from cart by {user_context_for_log} failed: {cae.user_facing_message}")

        return jsonify({"success": False, "error": cae.user_facing_message}), cae.status_code
    
    except Exception as e:
        logger.error(f"Unexpected error removing item from cart for {user_context_for_log}: {e}", exc_info=True)

        return jsonify({"success": False, "error": "Could not remove item from cart due to a server error."}), 500


@cart_bp.route("/update", methods=["POST"])
# No @login_required - guests can modify their session cart
def update_cart_quantity_route():
    """
    Handles AJAX requests to update the quantity of a specific book in the session cart.
    If requested quantity exceeds stock, it's capped. If quantity is set to 0 or less,
    the item is removed from the cart.

    Request JSON Payload:
        { 
            "book_id": "string_or_int",
            "quantity": int 
        }

    Returns:
        JSON: A JSON response indicating success or failure, with a message,
              updated cart item count, new cart total, actual quantity set for the item,
              and the new total price for that specific item.
    """
    user_context_for_log = _get_user_context_for_log()
    data = None

    try:
        data = request.get_json()

        if not data: raise CartActionError("Invalid request: Expected JSON payload.")

        book_id_str = str(data.get("book_id"))
        requested_quantity = int(data.get("quantity", 0)) # Default to 0 if not provided

        if not book_id_str: raise CartActionError("Book ID is required for quantity update.")

        cart = session.get("cart", {})

        # Handle case where item might not be in cart (e.g., if user tries to update non-existent item)
        if book_id_str not in cart and requested_quantity > 0:
            logger.warning(f"Attempt to update quantity for non-existent book ID {book_id_str} in cart by {user_context_for_log}.")
            # This could be treated as an "add" action, or an error. For "update", it's an error.
            raise CartActionError("Item not found in cart. Please add the item before updating quantity.", status_code=404)
        
        elif book_id_str not in cart and requested_quantity <=0:
             return jsonify({"success": True, "message": "Item was not in cart, no action taken."}), 200 # Benign
            
        book = get_book_by_id(int(book_id_str)) # Raises NotFoundError if book is invalid/deleted
        
        message = ""
        final_quantity_set_in_cart = requested_quantity

        if requested_quantity > 0:
            if requested_quantity > book.stock_quantity:
                final_quantity_set_in_cart = book.stock_quantity
                message = f"Quantity for '{book.title.title()}' was automatically adjusted to the maximum available stock: {final_quantity_set_in_cart}."

            else:
                message = f"Quantity for '{book.title.title()}' updated to {final_quantity_set_in_cart}."

            cart[book_id_str] = final_quantity_set_in_cart

        else: # Quantity is 0 or less, so remove the item from cart
            if book_id_str in cart: # Ensure it was actually in cart before deleting
                del cart[book_id_str]
                message = f"'{book.title.title()}' removed from cart as quantity was set to zero or less."

            else: # Should not be reached due to earlier checks
                message = f"'{book.title.title()}' was not in cart to begin with."
        
        session["cart"] = cart
        session.modified = True
        
        _, new_cart_total, _ = _calculate_current_cart_total_and_items(cart)
        # Calculate new total for this specific item based on final quantity
        item_price = book.price if book else Decimal('0.00') # Ensure book object exists
        new_item_line_total = (item_price * Decimal(final_quantity_set_in_cart if final_quantity_set_in_cart > 0 else 0)
                              ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        logger.info(f"Update cart by {user_context_for_log}: Book {book_id_str}. Final item qty in cart: {cart.get(book_id_str, 0)}. Message: {message}")
        return jsonify({
            "success": True, "message": message,
            "cart_item_count": sum(v for v in cart.values() if isinstance(v, int)),
            "new_cart_total_str": f"{new_cart_total:.2f}",
            "actual_quantity_set_for_item": cart.get(book_id_str, 0), # Current quantity of this item in cart
            "item_new_total_price_str": f"{new_item_line_total:.2f}"
        }), 200
        
    except (NotFoundError, CartActionError) as user_error:
        logger.warning(f"Update cart quantity by {user_context_for_log} failed: {user_error.user_facing_message}")

        return jsonify({"success": False, "error": user_error.user_facing_message}), user_error.status_code
    
    except ValueError: # For int conversion errors
        data_log = data if data and isinstance(data, dict) else 'N/A'
        logger.warning(f"Update cart quantity by {user_context_for_log} failed: Invalid book ID or quantity format. Data: {data_log}")

        return jsonify({"success": False, "error": "Invalid book ID or quantity format."}), 400
    
    except Exception as e:
        logger.error(f"Unexpected error updating cart quantity for {user_context_for_log}: {e}", exc_info=True)

        return jsonify({"success": False, "error": "Could not update cart quantity due to a server error."}), 500
    


@cart_bp.route("/checkout", methods=["GET"])
# No @login_required - guests can view checkout, will be prompted for details or to log in.
def checkout_page_route():
    """
    Displays the checkout page.
    If the cart is empty or items become unavailable/invalid, it redirects the user
    back to the cart view with appropriate messages.
    Pre-fills shipping address for logged-in users and guest email if available in session.
    """
    user_context_for_log = _get_user_context_for_log()
    cart_session = session.get("cart", {})

    if not cart_session:
        flash("Your cart is empty. Please add some books before proceeding to checkout.", "info")
        logger.info(f"{user_context_for_log} attempted to checkout with an empty cart session.")

        return redirect(url_for('main.home')) # Or 'cart.view_cart_route'
    

    cart_items_detailed, grand_total, is_empty = _calculate_current_cart_total_and_items(cart_session)
    
    if is_empty:
        flash("Your cart has become empty or contains only unavailable/invalid items. Please add books to your cart.", "info")
        logger.info(f"{user_context_for_log} attempted to checkout, but cart calculated as empty.")

        return redirect(url_for('cart.view_cart_route'))

    # Perform a final stock check before rendering the checkout page.
    # If stock issues are found, update the session cart and redirect back to cart view
    # where messages will be displayed by view_cart_route's session cleaning pass.
    session_updated_due_to_stock = False
    for item_on_page in cart_items_detailed: # Iterate over what _calculate_... prepared for display
        try:
            book = get_book_by_id(item_on_page["book_id"]) # Re-fetch for latest stock

            # Compare quantity intended for display with current actual stock
            if item_on_page["quantity"] > book.stock_quantity:
                flash(f"Unfortunately, stock for '{item_on_page['title']}' has changed. Only {book.stock_quantity} are available. Your cart has been updated. Please review before proceeding.", "warning")
                # Update session cart to reflect this stock change before redirecting
                book_id_session_key = str(book.book_id)

                if book_id_session_key in cart_session:
                    if book.stock_quantity > 0:
                        cart_session[book_id_session_key] = book.stock_quantity

                    else: # If stock is now 0, remove from cart
                        del cart_session[book_id_session_key]

                    session_updated_due_to_stock = True
                # Force redirect to cart view to show updated quantities and messages
                if session_updated_due_to_stock:
                    session["cart"] = cart_session
                    session.modified = True

                return redirect(url_for('cart.view_cart_route'))
            
        except NotFoundError:
             flash(f"The book '{item_on_page['title']}' is no longer available and has been removed from your cart. Please review your cart.", "danger")
             book_id_session_key = str(item_on_page["book_id"])

             if book_id_session_key in cart_session:
                 del cart_session[book_id_session_key]
                 session["cart"] = cart_session # Update session
                 session.modified = True

             return redirect(url_for('cart.view_cart_route'))

    # If session was updated, recalculate details for checkout display
    if session_updated_due_to_stock:
        cart_items_detailed, grand_total, is_empty = _calculate_current_cart_total_and_items(session.get("cart", {}))

        if is_empty: # Should be caught above, but defensive
            flash("Your cart is now empty after stock adjustments.", "info")

            return redirect(url_for('cart.view_cart_route'))


    shipping_address_to_prefill = {}
    guest_email_to_prefill = "" 

    if current_user.is_authenticated:
        # Pre-fill shipping address from user's profile if available
        shipping_address_to_prefill = {
            "shipping_address_line1": getattr(current_user, 'address_line1', '') or "",
            "shipping_address_line2": getattr(current_user, 'address_line2', '') or "",
            "shipping_city": getattr(current_user, 'city', '') or "",
            "shipping_state": getattr(current_user, 'state', '') or "",
            "shipping_zip_code": getattr(current_user, 'zip_code', '') or ""
        }

    else: # For guest, prefill email if they started checkout before and entered it
        guest_email_to_prefill = session.get('guest_checkout_email_prefill', '')

    logger.info(f"{user_context_for_log} is proceeding to the checkout page. Cart total: ${grand_total:.2f}")

    return render_template("checkout.html", 
                           cart_items=cart_items_detailed, 
                           cart_total=grand_total,
                           shipping_address=shipping_address_to_prefill, # Use specific var name
                           guest_email=guest_email_to_prefill) # Use specific var name


@cart_bp.route("/place_order", methods=["POST"])
# No @login_required; this route handles both authenticated and guest checkouts.
def place_order_route():
    """
    Handles the submission of the checkout form to place an order.
    It validates guest email (if applicable) and shipping details.
    Calls the `order_service.create_order_from_cart` to finalize the order,
    which includes stock deduction and database record creation within a transaction.
    Clears the cart from session on success and redirects to an order confirmation page.

    Returns:
        Response: Redirects to order confirmation on success, or back to checkout
                  page with error messages on failure.
    """
    user_context_for_log = _get_user_context_for_log()
    cart_session = session.get("cart", {})

    if not cart_session:
        logger.warning(f"{user_context_for_log} attempted to place order with an empty cart session.")
        flash("Your cart is empty. Cannot place an order.", "danger")

        return redirect(url_for('cart.view_cart_route'))

    form = request.form
    # Shipping details keys should match Order model __init__ params for easy unpacking in service
    shipping_details = {
        "shipping_address_line1": normalize_whitespace(form.get('shipping_address_line1', '')),
        "shipping_address_line2": normalize_whitespace(form.get('shipping_address_line2', '')),
        "shipping_city": normalize_whitespace(form.get('shipping_city', '')),
        "shipping_state": normalize_whitespace(form.get('shipping_state', '')).upper(),
        "shipping_zip_code": normalize_whitespace(form.get('shipping_zip_code', ''))
    }
    
    order_user_id = None
    guest_email_from_form = None # Use a distinct variable for email from this form submission

    if current_user.is_authenticated:
        order_user_id = current_user.id

    else: # Guest checkout: email is required from the form
        guest_email_from_form = normalize_whitespace(form.get('guest_email', '')).lower()

        if not guest_email_from_form or not re.match(EMAIL_REGEX, guest_email_from_form):
            flash("A valid email address is required for guest checkout.", "danger")
            # Re-render checkout page with errors; need cart data again
            cart_items_detailed, grand_total, _ = _calculate_current_cart_total_and_items(cart_session)

            return render_template("checkout.html", 
                                   cart_items=cart_items_detailed, cart_total=grand_total,
                                   shipping_address=shipping_details, # Pass back submitted shipping details
                                   guest_email=guest_email_from_form, # Pass back submitted (invalid) email
                                   errors={"guest_email": "A valid email address is required."}), 400
        
        # Store valid guest email in session in case they need to re-submit checkout form
        session['guest_checkout_email_prefill'] = guest_email_from_form 
        session.modified = True

    # Server-side validation for presence of required shipping fields
    required_shipping_keys_for_model = ['shipping_address_line1', 'shipping_city', 'shipping_state', 'shipping_zip_code']
    form_validation_errors = {} # To collect errors for re-rendering form

    for field_key in required_shipping_keys_for_model:
        if not shipping_details.get(field_key): # Check if empty after normalization
            error_message = "This shipping field is required."
            flash(f"The field '{field_key.replace('_',' ').title()}' is required for shipping.", "danger")
            form_validation_errors[field_key] = error_message # Key matches form field name or Order model attribute
            
    if form_validation_errors:
        cart_items_detailed, grand_total, _ = _calculate_current_cart_total_and_items(cart_session)

        return render_template("checkout.html", 
                               cart_items=cart_items_detailed, 
                               cart_total=grand_total,
                               shipping_address=shipping_details, # Pass back current shipping details
                               guest_email=guest_email_from_form if not order_user_id else None, 
                               errors=form_validation_errors), 400 # HTTP 400 for bad request
    
    try:
        logger.info(f"Attempting to place order for {user_context_for_log}. Cart: {cart_session}, Shipping: {shipping_details}")
        
        # Call the order service to create the order.
        # The service handles stock deduction and database transactions.
        order = create_order_from_cart(
            user_id=order_user_id, # Will be None for guests
            cart_items_session=cart_session, 
            shipping_details=shipping_details, # This dict uses keys like 'shipping_address_line1'
            guest_email_for_order=guest_email_from_form # Pass the validated guest email
        )
        
        # Clear cart from session on successful order creation
        session.pop("cart", None) 

        if not current_user.is_authenticated: # If it was a guest order
            session.pop("guest_checkout_email_prefill", None) # Clear prefill email
            # Set session variables for the guest to view this specific order confirmation page
            session['just_placed_order_id'] = order.order_id
            session['guest_order_email'] = guest_email_from_form # The email used for THIS order
            logger.debug(f"GUEST ORDER (place_order_route): Set session 'just_placed_order_id' to {order.order_id} and 'guest_order_email' to '{guest_email_from_form}' for confirmation page access.")

        session.modified = True # Ensure all session changes are saved
        
        logger.info(f"Order {order.order_id} placed successfully for {user_context_for_log}.")
        flash(f"Thank you! Your order (ID: {order.order_id}) has been placed successfully! A confirmation email will be sent shortly.", "success")
        
        logger.debug(f"Redirecting to order confirmation page for order_id: {order.order_id}. Current session before redirect: {dict(session)}")

        return redirect(url_for('order.order_confirmation_route', order_id=order.order_id))

    except (ValidationError, OrderProcessingError, NotFoundError, DatabaseError) as e:
        # These are specific, known exceptions from the service layer or validation.
        logger.error(f"Order placement failed for {user_context_for_log} with {type(e).__name__}: {getattr(e, 'user_facing_message', str(e))}", 
                     exc_info=True if isinstance(e, (OrderProcessingError, NotFoundError, DatabaseError)) else False) # More trace for some
        flash(getattr(e, 'user_facing_message', "An error occurred while processing your order. Please try again."), "danger")

        # Redirect back to checkout page; cart is still in session, user can retry.
        return redirect(url_for('cart.checkout_page_route')) 
    except Exception as e: # Catch any other unexpected exceptions
        logger.critical(f"Unexpected critical error during order placement for {user_context_for_log}: {e}", exc_info=True)
        flash("An unexpected critical error occurred while processing your order. Our team has been notified. Please try again later or contact support.", "danger")
        
        return redirect(url_for('cart.checkout_page_route'))