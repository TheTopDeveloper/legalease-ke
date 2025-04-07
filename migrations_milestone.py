"""
Database migration script to add the CaseMilestone model.
This adds a new table to track important milestones in the case timeline.
"""
import logging
import os
import sys
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection from environment variables"""
    try:
        # Try to load environment variables from .env file if it exists
        try:
            from dotenv import load_dotenv
            load_dotenv()
            logger.info("Loaded environment variables from .env file")
        except ImportError:
            logger.warning("python-dotenv not installed, proceeding without loading .env file")
        
        # First try to use DATABASE_URL environment variable
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            # If DATABASE_URL is available, use it directly
            logger.info("Connecting using DATABASE_URL")
            conn = psycopg2.connect(db_url)
        else:
            # Otherwise, fall back to individual connection parameters
            logger.info("Connecting using individual database parameters")
            conn = psycopg2.connect(
                dbname=os.environ.get('PGDATABASE'),
                user=os.environ.get('PGUSER'),
                password=os.environ.get('PGPASSWORD'),
                host=os.environ.get('PGHOST'),
                port=os.environ.get('PGPORT')
            )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        # Print more details to help with debugging
        logger.error(f"DATABASE_URL: {os.environ.get('DATABASE_URL') is not None}")
        logger.error(f"PGDATABASE: {os.environ.get('PGDATABASE') is not None}")
        logger.error(f"PGUSER: {os.environ.get('PGUSER') is not None}")
        # Don't exit the program, just return None so the caller can handle it
        return None

def migrate_milestone_table():
    """Create the case_milestone table for tracking case progress"""
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            logger.error("Failed to establish database connection")
            return
            
        cursor = conn.cursor()
        
        # Check if the table already exists
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'case_milestone')"
        )
        result = cursor.fetchone()
        if result is None:
            logger.error("Failed to check if table exists")
            if conn is not None:
                conn.close()
            return
            
        table_exists = result[0]
        
        if not table_exists:
            try:
                # Create the case_milestone table
                cursor.execute("""
                    CREATE TABLE case_milestone (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(200) NOT NULL,
                        description TEXT,
                        milestone_type VARCHAR(50),
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        order_index INTEGER NOT NULL DEFAULT 0,
                        target_date TIMESTAMP,
                        completion_date TIMESTAMP,
                        is_critical BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        case_id INTEGER NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
                        event_id INTEGER REFERENCES "event"(id) ON DELETE SET NULL,
                        document_id INTEGER REFERENCES "document"(id) ON DELETE SET NULL
                    )
                """)
                logger.info("Created case_milestone table")
                
                # Add index to improve query performance
                cursor.execute("CREATE INDEX idx_case_milestone_case_id ON case_milestone(case_id)")
                logger.info("Created index on case_milestone(case_id)")
                
            except Exception as e:
                logger.error(f"Error creating milestone table: {str(e)}")
        else:
            logger.info("case_milestone table already exists")
        
        conn.close()
        logger.info("Case milestone migration completed")
    except Exception as e:
        logger.error(f"Unexpected error in migrate_milestone_table: {str(e)}")
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
    migrate_milestone_table()