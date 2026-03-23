"""
ultimate_seed.py
The definitive seed script for the Atomic BookNook database.

Strategy:
  1. Deduplicate: Remove clutter by deleting books with duplicate titles,
     keeping only the row with the lowest book_id (preserving order history).
  2. One API Call: Fetch up to 150 fiction books from the Open Library
     Search API in a single HTTP request.
  3. Guaranteed Covers: Use the cover_i integer ID for image URLs, which
     guarantees a real cover (vs. the ISBN method which can 404).
  4. Overwrite & Append: UPDATE surviving rows with fresh data, INSERT
     the remainder until the catalog reaches ~120 unique books.

NO DELETE of full table. NO TRUNCATE. Foreign keys preserved.
No SQLAlchemy. Raw psycopg2 only.
"""

import json
import random
import urllib.request
import urllib.parse
from decimal import Decimal, ROUND_DOWN
from psycopg2.extras import execute_batch
from app import create_app
from app.models.db import get_db_connection
from app.logger import get_logger

logger = get_logger(__name__)

TARGET_TOTAL_BOOKS = 120
API_FETCH_LIMIT = 150
OPEN_LIBRARY_SEARCH_URL = (
    "https://openlibrary.org/search.json?"
    + urllib.parse.urlencode({
        "subject": "fiction",
        "limit": API_FETCH_LIMIT,
        "has_fulltext": "true",
        "fields": "title,author_name,cover_i,first_sentence,subject",
    })
)


def fetch_books_from_open_library():
    """Single GET request to Open Library Search API."""
    headers = {"User-Agent": "AtomicBookNook/1.0 (cs492 class project; contact: student@example.com)"}
    req = urllib.request.Request(OPEN_LIBRARY_SEARCH_URL, headers=headers)

    print(f"Fetching up to {API_FETCH_LIMIT} books from Open Library Search API...")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            raw_docs = data.get("docs", [])
    except Exception as e:
        raise RuntimeError(f"Failed to fetch from Open Library API: {e}") from e

    books = []
    for doc in raw_docs:
        title = doc.get("title", "").strip()
        authors = doc.get("author_name", [])
        cover_i = doc.get("cover_i")

        # Only include books that have all three required fields
        if not title or not authors or not cover_i:
            continue

        author = authors[0].strip()

        # Build description from first sentence if available, otherwise generic
        first_sentence = doc.get("first_sentence", [])
        if isinstance(first_sentence, list) and first_sentence:
            description = str(first_sentence[0])[:400]
        elif isinstance(first_sentence, str):
            description = first_sentence[:400]
        else:
            description = f"A compelling work of fiction by {author}."

        # Derive genre from subjects if available
        subjects = doc.get("subject", [])
        genre = "Fiction"
        genre_keywords = {
            "Science Fiction": ["science fiction", "sci-fi", "space", "robot"],
            "Mystery": ["mystery", "detective", "crime", "thriller"],
            "Romance": ["romance", "love story"],
            "Fantasy": ["fantasy", "magic", "wizard", "dragon"],
            "History": ["historical", "history"],
        }
        for genre_name, keywords in genre_keywords.items():
            if any(kw in s.lower() for s in subjects for kw in keywords):
                genre = genre_name
                break

        price = Decimal(str(round(random.uniform(10.0, 40.0), 2))).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )

        books.append({
            "title": title,
            "author": author,
            "genre": genre,
            "price": price,
            "stock_quantity": 50,
            "description": description,
            "image_url": f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg",
        })

    print(f"Parsed {len(books)} valid books (with title, author, and cover).")
    return books


def ultimate_seed():
    random.seed(99)  # Deterministic pricing
    print("=== Atomic BookNook: Ultimate Seed Script ===")
    app = create_app()

    with app.app_context():
        conn = get_db_connection()
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                # --- Step 2: Deduplicate ---
                print("Step 2: Removing duplicate book titles (keeping lowest book_id)...")
                cur.execute("""
                    DELETE FROM books a
                    USING books b
                    WHERE a.book_id > b.book_id
                      AND a.title = b.title;
                """)
                deleted_count = cur.rowcount
                print(f"  Deleted {deleted_count} duplicate rows.")

                # --- Fetch surviving IDs ---
                cur.execute("SELECT book_id FROM books ORDER BY book_id;")
                surviving_ids = [row["book_id"] for row in cur.fetchall()]
                num_surviving = len(surviving_ids)
                print(f"  {num_surviving} unique books remaining after deduplication.")

            # Fetch API data OUTSIDE the cursor but still inside the transaction
            api_books = fetch_books_from_open_library()
            if not api_books:
                raise RuntimeError("API returned no usable books. Cannot proceed.")

            with conn.cursor() as cur:
                # --- Step 4: Overwrite surviving rows ---
                books_needed_total = max(TARGET_TOTAL_BOOKS, num_surviving)
                api_books_slice = api_books[:books_needed_total]

                to_update = []
                for i, book in enumerate(api_books_slice[:num_surviving]):
                    book["book_id"] = surviving_ids[i]
                    to_update.append(book)

                to_insert = api_books_slice[num_surviving:]
                # Cap inserts so we don't exceed target
                slots_remaining = TARGET_TOTAL_BOOKS - num_surviving
                if slots_remaining > 0:
                    to_insert = to_insert[:slots_remaining]
                else:
                    to_insert = []

                if to_update:
                    print(f"Step 4a: Updating {len(to_update)} existing rows with fresh API data...")
                    update_sql = """
                        UPDATE books
                        SET title          = %(title)s,
                            author         = %(author)s,
                            genre          = %(genre)s,
                            price          = %(price)s,
                            stock_quantity = %(stock_quantity)s,
                            description    = %(description)s,
                            image_url      = %(image_url)s
                        WHERE book_id = %(book_id)s;
                    """
                    execute_batch(cur, update_sql, to_update)

                if to_insert:
                    print(f"Step 4b: Inserting {len(to_insert)} new books to reach target of {TARGET_TOTAL_BOOKS}...")
                    insert_sql = """
                        INSERT INTO books
                            (title, author, genre, price, stock_quantity, description, image_url)
                        VALUES
                            (%(title)s, %(author)s, %(genre)s, %(price)s,
                             %(stock_quantity)s, %(description)s, %(image_url)s);
                    """
                    execute_batch(cur, insert_sql, to_insert)

            conn.commit()
            final_count = num_surviving - deleted_count + len(to_insert)
            print(
                f"\n=== SUCCESS: Transaction committed! ===\n"
                f"  Duplicates removed : {deleted_count}\n"
                f"  Rows updated       : {len(to_update)}\n"
                f"  Rows inserted      : {len(to_insert)}\n"
                f"  Est. total in DB   : ~{num_surviving + len(to_insert)} books"
            )

        except Exception as e:
            conn.rollback()
            print(f"\n=== FAILED: Transaction rolled back. ===\nError: {e}")
            raise
        finally:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    ultimate_seed()
