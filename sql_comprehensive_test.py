"""
Comprehensive test script using direct SQLite database connection.
This avoids complex model relationships and LLM initialization.
Includes multiple test cases to verify core functionality:
1. Case creation and management
2. Document association
3. Case events and calendar
4. Client relationships
5. Case milestones
"""
import unittest
import sqlite3
import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestComprehensiveSQLite(unittest.TestCase):
    """Comprehensive test case using direct SQLite operations"""
    
    def setUp(self):
        """Set up test environment before each test"""
        logger.info("Setting up SQLite in-memory database")
        # Create an in-memory SQLite database
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        
        # Create schema function
        self.create_schema()
        
        # Populate initial test data
        self.populate_test_data()
        
        self.conn.commit()
    
    def tearDown(self):
        """Clean up after each test"""
        # Close the database connection
        self.conn.close()
    
    def create_schema(self):
        """Create all required database tables"""
        # User table
        self.cursor.execute('''
        CREATE TABLE user (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT
        )
        ''')
        
        # Client table
        self.cursor.execute('''
        CREATE TABLE client (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            address TEXT
        )
        ''')
        
        # Case table (using quotes to avoid SQLite reserved keyword)
        self.cursor.execute('''
        CREATE TABLE "case" (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            case_number TEXT NOT NULL,
            court_level TEXT,
            filing_date TEXT,
            status TEXT,
            outcome TEXT,
            closing_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES user (id)
        )
        ''')
        
        # Case-Client association table
        self.cursor.execute('''
        CREATE TABLE case_client (
            case_id INTEGER,
            client_id INTEGER,
            PRIMARY KEY (case_id, client_id),
            FOREIGN KEY (case_id) REFERENCES "case" (id),
            FOREIGN KEY (client_id) REFERENCES client (id)
        )
        ''')
        
        # Document table
        self.cursor.execute('''
        CREATE TABLE document (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            document_type TEXT,
            status TEXT,
            content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES user (id)
        )
        ''')
        
        # Case-Document association table
        self.cursor.execute('''
        CREATE TABLE case_document (
            case_id INTEGER,
            document_id INTEGER,
            PRIMARY KEY (case_id, document_id),
            FOREIGN KEY (case_id) REFERENCES "case" (id),
            FOREIGN KEY (document_id) REFERENCES document (id)
        )
        ''')
        
        # Event table
        self.cursor.execute('''
        CREATE TABLE event (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            event_type TEXT,
            start_time TEXT,
            end_time TEXT,
            location TEXT,
            description TEXT,
            is_all_day BOOLEAN DEFAULT 0,
            recurrence TEXT,
            reminder_time INTEGER,
            color TEXT,
            case_id INTEGER,
            user_id INTEGER,
            FOREIGN KEY (case_id) REFERENCES "case" (id),
            FOREIGN KEY (user_id) REFERENCES user (id)
        )
        ''')
        
        # Milestone table
        self.cursor.execute('''
        CREATE TABLE case_milestone (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            date TEXT,
            status TEXT,
            case_id INTEGER,
            FOREIGN KEY (case_id) REFERENCES "case" (id)
        )
        ''')
    
    def populate_test_data(self):
        """Populate test data for all tests"""
        # Add test users
        self.cursor.execute('''
        INSERT INTO user (username, email, password_hash)
        VALUES (?, ?, ?)
        ''', ('testlawyer', 'lawyer@example.com', 'hashedpassword1'))
        
        self.cursor.execute('''
        INSERT INTO user (username, email, password_hash)
        VALUES (?, ?, ?)
        ''', ('testassistant', 'assistant@example.com', 'hashedpassword2'))
        
        # Get user IDs
        self.cursor.execute('SELECT id FROM user WHERE username = ?', ('testlawyer',))
        self.lawyer_id = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT id FROM user WHERE username = ?', ('testassistant',))
        self.assistant_id = self.cursor.fetchone()[0]
        
        # Add test clients
        self.cursor.execute('''
        INSERT INTO client (name, email, phone, address)
        VALUES (?, ?, ?, ?)
        ''', ('Corporate Client Inc.', 'corporate@example.com', '1234567890', '123 Business Ave.'))
        
        self.cursor.execute('''
        INSERT INTO client (name, email, phone, address)
        VALUES (?, ?, ?, ?)
        ''', ('Individual Client', 'individual@example.com', '0987654321', '456 Person St.'))
        
        # Get client IDs
        self.cursor.execute('SELECT id FROM client WHERE name = ?', ('Corporate Client Inc.',))
        self.corporate_client_id = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT id FROM client WHERE name = ?', ('Individual Client',))
        self.individual_client_id = self.cursor.fetchone()[0]
        
        logger.info(f"Created users: {self.lawyer_id}, {self.assistant_id}")
        logger.info(f"Created clients: {self.corporate_client_id}, {self.individual_client_id}")
    
    def test_case_management(self):
        """Test basic case management functionality"""
        now = datetime.datetime.now().isoformat()
        
        # Create different types of cases
        self.cursor.execute('''
        INSERT INTO "case" (title, case_number, court_level, filing_date, status, user_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Commercial Contract Dispute', 'CC-2023-001', 'Commercial Court', now, 'Active', self.lawyer_id))
        commercial_case_id = self.cursor.lastrowid
        
        self.cursor.execute('''
        INSERT INTO "case" (title, case_number, court_level, filing_date, status, user_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Criminal Defense Case', 'CR-2023-123', 'High Court', now, 'Active', self.lawyer_id))
        criminal_case_id = self.cursor.lastrowid
        
        self.cursor.execute('''
        INSERT INTO "case" (title, case_number, court_level, filing_date, status, outcome, closing_date, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Closed Family Case', 'FC-2022-055', 'Family Court', 
              (datetime.datetime.now() - datetime.timedelta(days=180)).isoformat(),
              'Closed', 'Settlement reached', now, self.lawyer_id))
        closed_case_id = self.cursor.lastrowid
        
        # Associate cases with clients
        self.cursor.execute('''
        INSERT INTO case_client (case_id, client_id)
        VALUES (?, ?)
        ''', (commercial_case_id, self.corporate_client_id))
        
        self.cursor.execute('''
        INSERT INTO case_client (case_id, client_id)
        VALUES (?, ?)
        ''', (criminal_case_id, self.individual_client_id))
        
        self.cursor.execute('''
        INSERT INTO case_client (case_id, client_id)
        VALUES (?, ?)
        ''', (closed_case_id, self.individual_client_id))
        
        self.conn.commit()
        
        # Verify active cases count
        self.cursor.execute('''
        SELECT COUNT(*) FROM "case" WHERE status = 'Active'
        ''')
        active_count = self.cursor.fetchone()[0]
        self.assertEqual(active_count, 2, "Should have 2 active cases")
        
        # Verify closed cases count
        self.cursor.execute('''
        SELECT COUNT(*) FROM "case" WHERE status = 'Closed'
        ''')
        closed_count = self.cursor.fetchone()[0]
        self.assertEqual(closed_count, 1, "Should have 1 closed case")
        
        # Verify case-client associations
        self.cursor.execute('''
        SELECT c.title 
        FROM "case" c
        JOIN case_client cc ON c.id = cc.case_id
        WHERE cc.client_id = ?
        ''', (self.individual_client_id,))
        
        individual_cases = self.cursor.fetchall()
        self.assertEqual(len(individual_cases), 2, "Individual client should have 2 cases")
        
        # Update case status
        self.cursor.execute('''
        UPDATE "case" 
        SET status = 'On Hold', updated_at = ?
        WHERE id = ?
        ''', (now, commercial_case_id))
        self.conn.commit()
        
        # Verify update worked
        self.cursor.execute('''
        SELECT status FROM "case" WHERE id = ?
        ''', (commercial_case_id,))
        updated_status = self.cursor.fetchone()[0]
        self.assertEqual(updated_status, 'On Hold', "Status should be updated to On Hold")
        
        logger.info("Case management test passed!")
    
    def test_document_association(self):
        """Test document creation and association with cases"""
        now = datetime.datetime.now().isoformat()
        
        # Create a test case
        self.cursor.execute('''
        INSERT INTO "case" (title, case_number, court_level, filing_date, status, user_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Document Test Case', 'DOC-2023-001', 'Commercial Court', now, 'Active', self.lawyer_id))
        case_id = self.cursor.lastrowid
        
        # Associate case with client
        self.cursor.execute('''
        INSERT INTO case_client (case_id, client_id)
        VALUES (?, ?)
        ''', (case_id, self.corporate_client_id))
        
        # Create documents
        self.cursor.execute('''
        INSERT INTO document (title, document_type, status, content, user_id)
        VALUES (?, ?, ?, ?, ?)
        ''', ('Complaint', 'Pleading', 'Final', 'This is a complaint document', self.lawyer_id))
        complaint_id = self.cursor.lastrowid
        
        self.cursor.execute('''
        INSERT INTO document (title, document_type, status, content, user_id)
        VALUES (?, ?, ?, ?, ?)
        ''', ('Contract Evidence', 'Evidence', 'Final', 'This is a contract document', self.lawyer_id))
        contract_id = self.cursor.lastrowid
        
        self.cursor.execute('''
        INSERT INTO document (title, document_type, status, content, user_id)
        VALUES (?, ?, ?, ?, ?)
        ''', ('Settlement Draft', 'Agreement', 'Draft', 'This is a draft settlement', self.lawyer_id))
        settlement_id = self.cursor.lastrowid
        
        # Associate documents with case
        self.cursor.execute('''
        INSERT INTO case_document (case_id, document_id)
        VALUES (?, ?)
        ''', (case_id, complaint_id))
        
        self.cursor.execute('''
        INSERT INTO case_document (case_id, document_id)
        VALUES (?, ?)
        ''', (case_id, contract_id))
        
        self.cursor.execute('''
        INSERT INTO case_document (case_id, document_id)
        VALUES (?, ?)
        ''', (case_id, settlement_id))
        
        self.conn.commit()
        
        # Verify all documents are associated with the case
        self.cursor.execute('''
        SELECT COUNT(*) 
        FROM document d
        JOIN case_document cd ON d.id = cd.document_id
        WHERE cd.case_id = ?
        ''', (case_id,))
        
        doc_count = self.cursor.fetchone()[0]
        self.assertEqual(doc_count, 3, "Case should have 3 documents")
        
        # Verify document status counts
        self.cursor.execute('''
        SELECT COUNT(*) 
        FROM document d
        JOIN case_document cd ON d.id = cd.document_id
        WHERE cd.case_id = ? AND d.status = 'Final'
        ''', (case_id,))
        
        final_count = self.cursor.fetchone()[0]
        self.assertEqual(final_count, 2, "Case should have 2 final documents")
        
        # Verify document types
        self.cursor.execute('''
        SELECT d.document_type
        FROM document d
        JOIN case_document cd ON d.id = cd.document_id
        WHERE cd.case_id = ?
        ORDER BY d.document_type
        ''', (case_id,))
        
        doc_types = [row[0] for row in self.cursor.fetchall()]
        self.assertEqual(doc_types, ['Agreement', 'Evidence', 'Pleading'], "Document types should match")
        
        logger.info("Document association test passed!")
    
    def test_events_and_calendar(self):
        """Test creating events and checking calendar functionality"""
        now = datetime.datetime.now().isoformat()
        
        # Create a test case
        self.cursor.execute('''
        INSERT INTO "case" (title, case_number, court_level, filing_date, status, user_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Calendar Test Case', 'CAL-2023-001', 'High Court', now, 'Active', self.lawyer_id))
        case_id = self.cursor.lastrowid
        
        # Create case events
        hearing_date = (datetime.datetime.now() + datetime.timedelta(days=14)).isoformat()
        hearing_end = (datetime.datetime.now() + datetime.timedelta(days=14, hours=2)).isoformat()
        
        deadline_date = (datetime.datetime.now() + datetime.timedelta(days=7)).isoformat()
        
        meeting_date = (datetime.datetime.now() + datetime.timedelta(days=3)).isoformat()
        meeting_end = (datetime.datetime.now() + datetime.timedelta(days=3, hours=1)).isoformat()
        
        all_day_event_date = (datetime.datetime.now() + datetime.timedelta(days=21)).isoformat()
        
        # Add events with different types and properties
        self.cursor.execute('''
        INSERT INTO event (title, event_type, start_time, end_time, location, description, case_id, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Case Hearing', 'Hearing', hearing_date, hearing_end, 'Court Room 3A', 
              'Initial case hearing', case_id, self.lawyer_id))
        
        self.cursor.execute('''
        INSERT INTO event (title, event_type, start_time, end_time, description, case_id, user_id, reminder_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Document Submission Deadline', 'Deadline', deadline_date, deadline_date,
              'Submit all required documents', case_id, self.lawyer_id, 24))
        
        self.cursor.execute('''
        INSERT INTO event (title, event_type, start_time, end_time, location, description, case_id, user_id, color)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Client Meeting', 'Meeting', meeting_date, meeting_end, 'Office Conference Room', 
              'Preparation meeting with client', case_id, self.lawyer_id, '#2196F3'))
        
        self.cursor.execute('''
        INSERT INTO event (title, event_type, start_time, end_time, description, case_id, user_id, is_all_day)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Court Closure Day', 'Other', all_day_event_date, all_day_event_date,
              'Court closed for holiday', case_id, self.lawyer_id, 1))
        
        self.conn.commit()
        
        # Verify all events were added
        self.cursor.execute('''
        SELECT COUNT(*)
        FROM event
        WHERE case_id = ?
        ''', (case_id,))
        
        event_count = self.cursor.fetchone()[0]
        self.assertEqual(event_count, 4, "Case should have 4 events")
        
        # Verify event types
        self.cursor.execute('''
        SELECT event_type, COUNT(*)
        FROM event
        WHERE case_id = ?
        GROUP BY event_type
        ORDER BY event_type
        ''', (case_id,))
        
        event_types = {}
        for row in self.cursor.fetchall():
            event_types[row[0]] = row[1]
            
        self.assertEqual(event_types['Deadline'], 1, "Should have 1 deadline event")
        self.assertEqual(event_types['Hearing'], 1, "Should have 1 hearing event")
        self.assertEqual(event_types['Meeting'], 1, "Should have 1 meeting event")
        
        # Verify upcoming events (next 10 days)
        ten_days_later = (datetime.datetime.now() + datetime.timedelta(days=10)).isoformat()
        
        self.cursor.execute('''
        SELECT title
        FROM event
        WHERE case_id = ? AND start_time > ? AND start_time < ?
        ORDER BY start_time
        ''', (case_id, now, ten_days_later))
        
        upcoming_events = [row[0] for row in self.cursor.fetchall()]
        self.assertEqual(len(upcoming_events), 2, "Should have 2 events in the next 10 days")
        self.assertEqual(upcoming_events[0], 'Client Meeting', "First upcoming event should be Client Meeting")
        self.assertEqual(upcoming_events[1], 'Document Submission Deadline', "Second upcoming event should be Document Submission Deadline")
        
        # Verify all-day events
        self.cursor.execute('''
        SELECT COUNT(*)
        FROM event
        WHERE case_id = ? AND is_all_day = 1
        ''', (case_id,))
        
        all_day_count = self.cursor.fetchone()[0]
        self.assertEqual(all_day_count, 1, "Should have 1 all-day event")
        
        logger.info("Events and calendar test passed!")
    
    def test_case_milestones(self):
        """Test adding and tracking case milestones"""
        now = datetime.datetime.now().isoformat()
        
        # Create a test case
        self.cursor.execute('''
        INSERT INTO "case" (title, case_number, court_level, filing_date, status, user_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Milestone Test Case', 'MS-2023-001', 'Supreme Court', now, 'Active', self.lawyer_id))
        case_id = self.cursor.lastrowid
        
        # Create milestones with different dates and statuses
        self.cursor.execute('''
        INSERT INTO case_milestone (title, description, date, status, case_id)
        VALUES (?, ?, ?, ?, ?)
        ''', ('Case Filed', 'Initial case filing with the court', now, 'Completed', case_id))
        
        one_month_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat()
        self.cursor.execute('''
        INSERT INTO case_milestone (title, description, date, status, case_id)
        VALUES (?, ?, ?, ?, ?)
        ''', ('Evidence Submission', 'Submit all evidence to court', one_month_ago, 'Completed', case_id))
        
        one_week_later = (datetime.datetime.now() + datetime.timedelta(days=7)).isoformat()
        self.cursor.execute('''
        INSERT INTO case_milestone (title, description, date, status, case_id)
        VALUES (?, ?, ?, ?, ?)
        ''', ('Pre-trial Conference', 'Meeting with judge to discuss trial', one_week_later, 'Pending', case_id))
        
        one_month_later = (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
        self.cursor.execute('''
        INSERT INTO case_milestone (title, description, date, status, case_id)
        VALUES (?, ?, ?, ?, ?)
        ''', ('Trial Start', 'Beginning of court trial', one_month_later, 'Pending', case_id))
        
        two_months_later = (datetime.datetime.now() + datetime.timedelta(days=60)).isoformat()
        self.cursor.execute('''
        INSERT INTO case_milestone (title, description, date, status, case_id)
        VALUES (?, ?, ?, ?, ?)
        ''', ('Expected Verdict', 'Court decision expected', two_months_later, 'Not Started', case_id))
        
        self.conn.commit()
        
        # Verify milestone count
        self.cursor.execute('''
        SELECT COUNT(*)
        FROM case_milestone
        WHERE case_id = ?
        ''', (case_id,))
        
        milestone_count = self.cursor.fetchone()[0]
        self.assertEqual(milestone_count, 5, "Case should have 5 milestones")
        
        # Verify milestone statuses
        self.cursor.execute('''
        SELECT status, COUNT(*)
        FROM case_milestone
        WHERE case_id = ?
        GROUP BY status
        ORDER BY status
        ''', (case_id,))
        
        milestone_statuses = {}
        for row in self.cursor.fetchall():
            milestone_statuses[row[0]] = row[1]
            
        self.assertEqual(milestone_statuses['Completed'], 2, "Should have 2 completed milestones")
        self.assertEqual(milestone_statuses['Pending'], 2, "Should have 2 pending milestones")
        self.assertEqual(milestone_statuses['Not Started'], 1, "Should have 1 not started milestone")
        
        # Verify milestone chronological order
        self.cursor.execute('''
        SELECT title
        FROM case_milestone
        WHERE case_id = ?
        ORDER BY date
        ''', (case_id,))
        
        chronological_milestones = [row[0] for row in self.cursor.fetchall()]
        self.assertEqual(chronological_milestones[0], 'Evidence Submission', "First milestone should be Evidence Submission")
        self.assertEqual(chronological_milestones[1], 'Case Filed', "Second milestone should be Case Filed")
        self.assertEqual(chronological_milestones[4], 'Expected Verdict', "Last milestone should be Expected Verdict")
        
        # Update a milestone status
        self.cursor.execute('''
        UPDATE case_milestone
        SET status = 'Completed'
        WHERE case_id = ? AND title = ?
        ''', (case_id, 'Pre-trial Conference'))
        self.conn.commit()
        
        # Verify update
        self.cursor.execute('''
        SELECT status
        FROM case_milestone
        WHERE case_id = ? AND title = ?
        ''', (case_id, 'Pre-trial Conference'))
        
        updated_status = self.cursor.fetchone()[0]
        self.assertEqual(updated_status, 'Completed', "Pre-trial Conference should be marked as Completed")
        
        logger.info("Case milestones test passed!")

if __name__ == "__main__":
    unittest.main()