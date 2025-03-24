"""
Routes for document sharing functionality, allowing lawyers to share documents with clients.
"""
from datetime import datetime, timedelta
import secrets
import logging

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import SQLAlchemyError

from models import db, Document, Client, ClientPortalUser
from utils.permissions import has_permission, Permissions

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
document_sharing_bp = Blueprint('document_sharing', __name__, url_prefix='/documents/sharing')

@document_sharing_bp.route('/')
@login_required
@has_permission(Permissions.VIEW_DOCUMENT)
def index():
    """Document sharing dashboard"""
    try:
        # Get shared documents
        shared_documents = Document.query.filter(
            Document.created_by_id == current_user.id,
            Document.shared_with.any()
        ).all()
        
        # Get clients with their portal users
        clients = Client.query.order_by(Client.name).all()
        
        return render_template('document_sharing/index.html', 
                              shared_documents=shared_documents,
                              clients=clients)
    except SQLAlchemyError as e:
        logger.error(f"Database error in document sharing index: {e}")
        flash('An error occurred while loading document sharing data.', 'danger')
        return redirect(url_for('dashboard.index'))

@document_sharing_bp.route('/document/<int:document_id>', methods=['GET', 'POST'])
@login_required
@has_permission(Permissions.VIEW_DOCUMENT)
def share_document(document_id):
    """Share a document with client portal users"""
    try:
        document = Document.query.get_or_404(document_id)
        
        # Verify ownership or admin access
        if document.created_by_id != current_user.id and not current_user.is_admin():
            flash('You do not have permission to share this document.', 'danger')
            return redirect(url_for('documents.index'))
        
        # Get clients
        clients = Client.query.filter(Client.has_portal_access == True).order_by(Client.name).all()
        
        # Handle form submission
        if request.method == 'POST':
            portal_user_ids = request.form.getlist('client_portal_users')
            
            if not portal_user_ids:
                flash('Please select at least one portal user to share with.', 'warning')
                return redirect(url_for('document_sharing.share_document', document_id=document_id))
            
            # Get selected users
            portal_users = ClientPortalUser.query.filter(ClientPortalUser.id.in_(portal_user_ids)).all()
            
            # Share document with selected users
            for user in portal_users:
                if document not in user.shared_documents:
                    user.shared_documents.append(document)
            
            db.session.commit()
            
            flash(f'Document "{document.title}" has been shared with {len(portal_users)} portal users.', 'success')
            return redirect(url_for('document_sharing.index'))
        
        return render_template('document_sharing/share_document.html', 
                               document=document,
                               clients=clients)
    except SQLAlchemyError as e:
        logger.error(f"Database error in share document: {e}")
        db.session.rollback()
        flash('An error occurred while sharing the document.', 'danger')
        return redirect(url_for('documents.index'))

@document_sharing_bp.route('/client/<int:client_id>/users')
@login_required
@has_permission(Permissions.VIEW_CLIENT)
def get_client_portal_users(client_id):
    """Get portal users for a client (AJAX endpoint)"""
    try:
        client = Client.query.get_or_404(client_id)
        portal_users = client.portal_users.all()
        
        users_data = [{'id': user.id, 'email': user.email} for user in portal_users]
        
        return jsonify({'users': users_data})
    except Exception as e:
        logger.error(f"Error getting client portal users: {e}")
        return jsonify({'error': 'An error occurred while retrieving portal users'}), 500

@document_sharing_bp.route('/create-portal-user/<int:client_id>', methods=['GET', 'POST'])
@login_required
@has_permission(Permissions.EDIT_CLIENT)
def create_portal_user(client_id):
    """Create a new portal user for a client"""
    try:
        client = Client.query.get_or_404(client_id)
        
        # Handle form submission
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            send_notification = 'send_notification' in request.form
            
            # Validate input
            if not email or not password:
                flash('Email and password are required.', 'danger')
                return redirect(url_for('document_sharing.create_portal_user', client_id=client_id))
            
            # Check if user already exists
            existing_user = ClientPortalUser.query.filter_by(email=email).first()
            if existing_user:
                flash('A portal user with this email already exists.', 'danger')
                return redirect(url_for('document_sharing.create_portal_user', client_id=client_id))
            
            # Create new portal user
            new_user = ClientPortalUser(
                email=email,
                password_hash=generate_password_hash(password),
                client_id=client.id
            )
            
            # Generate access token
            new_user.access_token = secrets.token_urlsafe(32)
            new_user.token_expiry = datetime.utcnow() + timedelta(days=30)
            
            # Update client portal access flag
            client.has_portal_access = True
            
            db.session.add(new_user)
            db.session.commit()
            
            # Send notification if requested
            if send_notification:
                # TODO: Implement email notification
                pass
            
            flash(f'Portal user "{email}" created successfully for {client.name}.', 'success')
            return redirect(url_for('document_sharing.manage_portal_users', client_id=client_id))
        
        return render_template('document_sharing/create_portal_user.html', client=client)
    except SQLAlchemyError as e:
        logger.error(f"Database error in create portal user: {e}")
        db.session.rollback()
        flash('An error occurred while creating the portal user.', 'danger')
        return redirect(url_for('document_sharing.index'))

@document_sharing_bp.route('/manage/<int:client_id>')
@login_required
@has_permission(Permissions.EDIT_CLIENT)
def manage_portal_users(client_id):
    """Manage portal users for a client"""
    try:
        client = Client.query.get_or_404(client_id)
        portal_users = client.portal_users.all()
        
        return render_template('document_sharing/manage_portal_users.html', 
                               client=client,
                               portal_users=portal_users)
    except SQLAlchemyError as e:
        logger.error(f"Database error in manage portal users: {e}")
        flash('An error occurred while loading portal users.', 'danger')
        return redirect(url_for('document_sharing.index'))

@document_sharing_bp.route('/reset-password/<int:user_id>', methods=['GET', 'POST'])
@login_required
@has_permission(Permissions.EDIT_CLIENT)
def reset_password(user_id):
    """Reset password for a portal user"""
    try:
        portal_user = ClientPortalUser.query.get_or_404(user_id)
        client = portal_user.client
        
        # Handle form submission
        if request.method == 'POST':
            new_password = request.form.get('new_password')
            send_notification = 'send_notification' in request.form
            
            # Validate input
            if not new_password:
                flash('New password is required.', 'danger')
                return redirect(url_for('document_sharing.reset_password', user_id=user_id))
            
            # Update password
            portal_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            # Send notification if requested
            if send_notification:
                # TODO: Implement email notification
                pass
            
            flash(f'Password for {portal_user.email} has been reset successfully.', 'success')
            return redirect(url_for('document_sharing.manage_portal_users', client_id=client.id))
        
        return render_template('document_sharing/reset_password.html', 
                               portal_user=portal_user,
                               client=client)
    except SQLAlchemyError as e:
        logger.error(f"Database error in reset password: {e}")
        db.session.rollback()
        flash('An error occurred while resetting the password.', 'danger')
        return redirect(url_for('document_sharing.index'))

@document_sharing_bp.route('/reset-token/<int:user_id>', methods=['POST'])
@login_required
@has_permission(Permissions.EDIT_CLIENT)
def reset_token(user_id):
    """Reset access token for a portal user"""
    try:
        portal_user = ClientPortalUser.query.get_or_404(user_id)
        client = portal_user.client
        
        # Generate new token
        portal_user.access_token = secrets.token_urlsafe(32)
        portal_user.token_expiry = datetime.utcnow() + timedelta(days=30)
        db.session.commit()
        
        flash(f'Access token for {portal_user.email} has been reset successfully.', 'success')
        return redirect(url_for('document_sharing.manage_portal_users', client_id=client.id))
    except SQLAlchemyError as e:
        logger.error(f"Database error in reset token: {e}")
        db.session.rollback()
        flash('An error occurred while resetting the access token.', 'danger')
        return redirect(url_for('document_sharing.index'))

@document_sharing_bp.route('/delete-portal-user/<int:user_id>', methods=['POST'])
@login_required
@has_permission(Permissions.EDIT_CLIENT)
def delete_portal_user(user_id):
    """Delete a portal user"""
    try:
        portal_user = ClientPortalUser.query.get_or_404(user_id)
        client = portal_user.client
        
        db.session.delete(portal_user)
        
        # If this was the last portal user, update client's portal access flag
        if client.portal_users.count() == 0:
            client.has_portal_access = False
        
        db.session.commit()
        
        flash(f'Portal user {portal_user.email} has been deleted successfully.', 'success')
        return redirect(url_for('document_sharing.manage_portal_users', client_id=client.id))
    except SQLAlchemyError as e:
        logger.error(f"Database error in delete portal user: {e}")
        db.session.rollback()
        flash('An error occurred while deleting the portal user.', 'danger')
        return redirect(url_for('document_sharing.index'))

@document_sharing_bp.route('/secure-document/<token>/<int:document_id>')
def secure_document(token, document_id):
    """Access a document with a secure token (no login required)"""
    try:
        document = Document.query.get_or_404(document_id)
        
        # Find portal user with matching token
        portal_user = ClientPortalUser.query.filter_by(access_token=token).first()
        
        # Validate token and access
        if not portal_user or not portal_user.is_token_valid():
            flash('Invalid or expired access token.', 'danger')
            return redirect(url_for('client_portal.login'))
        
        # Check if user has access to this document
        if document not in portal_user.shared_documents:
            flash('You do not have access to this document.', 'danger')
            return redirect(url_for('client_portal.login'))
        
        # Log access
        # TODO: Implement access logging
        
        return render_template('client_portal/view_document.html', 
                               document=document,
                               secure_access=True)
    except SQLAlchemyError as e:
        logger.error(f"Database error in secure document: {e}")
        flash('An error occurred while accessing the document.', 'danger')
        return redirect(url_for('client_portal.login'))