"""
Extremely simplified test to verify basic functionality.
"""
import os
import logging
from app import app, db

# Configure logging
logging.basicConfig(level=logging.INFO, 
                  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Bypass LLM initialization
os.environ['MOCK_LLM'] = 'True'
os.environ['SKIP_LLM_INIT'] = 'True'
os.environ['NO_LLM'] = 'True'
os.environ['DISABLE_OLLAMA_CONNECTION'] = 'True'
os.environ['USE_MOCK_LLM'] = 'True'
os.environ['DISABLE_LLM_SERVICES'] = 'True'

def basic_test():
    """Run a very basic test to verify basic functionality"""
    print("Starting basic DB test...")
    
    # Create a new temporary database file
    import tempfile
    temp_db_file = tempfile.NamedTemporaryFile(suffix='.db').name
    temp_db_uri = f'sqlite:///{temp_db_file}'
    
    # Save original DB URI
    original_db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    
    try:
        # Use temp SQLite database for testing
        app.config['SQLALCHEMY_DATABASE_URI'] = temp_db_uri
        print(f"Using temporary database: {temp_db_uri}")
        
        # Work within the app context
        with app.app_context():
            # Create tables for our models
            db.create_all()
            print("Database tables created successfully.")
            
            # Import models just for the test
            from models import Case, Client, User
            
            try:
                # Check if we can access the models
                print(f"Models available - User: {User}, Client: {Client}, Case: {Case}")
                print("Basic model access test successful.")
                
                # Now let's try to create instances and test relationships
                import datetime
                
                # Create a test user
                test_user = User(
                    username='testuser', 
                    email='test@example.com',
                    password_hash='pbkdf2:sha256:1$iZn91vGW$f6d79bde83ef9ce9ec6b22b8007e0a9cabb6671f7bc5caf97644a1812b5eaae1'
                )
                db.session.add(test_user)
                db.session.commit()
                print(f"Created test user with ID: {test_user.id}")
                
                # Create a test client
                test_client = Client(
                    name='Test Client',
                    email='client@example.com',
                    phone='123-456-7890',
                    address='123 Test Street'
                )
                db.session.add(test_client)
                db.session.commit()
                print(f"Created test client with ID: {test_client.id}")
                
                # Create a test case
                test_case = Case(
                    title='Test Case Title',
                    case_number='TC-2023-001',
                    court_level='High Court',
                    filing_date=datetime.datetime.now(),
                    status='Active',
                    description='This is a test case description',
                    user_id=test_user.id
                )
                db.session.add(test_case)
                db.session.commit()
                print(f"Created test case with ID: {test_case.id}")
                
                # Associate the client with the case
                test_case.clients.append(test_client)
                db.session.commit()
                print("Associated the client with the case")
                
                # Verify the association
                retrieved_case = db.session.get(Case, test_case.id)
                if retrieved_case and len(retrieved_case.clients) > 0:
                    print(f"Case-client association verified: Case has {len(retrieved_case.clients)} clients")
                    print(f"Client name: {retrieved_case.clients[0].name}")
                else:
                    print("Failed to verify case-client association!")
                
            except Exception as e:
                import traceback
                print(f"Error during test: {e}")
                print(traceback.format_exc())
                db.session.rollback()
                raise
    
    finally:
        # Always restore original DB URI
        app.config['SQLALCHEMY_DATABASE_URI'] = original_db_uri
        print("Original database URI restored.")
        
    print("Basic test complete!")

if __name__ == '__main__':
    basic_test()