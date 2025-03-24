"""
Create an admin user for the system.
Run this after resetting the database.
"""
import logging
from werkzeug.security import generate_password_hash
from app import app, db
from models import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin_user():
    """Create an admin user if none exists"""
    try:
        # Check if admin user already exists
        admin = User.query.filter_by(username='admin').first()
        if admin:
            logger.info(f"Admin user already exists: {admin.username}")
        else:
            logger.info("Creating admin user...")
            # Create admin user
            admin = User(
                username="admin",
                email="admin@kenyalegalassistant.com",
                first_name="System",
                last_name="Administrator",
                role="admin",
                account_type="premium",
                tokens_available=1000,
                max_cases=999,
                is_active=True
            )
            admin.set_password("admin123")
            
            db.session.add(admin)
            db.session.commit()
            logger.info("Admin user created: admin / admin123")
        
        # Check if test user already exists
        test_user = User.query.filter_by(username='test').first()
        if test_user:
            logger.info(f"Test user already exists: {test_user.username}")
        else:
            logger.info("Creating test user...")
            user = User(
                username="test",
                email="test@example.com",
                first_name="Test",
                last_name="User",
                role="individual",
                account_type="free",
                tokens_available=50,
                max_cases=5,
                is_active=True
            )
            user.set_password("test123")
            
            db.session.add(user)
            db.session.commit()
            logger.info("Test user created: test / test123")
            
    except Exception as e:
        logger.error(f"Error creating users: {str(e)}")
        db.session.rollback()
        raise

if __name__ == "__main__":
    with app.app_context():
        create_admin_user()