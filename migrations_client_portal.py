"""
Database migration script to add client portal models.
This adds the ClientPortalUser model and updates Client model with portal access.
"""
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection from environment variables"""
    try:
        # First try to use DATABASE_URL environment variable
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            # If DATABASE_URL is available, use it directly
            conn = psycopg2.connect(db_url)
        else:
            # Otherwise, fall back to individual connection parameters
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
        logger.error(f"Error connecting to database: {e}")
        return None

def migrate_client_portal():
    """Create tables for client portal and update Client model"""
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            logger.error("Failed to establish database connection")
            return False
            
        cursor = conn.cursor()
        
        # 1. Add has_portal_access column to Client model
        logger.info("Adding has_portal_access column to client table...")
        cursor.execute("""
        ALTER TABLE client 
        ADD COLUMN IF NOT EXISTS has_portal_access BOOLEAN DEFAULT FALSE;
        """)
        
        # 2. Create document_sharing_association table
        logger.info("Creating document_sharing_association table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_sharing_association (
            document_id INTEGER REFERENCES document(id) ON DELETE CASCADE,
            client_portal_user_id INTEGER,
            PRIMARY KEY (document_id, client_portal_user_id)
        );
        """)
        
        # 3. Create client_portal_user table
        logger.info("Creating client_portal_user table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS client_portal_user (
            id SERIAL PRIMARY KEY,
            email VARCHAR(120) NOT NULL,
            password_hash VARCHAR(256) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP WITHOUT TIME ZONE,
            access_token VARCHAR(100),
            token_expiry TIMESTAMP WITHOUT TIME ZONE,
            client_id INTEGER REFERENCES client(id) ON DELETE CASCADE
        );
        """)
        
        # 4. Check if constraint exists before adding it
        logger.info("Checking and updating document_sharing_association foreign key...")
        cursor.execute("""
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_client_portal_user';
        """)
        constraint_exists = cursor.fetchone()
        
        if not constraint_exists:
            logger.info("Adding foreign key constraint fk_client_portal_user...")
            cursor.execute("""
            ALTER TABLE document_sharing_association
            ADD CONSTRAINT fk_client_portal_user 
            FOREIGN KEY (client_portal_user_id) 
            REFERENCES client_portal_user(id) 
            ON DELETE CASCADE;
            """)
        else:
            logger.info("Foreign key constraint fk_client_portal_user already exists")
        
        # Add index on client portal user email
        logger.info("Adding index on client_portal_user email...")
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_client_portal_user_email ON client_portal_user(email);
        """)
        
        # Add index on client portal user client_id
        logger.info("Adding index on client_portal_user client_id...")
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_client_portal_user_client_id ON client_portal_user(client_id);
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("Client portal database migration completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Error in client portal migration: {e}")
        # Handle connection cleanup if it exists and is not None
        if conn is not None:
            try:
                conn.rollback()
                conn.close()
            except Exception as close_err:
                logger.error(f"Error during connection cleanup: {close_err}")
        return False

if __name__ == "__main__":
    logger.info("Running client portal database migration...")
    success = migrate_client_portal()
    if success:
        logger.info("Client portal migration completed successfully!")
    else:
        logger.error("Client portal migration failed!")