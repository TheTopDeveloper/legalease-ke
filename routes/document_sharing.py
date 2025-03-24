"""
Routes for document sharing functionality, allowing lawyers to share documents with clients.
"""
import os
import logging
import secrets
import string
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc, or_, and_

from app import db
from models import Client, ClientPortalUser, Document, Case
from utils.permissions import has_permission, Permissions
from utils.notification_service import NotificationService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create notification service
notification_service = NotificationService()

# Create Blueprint
document_sharing_bp = Blueprint('document_sharing', __name__, url_prefix='/document-sharing')

# Document sharing management page
@document_sharing_bp.route('/')
@login_required
@has_permission(Permissions.VIEW_DOCUMENT)
def index():
    """Document sharing management dashboard"""
    # Get clients with portal access
    clients_with_access = Client.query.filter_by(has_portal_access=True).all()
    
    # Get all clients
    clients = Client.query.all()
    
    # Get shared documents
    shared_docs = Document.query.filter(Document.shared_with.any()).all()
    
    return render_template('document_sharing/index.html', 
                          clients_with_access=clients_with_access,
                          clients=clients,
                          shared_docs=shared_docs)

# Manage client portal access
@document_sharing_bp.route('/client/<int:client_id>', methods=['GET', 'POST'])
@login_required
@has_permission(Permissions.EDIT_CLIENT)
def manage_client_access(client_id):
    """Manage client portal access"""
    client = Client.query.get_or_404(client_id)
    
    if request.method == 'POST':
        # Enable/disable portal access
        enable_access = request.form.get('enable_access') == 'on'
        
        if enable_access and not client.has_portal_access:
            # Get email and generate password
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not email or not password:
                flash('Email and password are required to enable portal access', 'error')
                return redirect(url_for('document_sharing.manage_client_access', client_id=client.id))
            
            # Create portal user
            portal_user = client.create_portal_user(email, password)
            db.session.commit()
            
            # Generate access token for secure links
            token = portal_user.generate_access_token()
            db.session.commit()
            
            # Send notification if client has a phone number
            if client.phone:
                notification_service.send_sms(
                    client.phone,
                    f"Welcome to the client portal! Your account has been created. "
                    f"Login at {url_for('client_portal.login', _external=True)} with "
                    f"email: {email}"
                )
            
            flash('Client portal access enabled successfully', 'success')
            
        elif not enable_access and client.has_portal_access:
            # Disable portal access
            client.has_portal_access = False
            
            # Delete portal users
            ClientPortalUser.query.filter_by(client_id=client.id).delete()
            
            db.session.commit()
            flash('Client portal access disabled', 'success')
            
        return redirect(url_for('document_sharing.manage_client_access', client_id=client.id))
    
    # Get client portal users
    portal_users = ClientPortalUser.query.filter_by(client_id=client.id).all()
    
    # Get cases for this client
    cases = client.cases
    
    # Get shared documents for this client
    shared_docs = []
    for portal_user in portal_users:
        shared_docs.extend(portal_user.shared_documents)
    
    # Remove duplicates
    shared_docs = list(set(shared_docs))
    
    return render_template('document_sharing/manage_client.html',
                          client=client,
                          portal_users=portal_users,
                          cases=cases,
                          shared_docs=shared_docs)

# Create portal user for client
@document_sharing_bp.route('/client/<int:client_id>/add-user', methods=['POST'])
@login_required
@has_permission(Permissions.EDIT_CLIENT)
def add_portal_user(client_id):
    """Add a portal user for a client"""
    client = Client.query.get_or_404(client_id)
    
    # Get user details
    email = request.form.get('email')
    password = request.form.get('password')
    
    if not email or not password:
        flash('Email and password are required', 'error')
        return redirect(url_for('document_sharing.manage_client_access', client_id=client.id))
    
    # Check if client has portal access
    if not client.has_portal_access:
        client.has_portal_access = True
    
    # Check if portal user already exists
    existing_user = ClientPortalUser.query.filter_by(email=email, client_id=client.id).first()
    if existing_user:
        flash(f'Portal user with email {email} already exists', 'error')
        return redirect(url_for('document_sharing.manage_client_access', client_id=client.id))
    
    # Create portal user
    portal_user = ClientPortalUser(
        email=email,
        client_id=client.id,
        is_active=True
    )
    portal_user.set_password(password)
    
    # Generate access token
    portal_user.generate_access_token()
    
    db.session.add(portal_user)
    db.session.commit()
    
    flash('Portal user added successfully', 'success')
    return redirect(url_for('document_sharing.manage_client_access', client_id=client.id))

# Delete portal user
@document_sharing_bp.route('/client/user/<int:user_id>/delete', methods=['POST'])
@login_required
@has_permission(Permissions.EDIT_CLIENT)
def delete_portal_user(user_id):
    """Delete a portal user"""
    portal_user = ClientPortalUser.query.get_or_404(user_id)
    client_id = portal_user.client_id
    
    db.session.delete(portal_user)
    
    # Check if there are any portal users left for this client
    remaining_users = ClientPortalUser.query.filter_by(client_id=client_id).count()
    if remaining_users == 0:
        # Disable portal access for client
        client = Client.query.get(client_id)
        if client:
            client.has_portal_access = False
    
    db.session.commit()
    
    flash('Portal user deleted successfully', 'success')
    return redirect(url_for('document_sharing.manage_client_access', client_id=client_id))

# Share a document
@document_sharing_bp.route('/share-document', methods=['POST'])
@login_required
@has_permission(Permissions.EDIT_DOCUMENT)
def share_document():
    """Share a document with a client"""
    document_id = request.form.get('document_id')
    client_id = request.form.get('client_id')
    
    if not document_id or not client_id:
        flash('Document and client are required', 'error')
        return redirect(url_for('document_sharing.index'))
    
    document = Document.query.get_or_404(document_id)
    client = Client.query.get_or_404(client_id)
    
    # Check that client has portal access
    if not client.has_portal_access:
        flash('Client does not have portal access', 'error')
        return redirect(url_for('document_sharing.manage_client_access', client_id=client.id))
    
    # Get all portal users for this client
    portal_users = ClientPortalUser.query.filter_by(client_id=client.id).all()
    
    # Share with all portal users
    for portal_user in portal_users:
        if document not in portal_user.shared_documents:
            portal_user.shared_documents.append(document)
    
    db.session.commit()
    
    # Send notification if client has a phone number
    if client.phone:
        notification_service.send_sms(
            client.phone,
            f"A new document has been shared with you: {document.title}. "
            f"Login to your client portal to view it."
        )
    
    flash(f'Document "{document.title}" shared with {client.name}', 'success')
    
    # Redirect back to previous page
    next_page = request.form.get('next') or url_for('document_sharing.index')
    return redirect(next_page)

# Unshare a document
@document_sharing_bp.route('/unshare-document', methods=['POST'])
@login_required
@has_permission(Permissions.EDIT_DOCUMENT)
def unshare_document():
    """Unshare a document with a client"""
    document_id = request.form.get('document_id')
    client_id = request.form.get('client_id')
    
    if not document_id or not client_id:
        flash('Document and client are required', 'error')
        return redirect(url_for('document_sharing.index'))
    
    document = Document.query.get_or_404(document_id)
    client = Client.query.get_or_404(client_id)
    
    # Get all portal users for this client
    portal_users = ClientPortalUser.query.filter_by(client_id=client.id).all()
    
    # Unshare with all portal users
    for portal_user in portal_users:
        if document in portal_user.shared_documents:
            portal_user.shared_documents.remove(document)
    
    db.session.commit()
    
    flash(f'Document "{document.title}" unshared with {client.name}', 'success')
    
    # Redirect back to previous page
    next_page = request.form.get('next') or url_for('document_sharing.index')
    return redirect(next_page)

# Share multiple documents with a client
@document_sharing_bp.route('/share-multiple', methods=['POST'])
@login_required
@has_permission(Permissions.EDIT_DOCUMENT)
def share_multiple_documents():
    """Share multiple documents with a client"""
    document_ids = request.form.getlist('document_ids')
    client_id = request.form.get('client_id')
    
    if not document_ids or not client_id:
        flash('Documents and client are required', 'error')
        return redirect(url_for('document_sharing.index'))
    
    client = Client.query.get_or_404(client_id)
    
    # Check that client has portal access
    if not client.has_portal_access:
        flash('Client does not have portal access', 'error')
        return redirect(url_for('document_sharing.manage_client_access', client_id=client.id))
    
    # Get all portal users for this client
    portal_users = ClientPortalUser.query.filter_by(client_id=client.id).all()
    
    # Share documents with all portal users
    shared_count = 0
    for document_id in document_ids:
        document = Document.query.get(document_id)
        if document:
            for portal_user in portal_users:
                if document not in portal_user.shared_documents:
                    portal_user.shared_documents.append(document)
            shared_count += 1
    
    db.session.commit()
    
    # Send notification if client has a phone number
    if client.phone and shared_count > 0:
        notification_service.send_sms(
            client.phone,
            f"{shared_count} new documents have been shared with you. "
            f"Login to your client portal to view them."
        )
    
    flash(f'{shared_count} documents shared with {client.name}', 'success')
    
    # Redirect back to previous page
    next_page = request.form.get('next') or url_for('document_sharing.index')
    return redirect(next_page)

# Generate secure link for a document
@document_sharing_bp.route('/generate-secure-link', methods=['POST'])
@login_required
@has_permission(Permissions.EDIT_DOCUMENT)
def generate_secure_link():
    """Generate a secure link for a document"""
    document_id = request.form.get('document_id')
    client_id = request.form.get('client_id')
    
    if not document_id or not client_id:
        flash('Document and client are required', 'error')
        return redirect(url_for('document_sharing.index'))
    
    document = Document.query.get_or_404(document_id)
    client = Client.query.get_or_404(client_id)
    
    # Check that client has portal access
    if not client.has_portal_access:
        flash('Client does not have portal access', 'error')
        return redirect(url_for('document_sharing.manage_client_access', client_id=client.id))
    
    # Get first portal user for this client
    portal_user = ClientPortalUser.query.filter_by(client_id=client.id).first()
    
    if not portal_user:
        flash('No portal user found for this client', 'error')
        return redirect(url_for('document_sharing.manage_client_access', client_id=client.id))
    
    # Share document with portal user if not already shared
    if document not in portal_user.shared_documents:
        portal_user.shared_documents.append(document)
    
    # Generate or refresh access token
    token = portal_user.generate_access_token()
    
    db.session.commit()
    
    # Generate secure link
    secure_link = url_for('client_portal.secure_document', 
                         token=token, 
                         document_id=document.id,
                         _external=True)
    
    # Just return the secure link
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'secure_link': secure_link})
    
    # Otherwise store in session for template to display
    session = {}
    session['secure_link'] = secure_link
    session['secure_link_expires'] = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    flash('Secure link generated successfully', 'success')
    
    # Redirect back to previous page
    next_page = request.form.get('next') or url_for('document_sharing.index')
    return redirect(next_page)