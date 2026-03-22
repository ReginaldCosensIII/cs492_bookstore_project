# bookstore_project/app/services/email_service.py

from flask import current_app, render_template
from flask_mail import Message
from threading import Thread
from app import mail
from app.logger import get_logger
from app.services.exceptions import AppException

logger = get_logger(__name__)

def _send_async_email(app, msg):
    """
    Helper function to send email asynchronously within an application context.
    """
    with app.app_context():
        try:
            mail.send(msg)
            logger.info(f"Async email successfully sent to {msg.recipients}")
        except Exception as e:
            logger.error(f"Failed to send async email: {e}", exc_info=True)

def send_email(to_email: str, subject: str, template_path: str, **context_for_template) -> bool:
    """
    Sends an email asynchronously by rendering an HTML template with the given context.
    
    Args:
        to_email (str): The recipient's email address.
        subject (str): The subject of the email.
        template_path (str): The path to the Jinja2 HTML template file.
        **context_for_template: Keyword arguments to pass as context to the template.

    Returns:
        bool: True (as the sending is asynchronous, we assume success of queuing).
    """
    mail_default_sender = current_app.config.get('MAIL_DEFAULT_SENDER')

    try:
        html_body_rendered = render_template(template_path, **context_for_template)
    except Exception as template_error:
        logger.error(f"Error rendering email template '{template_path}': {template_error}", exc_info=True)
        raise AppException(
            message="Could not generate email content due to a template error.",
            log_message=f"Email template rendering error for '{template_path}': {template_error}",
            original_exception=template_error
        )

    msg = Message(subject=subject, 
                  sender=mail_default_sender, 
                  recipients=[to_email])
    msg.html = html_body_rendered

    # Start the async thread
    app_instance = current_app._get_current_object()
    Thread(target=_send_async_email, args=(app_instance, msg)).start()
    
    logger.info(f"Queued async HTML email to '{to_email}' with subject '{subject}'.")
    return True

def send_simple_email(to_email: str, subject: str, body_text: str) -> bool:
    """
    Sends a plain text email asynchronously.

    Args:
        to_email (str): The recipient's email address.
        subject (str): The subject of the email.
        body_text (str): The plain text content for the email body.

    Returns:
        bool: True (as the sending is asynchronous, we assume success of queuing).
    """
    if not current_app:
        logger.error("send_simple_email called outside of active Flask application context.")
        return False

    if current_app.config.get('MAIL_SUPPRESS_SEND', False):
        logger.info(f"Email sending suppressed (MAIL_SUPPRESS_SEND=True).")
        return True

    mail_default_sender = current_app.config.get('MAIL_DEFAULT_SENDER')

    msg = Message(subject=subject, 
                  sender=mail_default_sender, 
                  recipients=[to_email])
    msg.body = body_text

    app_instance = current_app._get_current_object()
    Thread(target=_send_async_email, args=(app_instance, msg)).start()

    logger.info(f"Queued async text email to '{to_email}' with subject '{subject}'.")
    return True