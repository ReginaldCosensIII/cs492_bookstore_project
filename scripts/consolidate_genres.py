"""
consolidate_genres.py
Script to consolidate niche genres into 5 core buckets.
"""
from app import create_app
from app.models.db import get_db_connection

def consolidate_genres():
    print("Initializing Flask App Context for genre consolidation...")
    app = create_app()

    with app.app_context():
        conn = get_db_connection()
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                update_sql = """
                    UPDATE books
                    SET genre = CASE
                        WHEN genre ILIKE '%Science%' OR genre ILIKE '%Computer%' THEN 'Tech & Science'
                        WHEN genre ILIKE '%History%' OR genre ILIKE '%Biography%' THEN 'History & Biography'
                        WHEN genre ILIKE '%Mystery%' OR genre ILIKE '%Thriller%' THEN 'Mystery & Thriller'
                        WHEN genre ILIKE '%Fantasy%' OR genre ILIKE '%Sci-Fi%' THEN 'Sci-Fi & Fantasy'
                        ELSE 'Fiction'
                    END;
                """
                cur.execute(update_sql)
                print(f"SUCCESS: Updated {cur.rowcount} rows with consolidated genres.")
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"FAILED: Error during genre consolidation. Transaction rolled back.\nError: {e}")
            raise
        finally:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    consolidate_genres()
