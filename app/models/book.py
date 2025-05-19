# app/models/book.py

import psycopg2
from psycopg2.extras import RealDictCursor
from app.db_setup import get_db_connection
import logging

logger = logging.getLogger(__name__)

class Book:
    def __init__(self, title, author, genre, price, stock_quantity, image_url=None, description=None, book_id=None):
        self.book_id = book_id
        self.title = title
        self.author = author
        self.genre = genre
        self.price = price
        self.stock_quantity = stock_quantity
        self.image_url = image_url or 'https://cdn.pixabay.com/photo/2014/04/02/14/06/book-306178_1280.png'
        self.description = description or "No description available."

    def to_dict(self):
        """Return a dictionary representation for rendering in templates or JSON."""
        return {
            'id': self.book_id,
            'title': self.title,
            'author': self.author,
            'genre': self.genre,
            'price': self.price,
            'stock_quantity': self.stock_quantity,
            'image_url': self.image_url,
            'description': self.description
        }

    def save(self):
        query = """
            INSERT INTO books (title, author, genre, price, stock_quantity, image_url, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING book_id;
        """
        values = (self.title, self.author, self.genre, self.price, self.stock_quantity, self.image_url, self.description)
        conn = None
        try:
            conn = get_db_connection()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query, values)
                    self.book_id = cur.fetchone()[0]
                    logger.info(f"Book added with ID {self.book_id}")
        except Exception as e:
            logger.error(f"Error saving book: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def update(self):
        query = """
            UPDATE books
            SET title = %s, author = %s, genre = %s, price = %s, stock_quantity = %s, image_url = %s, description = %s
            WHERE book_id = %s;
        """
        values = (self.title, self.author, self.genre, self.price,
                  self.stock_quantity, self.image_url, self.description, self.book_id)
        conn = None
        try:
            conn = get_db_connection()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query, values)
                    logger.info(f"Book with ID {self.book_id} updated.")
        except Exception as e:
            logger.error(f"Error updating book: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @staticmethod
    def delete(book_id):
        query = "DELETE FROM books WHERE book_id = %s;"
        conn = None
        try:
            conn = get_db_connection()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query, (book_id,))
                    logger.info(f"Book with ID {book_id} deleted.")
        except Exception as e:
            logger.error(f"Error deleting book ID {book_id}: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_by_id(book_id):
        query = "SELECT * FROM books WHERE book_id = %s;"
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (book_id,))
                result = cur.fetchone()
                if result:
                    return Book(**result)
                return None
        except Exception as e:
            logger.error(f"Error retrieving book by ID {book_id}: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_all():
        query = "SELECT * FROM books ORDER BY title ASC;"
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query)
                results = cur.fetchall()
                return [Book(**row).to_dict() for row in results]
        except Exception as e:
            logger.error(f"Error fetching all books: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def decrease_stock(self, quantity):
        if quantity > self.stock_quantity:
            raise ValueError("Insufficient stock.")
        self.stock_quantity -= quantity
        self.update()
