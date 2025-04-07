"""
Basic test with minimal database setup.
"""
import unittest
from app import app, db
from models import User

class TestDBBasic(unittest.TestCase):
    """Basic test case with minimal DB setup"""
    
    def setUp(self):
        """Set up test"""
        self.app = app
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Use in-memory SQLite for testing
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        db.create_all()
    
    def tearDown(self):
        """Clean up after test"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_create_user(self):
        """Test creating a user"""
        user = User(
            username='dbbasicuser',
            email='dbbasic@example.com'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        # Verify user was created
        found_user = User.query.filter_by(username='dbbasicuser').first()
        self.assertIsNotNone(found_user)
        self.assertEqual(found_user.email, 'dbbasic@example.com')

if __name__ == '__main__':
    unittest.main()