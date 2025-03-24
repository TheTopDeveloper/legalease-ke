"""
Database migration script to add new fields to the Event model.
"""
import logging
import sys
from app import app, db
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_event_columns():
    """Add new columns to event table for advanced calendar features"""
    with app.app_context():
        try:
            # List of columns to add with their SQL definitions
            columns = [
                ("priority", "INTEGER DEFAULT 2"),
                ("is_all_day", "BOOLEAN DEFAULT FALSE"),
                ("is_recurring", "BOOLEAN DEFAULT FALSE"),
                ("recurrence_pattern", "VARCHAR(50)"),
                ("recurrence_end_date", "TIMESTAMP"),
                ("reminder_sent", "BOOLEAN DEFAULT FALSE"),
                ("reminder_time", "INTEGER DEFAULT 24"),
                ("conflict_status", "VARCHAR(20)"),
                ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            ]
            
            # Check and add each column
            for column_name, column_def in columns:
                # Check if column already exists
                result = db.session.execute(text(
                    f"SELECT column_name FROM information_schema.columns "
                    f"WHERE table_name='event' AND column_name='{column_name}'"
                ))
                
                if not result.fetchone():
                    # Add the column
                    db.session.execute(text(f"ALTER TABLE event ADD COLUMN {column_name} {column_def}"))
                    logger.info(f"Added column {column_name} to event table")
                else:
                    logger.info(f"Column {column_name} already exists in event table")
            
            db.session.commit()
            logger.info("Successfully updated event table with new columns")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating event table: {e}")
            sys.exit(1)

if __name__ == "__main__":
    add_event_columns()