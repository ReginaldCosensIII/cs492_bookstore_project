# cs492_bookstore_project/app/admin/routes.py
from flask import render_template, current_app, request, redirect, url_for, flash
from flask_login import login_required, current_user
from typing import Dict, Any, List # For type hinting
from decimal import Decimal, InvalidOperation # For converting price

from . import admin_bp 
from app.logger import get_logger 
from app.services.exceptions import AuthorizationError, NotFoundError, DatabaseError, ValidationError
# Import Book service and potentially the Book model for form handling
from app.services import book_service # To call functions like book_service.get_all_books()
from app.models.book import Book # For type hinting and potentially creating form objects
from app.utils import sanitize_form_data, normalize_whitespace # For form data

logger = get_logger(__name__) 

def _ensure_admin_privileges():
    """
    Helper function to check if the currently authenticated user has admin privileges.
    Raises AuthorizationError if the user is not an admin.
    """
    if not (hasattr(current_user, 'is_admin') and callable(current_user.is_admin) and current_user.is_admin()):
        user_email = getattr(current_user, 'email', 'Anonymous/Unauthenticated')
        user_role = getattr(current_user, 'role', 'N/A') 
        user_id = getattr(current_user, 'id', 'N/A')
        logger.warning(
            f"Unauthorized access attempt to admin area by user '{user_email}' "
            f"(ID: {user_id}, Role: '{user_role}'). Admin privileges required."
        )
        raise AuthorizationError("You do not have sufficient permissions to access this admin area.")

@admin_bp.route('/', endpoint='dashboard')
@login_required 
def admin_dashboard_page(): 
    """
    Renders the main dashboard page for administrators.
    Serves as the entry point to various admin functionalities.

    Returns:
        Response: Renders the `admin/dashboard.html` template.
    
    Raises:
        AuthorizationError: If the logged-in user is not an admin.
    """
    _ensure_admin_privileges() 
    admin_name = getattr(current_user, 'first_name', 'Admin').title()
    user_email_log = getattr(current_user, 'email', 'N/A')
    user_id_log = getattr(current_user, 'id', 'N/A')
    logger.info(f"Admin dashboard accessed by administrator: {user_email_log} (ID: {user_id_log})")
    
    dashboard_data = {"greeting": f"Welcome to the Admin Dashboard, {admin_name}!"}
    return render_template('admin/dashboard.html', **dashboard_data) 

# --- Admin Book Management Routes ---

@admin_bp.route('/books', methods=['GET'], endpoint='list_books')
@login_required
def list_books_route():
    """
    Displays a list of all books for administrators.
    Allows admins to view current inventory and access actions like add, edit, delete.

    Returns:
        Response: Renders the `admin/admin_books_list.html` template with all books.
    """
    _ensure_admin_privileges()
    logger.info(f"Admin {getattr(current_user, 'email', 'N/A')} requesting to view all books.")

    try:
        all_books = book_service.get_all_books() # Fetches List[Book]
    except DatabaseError as e:
        logger.error(f"Database error fetching all books for admin view: {e.log_message}", exc_info=True)
        flash("Could not retrieve book list due to a database error.", "danger")

        all_books = []
        
    return render_template('admin/admin_books_list.html', books=all_books)

@admin_bp.route('/books/add', methods=['GET', 'POST'], endpoint='add_book')
@login_required
def add_book_route():
    """
    Handles the creation of new books by an administrator.
    GET: Displays the form to add a new book.
    POST: Processes the submitted form data, validates it, and calls the
          book service to add the new book to the database.

    Returns:
        Response: Renders `admin/admin_book_form.html` or redirects on success/failure.
    """
    _ensure_admin_privileges()
    form_data_for_template = {} # For re-populating form on error

    if request.method == 'POST':
        try:
            form_data_raw = request.form.to_dict()
            logger.info(f"Admin {getattr(current_user, 'email', 'N/A')} attempting to add new book. Raw data: {form_data_raw}")

            # Sanitize form data - specify fields that might contain user HTML
            # For book details, description is the most likely. Title, author, genre are usually plain text.
            fields_to_html_escape = {'description'}
            # Price and stock_quantity will be converted to Decimal/int, no HTML escaping needed.
            # Title, author, genre will be stripped.
            book_payload = sanitize_form_data(form_data_raw, escape_html_fields=fields_to_html_escape)
            
            # Convert price and stock to correct types before passing to service
            # Service or Model should also handle this, but good to do it here for early validation.
            try:
                book_payload['price'] = Decimal(str(book_payload.get('price', '0')))
                book_payload['stock_quantity'] = int(book_payload.get('stock_quantity', '0'))
            except (InvalidOperation, ValueError) as e:
                logger.warning(f"Invalid price or stock quantity format during add book: {e}")
                raise ValidationError("Price and Stock Quantity must be valid numbers.", 
                                      errors={'price_stock': "Invalid number format for price or stock."})

            # Minimal validation (service layer should do more comprehensive validation)
            if not book_payload.get('title') or not book_payload.get('author'):
                raise ValidationError("Title and Author are required fields.", 
                                      errors={'title_author': "Title and Author cannot be empty."})

            # Call the service to add the book
            # Assumes book_service.add_book exists and takes a dictionary
            new_book = book_service.admin_add_book(book_payload) # This function needs to be created/confirmed in book_service.py
            
            flash(f"Book '{new_book.title.title()}' added successfully!", "success")
            logger.info(f"Admin successfully added book ID {new_book.book_id} ('{new_book.title}').")
            return redirect(url_for('admin.list_books'))
        
        except ValidationError as ve:
            logger.warning(f"Validation error adding book: {ve.user_facing_message} - Errors: {ve.errors}")
            flash(ve.user_facing_message, "danger")
            if ve.errors: # If field-specific errors exist
                for field, msg_list in ve.errors.items():
                    if isinstance(msg_list, list):
                        for msg in msg_list: flash(f"{field.replace('_',' ').title()}: {msg}", "warning")
                    else:
                         flash(f"{field.replace('_',' ').title()}: {str(msg_list)}", "warning")
            form_data_for_template = book_payload # Repopulate with sanitized data
        except (DatabaseError, Exception) as e:
            logger.error(f"Error adding new book: {getattr(e, 'log_message', str(e))}", exc_info=True)
            flash(getattr(e, 'user_facing_message', "Could not add book due to a server error."), "danger")
            form_data_for_template = book_payload
        
        return render_template('admin/admin_book_form.html', form_title="Add New Book", book=form_data_for_template, action_url=url_for('admin.add_book'))

    # For GET request
    logger.debug(f"Admin {getattr(current_user, 'email', 'N/A')} accessing add book form.")
    return render_template('admin/admin_book_form.html', form_title="Add New Book", book={}, action_url=url_for('admin.add_book'))


@admin_bp.route('/books/edit/<int:book_id>', methods=['GET', 'POST'], endpoint='edit_book')
@login_required
def edit_book_route(book_id: int):
    """
    Handles editing of an existing book by an administrator.
    GET: Displays the form pre-filled with the book's current details.
    POST: Processes the submitted form data, validates it, and calls the
          book service to update the book in the database.

    Args:
        book_id (int): The ID of the book to be edited.

    Returns:
        Response: Renders `admin/admin_book_form.html` or redirects on success/failure.
    """
    _ensure_admin_privileges()
    admin_email = getattr(current_user, 'email', 'N/A')
    
    try:
        book_to_edit = book_service.get_book_by_id(book_id) # Fetches Book object or raises NotFoundError
    except NotFoundError:
        logger.warning(f"Admin {admin_email} attempted to edit non-existent book ID {book_id}.")
        flash(f"Book with ID {book_id} not found.", "danger")
        return redirect(url_for('admin.list_books'))
    except DatabaseError as e:
        logger.error(f"DB error fetching book ID {book_id} for edit: {e.log_message}", exc_info=True)
        flash("Error retrieving book details. Please try again.", "danger")
        return redirect(url_for('admin.list_books'))

    if request.method == 'POST':
        form_data_for_template = {} # For re-populating form on error
        try:
            form_data_raw = request.form.to_dict()
            logger.info(f"Admin {admin_email} attempting to update book ID {book_id}. Raw data: {form_data_raw}")

            fields_to_html_escape = {'description'}
            book_payload = sanitize_form_data(form_data_raw, escape_html_fields=fields_to_html_escape)
            
            try:
                book_payload['price'] = Decimal(str(book_payload.get('price', '0')))
                book_payload['stock_quantity'] = int(book_payload.get('stock_quantity', '0'))
            except (InvalidOperation, ValueError) as e:
                raise ValidationError("Price and Stock Quantity must be valid numbers.", 
                                      errors={'price_stock': "Invalid number format."})

            if not book_payload.get('title') or not book_payload.get('author'):
                raise ValidationError("Title and Author are required fields.", 
                                      errors={'title_author': "Title and Author cannot be empty."})

            # Call service to update the book
            # Assumes book_service.update_book exists
            updated_book = book_service.admin_update_book(book_id, book_payload)
            
            flash(f"Book '{updated_book.title.title()}' updated successfully!", "success")
            logger.info(f"Admin successfully updated book ID {book_id} ('{updated_book.title}').")
            return redirect(url_for('admin.list_books'))

        except ValidationError as ve:
            logger.warning(f"Validation error updating book ID {book_id}: {ve.user_facing_message} - Errors: {ve.errors}")
            flash(ve.user_facing_message, "danger")
            if ve.errors:
                for field, msg_list in ve.errors.items():
                    if isinstance(msg_list, list):
                        for msg in msg_list: flash(f"{field.replace('_',' ').title()}: {msg}", "warning")
                    else:
                        flash(f"{field.replace('_',' ').title()}: {str(msg_list)}", "warning")
            form_data_for_template = book_payload
        except (DatabaseError, NotFoundError, Exception) as e: # NotFoundError if book deleted during edit
            logger.error(f"Error updating book ID {book_id}: {getattr(e, 'log_message', str(e))}", exc_info=True)
            flash(getattr(e, 'user_facing_message', "Could not update book due to a server error."), "danger")
            form_data_for_template = book_payload # Repopulate with attempted changes

        # On POST error, re-render form with submitted data and errors
        # Pass the original book_to_edit for ID in action_url, but form_data for values
        current_data_for_form = {**book_to_edit.to_dict(), **form_data_for_template}
        return render_template('admin/admin_book_form.html', form_title=f"Edit Book: {book_to_edit.title.title()}", 
                               book=current_data_for_form, 
                               action_url=url_for('admin.edit_book', book_id=book_id))
    
    # For GET request, populate form with existing book data
    logger.debug(f"Admin {admin_email} accessing edit form for book ID {book_id}.")
    return render_template('admin/admin_book_form.html', form_title=f"Edit Book: {book_to_edit.title.title()}", 
                           book=book_to_edit.to_dict(), # Pass book data as dict
                           action_url=url_for('admin.edit_book', book_id=book_id))


@admin_bp.route('/books/delete/<int:book_id>', methods=['POST'], endpoint='delete_book')
@login_required
def delete_book_route(book_id: int):
    """
    Handles the deletion of a book by an administrator.
    This action is typically triggered by a POST request (e.g., from a form's delete button)
    to prevent accidental deletion via GET requests.

    Args:
        book_id (int): The ID of the book to be deleted.

    Returns:
        Response: Redirects to the admin books list page with a success or error message.
    """
    _ensure_admin_privileges()
    admin_email = getattr(current_user, 'email', 'N/A')
    logger.info(f"Admin {admin_email} attempting to delete book ID {book_id}.")
    try:
        # Call service to delete the book
        # Assumes book_service.delete_book(book_id) returns True on success or raises error
        # Or, it might return the title of the deleted book for the flash message.
        # Let's assume it might raise NotFoundError if book doesn't exist.
        book_service.admin_delete_book(book_id) # This function needs to be confirmed/created in book_service.py
        
        flash(f"Book ID {book_id} deleted successfully.", "success")
        logger.info(f"Admin successfully deleted book ID {book_id}.")
    except NotFoundError:
        logger.warning(f"Admin {admin_email} failed to delete book ID {book_id}: Not found.")
        flash(f"Book with ID {book_id} not found or already deleted.", "warning")
    except DatabaseError as de:
        logger.error(f"Database error deleting book ID {book_id}: {de.log_message}", exc_info=True)
        flash("Could not delete book due to a database error.", "danger")
    except Exception as e:
        logger.error(f"Unexpected error deleting book ID {book_id}: {e}", exc_info=True)
        flash("An unexpected error occurred while trying to delete the book.", "danger")
        
    return redirect(url_for('admin.list_books'))