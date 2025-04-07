"""
Database migration script to add advanced calendar features to the Event model.
This script adds new fields for better conflict detection and automated scheduling.
"""
import logging
import os
from datetime import datetime
from app import app
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection from environment variables"""
    db_url = os.environ.get('DATABASE_URL')
    return create_engine(db_url)

def is_postgres():
    """Check if the database is PostgreSQL"""
    return 'postgresql' in os.environ.get('DATABASE_URL', '')

def is_sqlite():
    """Check if the database is SQLite"""
    return 'sqlite' in os.environ.get('DATABASE_URL', '')

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
        query = text(f"PRAGMA table_info({table_name})")
        with engine.connect() as connection:
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
    logger.info("Starting migration to add advanced calendar features...")
    with app.app_context():
        add_calendar_fields()
    logger.info("Migration completed successfully")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()