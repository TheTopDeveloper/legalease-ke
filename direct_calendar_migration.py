"""
Direct SQL migration script to add advanced calendar features to Event table.
Use this as a fallback if migrations_calendar.py encounters issues.
"""
import logging
import os
import sys
import traceback
from datetime import datetime, timedelta

import psycopg2
from psycopg2 import sql

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection from environment variables"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("Database URL not found. Make sure DATABASE_URL environment variable is set.")
        
    # Connect directly using psycopg2
    return psycopg2.connect(db_url)

def check_column_exists(conn, cursor, table_name, column_name):
    """Check if a column exists in the database table"""
    query = sql.SQL("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s AND column_name = %s
    """)
    cursor.execute(query, (table_name, column_name))
    return bool(cursor.fetchone())

def add_calendar_fields():
    """Add new columns to event table for advanced calendar features"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # List of new columns to add
        new_columns = [
            ('is_flexible', 'BOOLEAN DEFAULT FALSE'),
            ('buffer_before', 'INTEGER DEFAULT 0'),
            ('buffer_after', 'INTEGER DEFAULT 0'),
            ('related_event_id', 'INTEGER'),
            ('court_reference_number', 'VARCHAR(100)'),
            ('participants', 'TEXT'),
            ('travel_time_minutes', 'INTEGER DEFAULT 0'),
            ('notification_preferences', 'VARCHAR(200)'),
            ('synchronization_status', 'VARCHAR(50)')
        ]
        
        for column_name, column_type in new_columns:
            # Skip if column already exists
            if check_column_exists(conn, cursor, 'event', column_name):
                logger.info(f"Column {column_name} already exists in event table")
                continue
            
            # Add column - use parameterized query construction for safety
            query = sql.SQL("ALTER TABLE {} ADD COLUMN {} {}").format(
                sql.Identifier('event'),
                sql.Identifier(column_name),
                sql.SQL(column_type)
            )
            cursor.execute(query)
            conn.commit()
            logger.info(f"Added column {column_name} to event table")
        
        # Add foreign key constraint if needed
        if not check_column_exists(conn, cursor, 'event', 'related_event_id_fk'):
            # Check if the constraint already exists
            cursor.execute("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'event'
                AND constraint_type = 'FOREIGN KEY'
                AND constraint_name LIKE '%related_event_id%'
            """)
            
            if not cursor.fetchone():
                # Add the constraint
                cursor.execute("""
                    ALTER TABLE event 
                    ADD CONSTRAINT fk_event_related_event 
                    FOREIGN KEY (related_event_id) REFERENCES event(id)
                """)
                conn.commit()
                logger.info("Added foreign key constraint for related_event_id")
    
    except Exception as e:
        conn.rollback()
        logger.error(f"Error adding columns: {str(e)}")
        logger.error(traceback.format_exc())
        raise
    finally:
        cursor.close()
        conn.close()
    
    logger.info("Successfully added advanced calendar fields to event table")

def main():
    """Main function to run migration"""
    try:
        logger.info("Starting direct SQL migration to add advanced calendar features...")
        
        # Print database URL for debugging (without exposing credentials)
        db_url = os.environ.get('DATABASE_URL', '')
        if db_url:
            # Split only if @ is in the string, to safely handle connection strings
            url_for_log = db_url.split('@')[0] + '...' if '@' in db_url else 'Valid URL but hiding details'
            logger.info(f"Using DATABASE_URL from environment: {url_for_log}")
        else:
            logger.error("DATABASE_URL not found in environment!")
            sys.exit(1)
            
        # Now perform the actual migration
        add_calendar_fields()
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()