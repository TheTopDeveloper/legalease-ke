"""
Notification service for SMS and email notifications.
Currently using mock implementations, but can be replaced with actual services.

Required API keys/tokens for production implementation:
1. TWILIO_ACCOUNT_SID - For Twilio SMS integration
2. TWILIO_AUTH_TOKEN - For Twilio SMS integration 
3. TWILIO_PHONE_NUMBER - For Twilio SMS integration
4. PESAPAL_CONSUMER_KEY - For PesaPal payment integration
5. PESAPAL_CONSUMER_SECRET - For PesaPal payment integration
"""
import os
import logging
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

class MockSMSService:
    """
    Mock SMS service for testing without actual SMS provider.
    This will be replaced with Twilio integration when API keys are available.
    """
    
    def __init__(self):
        """Initialize the mock SMS service"""
        self.sent_messages = []
    
    def send_sms(self, to_phone_number, message):
        """
        Send a SMS message (mock)
        
        Args:
            to_phone_number: Recipient phone number
            message: SMS message content
            
        Returns:
            Dict with success status and message ID
        """
        # Log the message for testing purposes
        logger.info(f"MOCK SMS to {to_phone_number}: {message}")
        
        # Store in sent messages for testing
        message_id = f"mock-sms-{len(self.sent_messages) + 1}"
        self.sent_messages.append({
            'to': to_phone_number,
            'message': message,
            'timestamp': datetime.utcnow(),
            'message_id': message_id
        })
        
        return {
            'success': True,
            'message_id': message_id
        }
    
    def get_sent_messages(self, to_phone_number=None):
        """
        Get sent messages for testing
        
        Args:
            to_phone_number: Optional filter by recipient
            
        Returns:
            List of sent messages
        """
        if to_phone_number:
            return [msg for msg in self.sent_messages if msg['to'] == to_phone_number]
        return self.sent_messages


class NotificationService:
    """
    Service for sending various types of notifications
    """
    
    def __init__(self, sms_service=None):
        """
        Initialize notification service
        
        Args:
            sms_service: SMS service to use (defaults to MockSMSService)
        """
        self.sms_service = sms_service or MockSMSService()
    
    def send_court_date_reminder(self, user, case, event):
        """
        Send a reminder about an upcoming court date
        
        Args:
            user: User object
            case: Case object
            event: Event object
            
        Returns:
            Dict with success status
        """
        if not user.phone:
            return {'success': False, 'error': 'User has no phone number'}
        
        # Calculate days until court date
        days_until = (event.start_time - datetime.utcnow()).days
        
        # Create message
        message = f"REMINDER: Court appearance for case {case.case_number} - {case.title} "
        message += f"scheduled for {event.start_time.strftime('%Y-%m-%d %H:%M')} "
        message += f"at {event.location} ({days_until} days from now)."
        
        # Send SMS
        result = self.sms_service.send_sms(user.phone, message)
        
        # Log activity
        self._log_notification_activity(user.id, 'court_reminder', case.id, result.get('success', False))
        
        return result
    
    def send_document_deadline_reminder(self, user, case, document, deadline_date):
        """
        Send a reminder about an upcoming document deadline
        
        Args:
            user: User object
            case: Case object
            document: Document object
            deadline_date: Datetime of the deadline
            
        Returns:
            Dict with success status
        """
        if not user.phone:
            return {'success': False, 'error': 'User has no phone number'}
        
        # Calculate days until deadline
        days_until = (deadline_date - datetime.utcnow()).days
        
        # Create message
        message = f"REMINDER: Document '{document.title}' for case {case.case_number} "
        message += f"is due on {deadline_date.strftime('%Y-%m-%d')} "
        message += f"({days_until} days from now)."
        
        # Send SMS
        result = self.sms_service.send_sms(user.phone, message)
        
        # Log activity
        self._log_notification_activity(user.id, 'document_deadline', case.id, result.get('success', False))
        
        return result
    
    def send_case_status_update(self, user, case, new_status):
        """
        Send notification about a case status change
        
        Args:
            user: User object
            case: Case object
            new_status: New status of the case
            
        Returns:
            Dict with success status
        """
        if not user.phone:
            return {'success': False, 'error': 'User has no phone number'}
        
        # Create message
        message = f"CASE UPDATE: Status of case {case.case_number} - {case.title} "
        message += f"has been updated to '{new_status}'."
        
        # Send SMS
        result = self.sms_service.send_sms(user.phone, message)
        
        # Log activity
        self._log_notification_activity(user.id, 'status_update', case.id, result.get('success', False))
        
        return result
    
    def send_payment_confirmation(self, user, payment):
        """
        Send payment confirmation notification
        
        Args:
            user: User object
            payment: Payment object
            
        Returns:
            Dict with success status
        """
        if not user.phone:
            return {'success': False, 'error': 'User has no phone number'}
        
        # Create message
        message = f"PAYMENT CONFIRMED: Your payment of KSh {payment.amount} "
        
        if payment.payment_type == 'subscription':
            message += f"for {payment.subscription.name} subscription plan "
        elif payment.payment_type == 'tokens':
            message += f"for {payment.token_package.token_count} tokens "
            
        message += f"has been successfully processed (Transaction ID: {payment.transaction_id})."
        
        # Send SMS
        result = self.sms_service.send_sms(user.phone, message)
        
        # Log activity
        self._log_notification_activity(user.id, 'payment_confirmation', None, result.get('success', False))
        
        return result
    
    def send_scheduled_reminders(self):
        """
        Send scheduled reminders for upcoming events
        This would be called by a scheduled task/cron job
        
        Returns:
            Dict with success counts
        """
        from models import Event, Case, User
        from app import db
        
        now = datetime.utcnow()
        # Get events happening in the next 24-48 hours
        tomorrow = now + timedelta(days=1)
        day_after = now + timedelta(days=2)
        
        upcoming_events = db.session.query(Event, Case, User).join(
            Case, Event.case_id == Case.id
        ).join(
            User, Case.user_id == User.id
        ).filter(
            Event.start_time >= tomorrow,
            Event.start_time <= day_after,
            Event.event_type == 'Court Appearance'
        ).all()
        
        success_count = 0
        failure_count = 0
        
        for event, case, user in upcoming_events:
            result = self.send_court_date_reminder(user, case, event)
            if result.get('success', False):
                success_count += 1
            else:
                failure_count += 1
        
        return {
            'success_count': success_count,
            'failure_count': failure_count,
            'total_count': success_count + failure_count
        }
    
    def _log_notification_activity(self, user_id, notification_type, case_id=None, success=True):
        """
        Log notification activity for tracking
        
        Args:
            user_id: User ID
            notification_type: Type of notification
            case_id: Optional case ID
            success: Whether notification was successful
        """
        from models import Activity
        from app import db
        
        description = f"Sent {notification_type} notification"
        if case_id:
            description += f" for case #{case_id}"
        if not success:
            description += " (failed)"
        
        activity = Activity(
            user_id=user_id,
            activity_type='notification',
            description=description,
            points=0  # No points for notifications
        )
        
        db.session.add(activity)
        db.session.commit()


# Create a default notification service instance
notification_service = NotificationService()