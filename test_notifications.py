"""
Test script for the notification system.
This script tests the functionality of SMS and email notifications.
"""
import unittest
from unittest.mock import patch, MagicMock
import os
import json
import datetime

# Import the necessary modules
from app import db, app
from models import User, Notification, Case, Event, Client
from utils.notifications import (
    SMSNotifier,
    EmailNotifier,
    NotificationManager,
    NotificationType
)

class TestNotifications(unittest.TestCase):
    """Test case for the notification system"""
    
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
            username='testuser',
            email='test@example.com',
            phone='1234567890'
        )
        self.test_user.set_password('testpassword')
        db.session.add(self.test_user)
        
        # Create test client
        self.test_client = Client(
            name='Test Client',
            email='client@example.com',
            phone='0987654321',
            address='123 Test Street',
            user_id=1
        )
        db.session.add(self.test_client)
        
        # Create test case
        self.test_case = Case(
            title='Notification Test Case',
            case_number='CV-2023-007',
            court='Supreme Court',
            filing_date=datetime.datetime.now(),
            status='Active',
            description='This is a test case for notifications',
            client_id=1,
            user_id=1
        )
        db.session.add(self.test_case)
        
        # Create test event
        self.test_event = Event(
            title='Test Hearing',
            event_type='Hearing',
            start_time=datetime.datetime.now() + datetime.timedelta(days=1),
            end_time=datetime.datetime.now() + datetime.timedelta(days=1, hours=2),
            location='Court Room 5',
            description='Test hearing for notification',
            case_id=1,
            user_id=1
        )
        db.session.add(self.test_event)
        db.session.commit()
    
    def tearDown(self):
        """Clean up after each test"""
        # Remove database tables
        db.session.remove()
        db.drop_all()
        
        # Remove app context
        self.app_context.pop()
    
    @patch('utils.notifications.SMSNotifier.send_sms')
    def test_sms_notification(self, mock_send_sms):
        """Test sending SMS notifications"""
        # Configure mock
        mock_send_sms.return_value = True
        
        # Create SMS notifier
        sms_notifier = SMSNotifier()
        
        # Send test notification
        result = sms_notifier.send_notification(
            recipient=self.test_user.phone,
            subject="Test Notification",
            message="This is a test SMS notification"
        )
        
        # Verify notification was sent
        self.assertTrue(result, "SMS notification should be sent successfully")
        mock_send_sms.assert_called_once_with(
            to_phone=self.test_user.phone,
            message="This is a test SMS notification"
        )
    
    @patch('utils.notifications.EmailNotifier.send_email')
    def test_email_notification(self, mock_send_email):
        """Test sending email notifications"""
        # Configure mock
        mock_send_email.return_value = True
        
        # Create email notifier
        email_notifier = EmailNotifier()
        
        # Send test notification
        result = email_notifier.send_notification(
            recipient=self.test_user.email,
            subject="Test Email Notification",
            message="This is a test email notification",
            attachments=None
        )
        
        # Verify notification was sent
        self.assertTrue(result, "Email notification should be sent successfully")
        mock_send_email.assert_called_once_with(
            to_email=self.test_user.email,
            subject="Test Email Notification",
            message="This is a test email notification",
            attachments=None
        )
    
    @patch('utils.notifications.SMSNotifier.send_sms')
    @patch('utils.notifications.EmailNotifier.send_email')
    def test_notification_manager(self, mock_send_email, mock_send_sms):
        """Test notification manager with different notification types"""
        # Configure mocks
        mock_send_sms.return_value = True
        mock_send_email.return_value = True
        
        # Create notification manager
        notification_manager = NotificationManager()
        
        # Test SMS notification
        notification_manager.send_notification(
            notification_type=NotificationType.SMS,
            recipient=self.test_user.phone,
            subject="Test SMS",
            message="This is a test SMS notification"
        )
        
        # Verify SMS was sent
        mock_send_sms.assert_called_once()
        
        # Test email notification
        notification_manager.send_notification(
            notification_type=NotificationType.EMAIL,
            recipient=self.test_user.email,
            subject="Test Email",
            message="This is a test email notification"
        )
        
        # Verify email was sent
        mock_send_email.assert_called_once()
    
    def test_notification_model(self):
        """Test creating and retrieving notifications in the database"""
        # Create a test notification
        test_notification = Notification(
            user_id=self.test_user.id,
            case_id=self.test_case.id,
            title="Database Notification Test",
            message="This is a test notification stored in the database",
            notification_type="SYSTEM",
            is_read=False
        )
        db.session.add(test_notification)
        db.session.commit()
        
        # Retrieve notification
        saved_notification = Notification.query.filter_by(title="Database Notification Test").first()
        
        # Verify notification details
        self.assertIsNotNone(saved_notification, "Notification should be saved to database")
        self.assertEqual(saved_notification.user_id, self.test_user.id, "User ID should match")
        self.assertEqual(saved_notification.case_id, self.test_case.id, "Case ID should match")
        self.assertEqual(saved_notification.message, "This is a test notification stored in the database", "Message should match")
        self.assertEqual(saved_notification.notification_type, "SYSTEM", "Type should match")
        self.assertFalse(saved_notification.is_read, "Notification should be unread")
        
        # Test marking as read
        saved_notification.is_read = True
        db.session.commit()
        
        # Verify update
        updated_notification = Notification.query.get(saved_notification.id)
        self.assertTrue(updated_notification.is_read, "Notification should be marked as read")
    
    @patch('utils.notifications.NotificationManager.send_notification')
    def test_event_reminder_notification(self, mock_send_notification):
        """Test sending event reminder notifications"""
        # Configure mock
        mock_send_notification.return_value = True
        
        # Create notification manager with mocked methods
        notification_manager = NotificationManager()
        
        # Send event reminder
        notification_manager.send_event_reminder(
            event=self.test_event,
            user=self.test_user,
            notification_type=NotificationType.EMAIL
        )
        
        # Verify notification was sent with correct details
        mock_send_notification.assert_called_once()
        args = mock_send_notification.call_args[1]
        
        self.assertEqual(args['notification_type'], NotificationType.EMAIL, "Notification type should be EMAIL")
        self.assertEqual(args['recipient'], self.test_user.email, "Recipient should be user email")
        self.assertIn('Test Hearing', args['subject'], "Subject should include event title")
        self.assertIn('Court Room 5', args['message'], "Message should include event location")
        
        # Test saving reminder to database
        notification = Notification(
            user_id=self.test_user.id,
            event_id=self.test_event.id,
            case_id=self.test_case.id,
            title=f"Reminder: {self.test_event.title}",
            message=f"Reminder for your event: {self.test_event.title} at {self.test_event.location}",
            notification_type="EVENT_REMINDER",
            is_read=False
        )
        db.session.add(notification)
        db.session.commit()
        
        # Verify notification was saved
        saved_reminder = Notification.query.filter_by(event_id=self.test_event.id).first()
        self.assertIsNotNone(saved_reminder, "Event reminder should be saved to database")
        self.assertEqual(saved_reminder.notification_type, "EVENT_REMINDER", "Type should be EVENT_REMINDER")
    
    @patch('utils.notifications.NotificationManager.send_notification')
    def test_case_status_notification(self, mock_send_notification):
        """Test sending case status change notifications"""
        # Configure mock
        mock_send_notification.return_value = True
        
        # Create notification manager with mocked methods
        notification_manager = NotificationManager()
        
        # Update case status
        old_status = self.test_case.status
        new_status = "Postponed"
        self.test_case.status = new_status
        db.session.commit()
        
        # Send case status notification
        notification_manager.send_case_status_notification(
            case=self.test_case,
            old_status=old_status,
            new_status=new_status,
            user=self.test_user,
            notification_type=NotificationType.SMS
        )
        
        # Verify notification was sent with correct details
        mock_send_notification.assert_called_once()
        args = mock_send_notification.call_args[1]
        
        self.assertEqual(args['notification_type'], NotificationType.SMS, "Notification type should be SMS")
        self.assertEqual(args['recipient'], self.test_user.phone, "Recipient should be user phone")
        self.assertIn('Status Update', args['subject'], "Subject should indicate status update")
        self.assertIn('Postponed', args['message'], "Message should include new status")
        
        # Test saving status notification to database
        notification = Notification(
            user_id=self.test_user.id,
            case_id=self.test_case.id,
            title=f"Status Update: {self.test_case.title}",
            message=f"Case status changed from {old_status} to {new_status}",
            notification_type="STATUS_CHANGE",
            is_read=False
        )
        db.session.add(notification)
        db.session.commit()
        
        # Verify notification was saved
        saved_notification = Notification.query.filter_by(notification_type="STATUS_CHANGE").first()
        self.assertIsNotNone(saved_notification, "Status notification should be saved to database")
        self.assertEqual(saved_notification.case_id, self.test_case.id, "Case ID should match")
    
    @patch('utils.notifications.NotificationManager.send_notification')
    def test_client_notification(self, mock_send_notification):
        """Test sending notifications to clients"""
        # Configure mock
        mock_send_notification.return_value = True
        
        # Create notification manager with mocked methods
        notification_manager = NotificationManager()
        
        # Send notification to client
        notification_manager.send_client_notification(
            client=self.test_client,
            subject="Document Shared",
            message="A new document has been shared with you",
            notification_type=NotificationType.EMAIL
        )
        
        # Verify notification was sent with correct details
        mock_send_notification.assert_called_once()
        args = mock_send_notification.call_args[1]
        
        self.assertEqual(args['notification_type'], NotificationType.EMAIL, "Notification type should be EMAIL")
        self.assertEqual(args['recipient'], self.test_client.email, "Recipient should be client email")
        self.assertEqual(args['subject'], "Document Shared", "Subject should match")
        self.assertEqual(args['message'], "A new document has been shared with you", "Message should match")

if __name__ == "__main__":
    unittest.main()