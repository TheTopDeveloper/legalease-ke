"""
Database migration script to add the ruling database models.
This adds the Ruling, Judge, Tag, RulingReference, RulingAnnotation, and RulingAnalysis models.
"""
import os
import sys
import logging
import psycopg2
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
            
        # First try to use the DATABASE_URL environment variable
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            logger.info("Connecting using DATABASE_URL")
            conn = psycopg2.connect(database_url)
            return conn
        
        # Fallback to individual connection parameters
        logger.info("Connecting using individual connection parameters")
        conn = psycopg2.connect(
            host=os.environ.get('PGHOST'),
            database=os.environ.get('PGDATABASE'),
            user=os.environ.get('PGUSER'),
            password=os.environ.get('PGPASSWORD'),
            port=os.environ.get('PGPORT')
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to the database: {e}")
        return None

def migrate_ruling_database():
    """Create tables for ruling database and judicial trend analysis"""
    conn = None
    try:
        # Connect to the database
        conn = get_db_connection()
        if conn is None:
            logger.error("Failed to establish database connection")
            return False
            
        cursor = conn.cursor()
        
        # Create the tables using SQL
        # Create Judge table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS judge (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            title VARCHAR(50),
            court VARCHAR(100),
            bio TEXT,
            photo_url VARCHAR(500),
            start_date DATE,
            end_date DATE,
            is_active BOOLEAN DEFAULT TRUE
        );
        """)
        
        # Create Tag table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tag (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            parent_id INTEGER REFERENCES tag(id)
        );
        """)
        
        # Create Ruling table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ruling (
            id SERIAL PRIMARY KEY,
            case_number VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            court VARCHAR(100) NOT NULL,
            date_of_ruling DATE NOT NULL,
            citation VARCHAR(200),
            url VARCHAR(500),
            summary TEXT,
            full_text TEXT,
            outcome VARCHAR(50),
            category VARCHAR(100),
            importance_score INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_landmark BOOLEAN DEFAULT FALSE,
            user_id INTEGER REFERENCES "user"(id)
        );
        """)
        
        # Create association tables
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ruling_tag (
            ruling_id INTEGER REFERENCES ruling(id) ON DELETE CASCADE,
            tag_id INTEGER REFERENCES tag(id) ON DELETE CASCADE,
            PRIMARY KEY (ruling_id, tag_id)
        );
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ruling_judge (
            ruling_id INTEGER REFERENCES ruling(id) ON DELETE CASCADE,
            judge_id INTEGER REFERENCES judge(id) ON DELETE CASCADE,
            PRIMARY KEY (ruling_id, judge_id)
        );
        """)
        
        # Create RulingReference table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ruling_reference (
            id SERIAL PRIMARY KEY,
            source_ruling_id INTEGER REFERENCES ruling(id) ON DELETE CASCADE,
            target_ruling_id INTEGER REFERENCES ruling(id) ON DELETE CASCADE,
            reference_type VARCHAR(50),
            context TEXT
        );
        """)
        
        # Create RulingAnnotation table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ruling_annotation (
            id SERIAL PRIMARY KEY,
            ruling_id INTEGER REFERENCES ruling(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES "user"(id) ON DELETE CASCADE,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_private BOOLEAN DEFAULT TRUE
        );
        """)
        
        # Create RulingAnalysis table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ruling_analysis (
            id SERIAL PRIMARY KEY,
            ruling_id INTEGER REFERENCES ruling(id) ON DELETE CASCADE,
            analysis_type VARCHAR(50),
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Create indexes to improve query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ruling_court ON ruling(court);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ruling_date ON ruling(date_of_ruling);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ruling_category ON ruling(category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ruling_landmark ON ruling(is_landmark);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_judge_name ON judge(name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tag_name ON tag(name);")
        
        # Commit the transaction
        conn.commit()
        logger.info("Successfully created ruling database tables")
        return True
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        if conn is not None:
            try:
                conn.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception as close_error:
                logger.error(f"Error closing connection: {close_error}")

if __name__ == "__main__":
    logger.info("Running rulings database migration...")
    success = migrate_ruling_database()
    if success:
        logger.info("Rulings database migration completed successfully!")
    else:
        logger.error("Rulings database migration failed!")