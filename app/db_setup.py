# app/db_setup.py

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not set in environment")

    # Parse DATABASE_URL for compatibility with psycopg2
    result = urlparse(db_url)
    username = result.username
    password = result.password
    database = result.path[1:]  # skip leading /
    hostname = result.hostname
    port = result.port

    conn = psycopg2.connect(
        dbname=database,
        user=username,
        password=password,
        host=hostname,
        port=port,
        cursor_factory=RealDictCursor
    )
    return conn
