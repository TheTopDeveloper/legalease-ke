"""
Script to apply database migrations directly using SQL.
"""
import os
import logging
import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection from environment variables"""
    db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        raise Exception("DATABASE_URL environment variable not set")
    
    return psycopg2.connect(db_url)

def migrate_database():
    """Apply database migrations directly with SQL"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Migrations
        
        # 1. Create role_permission_association table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS role_permission_association (
            role_id INTEGER,
            permission_id INTEGER,
            PRIMARY KEY (role_id, permission_id)
        )
        """)
        
        # 2. Create user_organization_association table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_organization_association (
            user_id INTEGER,
            organization_id INTEGER,
            PRIMARY KEY (user_id, organization_id)
        )
        """)
        
        # 3. Create permission table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS permission (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL,
            description VARCHAR(200)
        )
        """)
        
        # 4. Create role table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS role (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL,
            description VARCHAR(200),
            is_default BOOLEAN DEFAULT FALSE,
            is_custom BOOLEAN DEFAULT FALSE
        )
        """)
        
        # 5. Create organization table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS organization (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            address TEXT,
            phone VARCHAR(20),
            email VARCHAR(120),
            size INTEGER,
            account_type VARCHAR(20) DEFAULT 'basic',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            subscription_end TIMESTAMP,
            owner_id INTEGER REFERENCES "user" (id)
        )
        """)
        
        # 6. Add new columns to user table
        
        # Check if columns exist before adding
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='user' AND column_name='custom_role_id'")
        if not cursor.fetchone():
            cursor.execute("""
            ALTER TABLE "user" ADD COLUMN custom_role_id INTEGER REFERENCES role(id)
            """)
            logger.info("Added custom_role_id column to user table")
        
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='user' AND column_name='active_organization_id'")
        if not cursor.fetchone():
            cursor.execute("""
            ALTER TABLE "user" ADD COLUMN active_organization_id INTEGER REFERENCES organization(id)
            """)
            logger.info("Added active_organization_id column to user table")
        
        # Commit the transaction
        conn.commit()
        
        logger.info("Database migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate_database()