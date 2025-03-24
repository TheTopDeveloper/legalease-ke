"""
Create an admin user for the system.
Run this after resetting the database.
"""

from werkzeug.security import generate_password_hash
from app import app, db
from models import User

def create_admin_user():
    """Create an admin user if none exists"""
    
    # Check if admin user already exists
    admin = User.query.filter_by(role='admin').first()
    if admin:
        print(f"Admin user already exists: {admin.username}")
        return
    
    # Create admin user
    admin = User(
        username="admin",
        email="admin@kenyalegalassistant.com",
        password_hash=generate_password_hash("admin123"),
        first_name="System",
        last_name="Administrator",
        role="admin",
        account_type="premium",
        tokens_available=1000,
        max_cases=999,
        is_active=True
    )
    
    db.session.add(admin)
    
    # Create a test user too
    user = User(
        username="test",
        email="test@example.com",
        password_hash=generate_password_hash("test123"),
        first_name="Test",
        last_name="User",
        role="individual",
        account_type="free",
        tokens_available=50,
        max_cases=5,
        is_active=True
    )
    
    db.session.add(user)
    db.session.commit()
    
    print(f"Admin user created: admin / admin123")
    print(f"Test user created: test / test123")

if __name__ == "__main__":
    with app.app_context():
        create_admin_user()