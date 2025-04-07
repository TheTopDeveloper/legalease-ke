"""
Simple test script using direct SQLite database connection.
This avoids complex model relationships and LLM initialization.
"""
import unittest
import sqlite3
import datetime

class TestSimpleSQLite(unittest.TestCase):
    """Test case using direct SQLite operations"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Create an in-memory SQLite database
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        
        # Create the necessary tables
        self.cursor.execute('''
        CREATE TABLE user (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT
        )
        ''')
        
        self.cursor.execute('''
        CREATE TABLE client (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            address TEXT
        )
        ''')
        
        self.cursor.execute('''
        CREATE TABLE "case" (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            case_number TEXT NOT NULL,
            court_level TEXT,
            filing_date TEXT,
            status TEXT,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES user (id)
        )
        ''')
        
        self.cursor.execute('''
        CREATE TABLE case_client (
            case_id INTEGER,
            client_id INTEGER,
            PRIMARY KEY (case_id, client_id),
            FOREIGN KEY (case_id) REFERENCES "case" (id),
            FOREIGN KEY (client_id) REFERENCES client (id)
        )
        ''')
        
        self.cursor.execute('''
        CREATE TABLE document (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            document_type TEXT,
            status TEXT,
            content TEXT,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES user (id)
        )
        ''')
        
        self.cursor.execute('''
        CREATE TABLE case_document (
            case_id INTEGER,
            document_id INTEGER,
            PRIMARY KEY (case_id, document_id),
            FOREIGN KEY (case_id) REFERENCES "case" (id),
            FOREIGN KEY (document_id) REFERENCES document (id)
        )
        ''')
        
        self.cursor.execute('''
        CREATE TABLE event (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            event_type TEXT,
            start_time TEXT,
            end_time TEXT,
            location TEXT,
            description TEXT,
            case_id INTEGER,
            user_id INTEGER,
            FOREIGN KEY (case_id) REFERENCES "case" (id),
            FOREIGN KEY (user_id) REFERENCES user (id)
        )
        ''')
        
        # Insert test user
        self.cursor.execute('''
        INSERT INTO user (username, email, password_hash)
        VALUES (?, ?, ?)
        ''', ('testuser', 'test@example.com', 'hashedpassword'))
        
        # Insert test client
        self.cursor.execute('''
        INSERT INTO client (name, email, phone, address)
        VALUES (?, ?, ?, ?)
        ''', ('Test Client', 'client@example.com', '1234567890', '123 Test St'))
        
        self.conn.commit()
        
        # Store IDs for test entities - get actual values
        self.cursor.execute('SELECT id FROM user WHERE username = ?', ('testuser',))
        self.user_id = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT id FROM client WHERE name = ?', ('Test Client',))
        self.client_id = self.cursor.fetchone()[0]
    
    def tearDown(self):
        """Clean up after each test"""
        # Close the database connection
        self.conn.close()
    
    def test_document_association(self):
        """Test associating documents with cases using SQLite"""
        # Create a test case
        now = datetime.datetime.now().isoformat()
        self.cursor.execute('''
        INSERT INTO "case" (title, case_number, court_level, filing_date, status, user_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Document Test Case', 'CV-2023-003', 'Commercial Court', now, 'Active', self.user_id))
        case_id = self.cursor.lastrowid
        
        # Associate case with client
        self.cursor.execute('''
        INSERT INTO case_client (case_id, client_id)
        VALUES (?, ?)
        ''', (case_id, self.client_id))
        
        # Create a document
        self.cursor.execute('''
        INSERT INTO document (title, document_type, status, content, user_id)
        VALUES (?, ?, ?, ?, ?)
        ''', ('Test Pleading', 'Pleading', 'Draft', 'This is a test pleading document', self.user_id))
        document_id = self.cursor.lastrowid
        
        # Associate document with case
        self.cursor.execute('''
        INSERT INTO case_document (case_id, document_id)
        VALUES (?, ?)
        ''', (case_id, document_id))
        
        self.conn.commit()
        
        # Verify document was associated with case
        self.cursor.execute('''
        SELECT d.title
        FROM document d
        JOIN case_document cd ON d.id = cd.document_id
        WHERE cd.case_id = ?
        ''', (case_id,))
        
        documents = self.cursor.fetchall()
        self.assertEqual(len(documents), 1, "Case should have 1 document")
        self.assertEqual(documents[0][0], 'Test Pleading', "Document title should match")
        print("Document association test passed!")
    
    def test_case_events(self):
        """Test adding and managing case events using SQLite"""
        # Create a test case
        now = datetime.datetime.now().isoformat()
        self.cursor.execute('''
        INSERT INTO "case" (title, case_number, court_level, filing_date, status, user_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Event Test Case', 'CV-2023-005', 'High Court', now, 'Active', self.user_id))
        case_id = self.cursor.lastrowid
        
        # Associate case with client
        self.cursor.execute('''
        INSERT INTO case_client (case_id, client_id)
        VALUES (?, ?)
        ''', (case_id, self.client_id))
        
        # Create case events
        hearing_date = (datetime.datetime.now() + datetime.timedelta(days=14)).isoformat()
        hearing_end = (datetime.datetime.now() + datetime.timedelta(days=14, hours=2)).isoformat()
        
        deadline_date = (datetime.datetime.now() + datetime.timedelta(days=7)).isoformat()
        
        self.cursor.execute('''
        INSERT INTO event (title, event_type, start_time, end_time, location, description, case_id, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Case Hearing', 'Hearing', hearing_date, hearing_end, 'Court Room 3A', 
              'Initial case hearing', case_id, self.user_id))
        
        self.cursor.execute('''
        INSERT INTO event (title, event_type, start_time, end_time, description, case_id, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('Document Submission Deadline', 'Deadline', deadline_date, deadline_date,
              'Submit all required documents', case_id, self.user_id))
        
        self.conn.commit()
        
        # Verify events were added
        self.cursor.execute('''
        SELECT title, event_type
        FROM event
        WHERE case_id = ?
        ''', (case_id,))
        
        events = self.cursor.fetchall()
        self.assertEqual(len(events), 2, "Case should have 2 events")
        
        # Sort events by title
        events.sort(key=lambda x: x[0])
        
        # Verify event details
        self.assertEqual(events[0][0], 'Case Hearing', "Case hearing title should match")
        self.assertEqual(events[0][1], 'Hearing', "Case hearing type should match")
        self.assertEqual(events[1][0], 'Document Submission Deadline', "Deadline title should match")
        self.assertEqual(events[1][1], 'Deadline', "Deadline type should match")
        
        # Get upcoming events
        now = datetime.datetime.now().isoformat()
        self.cursor.execute('''
        SELECT title
        FROM event
        WHERE case_id = ? AND start_time > ?
        ORDER BY start_time
        ''', (case_id, now))
        
        upcoming_events = self.cursor.fetchall()
        self.assertEqual(len(upcoming_events), 2, "Should have 2 upcoming events")
        self.assertEqual(upcoming_events[0][0], 'Document Submission Deadline', "Deadline should be first")
        self.assertEqual(upcoming_events[1][0], 'Case Hearing', "Hearing should be second")
        print("Case events test passed!")


if __name__ == "__main__":
    unittest.main()