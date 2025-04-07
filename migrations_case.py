"""
Database migration script to add outcome and closing_date fields to the Case model.
"""
import os
import sys
import psycopg2
from datetime import datetime

def get_db_connection():
    """Get database connection from environment variables"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Parse components from DATABASE_URL
    conn = psycopg2.connect(db_url)
    return conn

def add_case_columns():
    """Add outcome and closing_date columns to case table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'case' 
            AND column_name IN ('outcome', 'closing_date')
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Add outcome column if it doesn't exist
        if 'outcome' not in existing_columns:
            print("Adding 'outcome' column to case table...")
            cursor.execute("""
                ALTER TABLE "case" 
                ADD COLUMN outcome TEXT
            """)
        else:
            print("Column 'outcome' already exists.")
        
        # Add closing_date column if it doesn't exist
        if 'closing_date' not in existing_columns:
            print("Adding 'closing_date' column to case table...")
            cursor.execute("""
                ALTER TABLE "case" 
                ADD COLUMN closing_date TIMESTAMP
            """)
        else:
            print("Column 'closing_date' already exists.")
        
        # Commit changes
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    add_case_columns()