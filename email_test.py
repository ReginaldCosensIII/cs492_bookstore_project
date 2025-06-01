# test_email.py
import smtplib

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SENDER_EMAIL = 'AtomicsBookNook@gmail.com'
SENDER_PASSWORD = 'tqds ficd ijio uqjh' # Use the same one as in .env
RECEIVER_EMAIL = 'ReginaldCosensIII@gmail.com'

message = f"""\
Subject: SMTP Test

This is a test email sent from Python smtplib via Gmail."""

try:
    print(f"Attempting to connect to {SMTP_SERVER} on port {SMTP_PORT}...")
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.set_debuglevel(1) # See detailed SMTP conversation
    print("Connection successful. Starting TLS...")
    server.starttls() # Secure the connection
    print("TLS started. Logging in...")
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    print("Login successful. Sending email...")
    server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, message)
    print("Email sent successfully!")
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'server' in locals() and server:
        server.quit()
        print("Connection closed.")