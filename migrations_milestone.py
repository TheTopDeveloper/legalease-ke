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
        sys.exit(1)

def migrate_milestone_table():
    """Create the case_milestone table for tracking case progress"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if the table already exists
    cursor.execute(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'case_milestone')"
    )
    table_exists = cursor.fetchone()[0]
    
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

if __name__ == "__main__":
    migrate_milestone_table()