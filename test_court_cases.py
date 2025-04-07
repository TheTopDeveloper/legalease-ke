"""
Test script for court cases functionality.
This script tests the functionality of handling court cases, including CRUD operations and search.
"""
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
import shutil
import datetime

# Import the necessary modules
from app import db, app
from models import User, Case, CaseMilestone, Client, Document, Event
from utils.vector_db import VectorDatabase
from utils.llm import MockLLMClient

class TestCourtCases(unittest.TestCase):
    """Test case for court cases functionality"""
    
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
            username='courtcasetestuser',
            email='courtcase_test@example.com'
        )
        self.test_user.set_password('testpassword')
        db.session.add(self.test_user)
        
        # Create test client
        self.test_client = Client(
            name='Test Court Case Client',
            email='courtcase_client@example.com',
            phone='1234567890',
            address='123 Test Street'
        )
        db.session.add(self.test_client)
        db.session.commit()
        
        # Create temporary directory for vector database
        self.temp_dir = tempfile.mkdtemp()
        self.mock_llm = MockLLMClient()
        self.vector_db = VectorDatabase(db_path=self.temp_dir, llm_client=self.mock_llm)
    
    def tearDown(self):
        """Clean up after each test"""
        # Remove database tables
        db.session.remove()
        db.drop_all()
        
        # Remove app context
        self.app_context.pop()
        
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_create_case(self):
        """Test creating a new case"""
        # Create a test case
        test_case = Case(
            title='Test Case v. Respondent',
            case_number='CV-2023-001',
            court_level='Supreme Court',  # Changed from 'court' to 'court_level' to match model
            filing_date=datetime.datetime.now(),
            status='Active',
            description='This is a test case',
            user_id=self.test_user.id
        )
        db.session.add(test_case)
        db.session.commit()
        
        # Verify case was created
        case = Case.query.filter_by(title='Test Case v. Respondent').first()
        self.assertIsNotNone(case, "Case should be created")
        self.assertEqual(case.case_number, 'CV-2023-001', "Case number should match")
        self.assertEqual(case.court_level, 'Supreme Court', "Court level should match")
        self.assertEqual(case.status, 'Active', "Status should match")
        self.assertEqual(case.user_id, self.test_user.id, "User ID should match")
        
        # Add the client association
        case.clients.append(self.test_client)
        db.session.commit()
        
        # Verify client association
        self.assertEqual(len(case.clients), 1, "Case should have 1 client")
        self.assertEqual(case.clients[0].id, self.test_client.id, "Client ID should match")
    
    def test_case_milestone_tracking(self):
        """Test adding and tracking case milestones"""
        # Create a test case
        test_case = Case(
            title='Milestone Test Case',
            case_number='CV-2023-002',
            court_level='High Court',
            filing_date=datetime.datetime.now(),
            status='Active',
            user_id=self.test_user.id
        )
        test_case.clients.append(self.test_client)
        db.session.add(test_case)
        db.session.commit()
        
        # Add milestones
        milestone1 = CaseMilestone(
            case_id=test_case.id,
            title='Case Filing',
            description='Initial case filing',
            due_date=datetime.datetime.now(),
            is_completed=True,
            completion_date=datetime.datetime.now(),
            user_id=self.test_user.id
        )
        
        milestone2 = CaseMilestone(
            case_id=test_case.id,
            title='Document Submission',
            description='Submit required documents',
            due_date=datetime.datetime.now() + datetime.timedelta(days=30),
            is_completed=False,
            user_id=self.test_user.id
        )
        
        db.session.add(milestone1)
        db.session.add(milestone2)
        db.session.commit()
        
        # Verify milestones were added
        case = Case.query.filter_by(title='Milestone Test Case').first()
        self.assertEqual(len(case.milestones), 2, "Case should have 2 milestones")
        
        # Verify milestone details
        self.assertTrue(case.milestones[0].is_completed, "First milestone should be completed")
        self.assertFalse(case.milestones[1].is_completed, "Second milestone should not be completed")
        
        # Update milestone status
        milestone2.is_completed = True
        milestone2.completion_date = datetime.datetime.now()
        db.session.commit()
        
        # Verify update
        updated_milestone = CaseMilestone.query.filter_by(title='Document Submission').first()
        self.assertTrue(updated_milestone.is_completed, "Milestone should be updated to completed")
    
    def test_case_document_association(self):
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
            user_id=self.test_user.id,
            case_id=test_case.id
        )
        db.session.add(test_document)
        db.session.commit()
        
        # Verify document was associated with case
        case = Case.query.filter_by(title='Document Test Case').first()
        self.assertEqual(len(case.documents), 1, "Case should have 1 document")
        self.assertEqual(case.documents[0].title, 'Test Pleading', "Document title should match")
    
    def test_case_vector_db_integration(self):
        """Test integrating case data with vector database"""
        # Create a test case
        test_case = Case(
            title='Vector DB Test Case',
            case_number='CV-2023-004',
            court_level='Supreme Court',
            filing_date=datetime.datetime.now(),
            status='Active',
            description='This is a test case for vector database integration',
            user_id=self.test_user.id
        )
        test_case.clients.append(self.test_client)
        db.session.add(test_case)
        db.session.commit()
        
        # Prepare case data for vector database
        case_data = {
            'id': str(test_case.id),
            'title': test_case.title,
            'citation': test_case.case_number,
            'court': test_case.court_level,
            'date': test_case.filing_date.strftime('%Y-%m-%d'),
            'parties': {
                'applicant': 'Test Applicant',
                'respondent': 'Test Respondent'
            },
            'summary': test_case.description,
            'url': f'/cases/{test_case.id}'
        }
        
        # Add to vector database
        case_id = self.vector_db.add_case(case_data)
        
        # Verify case was added to vector database
        self.assertEqual(case_id, str(test_case.id), "Vector DB case ID should match database ID")
        
        # Search for case in vector database
        search_results = self.vector_db.search_cases("vector database integration")
        
        # Verify search results
        self.assertTrue(len(search_results) > 0, "Search should return results")
        self.assertEqual(search_results[0]['id'], str(test_case.id), "Search result ID should match case ID")
    
    def test_case_events(self):
        """Test adding and managing case events"""
        # Create a test case
        test_case = Case(
            title='Event Test Case',
            case_number='CV-2023-005',
            court_level='High Court',
            filing_date=datetime.datetime.now(),
            status='Active',
            user_id=self.test_user.id
        )
        test_case.clients.append(self.test_client)
        db.session.add(test_case)
        db.session.commit()
        
        # Create case events
        hearing_date = datetime.datetime.now() + datetime.timedelta(days=14)
        hearing_event = Event(
            title='Case Hearing',
            event_type='Hearing',
            start_time=hearing_date,
            end_time=hearing_date + datetime.timedelta(hours=2),
            location='Court Room 3A',
            description='Initial case hearing',
            case_id=test_case.id,
            user_id=self.test_user.id
        )
        
        deadline_date = datetime.datetime.now() + datetime.timedelta(days=7)
        deadline_event = Event(
            title='Document Submission Deadline',
            event_type='Deadline',
            start_time=deadline_date,
            end_time=deadline_date,
            description='Submit all required documents',
            case_id=test_case.id,
            user_id=self.test_user.id
        )
        
        db.session.add(hearing_event)
        db.session.add(deadline_event)
        db.session.commit()
        
        # Verify events were added
        case = Case.query.filter_by(title='Event Test Case').first()
        self.assertEqual(len(case.events), 2, "Case should have 2 events")
        
        # Verify event details
        self.assertEqual(case.events[0].event_type, 'Hearing', "First event should be a hearing")
        self.assertEqual(case.events[1].event_type, 'Deadline', "Second event should be a deadline")
        
        # Get upcoming events
        upcoming_events = Event.query.filter(
            Event.case_id == test_case.id,
            Event.start_time > datetime.datetime.now()
        ).order_by(Event.start_time).all()
        
        self.assertEqual(len(upcoming_events), 2, "Should have 2 upcoming events")
        self.assertEqual(upcoming_events[0].title, 'Document Submission Deadline', "Deadline should be first")
        self.assertEqual(upcoming_events[1].title, 'Case Hearing', "Hearing should be second")
    
    def test_case_status_updates(self):
        """Test updating case status"""
        # Create a test case
        test_case = Case(
            title='Status Update Test Case',
            case_number='CV-2023-006',
            court_level='Court of Appeal',
            filing_date=datetime.datetime.now(),
            status='Active',
            user_id=self.test_user.id
        )
        test_case.clients.append(self.test_client)
        db.session.add(test_case)
        db.session.commit()
        
        # Update case status
        test_case.status = 'Postponed'
        test_case.updated_at = datetime.datetime.now()
        db.session.commit()
        
        # Verify status update
        updated_case = Case.query.filter_by(title='Status Update Test Case').first()
        self.assertEqual(updated_case.status, 'Postponed', "Status should be updated to Postponed")
        
        # Update to closed status
        test_case.status = 'Closed'
        test_case.outcome = 'Favorable judgment'
        test_case.closing_date = datetime.datetime.now()
        test_case.updated_at = datetime.datetime.now()
        db.session.commit()
        
        # Verify final status
        final_case = Case.query.filter_by(title='Status Update Test Case').first()
        self.assertEqual(final_case.status, 'Closed', "Status should be updated to Closed")
        self.assertEqual(final_case.outcome, 'Favorable judgment', "Outcome should be set")
        self.assertIsNotNone(final_case.closing_date, "Closing date should be set")

if __name__ == "__main__":
    unittest.main()