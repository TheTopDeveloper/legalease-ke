"""
Test script for notification functionality.
Run this script to verify that SMS notifications are working correctly.
"""
import os
import sys
from datetime import datetime, timedelta
from app import app, db
from models import User, Case, Event, Document
from utils.notification_service import notification_service
from utils.send_message import send_twilio_message

def test_notifications():
    """Test notification functionality"""
    print("=== Notification System Test ===")
    
    # Check which SMS service is being used
    service_type = type(notification_service.sms_service).__name__
    print(f"Using SMS service: {service_type}")
    
    if service_type == "MockSMSService":
        print("NOTE: Using mock SMS service for testing (Twilio unavailable or not configured)")
        print("To use Twilio, set the following environment variables:")
        print("  - TWILIO_ACCOUNT_SID")
        print("  - TWILIO_AUTH_TOKEN")
        print("  - TWILIO_PHONE_NUMBER")
    
    # Test if we have any users in the system
    print("\nChecking for existing users...")
    with app.app_context():
        user_count = User.query.count()
        print(f"Found {user_count} users in the system")
        
        # Get or create a test user
        test_user = User.query.filter_by(username="test").first()
        if not test_user:
            print("Creating test user...")
            from werkzeug.security import generate_password_hash
            test_user = User(
                username="test",
                email="test@example.com",
                password_hash=generate_password_hash("test123"),
                role="individual",
                account_type="basic",
                first_name="Test",
                last_name="User",
                phone="0700123456"  # Kenyan mobile format
            )
            db.session.add(test_user)
            db.session.commit()
            print("Test user created successfully")
        else:
            print(f"Using existing test user: {test_user.username}")
            
            # Ensure test user has a phone number
            if not test_user.phone:
                test_user.phone = "0700123456"
                db.session.commit()
                print("Added phone number to test user")
        
        # Create test case if needed
        test_case = Case.query.filter_by(user_id=test_user.id).first()
        if not test_case:
            print("Creating test case...")
            test_case = Case(
                case_number="TEST-001",
                title="Test Legal Case",
                description="This is a test case for notification testing",
                court_level="High Court",
                case_type="Civil",
                practice_area="Commercial",
                filing_date=datetime.utcnow().date(),
                status="Active",
                court_stage="Mention",
                next_court_date=datetime.utcnow() + timedelta(days=7),
                user_id=test_user.id
            )
            db.session.add(test_case)
            db.session.commit()
            print("Test case created successfully")
        
        # Create test event if needed
        test_event = Event.query.filter_by(case_id=test_case.id).first()
        if not test_event:
            print("Creating test event...")
            test_event = Event(
                title="Test Court Appearance",
                description="Test court appearance for notification testing",
                event_type="Court Appearance",
                start_time=datetime.utcnow() + timedelta(days=2),
                end_time=datetime.utcnow() + timedelta(days=2, hours=2),
                location="Nairobi High Court",
                case_id=test_case.id,
                user_id=test_user.id
            )
            db.session.add(test_event)
            db.session.commit()
            print("Test event created successfully")
        
        # Send a test notification
        print("\nSending test court reminder...")
        result = notification_service.send_court_date_reminder(test_user, test_case, test_event)
        
        if result.get('success', False):
            print(f"✓ Notification sent successfully (ID: {result.get('message_id')})")
        else:
            print(f"✗ Failed to send notification: {result.get('error', 'Unknown error')}")
        
        # Get sent messages
        sent_messages = notification_service.sms_service.get_sent_messages(test_user.phone)
        print(f"\nSent messages ({len(sent_messages)}):")
        
        for msg in sent_messages:
            print(f"  - To: {msg['to']}")
            print(f"    Message: {msg['message']}")
            print(f"    Sent at: {msg['timestamp']}")
            print(f"    ID: {msg['message_id']}")
            print()
        
        print("Test completed successfully!")

if __name__ == "__main__":
    test_notifications()