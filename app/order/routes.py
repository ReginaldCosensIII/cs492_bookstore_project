# app/order/routes.py

from . import order_bp                                                             # Import the blueprint instance
from typing import Optional                                                        # For type hinting
from app.logger import get_logger                                                  # Custom application logger
from flask_login import login_required, current_user                               # current_user for authenticated checks
from app.services.order_service import get_order_details                           # Service to fetch the order Details
from flask import render_template, redirect, url_for, flash, session, current_app
from app.services.exceptions import NotFoundError, AuthorizationError, DatabaseError

logger = get_logger(__name__) # Logger instance for this module

def _get_user_or_guest_context_for_log_order() -> str:
    """
    Helper function to generate a consistent string representation for logging 
    the current user context (authenticated user or guest) within the order blueprint.

    Returns:
        str: A string identifying the user, e.g., "user 123 (user@example.com)" or "guest user".
    """
    if current_user.is_authenticated:
        # Safely access attributes that might not exist on all user-like objects
        user_id_log = getattr(current_user, 'id', 'UNKNOWN_ID')
        user_email_log = getattr(current_user, 'email', 'UNKNOWN_EMAIL')

        return f"user {user_id_log} ({user_email_log})"
    
    return "guest user (session-based access for order confirmation)"


@order_bp.route('/confirmation/<int:order_id>')
# No @login_required decorator here, as guest users need to see their order confirmation.
# Access control for guests is handled by checking specific session variables.
def order_confirmation_route(order_id: int):
    """
    Displays an order confirmation page (`order_confirmation.html`) after a successful checkout.
    
    For authenticated users, it verifies they own the order.
    For guest users, it relies on temporary session flags (`just_placed_order_id` 
    and `guest_order_email`) that are set during the order placement process. 
    These session flags are cleared after successfully displaying the confirmation 
    to prevent unauthorized re-access.

    Args:
        order_id (int): The ID of the order for which to display confirmation.

    Returns:
        Response: Renders the order confirmation template with order details,
                  or redirects to the home page with an error/warning message if
                  the order is not found or access is not authorized.
    """
    user_context_log = _get_user_or_guest_context_for_log_order()
    logger.info(f"Route: Order confirmation page requested for order_id: {order_id} by {user_context_log}")
    
    order_to_display = None # Initialize to ensure it's defined
    
    try:
        if current_user.is_authenticated:
            # For logged-in users, fetch and authorize based on their user ID.
            logger.debug(f"Authenticated {user_context_log} viewing confirmation for order {order_id}")
            order_to_display = get_order_details(order_id=order_id, user_id_for_auth=current_user.id)

        else:
            # For guest users, check session flags.
            just_placed_order_id_in_session = session.get('just_placed_order_id')
            guest_order_email_in_session = session.get('guest_order_email')

            logger.debug(
                f"Guest viewing confirmation. URL order_id: {order_id}, "
                f"Session order_id: {just_placed_order_id_in_session}, Session email: {guest_order_email_in_session}"
            )

            if just_placed_order_id_in_session == order_id and guest_order_email_in_session:
                # Session flags match the requested order; attempt to fetch using guest email for auth.
                order_to_display = get_order_details(order_id=order_id, guest_email_for_auth=guest_order_email_in_session)
                
                # Critical: Clear session flags after successful retrieval for one-time access.
                session.pop('just_placed_order_id', None)
                session.pop('guest_order_email', None)
                session.modified = True
                logger.info(f"Guest order {order_id} confirmation successfully displayed and session flags cleared.")

            else:
                # Session flags are missing, don't match, or have expired.
                logger.warning(
                    f"Guest attempt to view order confirmation for {order_id} with invalid/missing session flags "
                    f"(Session order_id: {just_placed_order_id_in_session}, Session email: {guest_order_email_in_session})."
                )

                raise AuthorizationError(
                    "Order confirmation is not available for this session. "
                    "If you placed this order as a guest, please refer to your confirmation email for details."
                )
        
        if not order_to_display: # Should ideally be caught by NotFoundError from get_order_details
            logger.warning(f"Order {order_id} not found for confirmation display for {user_context_log}, even after auth checks.")

            raise NotFoundError(resource_name="Order confirmation", resource_id=order_id)
            
        return render_template('order_confirmation.html', order=order_to_display)

    except NotFoundError as nfe:
        logger.warning(f"Order confirmation: Order {order_id} not found for {user_context_log}. Error: {getattr(nfe, 'user_facing_message', str(nfe))}")
        flash(getattr(nfe, 'user_facing_message', "The requested order confirmation could not be found."), "danger")

        return redirect(url_for('main.home')) 
    
    except AuthorizationError as ae:
        logger.warning(f"Order confirmation: {user_context_log} not authorized for order {order_id}. Error: {getattr(ae, 'user_facing_message', str(ae))}")
        flash(getattr(ae, 'user_facing_message', "You are not authorized to view this order confirmation."), "danger")

        return redirect(url_for('main.home'))
    
    except DatabaseError as de:
        logger.error(f"Database error viewing order confirmation {order_id} for {user_context_log}: {de.log_message}", exc_info=True)
        flash(getattr(de, 'user_facing_message', "A database error occurred while retrieving the order confirmation."), "danger")

        return redirect(url_for('main.home'))
    
    except Exception as e:
        logger.error(f"Unexpected error displaying order confirmation for order {order_id} ({user_context_log}): {e}", exc_info=True)
        flash("An unexpected error occurred while trying to display your order confirmation. Please try again later.", "danger")

        return redirect(url_for('main.home'))
    


@order_bp.route('/details/<int:order_id>') 
@login_required # Viewing general order details (e.g., from history) requires login.
def view_order_details_route(order_id: int):
    """
    Displays the detailed information for a specific order (`order_details.html`).
    This route is accessible only to authenticated users and will verify that the
    order belongs to the currently logged-in user.

    Args:
        order_id (int): The ID of the order whose details are to be viewed.

    Returns:
        Response: Renders the order details template with the fetched order data,
                  or redirects to the user's profile page with an error message if
                  the order is not found or access is not authorized.
    """
    # current_user is guaranteed to be authenticated due to @login_required
    user_context_log = _get_user_or_guest_context_for_log_order() 
    logger.info(f"{user_context_log} requesting details for order_id: {order_id}")

    try:
        # Fetch order details, service function handles authorization against current_user.id
        order = get_order_details(order_id=order_id, user_id_for_auth=current_user.id)

        if not order: # Should be caught by NotFoundError from service, but defensive
             logger.warning(f"Order details: Order {order_id} evaluated to None after service call for {user_context_log}.")

             raise NotFoundError(resource_name="Order", resource_id=order_id)
        
        return render_template('order_details.html', order=order)
    
    except NotFoundError as nfe:
        logger.warning(f"Order details: Order {order_id} not found for {user_context_log}. Error: {getattr(nfe, 'user_facing_message', str(nfe))}")
        flash(getattr(nfe, 'user_facing_message', "The requested order could not be found."), "danger")

        return redirect(url_for('main.profile_page')) # Redirect to profile or order history list
    
    except AuthorizationError as ae:
        logger.warning(f"{user_context_log} unauthorized to view order details for {order_id}. Error: {getattr(ae, 'user_facing_message', str(ae))}")
        flash(getattr(ae, 'user_facing_message', "You are not authorized to view this order's details."), "danger")

        return redirect(url_for('main.profile_page'))
    
    except DatabaseError as de:
        logger.error(f"Database error viewing order details {order_id} for {user_context_for_log}: {de.log_message}", exc_info=True)
        flash(getattr(de, 'user_facing_message', "Could not load order details due to a database issue."), "danger")

        return redirect(url_for('main.profile_page'))
    
    except Exception as e:
        logger.error(f"Unexpected error viewing order details for order {order_id} for {user_context_for_log}: {e}", exc_info=True)
        flash("An unexpected error occurred while retrieving your order details. Please try again later.", "danger")
        
        return redirect(url_for('main.profile_page'))