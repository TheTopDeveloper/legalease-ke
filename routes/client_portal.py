"""
Routes for client portal functionality, allowing clients to access shared documents.
"""
import os
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import desc, or_, and_

from app import db, login_manager
from models import Client, ClientPortalUser, Document, Case, Event
from utils.permissions import has_permission, Permissions

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
client_portal_bp = Blueprint('client_portal', __name__, url_prefix='/client-portal')

# Client portal user loader
@login_manager.user_loader
def load_user(user_id):
    """Load user by ID - works for both User and ClientPortalUser"""
    # Try loading as regular user first
    from models import User
    user = User.query.get(int(user_id))
    if user:
        return user
        
    # If not found, try as client portal user
    return ClientPortalUser.query.get(int(user_id))

# Client portal login page
@client_portal_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Client portal login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Find client portal user
        portal_user = ClientPortalUser.query.filter_by(email=email).first()
        
        if portal_user and portal_user.check_password(password):
            # Set client portal session flag
            session['is_client_portal'] = True
            
            # Update last login time
            portal_user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Log in the user
            login_user(portal_user)
            
            # Redirect to client portal dashboard
            flash('Login successful!', 'success')
            return redirect(url_for('client_portal.dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('client_portal/login.html')

# Client portal logout
@client_portal_bp.route('/logout')
def logout():
    """Client portal logout"""
    logout_user()
    
    # Clear client portal session flag
    session.pop('is_client_portal', None)
    
    flash('You have been logged out', 'info')
    return redirect(url_for('client_portal.login'))

# Client portal dashboard
@client_portal_bp.route('/')
@login_required
def dashboard():
    """Client portal dashboard"""
    # Make sure we're logged in as a client portal user
    if not session.get('is_client_portal'):
        flash('You must be logged in as a client to access the client portal', 'error')
        return redirect(url_for('client_portal.login'))
    
    # Get client information
    client = current_user.client
    
    # Get shared documents
    documents = current_user.shared_documents
    
    # Get associated cases
    cases = client.cases
    
    # Get upcoming events
    upcoming_events = []
    for case in cases:
        events = Event.query.filter_by(case_id=case.id).filter(
            Event.start_time > datetime.utcnow()
        ).order_by(Event.start_time).limit(5).all()
        upcoming_events.extend(events)
    
    # Sort events by start time
    upcoming_events.sort(key=lambda x: x.start_time)
    
    return render_template('client_portal/dashboard.html',
                          client=client,
                          documents=documents,
                          cases=cases,
                          upcoming_events=upcoming_events[:5])  # Limit to 5 events

# View shared documents
@client_portal_bp.route('/documents')
@login_required
def documents():
    """View all shared documents"""
    # Make sure we're logged in as a client portal user
    if not session.get('is_client_portal'):
        flash('You must be logged in as a client to access the client portal', 'error')
        return redirect(url_for('client_portal.login'))
    
    # Get shared documents
    documents = current_user.shared_documents
    
    return render_template('client_portal/documents.html', documents=documents)

# View a specific document
@client_portal_bp.route('/documents/<int:document_id>')
@login_required
def view_document(document_id):
    """View a specific shared document"""
    # Make sure we're logged in as a client portal user
    if not session.get('is_client_portal'):
        flash('You must be logged in as a client to access the client portal', 'error')
        return redirect(url_for('client_portal.login'))
    
    # Get document and make sure it's shared with the current user
    document = Document.query.get_or_404(document_id)
    
    if document not in current_user.shared_documents:
        flash('You do not have permission to view this document', 'error')
        return redirect(url_for('client_portal.documents'))
    
    return render_template('client_portal/view_document.html', document=document)

# View cases
@client_portal_bp.route('/cases')
@login_required
def cases():
    """View all associated cases"""
    # Make sure we're logged in as a client portal user
    if not session.get('is_client_portal'):
        flash('You must be logged in as a client to access the client portal', 'error')
        return redirect(url_for('client_portal.login'))
    
    # Get client cases
    cases = current_user.client.cases
    
    return render_template('client_portal/cases.html', cases=cases)

# View a specific case
@client_portal_bp.route('/cases/<int:case_id>')
@login_required
def view_case(case_id):
    """View a specific case"""
    # Make sure we're logged in as a client portal user
    if not session.get('is_client_portal'):
        flash('You must be logged in as a client to access the client portal', 'error')
        return redirect(url_for('client_portal.login'))
    
    # Get case and make sure it's associated with the client
    case = Case.query.get_or_404(case_id)
    
    if current_user.client not in case.clients:
        flash('You do not have permission to view this case', 'error')
        return redirect(url_for('client_portal.cases'))
    
    # Get case events
    events = Event.query.filter_by(case_id=case.id).order_by(Event.start_time).all()
    
    # Get case documents that are shared with the client
    case_documents = [doc for doc in case.documents if doc in current_user.shared_documents]
    
    return render_template('client_portal/view_case.html', 
                          case=case, 
                          events=events,
                          case_documents=case_documents)

# Calendar view
@client_portal_bp.route('/calendar')
@login_required
def calendar():
    """View calendar of events"""
    # Make sure we're logged in as a client portal user
    if not session.get('is_client_portal'):
        flash('You must be logged in as a client to access the client portal', 'error')
        return redirect(url_for('client_portal.login'))
    
    # Get all events for client's cases
    client_cases = current_user.client.cases
    case_ids = [case.id for case in client_cases]
    
    # If no cases, just show empty calendar
    if not case_ids:
        return render_template('client_portal/calendar.html', events=[])
    
    # Get all events for these cases
    events = Event.query.filter(Event.case_id.in_(case_ids)).all()
    
    return render_template('client_portal/calendar.html', events=events)

# Profile view/edit
@client_portal_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """View/edit client profile"""
    # Make sure we're logged in as a client portal user
    if not session.get('is_client_portal'):
        flash('You must be logged in as a client to access the client portal', 'error')
        return redirect(url_for('client_portal.login'))
    
    client = current_user.client
    
    if request.method == 'POST':
        # Update password if provided
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if current_password and new_password and confirm_password:
            # Verify current password
            if current_user.check_password(current_password):
                # Check that new passwords match
                if new_password == confirm_password:
                    # Update password
                    current_user.set_password(new_password)
                    db.session.commit()
                    flash('Password updated successfully', 'success')
                else:
                    flash('New passwords do not match', 'error')
            else:
                flash('Current password is incorrect', 'error')
    
    return render_template('client_portal/profile.html', client=client, portal_user=current_user)

# Secured document access with token
@client_portal_bp.route('/secure-document/<string:token>/<int:document_id>')
def secure_document(token, document_id):
    """Access a document with a secure token (no login required)"""
    # Find portal user with this token
    portal_user = ClientPortalUser.query.filter_by(access_token=token).first()
    
    # Check if token exists and is valid
    if not portal_user or not portal_user.is_token_valid():
        flash('Invalid or expired access token', 'error')
        return redirect(url_for('client_portal.login'))
    
    # Get document
    document = Document.query.get_or_404(document_id)
    
    # Check if document is shared with this user
    if document not in portal_user.shared_documents:
        abort(403)
    
    return render_template('client_portal/secure_document.html', document=document, client=portal_user.client)