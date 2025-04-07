"""
Simple test to verify basic functionality without circular dependencies.
This test focuses only on the Case-Client relationship to avoid complex dependencies.
"""
import unittest
from app import app, db
import datetime
import os
import logging
import sys
import sqlalchemy as sa

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Bypass LLM initialization to speed up tests
os.environ['MOCK_LLM'] = 'True'
os.environ['SKIP_LLM_INIT'] = 'True'

# No need for this table, as we're using our own minimal models

# Define minimal models for testing
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.ext.declarative import declarative_base
from flask_login import UserMixin

# Minimal test models
class MinimalUser(db.Model, UserMixin):
    """Minimal User model for testing"""
    __tablename__ = 'minimal_user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class MinimalClient(db.Model):
    """Minimal Client model for testing"""
    __tablename__ = 'minimal_client'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))

class MinimalCase(db.Model):
    """Minimal Case model for testing"""
    __tablename__ = 'minimal_case'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    case_number = db.Column(db.String(50), nullable=False)
    court_level = db.Column(db.String(50))
    filing_date = db.Column(db.DateTime)
    status = db.Column(db.String(20))
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('minimal_user.id'))
    # Add the columns from migrations_case.py that might be required
    outcome = db.Column(db.String(100))
    closing_date = db.Column(db.DateTime)
    
    # Define the relationship with clients through the association table
    clients = db.relationship('MinimalClient', secondary='minimal_case_client_association',
                            backref=db.backref('cases', lazy='dynamic'))

# Minimal association table
minimal_case_client_association = db.Table('minimal_case_client_association',
    db.Column('case_id', db.Integer, db.ForeignKey('minimal_case.id'), primary_key=True),
    db.Column('client_id', db.Integer, db.ForeignKey('minimal_client.id'), primary_key=True)
)

class TestSimple(unittest.TestCase):
    """Simple test case using minimal models to avoid circular dependencies"""
    
    def setUp(self):
        """Set up test environment with minimal models"""
        # Set up app context
        self.app = app
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Use in-memory SQLite database for testing
        original_db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        logger.info("Setting up in-memory SQLite test database with minimal models")
        
        # Create database tables for our minimal models only
        db.create_all()
        
        # Create test user
        self.test_user = MinimalUser(
            username='simpletestuser',
            email='simple_test@example.com'
        )
        self.test_user.set_password('testpassword')
        db.session.add(self.test_user)
        
        # Create test client
        self.test_client = MinimalClient(
            name='Simple Test Client',
            email='simple_client@example.com',
            phone='1234567890',
            address='123 Test Street'
        )
        db.session.add(self.test_client)
        db.session.commit()
        
        # Store the original DB URI to restore it later
        self.original_db_uri = original_db_uri
    
    def tearDown(self):
        """Clean up after test"""
        db.session.remove()
        db.drop_all()
        
        # Restore the original database URI
        app.config['SQLALCHEMY_DATABASE_URI'] = self.original_db_uri
        
        self.app_context.pop()
        logger.info("Test database cleanup completed")
    
    def test_create_case(self):
        """Test creating a case with minimal models"""
        # Create a case
        test_case = MinimalCase(
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
        case = MinimalCase.query.filter_by(title='Simple Test Case').first()
        self.assertIsNotNone(case)
        self.assertEqual(case.case_number, 'ST-2023-001')
        
        # Add client association
        case.clients.append(self.test_client)
        db.session.commit()
        
        # Verify client association
        self.assertEqual(len(case.clients), 1)
        self.assertEqual(case.clients[0].id, self.test_client.id)
        logger.info("Test completed successfully")

if __name__ == '__main__':
    unittest.main()