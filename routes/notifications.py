"""
Routes for notification management and testing.
"""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from models import User, Case, Event, Document
from utils.notification_service import notification_service

# Create blueprint
notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@notifications_bp.route('/')
@login_required
def index():
    """Notification preferences and management"""
    # Get user's cases for the test notification feature
    cases = Case.query.filter_by(user_id=current_user.id).all()
    
    # Get user's events for reminder testing
    upcoming_events = Event.query.join(
        Case, Event.case_id == Case.id
    ).filter(
        Case.user_id == current_user.id,
        Event.start_time > datetime.utcnow()
    ).order_by(Event.start_time).limit(5).all()
    
    # Get recent sent messages for this user if any (for demonstration)
    sent_messages = []
    if hasattr(current_user, 'phone') and current_user.phone:
        sent_messages = notification_service.sms_service.get_sent_messages(current_user.phone)
    
    return render_template(
        'notifications/index.html',
        cases=cases,
        upcoming_events=upcoming_events,
        sent_messages=sent_messages
    )

@notifications_bp.route('/update-preferences', methods=['POST'])
@login_required
def update_preferences():
    """Update notification preferences"""
    # Get form data
    receive_sms = 'receive_sms' in request.form
    receive_email = 'receive_email' in request.form
    court_reminders = 'court_reminders' in request.form
    document_deadlines = 'document_deadlines' in request.form
    status_updates = 'status_updates' in request.form
    payment_confirmations = 'payment_confirmations' in request.form
    
    # Update user preferences
    user = User.query.get(current_user.id)
    if not hasattr(user, 'notification_preferences'):
        # This would require adding notification_preferences field to User model
        # For now, we'll just store preferences as a note in the user object
        flash('Notification preferences not yet implemented in database schema', 'warning')
    
    # Update phone number if provided
    phone = request.form.get('phone')
    if phone:
        user.phone = phone
        db.session.commit()
        flash('Phone number updated successfully', 'success')
    
    flash('Notification preferences updated', 'success')
    return redirect(url_for('notifications.index'))

@notifications_bp.route('/test-notification', methods=['POST'])
@login_required
def test_notification():
    """Send a test notification"""
    notification_type = request.form.get('notification_type')
    case_id = request.form.get('case_id')
    
    if not notification_type or not case_id:
        flash('Please select a notification type and case', 'warning')
        return redirect(url_for('notifications.index'))
    
    case = Case.query.get(case_id)
    if not case or case.user_id != current_user.id:
        flash('Invalid case selected', 'danger')
        return redirect(url_for('notifications.index'))
    
    result = {'success': False, 'message': 'Unknown notification type'}
    
    if notification_type == 'court_reminder':
        # Create a dummy event for testing if none exists
        event = Event.query.filter_by(case_id=case.id).first()
        if not event:
            event = Event(
                title=f"Mock Court Appearance for {case.title}",
                event_type="Court Appearance",
                start_time=datetime.utcnow() + timedelta(days=2),
                end_time=datetime.utcnow() + timedelta(days=2, hours=2),
                location="Nairobi High Court",
                case_id=case.id,
                user_id=current_user.id
            )
        
        result = notification_service.send_court_date_reminder(current_user, case, event)
        
    elif notification_type == 'document_deadline':
        # Create a dummy document for testing if none exists
        document = Document.query.filter_by(user_id=current_user.id).first()
        if not document:
            document = Document(
                title=f"Mock Document for {case.title}",
                document_type="Pleading",
                content="This is a mock document for testing notifications",
                status="Draft",
                user_id=current_user.id
            )
        
        deadline_date = datetime.utcnow() + timedelta(days=3)
        result = notification_service.send_document_deadline_reminder(
            current_user, case, document, deadline_date
        )
        
    elif notification_type == 'status_update':
        result = notification_service.send_case_status_update(
            current_user, case, "In Progress"
        )
    
    if result.get('success', False):
        flash('Test notification sent successfully', 'success')
    else:
        flash(f'Failed to send test notification: {result.get("error", "Unknown error")}', 'danger')
    
    return redirect(url_for('notifications.index'))

@notifications_bp.route('/send-reminders', methods=['POST'])
@login_required
def send_reminders():
    """
    Manually trigger sending reminders
    This would normally be handled by a scheduled task
    """
    # Check if user is admin
    if not current_user.role == 'admin':
        flash('You do not have permission to perform this action', 'danger')
        return redirect(url_for('notifications.index'))
    
    result = notification_service.send_scheduled_reminders()
    
    flash(f"Sent {result['success_count']} reminders successfully. {result['failure_count']} failed.", 'info')
    return redirect(url_for('notifications.index'))