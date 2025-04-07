"""
Database migration script to add new fields to the Event model.
"""
import logging
import sys
import os
import sqlite3
import psycopg2
from app import app, db
from sqlalchemy import text, inspect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_postgres():
    """Check if the database is PostgreSQL"""
    database_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    return database_uri.startswith('postgresql') or database_uri.startswith('postgres')

def is_sqlite():
    """Check if the database is SQLite"""
    database_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    return database_uri.startswith('sqlite')

def check_column_sqlite(table_name, column_name):
    """Check if a column exists in SQLite database"""
    try:
        # Extract the database path from the URI
        database_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        # Remove the sqlite:/// prefix to get the file path
        if database_uri.startswith('sqlite:///'):
            db_path = database_uri[10:]
        else:
            db_path = database_uri[9:] if database_uri.startswith('sqlite://') else 'kenyalaw.db'
        
        # Connect to the SQLite database directly
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query to check if the column exists
        cursor.execute(f"PRAGMA table_info('{table_name}')")
        columns = cursor.fetchall()
        conn.close()
        
        # Check if the column exists in the result
        return any(col[1] == column_name for col in columns)
    except Exception as e:
        logger.error(f"Error checking SQLite column: {e}")
        return False

def check_column_postgres(table_name, column_name):
    """Check if a column exists in PostgreSQL database"""
    try:
        result = db.session.execute(text(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_name='{table_name}' AND column_name='{column_name}'"
        ))
        return result.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking PostgreSQL column: {e}")
        return False

def check_column_exists(table_name, column_name):
    """Check if a column exists in the database table using SQLAlchemy inspector"""
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        logger.error(f"Error with SQLAlchemy inspector: {e}")
        
        # Fall back to database-specific checks
        if is_postgres():
            return check_column_postgres(table_name, column_name)
        elif is_sqlite():
            return check_column_sqlite(table_name, column_name)
        return False

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
            
            # Ensure the event table exists before proceeding
            inspector = inspect(db.engine)
            if 'event' not in inspector.get_table_names():
                logger.error("Event table does not exist! Please run create_all() first.")
                sys.exit(1)
                
            # Check and add each column
            for column_name, column_def in columns:
                # Check if column already exists using database-agnostic approach
                if not check_column_exists('event', column_name):
                    # Add the column with database-specific syntax
                    if is_sqlite():
                        # SQLite has different syntax for boolean and default timestamp
                        if "BOOLEAN" in column_def:
                            # SQLite doesn't have a BOOLEAN type, use INTEGER instead
                            column_def = column_def.replace("BOOLEAN", "INTEGER")
                            column_def = column_def.replace("FALSE", "0")
                            column_def = column_def.replace("TRUE", "1")
                        if "TIMESTAMP DEFAULT CURRENT_TIMESTAMP" in column_def:
                            # Use SQLite's datetime function
                            column_def = "DATETIME DEFAULT (datetime('now'))"
                    
                    # Execute the ALTER TABLE statement
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