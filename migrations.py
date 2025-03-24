"""
Database migration script to add template_id to the Document model.
"""
import logging
import sys
from app import app, db
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_template_id_column():
    """Add template_id column to document table"""
    with app.app_context():
        try:
            # Check if column already exists
            result = db.session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='document' AND column_name='template_id'"))
            if result.fetchone():
                logger.info("Column template_id already exists in document table.")
                return
            
            # Add the column
            db.session.execute(text("ALTER TABLE document ADD COLUMN template_id INTEGER"))
            
            # Add foreign key constraint
            db.session.execute(text("ALTER TABLE document ADD CONSTRAINT fk_document_template_id FOREIGN KEY (template_id) REFERENCES document_template (id)"))
            
            db.session.commit()
            logger.info("Successfully added template_id column to document table.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding template_id column: {e}")
            sys.exit(1)

if __name__ == "__main__":
    add_template_id_column()