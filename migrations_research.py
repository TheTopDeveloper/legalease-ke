"""
Database migration script to add new fields to the LegalResearch model.
This adds the court_filter, has_arguments, has_rebuttals, and tokens_used columns.
"""
import os
import logging
import psycopg2
from psycopg2 import sql

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection from environment variables"""
    try:
        # First try to use DATABASE_URL environment variable
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            # If DATABASE_URL is available, use it directly
            conn = psycopg2.connect(db_url)
        else:
            # Otherwise, fall back to individual connection parameters
            conn = psycopg2.connect(
                host=os.environ.get('PGHOST'),
                database=os.environ.get('PGDATABASE'),
                user=os.environ.get('PGUSER'),
                password=os.environ.get('PGPASSWORD'),
                port=os.environ.get('PGPORT')
            )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return None


def add_research_columns():
    """Add new columns to legal_research table for advanced research features"""
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            logger.error("Failed to establish database connection")
            return
            
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if table exists before attempting migration
        cursor.execute(
            "SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name='legal_research')"
        )
        result = cursor.fetchone()
        if result is None or not result[0]:
            logger.warning("legal_research table does not exist, skipping migration")
            conn.close()
            return
        
        # Check if columns already exist
        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='legal_research'"
        )
        existing_columns = [col[0] for col in cursor.fetchall()]
        
        columns_to_add = {
            'court_filter': 'VARCHAR(50)',
            'result_count': 'INTEGER DEFAULT 0',
            'has_arguments': 'BOOLEAN DEFAULT FALSE',
            'has_rebuttals': 'BOOLEAN DEFAULT FALSE',
            'tokens_used': 'INTEGER DEFAULT 0',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
        
        for column_name, column_type in columns_to_add.items():
            if column_name not in existing_columns:
                try:
                    cursor.execute(
                        sql.SQL("ALTER TABLE legal_research ADD COLUMN {} {}").format(
                            sql.Identifier(column_name),
                            sql.SQL(column_type)
                        )
                    )
                    logger.info(f"Added column {column_name} to legal_research table")
                except Exception as e:
                    logger.error(f"Error adding column {column_name}: {str(e)}")
        
        conn.close()
        logger.info("LegalResearch table migration completed")
    except Exception as e:
        logger.error(f"Unexpected error in add_research_columns: {str(e)}")
        # Handle connection cleanup if it exists
        if 'conn' in locals():
            try:
                # Only close if conn is not None
                conn_var = locals().get('conn')
                if conn_var is not None:
                    conn_var.close()
            except Exception as close_err:
                logger.error(f"Error closing connection: {str(close_err)}")
                pass


if __name__ == "__main__":
    add_research_columns()