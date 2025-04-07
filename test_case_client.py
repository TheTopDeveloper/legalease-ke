"""
Test script specifically for testing the Case-Client relationship.
This script uses SQLite in memory to avoid PostgreSQL specific issues.
"""
import os
import unittest
import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure environment variables to bypass LLM initialization
os.environ['MOCK_LLM'] = 'True'
os.environ['SKIP_LLM_INIT'] = 'True'

# Create a clean app and db for testing
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TESTING'] = True
db.init_app(app)

# Define minimal models for testing
class User(db.Model):
    """Minimal User model for testing"""
    __tablename__ = 'test_user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = f"mocked_password_hash_{password}"

class Client(db.Model):
    """Minimal Client model for testing"""
    __tablename__ = 'test_client'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))

# Association table for many-to-many relationship
case_client_association = db.Table(
    'test_case_client_association',
    db.Column('case_id', db.Integer, db.ForeignKey('test_case.id'), primary_key=True),
    db.Column('client_id', db.Integer, db.ForeignKey('test_client.id'), primary_key=True)
)

class Case(db.Model):
    """Minimal Case model for testing"""
    __tablename__ = 'test_case'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    case_number = db.Column(db.String(50), nullable=False)
    court_level = db.Column(db.String(50))
    filing_date = db.Column(db.DateTime)
    status = db.Column(db.String(20))
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('test_user.id'))
    
    # Add the columns that might be required
    outcome = db.Column(db.String(100))
    closing_date = db.Column(db.DateTime)
    
    # Define the relationship with clients through the association table
    clients = db.relationship('Client', secondary=case_client_association,
                           backref=db.backref('cases', lazy='dynamic'))

class TestCaseClientRelationship(unittest.TestCase):
    """Test case for testing Case-Client relationship"""
    
    def setUp(self):
        """Set up test environment"""
        self.app_context = app.app_context()
        self.app_context.push()
        
        db.create_all()
        
        # Create test user
        self.test_user = User(username='testuser', email='test@example.com')
        self.test_user.set_password('password123')
        db.session.add(self.test_user)
        db.session.commit()
        
        # Store the user ID explicitly
        self.user_id = self.test_user.id
        print(f"Created test user with ID: {self.user_id}")
        
        # Create test clients
        self.client1 = Client(
            name='Client One',
            email='client1@example.com',
            phone='123-456-7890',
            address='123 Test Street'
        )
        self.client2 = Client(
            name='Client Two',
            email='client2@example.com',
            phone='098-765-4321',
            address='456 Test Avenue'
        )
        db.session.add_all([self.client1, self.client2])
        db.session.commit()
        
        # Store client IDs explicitly
        self.client1_id = self.client1.id
        self.client2_id = self.client2.id
        print(f"Created clients with IDs: {self.client1_id}, {self.client2_id}")
    
    def tearDown(self):
        """Clean up after test"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_case_client_association(self):
        """Test creating a case and associating it with clients"""
        # Create a test case
        test_case = Case(
            title='Test Case With Multiple Clients',
            case_number='TC-2023-001',
            court_level='High Court',
            filing_date=datetime.datetime.now(),
            status='Active',
            description='Test case description',
            user_id=self.user_id  # Use the stored user ID
        )
        db.session.add(test_case)
        db.session.commit()
        print(f"Created test case with ID: {test_case.id}")
        
        # Get fresh instances of clients from database to avoid detached instance errors
        client1 = Client.query.get(self.client1_id)
        client2 = Client.query.get(self.client2_id)
        
        # Associate clients with the case
        test_case.clients.append(client1)
        test_case.clients.append(client2)
        db.session.commit()
        print("Associated clients with the case")
        
        # Verify associations
        retrieved_case = Case.query.get(test_case.id)
        self.assertEqual(len(retrieved_case.clients), 2)
        client_names = sorted([client.name for client in retrieved_case.clients])
        self.assertEqual(client_names, ['Client One', 'Client Two'])
        print("Case-client associations verified")
        
        # Verify bidirectional relationship
        client1_refreshed = Client.query.get(self.client1_id)
        client1_cases = list(client1_refreshed.cases)
        self.assertEqual(len(client1_cases), 1)
        self.assertEqual(client1_cases[0].title, 'Test Case With Multiple Clients')
        print("Bidirectional relationship verified")
        
        print("Case-Client association test passed successfully!")

if __name__ == '__main__':
    unittest.main()