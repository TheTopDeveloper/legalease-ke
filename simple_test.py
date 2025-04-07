"""
Very minimal isolated test - no connections to app context
"""
import unittest
import os
import sqlite3
import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestSimpleSQLite(unittest.TestCase):
    """Simple test case using direct SQLite connections"""
    
    def setUp(self):
        """Set up test environment with SQLite"""
        # Use in-memory SQLite database
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        
        # Create minimal tables for our test
        self.cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE
        )
        ''')
        
        self.cursor.execute('''
        CREATE TABLE clients (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            address TEXT
        )
        ''')
        
        self.cursor.execute('''
        CREATE TABLE cases (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            case_number TEXT NOT NULL,
            court_level TEXT,
            filing_date TEXT,
            status TEXT,
            description TEXT,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        
        self.cursor.execute('''
        CREATE TABLE case_client (
            case_id INTEGER,
            client_id INTEGER,
            PRIMARY KEY (case_id, client_id),
            FOREIGN KEY (case_id) REFERENCES cases(id),
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
        ''')
        
        # Create test user
        self.cursor.execute(
            "INSERT INTO users (username, email) VALUES (?, ?)",
            ("testuser", "test@example.com")
        )
        
        # Create test client
        self.cursor.execute(
            "INSERT INTO clients (name, email, phone, address) VALUES (?, ?, ?, ?)",
            ("Test Client", "client@example.com", "1234567890", "123 Test St")
        )
        
        self.conn.commit()
        
        # Store the ids for later use
        self.user_id = self.cursor.lastrowid - 1  # user was inserted before client
        self.client_id = self.cursor.lastrowid
        
        logger.info("Test database setup completed")
        
    def tearDown(self):
        """Clean up after test"""
        self.conn.close()
        logger.info("Test database cleanup completed")
    
    def test_create_case(self):
        """Test creating a case with SQLite"""
        # Create a case
        now = datetime.datetime.now().isoformat()
        self.cursor.execute(
            """INSERT INTO cases 
               (title, case_number, court_level, filing_date, status, description, user_id) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("Test Case", "TC-2023-001", "High Court", now, "Active", "Test case description", self.user_id)
        )
        
        case_id = self.cursor.lastrowid
        self.conn.commit()
        
        # Verify case was created
        self.cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        case = self.cursor.fetchone()
        self.assertIsNotNone(case)
        self.assertEqual(case[1], "Test Case")  # title is at index 1
        self.assertEqual(case[2], "TC-2023-001")  # case_number is at index 2
        
        # Add client association
        self.cursor.execute(
            "INSERT INTO case_client (case_id, client_id) VALUES (?, ?)",
            (case_id, self.client_id)
        )
        self.conn.commit()
        
        # Verify client association
        self.cursor.execute("SELECT * FROM case_client WHERE case_id = ?", (case_id,))
        association = self.cursor.fetchone()
        self.assertIsNotNone(association)
        self.assertEqual(association[0], case_id)
        self.assertEqual(association[1], self.client_id)
        
        logger.info("Test completed successfully")

if __name__ == '__main__':
    unittest.main()