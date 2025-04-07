"""
Ultra-simplified test script that completely bypasses LLM initialization.
This test focuses only on testing the database models and relationships.
"""
import os
import sys
import unittest
import logging
import tempfile
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, 
                  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Completely bypass LLM initialization
os.environ['MOCK_LLM'] = 'True'
os.environ['SKIP_LLM_INIT'] = 'True'
os.environ['NO_LLM'] = 'True'
os.environ['DISABLE_OLLAMA_CONNECTION'] = 'True'
os.environ['USE_MOCK_LLM'] = 'True'
os.environ['DISABLE_LLM_SERVICES'] = 'True'

# Suppress INFO logs from other modules to make output cleaner
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Set up Flask application and database
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

# Use in-memory SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Define minimal models for testing
class Case(db.Model):
    """Minimal Case model for testing"""
    __tablename__ = 'ultra_simple_case'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    case_number = db.Column(db.String(50), nullable=False)
    court_level = db.Column(db.String(50))
    filing_date = db.Column(db.DateTime)
    status = db.Column(db.String(20))
    description = db.Column(db.Text)
    outcome = db.Column(db.Text)
    closing_date = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('ultra_simple_user.id'))
    
    # Relationships
    clients = db.relationship('Client', secondary='ultra_simple_case_client',
                            backref=db.backref('cases', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Case {self.case_number}: {self.title}>'

class Client(db.Model):
    """Minimal Client model for testing"""
    __tablename__ = 'ultra_simple_client'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    
    def __repr__(self):
        return f'<Client {self.id}: {self.name}>'

class User(db.Model):
    """Minimal User model for testing"""
    __tablename__ = 'ultra_simple_user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    
    def __repr__(self):
        return f'<User {self.username}>'

# Association table for Case-Client many-to-many relationship
case_client_association = db.Table('ultra_simple_case_client',
    db.Column('case_id', db.Integer, db.ForeignKey('ultra_simple_case.id'), primary_key=True),
    db.Column('client_id', db.Integer, db.ForeignKey('ultra_simple_client.id'), primary_key=True)
)

class UltraSimpleTest(unittest.TestCase):
    """Ultra-simplified test case that completely bypasses LLM initialization"""
    
    def setUp(self):
        """Set up test environment"""
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Create all tables in the in-memory database
        db.create_all()
        print("Database tables created successfully")
        
        # Create a test user
        self.test_user = User(
            username='testuser', 
            email='test@example.com',
            password_hash='dummy_hash'
        )
        db.session.add(self.test_user)
        db.session.commit()
        self.user_id = self.test_user.id
        print(f"Created test user with ID: {self.user_id}")
        
        # Create test clients
        self.client1 = Client(
            name='Client One',
            email='client1@example.com',
            phone='123-456-7890',
            address='123 Main St'
        )
        self.client2 = Client(
            name='Client Two',
            email='client2@example.com',
            phone='987-654-3210',
            address='456 Oak Ave'
        )
        db.session.add_all([self.client1, self.client2])
        db.session.commit()
        print(f"Created clients with IDs: {self.client1.id}, {self.client2.id}")
    
    def tearDown(self):
        """Clean up after test"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        print("Test cleanup completed")
    
    def test_case_client_association(self):
        """Test creating a case and associating it with clients"""
        # Create a test case
        test_case = Case(
            title='Test Case With Multiple Clients',
            case_number='TC-2023-002',
            court_level='High Court',
            filing_date=datetime.now(),
            status='Active',
            description='Test case description with multiple clients',
            user_id=self.user_id,
            outcome='Pending',
            closing_date=None
        )
        db.session.add(test_case)
        db.session.commit()
        print(f"Created test case with ID: {test_case.id}")
        
        # Associate clients with the case
        test_case.clients.append(self.client1)
        test_case.clients.append(self.client2)
        db.session.commit()
        print("Associated clients with the case")
        
        # Verify associations
        retrieved_case = db.session.get(Case, test_case.id)
        self.assertEqual(len(retrieved_case.clients), 2)
        client_names = sorted([client.name for client in retrieved_case.clients])
        self.assertEqual(client_names, ['Client One', 'Client Two'])
        print("Case-client associations verified")
        
        # Verify bidirectional relationship
        client1_refreshed = db.session.get(Client, self.client1.id)
        client1_cases = list(client1_refreshed.cases)
        self.assertEqual(len(client1_cases), 1)
        self.assertEqual(client1_cases[0].title, 'Test Case With Multiple Clients')
        print("Bidirectional relationship verified")
        
        # Verify outcome and closing_date fields
        self.assertEqual(retrieved_case.outcome, 'Pending')
        self.assertIsNone(retrieved_case.closing_date)
        print("Outcome and closing_date fields verified")
        
        print("Case-Client association test passed successfully!")

if __name__ == '__main__':
    unittest.main()