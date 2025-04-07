"""
Test case events with lazy dynamic relationship
"""
import unittest
import tempfile
import os
import shutil
import datetime

# Import the necessary modules
from app import db, app
from models import User, Case, Client, Event
from utils.llm import MockLLMClient

# Bypass LLM initialization to speed up tests
os.environ['MOCK_LLM'] = 'True'
os.environ['SKIP_LLM_INIT'] = 'True'

class TestCaseEvents(unittest.TestCase):
    """Test case for case events"""
    
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
            username='eventstestuser',
            email='events_test@example.com'
        )
        self.test_user.set_password('testpassword')
        db.session.add(self.test_user)
        
        # Create test client
        self.test_client = Client(
            name='Test Events Client',
            email='events_client@example.com',
            phone='1234567890',
            address='123 Test Street'
        )
        db.session.add(self.test_client)
        db.session.commit()
        
        # Create temporary directory if needed
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
        
        # Verify events were added - need to convert lazy dynamic to list first
        case = Case.query.filter_by(title='Event Test Case').first()
        print(f"Event relationship type: {type(case.events)}")
        
        # Get all events as a list and verify count
        events = case.events.all()
        self.assertEqual(len(events), 2, "Case should have 2 events")
        
        # Verify event details
        event_types = sorted([event.event_type for event in events])
        self.assertEqual(event_types[0], 'Deadline', "Should have a Deadline event")
        self.assertEqual(event_types[1], 'Hearing', "Should have a Hearing event")
        
        # Get upcoming events
        upcoming_events = Event.query.filter(
            Event.case_id == test_case.id,
            Event.start_time > datetime.datetime.now()
        ).order_by(Event.start_time).all()
        
        self.assertEqual(len(upcoming_events), 2, "Should have 2 upcoming events")
        self.assertEqual(upcoming_events[0].title, 'Document Submission Deadline', "Deadline should be first")
        self.assertEqual(upcoming_events[1].title, 'Case Hearing', "Hearing should be second")
        print("Case events test passed!")

if __name__ == "__main__":
    unittest.main()