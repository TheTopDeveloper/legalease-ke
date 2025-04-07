"""
Routes for client portal functionality, allowing clients to access shared documents.
"""

from datetime import datetime, timedelta
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import db
from utils.permissions import Permissions
from models import ClientPortalUser, Client, Document, Case, Event, CaseMilestone

client_portal_bp = Blueprint('client_portal_bp', __name__, url_prefix='/client')

# Function to load user for Flask-Login
def load_user(user_id):
    """Load user by ID for Flask-Login - works for both User and ClientPortalUser"""
    # Try to load as ClientPortalUser first
    user = ClientPortalUser.query.get(int(user_id))
    return user

@client_portal_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Client portal login"""
    if current_user.is_authenticated:
        return redirect(url_for('client_portal_bp.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = ClientPortalUser.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash('Login successful. Welcome to your client portal.', 'success')
            return redirect(url_for('client_portal_bp.dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
            
    return render_template('client_portal/login.html')

@client_portal_bp.route('/logout')
@login_required
def logout():
    """Client portal logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('client_portal_bp.login'))

@client_portal_bp.route('/')
@login_required
def dashboard():
    """Client portal dashboard"""
    # Verify the user is a ClientPortalUser
    if not isinstance(current_user, ClientPortalUser):
        flash('Access denied. You do not have permission to access the client portal.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Get client details
    client = Client.query.get(current_user.client_id)
    if not client:
        flash('Client account not found.', 'danger')
        return redirect(url_for('client_portal_bp.logout'))
    
    # Get shared documents
    documents = Document.query.join(
        Document.shared_with).filter(
        ClientPortalUser.id == current_user.id
    ).order_by(Document.created_at.desc()).all()
    
    # Get cases associated with this client
    cases = Case.query.join(
        Case.clients).filter(
        Client.id == client.id
    ).order_by(Case.next_court_date.asc()).all()
    
    # Get upcoming events for the next 30 days
    thirty_days_from_now = datetime.utcnow() + timedelta(days=30)
    upcoming_events = Event.query.join(
        Event.case).join(
        Case.clients).filter(
        Client.id == client.id,
        Event.start_time > datetime.utcnow(),
        Event.start_time <= thirty_days_from_now
    ).order_by(Event.start_time.asc()).all()
    
    return render_template('client_portal/dashboard.html',
                          client=client,
                          documents=documents,
                          cases=cases,
                          upcoming_events=upcoming_events)

@client_portal_bp.route('/documents')
@login_required
def documents():
    """View all shared documents"""
    # Verify the user is a ClientPortalUser
    if not isinstance(current_user, ClientPortalUser):
        return redirect(url_for('auth.login'))
    
    # Get shared documents
    documents = Document.query.join(
        Document.shared_with).filter(
        ClientPortalUser.id == current_user.id
    ).order_by(Document.created_at.desc()).all()
    
    return render_template('client_portal/documents.html', documents=documents)

@client_portal_bp.route('/documents/<int:document_id>')
@login_required
def view_document(document_id):
    """View a specific shared document"""
    # Verify the user is a ClientPortalUser
    if not isinstance(current_user, ClientPortalUser):
        return redirect(url_for('auth.login'))
    
    # Get the document and check permissions
    document = Document.query.get_or_404(document_id)
    
    # Check if the document is shared with the current user
    if current_user not in document.shared_with:
        flash('Access denied. You do not have permission to view this document.', 'danger')
        return redirect(url_for('client_portal_bp.documents'))
    
    return render_template('client_portal/view_document.html', document=document)

@client_portal_bp.route('/cases')
@login_required
def cases():
    """View all associated cases"""
    # Verify the user is a ClientPortalUser
    if not isinstance(current_user, ClientPortalUser):
        return redirect(url_for('auth.login'))
    
    # Get client details
    client = Client.query.get(current_user.client_id)
    
    # Get cases associated with this client
    cases = Case.query.join(
        Case.clients).filter(
        Client.id == client.id
    ).order_by(Case.next_court_date.asc()).all()
    
    return render_template('client_portal/cases.html', cases=cases)

@client_portal_bp.route('/cases/<int:case_id>')
@login_required
def view_case(case_id):
    """View a specific case"""
    # Verify the user is a ClientPortalUser
    if not isinstance(current_user, ClientPortalUser):
        return redirect(url_for('auth.login'))
    
    # Get the case and check permissions
    case = Case.query.get_or_404(case_id)
    
    # Get client details
    client = Client.query.get(current_user.client_id)
    
    # Check if the case is associated with the client
    if client not in case.clients:
        flash('Access denied. You do not have permission to view this case.', 'danger')
        return redirect(url_for('client_portal_bp.cases'))
    
    # Get documents related to this case and shared with this user
    documents = Document.query.join(
        Document.cases
    ).join(
        Document.shared_with
    ).filter(
        Case.id == case_id,
        ClientPortalUser.id == current_user.id
    ).all()
    
    # Get events for this case
    events = Event.query.filter(
        Event.case_id == case_id
    ).order_by(Event.start_time.asc()).all()
    
    # Get upcoming events
    upcoming_events = Event.query.filter(
        Event.case_id == case_id,
        Event.start_time > datetime.utcnow()
    ).order_by(Event.start_time.asc()).all()
    
    return render_template('client_portal/view_case.html',
                          case=case,
                          documents=documents,
                          events=events,
                          upcoming_events=upcoming_events)

@client_portal_bp.route('/calendar')
@login_required
def calendar():
    """View calendar of events"""
    # Verify the user is a ClientPortalUser
    if not isinstance(current_user, ClientPortalUser):
        return redirect(url_for('auth.login'))
    
    # Get client details
    client = Client.query.get(current_user.client_id)
    
    # Get all events for cases associated with this client
    events = Event.query.join(
        Event.case).join(
        Case.clients).filter(
        Client.id == client.id
    ).order_by(Event.start_time.asc()).all()
    
    # Get upcoming events for the next 30 days
    thirty_days_from_now = datetime.utcnow() + timedelta(days=30)
    upcoming_events = Event.query.join(
        Event.case).join(
        Case.clients).filter(
        Client.id == client.id,
        Event.start_time > datetime.utcnow(),
        Event.start_time <= thirty_days_from_now
    ).order_by(Event.start_time.asc()).all()
    
    return render_template('client_portal/calendar.html',
                          events=events,
                          upcoming_events=upcoming_events)

@client_portal_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """View/edit client profile"""
    # Verify the user is a ClientPortalUser
    if not isinstance(current_user, ClientPortalUser):
        return redirect(url_for('auth.login'))
    
    # Get client details
    client = Client.query.get(current_user.client_id)
    
    # Create a simple form object for rendering
    class SimpleForm:
        def hidden_tag(self):
            csrf_token = request.form.get('csrf_token', '')
            return f'<input type="hidden" name="csrf_token" value="{csrf_token}">'
    
    form = SimpleForm()
    notification_form = SimpleForm()
    
    # Process password change form
    if request.method == 'POST':
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        if password and password != password_confirm:
            flash('Password confirmation does not match.', 'danger')
        elif password:
            current_user.password_hash = generate_password_hash(password)
            db.session.commit()
            flash('Password updated successfully.', 'success')
        else:
            flash('No changes were made.', 'info')
        
        return redirect(url_for('client_portal_bp.profile'))
    
    # Get mock notification preferences (would be from a real model in production)
    notification_preferences = {
        'email_notifications': True,
        'sms_notifications': False,
        'court_date_reminders': True,
        'document_updates': True,
        'phone': client.phone
    }
    
    # Get password last changed date (mock for now)
    password_last_changed = current_user.last_login
    
    # Get recent activities (mock for now)
    activities = [
        {'activity_type': 'Login', 'timestamp': current_user.last_login, 'description': 'Logged in to client portal'}
    ]
    
    return render_template('client_portal/profile.html',
                          form=form,
                          notification_form=notification_form,
                          client=client,
                          notification_preferences=notification_preferences,
                          password_last_changed=password_last_changed,
                          activities=activities)

@client_portal_bp.route('/notification-preferences', methods=['POST'])
@login_required
def notification_preferences():
    """Update notification preferences"""
    # Verify the user is a ClientPortalUser
    if not isinstance(current_user, ClientPortalUser):
        return redirect(url_for('auth.login'))
    
    # Mock handling notification preferences (would save to a real model in production)
    flash('Notification preferences updated successfully.', 'success')
    return redirect(url_for('client_portal_bp.profile'))

@client_portal_bp.route('/generate-token', methods=['POST'])
@login_required
def generate_token():
    """Generate a new access token for secure document sharing"""
    # Verify the user is a ClientPortalUser
    if not isinstance(current_user, ClientPortalUser):
        return redirect(url_for('auth.login'))
    
    # Generate a new token
    current_user.generate_access_token()
    db.session.commit()
    
    flash('New access token generated successfully.', 'success')
    return redirect(url_for('client_portal_bp.profile'))

@client_portal_bp.route('/cases/<int:case_id>/milestones')
@login_required
def case_milestones(case_id):
    """View milestones for a specific case"""
    # Verify the user is a ClientPortalUser
    if not isinstance(current_user, ClientPortalUser):
        return redirect(url_for('auth.login'))
    
    # Get the case and check permissions
    case = Case.query.get_or_404(case_id)
    
    # Get client details
    client = Client.query.get(current_user.client_id)
    
    # Check if the case is associated with the client
    if client not in case.clients:
        flash('Access denied. You do not have permission to view this case.', 'danger')
        return redirect(url_for('client_portal_bp.cases'))
    
    # Get milestones for this case ordered by order_index
    milestones = CaseMilestone.query.filter_by(case_id=case_id).order_by(CaseMilestone.order_index).all()
    
    return render_template('client_portal/milestones.html',
                          case=case,
                          milestones=milestones,
                          title=f"Milestones for {case.title}")

@client_portal_bp.route('/cases/<int:case_id>/timeline')
@login_required
def case_timeline(case_id):
    """View timeline for a specific case"""
    # Verify the user is a ClientPortalUser
    if not isinstance(current_user, ClientPortalUser):
        return redirect(url_for('auth.login'))
    
    # Get the case and check permissions
    case = Case.query.get_or_404(case_id)
    
    # Get client details
    client = Client.query.get(current_user.client_id)
    
    # Check if the case is associated with the client
    if client not in case.clients:
        flash('Access denied. You do not have permission to view this case.', 'danger')
        return redirect(url_for('client_portal_bp.cases'))
    
    # Get milestones for this case ordered by order_index
    milestones = CaseMilestone.query.filter_by(case_id=case_id).order_by(CaseMilestone.order_index).all()
    
    # Get events for this case
    events = Event.query.filter_by(case_id=case_id).order_by(Event.start_time).all()
    
    return render_template('client_portal/timeline.html',
                          case=case,
                          milestones=milestones,
                          events=events,
                          title=f"Timeline for {case.title}")

@client_portal_bp.route('/api/case/<int:case_id>/milestone_stats')
@login_required
def milestone_stats(case_id):
    """Return milestone statistics for a case in JSON format"""
    # Verify the user is a ClientPortalUser
    if not isinstance(current_user, ClientPortalUser):
        return jsonify({"error": "Authentication required"}), 401
    
    # Get the case
    case = Case.query.get_or_404(case_id)
    
    # Get client details
    client = Client.query.get(current_user.client_id)
    
    # Check if the case is associated with the client
    if client not in case.clients:
        return jsonify({"error": "Permission denied"}), 403
    
    # Get milestone data
    milestones = CaseMilestone.query.filter_by(case_id=case_id).all()
    
    # Calculate statistics
    total_count = len(milestones)
    completed_count = sum(1 for m in milestones if m.status == 'completed')
    in_progress_count = sum(1 for m in milestones if m.status == 'in_progress')
    pending_count = sum(1 for m in milestones if m.status == 'pending')
    delayed_count = sum(1 for m in milestones if hasattr(m, 'is_delayed') and m.is_delayed())
    critical_count = sum(1 for m in milestones if m.is_critical)
    
    # Prepare milestone data for timeline
    timeline_data = []
    for milestone in milestones:
        milestone_data = {
            'id': milestone.id,
            'title': milestone.title,
            'type': milestone.milestone_type,
            'status': milestone.status,
            'target_date': milestone.target_date.isoformat() if milestone.target_date else None,
            'completion_date': milestone.completion_date.isoformat() if milestone.completion_date else None,
            'is_critical': milestone.is_critical,
            'is_delayed': milestone.is_delayed() if hasattr(milestone, 'is_delayed') else False,
            'days_remaining': milestone.days_remaining() if hasattr(milestone, 'days_remaining') else None,
            'order_index': milestone.order_index
        }
        timeline_data.append(milestone_data)
    
    return jsonify({
        'total_count': total_count,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'pending_count': pending_count,
        'delayed_count': delayed_count,
        'critical_count': critical_count,
        'timeline_data': timeline_data,
        'completion_percentage': round((completed_count / total_count) * 100) if total_count > 0 else 0
    })

@client_portal_bp.route('/secure-document/<token>/<int:document_id>')
def secure_document(token, document_id):
    """Access a document with a secure token (no login required)"""
    # Find the user with the given token
    user = ClientPortalUser.query.filter_by(access_token=token).first()
    
    if not user or not user.is_token_valid():
        flash('Invalid or expired access token.', 'danger')
        return redirect(url_for('client_portal_bp.login'))
    
    # Get the document
    document = Document.query.get_or_404(document_id)
    
    # Check if the document is shared with the user
    if user not in document.shared_with:
        flash('Access denied. You do not have permission to view this document.', 'danger')
        return redirect(url_for('client_portal_bp.login'))
    
    # Log this access
    # In a real implementation, you would log this access for audit purposes
    
    return render_template('client_portal/view_document.html', document=document, secure_access=True)