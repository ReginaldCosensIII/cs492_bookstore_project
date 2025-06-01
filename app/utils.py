# cs492_bookstore_project/app/utils.py

import re
from flask import current_app # For accessing app.logger and mail instance
from flask_mail import Message # For creating email messages
from app.logger import get_logger # Your custom logger
from markupsafe import escape as markupsafe_escape 

logger = get_logger(__name__) # Logger for this module

DEFAULT_LOWERCASE_FIELDS = {'email', 'username'}

def sanitize_html_text(text_input):
    """
    Sanitizes a single string input by stripping whitespace and then escaping HTML characters.
    """
    if not isinstance(text_input, str):
        return text_input
    return markupsafe_escape(text_input.strip())


def sanitize_form_field_value(value, key_name=None, lowercase_fields_set=None, should_escape_html=True): # CHANGED HERE
    """
    Sanitizes a single form field value.
    - Strips whitespace if it's a string.
    - Converts to lowercase if it's a string and key_name is in lowercase_fields_set.
    - HTML-escapes the string if should_escape_html is True.
    """
    if lowercase_fields_set is None:
        lowercase_fields_set = DEFAULT_LOWERCASE_FIELDS

    if isinstance(value, str):
        processed_value = value.strip()
        if key_name and key_name in lowercase_fields_set:
            processed_value = processed_value.lower()
        
        if should_escape_html: # CHANGED HERE
            processed_value = markupsafe_escape(processed_value)
        return processed_value
    return value


def sanitize_form_data(form_data_dict, lowercase_fields_set=None, escape_html_fields=None):
    """
    Sanitizes string values within a dictionary (typically from flat form data).
    """
    if not isinstance(form_data_dict, dict):
        return form_data_dict 

    if lowercase_fields_set is None:
        lowercase_fields_set = DEFAULT_LOWERCASE_FIELDS
    if escape_html_fields is None:
        escape_html_fields = set() 
    
    sanitized_data = {}
    for key, value in form_data_dict.items():
        should_escape = key in escape_html_fields
        sanitized_data[key] = sanitize_form_field_value(
            value, 
            key_name=key, 
            lowercase_fields_set=lowercase_fields_set, 
            should_escape_html=should_escape # This call is now correct
        )
    return sanitized_data

def normalize_whitespace(text):
    """
    Normalizes all whitespace in a string.
    """
    if not isinstance(text, str):
        return text
    normalized_text = re.sub(r'\s+', ' ', text)
    return normalized_text.strip()

# *** NEW EMAIL SENDING FUNCTION ***
def send_email(to_recipient: str, subject: str, template_name_or_html_body: str, **kwargs):
    """
    Sends an email using Flask-Mail.

    It can either render an HTML template or use a pre-rendered HTML string as the body.
    Configuration for Flask-Mail (sender, server, etc.) is expected to be set in the
    Flask app configuration.

    Args:
        to_recipient (str): The primary recipient's email address.
        subject (str): The subject line of the email.
        template_name_or_html_body (str): The name of the Jinja2 template to render for the email body
                                          (e.g., 'email/order_confirmation_email.html') OR
                                          a string containing the fully rendered HTML body.
        **kwargs: Keyword arguments to pass to `render_template` if `template_name_or_html_body`
                  is a template name. These become the context for rendering the email template.

    Returns:
        bool: True if the email was sent (or suppressed successfully), False on failure.

    Raises:
        RuntimeError: If called outside of an active Flask application context.
    """
    i = 0
    print(i)
    # Ensure we have access to the Flask app context for config and mail instance
    if not current_app:
        i = 1
        print(i)
        logger.error("send_email called outside of active Flask application context.")
        # In a real scenario, you might re-raise or handle differently depending on how this util is used.
        # For now, just log and return False if not in app context.
        return False

    # Get the mail instance from the current app's extensions
    # This is a more robust way to get it within a function that might be called from various places.
    mail_instance = current_app.extensions.get('mail')

    if not mail_instance:
        i = 2
        print(i)
        logger.error("Flask-Mail instance not found in current_app.extensions. Ensure it's initialized.")
        return False
    
    i = 3
    print(i)
    # Determine if template_name_or_html_body is a template path or an HTML string
    # A simple check: if it ends with .html (or .htm, .txt for text emails), assume it's a template.
    is_template_path = template_name_or_html_body.lower().endswith(('.html', '.htm', '.txt'))

    try:
        # Create the email message object
        # MAIL_DEFAULT_SENDER should be configured in app.config
        # If it's just an email like 'me@example.com', Flask-Mail uses it directly.
        # If it's "Sender Name <me@example.com>", Flask-Mail parses it.
        msg = Message(
            subject=subject,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'no-reply@booknook.example.com'),
            recipients=[to_recipient] # Must be a list
        )
        
        i = 4
        print(i)

        if is_template_path:
            i = 5
            print(i)
            from flask import render_template # Local import to avoid issues if utils is imported early
            logger.debug(f"Rendering email template: '{template_name_or_html_body}' with context: {kwargs}")
            msg.html = render_template(template_name_or_html_body, **kwargs)
            # You can also set msg.body for a plain text version:
            # msg.body = render_template(template_name_or_html_body.replace('.html', '.txt'), **kwargs) # If you have a .txt version
        else:
            i = 6
            print(i)
            # Assume template_name_or_html_body is the pre-rendered HTML string
            msg.html = template_name_or_html_body
            # msg.body could be a stripped version or a plain text alternative passed via kwargs

        if current_app.config.get('MAIL_SUPPRESS_SEND', False):
            i = 7
            print(i)
            logger.info(f"Email sending suppressed (MAIL_SUPPRESS_SEND=True). Email to '{to_recipient}' with subject '{subject}' would have been sent.")
            # For debugging, you could print the email content here if not using MAIL_BACKEND='console'
            print("--- EMAIL TO BE SENT (SUPPRESSED) ---")
            print(f"To: {to_recipient}")
            print(f"From: {msg.sender}")
            print(f"Subject: {subject}")
            print("--- HTML Body ---")
            print(msg.html)
            print("-----------------------------------")
            return True # Report as success if suppressed as per config       

        i = 8
        print(i)
        mail_instance.send(msg)
        logger.info(f"Email successfully sent to '{to_recipient}' with subject: '{subject}'")
        return True

    except Exception as e:
        i = 9
        print(i)
        logger.error(f"Failed to send email to '{to_recipient}' with subject '{subject}'. Error: {e}", exc_info=True)
        # In a real app, you might want to queue this email for retry or notify admins.
        return False
# *** END OF NEW EMAIL SENDING FUNCTION ***