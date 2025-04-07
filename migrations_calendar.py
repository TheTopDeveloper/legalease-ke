"""
Database migration script to add advanced calendar features to the Event model.
This script adds new fields for better conflict detection and automated scheduling.
"""
import logging
import os
import sys
import traceback
from datetime import datetime, timedelta

from sqlalchemy import create_engine, text

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection from environment variables"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        # If DATABASE_URL is not set, use the one from app.config
        from app import app
        with app.app_context():
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI')
    
    if not db_url:
        # As a fallback, try connecting to the SQLite database directly
        db_url = 'sqlite:///instance/kenyalaw.db'
        logger.info(f"Using fallback SQLite database at {db_url}")
    
    logger.info(f"Database URL: {db_url.split(':')[0]}")
    return create_engine(db_url)

def is_postgres():
    """Check if the database is PostgreSQL"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        from app import app
        with app.app_context():
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    
    if not db_url:
        # Fallback to SQLite if no db_url is found
        return False
        
    return 'postgresql' in db_url.lower()

def is_sqlite():
    """Check if the database is SQLite"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        from app import app
        with app.app_context():
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    
    if not db_url:
        # Fallback to SQLite if no db_url is found
        return True
        
    return 'sqlite' in db_url.lower()

def check_column_exists(table_name, column_name):
    """Check if a column exists in the database table"""
    engine = get_db_connection()
    
    if is_postgres():
        query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = :table_name AND column_name = :column_name
        """)
        with engine.connect() as connection:
            result = connection.execute(query, {'table_name': table_name, 'column_name': column_name})
            return bool(result.fetchone())
    
    elif is_sqlite():
        # First check if the table exists
        check_table_query = text(f"SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name")
        with engine.connect() as connection:
            result = connection.execute(check_table_query, {'table_name': table_name})
            if not result.fetchone():
                logger.warning(f"Table {table_name} does not exist in SQLite database")
                return False
            
            # Table exists, now check the column
            query = text(f"PRAGMA table_info({table_name})")
            result = connection.execute(query)
            columns = [row['name'] for row in result]
            return column_name in columns
    
    return False

def add_calendar_fields():
    """Add new columns to event table for advanced calendar features"""
    engine = get_db_connection()
    
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
    
    # Add foreign key constraint for related_event_id
    fk_constraint = "FOREIGN KEY (related_event_id) REFERENCES event(id)"
    
    with engine.connect() as connection:
        for column_name, column_type in new_columns:
            # Skip if column already exists
            if check_column_exists('event', column_name):
                logger.info(f"Column {column_name} already exists in event table")
                continue
            
            # Add column
            if is_postgres():
                query = text(f"ALTER TABLE event ADD COLUMN {column_name} {column_type}")
            else:  # SQLite
                query = text(f"ALTER TABLE event ADD COLUMN {column_name} {column_type}")
            
            connection.execute(query)
            logger.info(f"Added column {column_name} to event table")
        
        # Add foreign key constraint if needed and if the related_event_id column was newly added
        if is_postgres():
            # Check if the constraint already exists
            constraint_query = text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'event'
                AND constraint_type = 'FOREIGN KEY'
                AND constraint_name LIKE '%related_event_id%'
            """)
            
            result = connection.execute(constraint_query)
            if not result.fetchone():
                # Add the constraint
                connection.execute(text(
                    f"ALTER TABLE event ADD CONSTRAINT fk_event_related_event {fk_constraint}"
                ))
                logger.info("Added foreign key constraint for related_event_id")
        
        # Commit the transaction
        connection.commit()
    
    logger.info("Successfully added advanced calendar fields to event table")

def main():
    """Main function to run migration"""
    try:
        logger.info("Starting migration to add advanced calendar features...")
        
        # Import app here to avoid circular imports
        from app import app
        logger.info("Successfully imported app")
        
        # Print database URL for debugging (without exposing credentials)
        db_url = os.environ.get('DATABASE_URL', '')
        if db_url:
            # Split only if @ is in the string, to safely handle connection strings
            url_for_log = db_url.split('@')[0] + '...' if '@' in db_url else 'Valid URL but hiding details'
            logger.info(f"Using DATABASE_URL from environment: {url_for_log}")
        else:
            logger.info("DATABASE_URL not found in environment, will try to get from app.config")
            
        with app.app_context():
            logger.info("Entered app context")
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if db_url:
                # Split only if @ is in the string
                url_for_log = db_url.split('@')[0] + '...' if '@' in db_url else 'Valid URL but hiding details'
                logger.info(f"Using database URL from app.config: {url_for_log}")
            else:
                logger.warning("No database URL found in app.config either!")
                
            # Now perform the actual migration
            add_calendar_fields()
            
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    # This will be overridden by the earlier basicConfig
    logging.basicConfig(level=logging.INFO)
    main()