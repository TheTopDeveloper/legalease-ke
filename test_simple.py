"""
Simple test to verify basic functionality.
"""
import unittest
from app import app, db
from models import User, Client, Case
import datetime

class TestSimple(unittest.TestCase):
    """Simple test case"""
    
    def setUp(self):
        """Set up test environment"""
        # Set up app context
        self.app = app
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Use in-memory SQLite database for testing
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        # Create database tables
        db.create_all()
        
        # Create test user
        self.test_user = User(
            username='simpletestuser',
            email='simple_test@example.com'
        )
        self.test_user.set_password('testpassword')
        db.session.add(self.test_user)
        
        # Create test client
        self.test_client = Client(
            name='Simple Test Client',
            email='simple_client@example.com',
            phone='1234567890',
            address='123 Test Street'
        )
        db.session.add(self.test_client)
        db.session.commit()
    
    def tearDown(self):
        """Clean up after test"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_create_case(self):
        """Test creating a case"""
        # Create a case
        test_case = Case(
            title='Simple Test Case',
            case_number='ST-2023-001',
            court_level='Supreme Court',
            filing_date=datetime.datetime.now(),
            status='Active',
            description='Simple test case description',
            user_id=self.test_user.id
        )
        db.session.add(test_case)
        db.session.commit()
        
        # Verify case was created
        case = Case.query.filter_by(title='Simple Test Case').first()
        self.assertIsNotNone(case)
        self.assertEqual(case.case_number, 'ST-2023-001')
        
        # Add client association
        case.clients.append(self.test_client)
        db.session.commit()
        
        # Verify client association
        self.assertEqual(len(case.clients), 1)
        self.assertEqual(case.clients[0].id, self.test_client.id)

if __name__ == '__main__':
    unittest.main()