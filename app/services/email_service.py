# bookstore_project/app/services/email_service.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app, render_template # MODIFIED: Added render_template
from app.logger import get_logger
from app.services.exceptions import AppException

logger = get_logger(__name__)

# MODIFIED: Function signature and body
def send_email(to_email: str, subject: str, template_path: str, **context_for_template) -> bool:
    """
    Sends an email by rendering an HTML template with the given context.
    Uses SMTP configuration from the Flask app config.

    Args:
        to_email (str): The recipient's email address.
        subject (str): The subject of the email.
        template_path (str): The path to the Jinja2 HTML template file
                             (e.g., 'email/order_confirmation_email.html').
        **context_for_template: Keyword arguments to pass as context to the template.

    Returns:
        bool: True if the email was sent successfully.

    Raises:
        AppException: If email configuration is missing, template rendering fails,
                      or if sending fails critically.
    """
    mail_server = current_app.config.get('MAIL_SERVER')
    mail_port = current_app.config.get('MAIL_PORT')
    mail_use_tls = current_app.config.get('MAIL_USE_TLS')
    mail_username = current_app.config.get('MAIL_USERNAME')
    mail_password = current_app.config.get('MAIL_PASSWORD')
    mail_default_sender = current_app.config.get('MAIL_DEFAULT_SENDER', mail_username)

    if not all([mail_server, mail_port, mail_username, mail_password, mail_default_sender]):
        logger.error(
            "Email configuration incomplete. MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, "
            "MAIL_PASSWORD, and MAIL_DEFAULT_SENDER must be set."
        )
        raise AppException(
            message="Email service is not configured correctly. Please contact support.",
            log_message="Email configuration is missing or incomplete in app settings."
        )

    msg = MIMEMultipart('alternative')
    msg['From'] = mail_default_sender
    msg['To'] = to_email
    msg['Subject'] = subject

    try:
        # MODIFIED: Render the HTML body from a template
        html_body_rendered = render_template(template_path, **context_for_template)
        msg.attach(MIMEText(html_body_rendered, 'html'))
        logger.debug(f"Successfully rendered email template: {template_path} for {to_email}")
    except Exception as template_error:
        logger.error(f"Error rendering email template '{template_path}': {template_error}", exc_info=True)
        raise AppException(
            message="Could not generate email content due to a template error.",
            log_message=f"Email template rendering error for '{template_path}': {template_error}",
            original_exception=template_error
        )

    try:
        logger.info(f"Attempting to send email to '{to_email}' with subject '{subject}' from '{mail_default_sender}'.")
        with smtplib.SMTP(mail_server, mail_port) as server:
            if mail_use_tls:
                server.starttls()
            server.login(mail_username, mail_password)
            server.sendmail(mail_default_sender, to_email, msg.as_string())
        logger.info(f"Email successfully sent to '{to_email}'.")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication Error sending email to '{to_email}': {e}", exc_info=True)
        raise AppException(
            message="Could not send email due to authentication failure with the email server.",
            log_message=f"SMTP Authentication Error for user {mail_username}: {e}",
            original_exception=e
        )
    except smtplib.SMTPException as e:
        logger.error(f"SMTP Error sending email to '{to_email}': {e}", exc_info=True)
        raise AppException(
            message="Could not send email due to an SMTP issue. Please try again later.",
            log_message=f"SMTP Error: {e}",
            original_exception=e
        )
    except Exception as e:
        logger.error(f"Unexpected error sending email to '{to_email}': {e}", exc_info=True)
        raise AppException(
            message="An unexpected error occurred while trying to send the email.",
            log_message=f"Unexpected email sending error: {e}",
            original_exception=e
        )
    
def send_simple_email(to_email: str, subject: str, body_text: str) -> bool:
    """
    Sends a plain text email using SMTP configuration from the Flask app config.

    Args:
        to_email (str): The recipient's email address.
        subject (str): The subject of the email.
        body_text (str): The plain text content for the email body.

    Returns:
        bool: True if the email was sent successfully or suppressed, False on failure.

    Raises:
        AppException: If email configuration is missing or if sending fails critically.
                      (Currently logs errors and returns False for sending failures).
    """
    if not current_app:
        logger.error("send_simple_email called outside of active Flask application context.")
        return False

    mail_server = current_app.config.get('MAIL_SERVER')
    mail_port = current_app.config.get('MAIL_PORT')
    mail_use_tls = current_app.config.get('MAIL_USE_TLS')
    mail_username = current_app.config.get('MAIL_USERNAME')
    mail_password = current_app.config.get('MAIL_PASSWORD')
    mail_default_sender = current_app.config.get('MAIL_DEFAULT_SENDER', mail_username)

    if not all([mail_server, mail_port, mail_username, mail_password, mail_default_sender]):
        logger.error(
            "Email configuration incomplete. Required MAIL_* settings are missing."
        )
        # Depending on strictness, you might raise AppException here or just return False
        # For now, let's make it explicit for the caller to handle
        # raise AppException("Email service not configured.", log_message="Email config missing.")
        return False # Indicate failure due to config

    if current_app.config.get('MAIL_SUPPRESS_SEND', False):
        logger.info(f"Email sending suppressed (MAIL_SUPPRESS_SEND=True).")
        logger.info(f"--- Would send to: {to_email} ---")
        logger.info(f"--- Subject: {subject} ---")
        logger.info(f"--- Body ---\n{body_text}\n--- End Body ---")
        return True # Report as success if suppressed

    # Create a plain text message
    msg = MIMEText(body_text, 'plain', 'utf-8') # Specify plain text and encoding
    msg['From'] = mail_default_sender
    msg['To'] = to_email
    msg['Subject'] = subject

    try:
        logger.info(f"Attempting to send email to '{to_email}' with subject '{subject}' from '{mail_default_sender}'.")
        # Ensure port is integer
        port = int(mail_port) if isinstance(mail_port, (str, int)) else 587 
        
        with smtplib.SMTP(mail_server, port) as server:
            if mail_use_tls:
                server.starttls()
            server.login(mail_username, mail_password)
            server.sendmail(mail_default_sender, to_email, msg.as_string())
        logger.info(f"Email successfully sent to '{to_email}'.")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication Error sending email to '{to_email}': {e}", exc_info=True)
        # For now, just log and return False. Caller can flash messages.
        return False
    except smtplib.SMTPException as e: # Covers other SMTP related errors (e.g., connection, send failures)
        logger.error(f"SMTP Error sending email to '{to_email}': {e}", exc_info=True)
        return False
    except ConnectionRefusedError as e: # Specific catch for connection refusal
        logger.error(f"ConnectionRefusedError sending email to '{to_email}': {e}", exc_info=True)
        return False
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"Unexpected error sending email to '{to_email}': {e}", exc_info=True)
        return False