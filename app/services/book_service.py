# app/services/book_service.py

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Setup logger
logger = logging.getLogger(__name__)

# Establish a connection to the PostgreSQL database
def get_db_connection():
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

# Get all books from the database
def get_all_books():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM books ORDER BY title;")
        books = cur.fetchall()
        conn.close()
        return books
    except Exception as e:
        logger.error(f"Failed to fetch books: {e}")
        return []
