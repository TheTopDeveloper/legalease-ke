"""
Isolated test for database functionality.
"""
import unittest
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime

# Create a completely isolated application
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create a minimal Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['TESTING'] = True
db.init_app(app)

# Define a minimal User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Define a minimal Client model
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Simple many-to-many association table
case_client_association = db.Table(
    'case_client_association',
    db.Column('case_id', db.Integer, db.ForeignKey('case.id')),
    db.Column('client_id', db.Integer, db.ForeignKey('client.id'))
)

# Define a minimal Case model
class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    case_number = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Define relationship to clients
    clients = db.relationship('Client', secondary=case_client_association, backref='cases')

class TestIsolated(unittest.TestCase):
    """Test case with isolated database setup"""
    
    def setUp(self):
        """Set up test"""
        self.app = app
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
    
    def tearDown(self):
        """Clean up after test"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_create_case_with_client(self):
        """Test creating a case with a client"""
        # Create a user
        user = User(username='testuser', email='test@example.com')
        db.session.add(user)
        db.session.commit()
        
        # Create a client
        client = Client(name='Test Client', email='client@example.com', 
                        phone='1234567890', address='123 Test St')
        db.session.add(client)
        db.session.commit()
        
        # Create a case
        case = Case(title='Test Case', case_number='TC-2023-001', status='Active',
                    description='Test case description', user_id=user.id)
        db.session.add(case)
        db.session.commit()
        
        # Associate client with case
        case.clients.append(client)
        db.session.commit()
        
        # Verify case was created and associated with client
        found_case = Case.query.filter_by(case_number='TC-2023-001').first()
        self.assertIsNotNone(found_case)
        self.assertEqual(found_case.title, 'Test Case')
        self.assertEqual(len(found_case.clients), 1)
        self.assertEqual(found_case.clients[0].id, client.id)

if __name__ == '__main__':
    unittest.main()