#!/usr/bin/env python3
"""
Simplified script for direct database migration to add advanced calendar features.
"""
import logging
import os
import sqlite3
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_sqlite_connection():
    """Connect to the SQLite database directly"""
    try:
        # Try to connect to the kenyalaw.db database in the instance folder
        conn = sqlite3.connect('instance/kenyalaw.db')
        logger.info("Connected to database at instance/kenyalaw.db")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        sys.exit(1)

def check_column_exists(conn, table_name, column_name):
    """Check if a column exists in the table"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for column in columns:
        if column[1] == column_name:
            return True
    return False

def add_calendar_fields():
    """Add advanced calendar fields to the event table"""
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    
    # Verify that the event table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='event'")
    if not cursor.fetchone():
        logger.error("Event table does not exist!")
        return False
    
    # List of new columns to add
    new_columns = [
        ('is_flexible', 'BOOLEAN DEFAULT 0'),
        ('buffer_before', 'INTEGER DEFAULT 0'),
        ('buffer_after', 'INTEGER DEFAULT 0'),
        ('related_event_id', 'INTEGER'),
        ('court_reference_number', 'VARCHAR(100)'),
        ('participants', 'TEXT'),
        ('travel_time_minutes', 'INTEGER DEFAULT 0'),
        ('notification_preferences', 'VARCHAR(200)'),
        ('synchronization_status', 'VARCHAR(50)')
    ]
    
    # Add each column
    for column_name, column_type in new_columns:
        if check_column_exists(conn, 'event', column_name):
            logger.info(f"Column {column_name} already exists in event table")
            continue
        
        try:
            sql = f"ALTER TABLE event ADD COLUMN {column_name} {column_type}"
            cursor.execute(sql)
            logger.info(f"Added column {column_name} to event table")
        except Exception as e:
            logger.error(f"Error adding column {column_name}: {str(e)}")
            conn.close()
            return False
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    logger.info("Successfully added all calendar fields to event table")
    return True

if __name__ == "__main__":
    logger.info("Starting simple migration for calendar fields...")
    success = add_calendar_fields()
    if success:
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration failed")
        sys.exit(1)