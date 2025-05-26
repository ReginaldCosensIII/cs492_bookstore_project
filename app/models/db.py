# app/models/db.py

import os
import logging
import psycopg2
from urllib.parse import urlparse # For parsing DATABASE_URL
from psycopg2.extras import RealDictCursor # For returning rows as dictionaries
# Use the app's configured logger once available, or a module-specific one.
# For this low-level connection module, standard logging before app logger is set is fine.

logger = logging.getLogger(__name__) # Standard logger for this module

def get_db_connection():
    """
    Establishes and returns a new database connection using credentials 
    from the DATABASE_URL environment variable.
    
    This function configures the connection to use `RealDictCursor` by default,
    so database rows are returned as dictionary-like objects (RealDictRow) 
    instead of tuples. This allows accessing columns by their names.

    Returns:
        psycopg2.connection: A new PostgreSQL database connection object.
                             The caller is responsible for closing this connection.

    Raises:
        ValueError: If the DATABASE_URL environment variable is not set or is invalid.
        psycopg2.Error: For underlying database connection errors (e.g., bad credentials,
                        server not reachable).
    """
    db_url = os.environ.get("DATABASE_URL")

    if not db_url:
        logger.critical("DATABASE_URL environment variable is not set. Cannot establish database connection.")
        raise ValueError("DATABASE_URL environment variable is not set. Database connection cannot be established.")

    try:
        # Parse the DATABASE_URL (e.g., postgresql://user:password@host:port/dbname)
        result = urlparse(db_url)
        conn_params = {
            'dbname': result.path[1:],  # Remove leading '/' from path
            'user': result.username,
            'password': result.password,
            'host': result.hostname,
            'port': result.port or 5432 # Default PostgreSQL port if not specified
        }
        
        # Establish the connection, setting RealDictCursor as the default for cursors from this connection.
        conn = psycopg2.connect(**conn_params, cursor_factory=RealDictCursor)
        logger.debug(f"Database connection successfully established to host: {conn_params['host']}, database: {conn_params['dbname']}")
        return conn
    
    except psycopg2.Error as e: # Catch specific psycopg2 operational or programming errors
        logger.error(f"PostgreSQL database connection error: {e}", exc_info=True)
        # Re-raise the specific psycopg2 error to allow for more granular error handling by the caller,
        # or wrap it in a custom DatabaseError if preferred for abstraction.
        raise 
    
    except Exception as e: # Catch other potential errors (e.g., from urlparse if URL is malformed)
        logger.error(f"Failed to parse DATABASE_URL or establish connection: {e}", exc_info=True)
        raise ValueError(f"Invalid DATABASE_URL or other connection failure: {e}")