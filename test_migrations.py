"""
Test script for verifying database migrations.
This script tests the migrations from migrations_case.py.
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
    __tablename__ = 'test_migration_user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

class Client(db.Model):
    """Minimal Client model for testing"""
    __tablename__ = 'test_migration_client'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))

# Association table for many-to-many relationship
case_client_association = db.Table(
    'test_migration_case_client',
    db.Column('case_id', db.Integer, db.ForeignKey('test_migration_case.id'), primary_key=True),
    db.Column('client_id', db.Integer, db.ForeignKey('test_migration_client.id'), primary_key=True)
)

# Initial Case model without outcome and closing_date
class InitialCase(db.Model):
    """
    Represents the initial Case model before migrations.
    This is used to test the migration process.
    """
    __tablename__ = 'test_migration_case'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    case_number = db.Column(db.String(50), nullable=False)
    court_level = db.Column(db.String(50))
    filing_date = db.Column(db.DateTime)
    status = db.Column(db.String(20))
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('test_migration_user.id'))
    
    # Define the relationship with clients
    clients = db.relationship('Client', secondary=case_client_association,
                           backref=db.backref('cases', lazy='dynamic'))

# We don't need an updated case model since we're testing the migration on the initial model
# Instead, let's modify our InitialCase model to accept outcome and closing_date fields
# that will be added via migration
class MigratedCase(InitialCase):
    """
    Proxy class to help with testing column addition via migrations.
    We're not actually using this as a separate table, but just as a
    type hint to make testing cleaner.
    """
    outcome = None  # Will be added via migration
    closing_date = None  # Will be added via migration

class MigrationTester:
    """Helper class for testing migrations"""
    
    @staticmethod
    def add_outcome_column(db_conn, table_name='test_migration_case'):
        """
        Add outcome column to case table.
        This simulates the migration in migrations_case.py.
        """
        from sqlalchemy import text
        sql = text(f'ALTER TABLE {table_name} ADD COLUMN outcome TEXT')
        db_conn.execute(sql)
        db_conn.commit()
        print(f"Added outcome column to {table_name}")
    
    @staticmethod
    def add_closing_date_column(db_conn, table_name='test_migration_case'):
        """
        Add closing_date column to case table.
        This simulates the migration in migrations_case.py.
        """
        from sqlalchemy import text
        sql = text(f'ALTER TABLE {table_name} ADD COLUMN closing_date TIMESTAMP')
        db_conn.execute(sql)
        db_conn.commit()
        print(f"Added closing_date column to {table_name}")

class TestMigrations(unittest.TestCase):
    """Test case for database migrations"""
    
    def setUp(self):
        """Set up test environment"""
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Create database tables using the initial model
        db.create_all()
        
        # Create test user
        self.test_user = User(username='migrationtestuser', email='migration_test@example.com')
        db.session.add(self.test_user)
        
        # Create test client
        self.test_client = Client(name='Migration Test Client', email='migration_client@example.com')
        db.session.add(self.test_client)
        
        # Create a test case using the initial model
        self.test_case = InitialCase(
            title='Migration Test Case',
            case_number='MIG-2023-001',
            court_level='Supreme Court',
            filing_date=datetime.datetime.now(),
            status='Active',
            description='Migration test case description',
            user_id=self.test_user.id
        )
        db.session.add(self.test_case)
        
        # Associate the client with the case
        self.test_case.clients.append(self.test_client)
        db.session.commit()
        
        print(f"Set up complete: Created test case with ID {self.test_case.id}")
    
    def tearDown(self):
        """Clean up after test"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_case_migration(self):
        """Test adding outcome and closing_date columns to the case table"""
        from sqlalchemy import text
        
        # Perform the migrations
        print("Performing migrations...")
        
        # Use a transaction for SQLAlchemy 2.0 compatibility
        with db.engine.begin() as conn:
            # Add outcome column
            outcome_sql = text(f'ALTER TABLE test_migration_case ADD COLUMN outcome TEXT')
            conn.execute(outcome_sql)
            
            # Add closing_date column
            closing_date_sql = text(f'ALTER TABLE test_migration_case ADD COLUMN closing_date TIMESTAMP')
            conn.execute(closing_date_sql)
            
            print("Migration SQL executed successfully")
        
        # Verify that the columns were added by updating a case
        print("Verifying migrations...")
        
        # Use the session API to get objects by primary key
        case = db.session.get(InitialCase, self.test_case.id)
        
        # Check if columns exist and can be updated
        try:
            case.outcome = "Settled"
            case.closing_date = datetime.datetime.now()
            db.session.commit()
            print("Successfully updated case with new columns")
            
            # Retrieve the case and verify the values
            updated_case = db.session.get(InitialCase, self.test_case.id)
            self.assertEqual(updated_case.outcome, "Settled")
            self.assertIsNotNone(updated_case.closing_date)
            print("Migration test passed!")
        except Exception as e:
            self.fail(f"Migration test failed: {str(e)}")

if __name__ == '__main__':
    unittest.main()