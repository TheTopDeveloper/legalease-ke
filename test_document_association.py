"""
Test document association only
"""
import unittest
import tempfile
import os
import shutil
import datetime

# Import the necessary modules
from app import db, app
from models import User, Case, Client, Document
from utils.vector_db import VectorDatabase
from utils.llm import MockLLMClient

# Bypass LLM initialization to speed up tests
os.environ['MOCK_LLM'] = 'True'
os.environ['SKIP_LLM_INIT'] = 'True'

class TestDocumentAssociation(unittest.TestCase):
    """Test case for document association"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Configure Flask app for testing
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        # Create app context
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Create database tables
        db.create_all()
        
        # Create test user
        self.test_user = User(
            username='docasstestuser',
            email='docass_test@example.com'
        )
        self.test_user.set_password('testpassword')
        db.session.add(self.test_user)
        
        # Create test client
        self.test_client = Client(
            name='Test Document Association Client',
            email='docass_client@example.com',
            phone='1234567890',
            address='123 Test Street'
        )
        db.session.add(self.test_client)
        db.session.commit()
        
        # Create temporary directory for vector database
        self.temp_dir = tempfile.mkdtemp()
        self.mock_llm = MockLLMClient()
    
    def tearDown(self):
        """Clean up after each test"""
        # Remove database tables
        db.session.remove()
        db.drop_all()
        
        # Remove app context
        self.app_context.pop()
        
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_document_association(self):
        """Test associating documents with cases"""
        # Create a test case
        test_case = Case(
            title='Document Test Case',
            case_number='CV-2023-003',
            court_level='Commercial Court',
            filing_date=datetime.datetime.now(),
            status='Active',
            user_id=self.test_user.id
        )
        test_case.clients.append(self.test_client)
        db.session.add(test_case)
        db.session.commit()
        
        # Create a document
        test_document = Document(
            title='Test Pleading',
            document_type='Pleading',
            status='Draft',
            content='This is a test pleading document',
            user_id=self.test_user.id
        )
        db.session.add(test_document)
        db.session.commit()
        
        # Associate document with case using the many-to-many relationship
        test_case.documents.append(test_document)
        db.session.commit()
        
        # Verify document was associated with case
        case = Case.query.filter_by(title='Document Test Case').first()
        self.assertEqual(len(case.documents), 1, "Case should have 1 document")
        self.assertEqual(case.documents[0].title, 'Test Pleading', "Document title should match")
        print("Document association test passed!")

if __name__ == "__main__":
    unittest.main()