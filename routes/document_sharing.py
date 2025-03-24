"""
Routes for document sharing functionality, allowing legal professionals to share documents with clients.
"""

from datetime import datetime, timedelta
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import and_
from app import db
from utils.permissions import Permissions, has_permission
from utils.notification_service import NotificationService
from models import Document, ClientPortalUser, Client

# Initialize service
notification_service = NotificationService()

document_sharing_bp = Blueprint('document_sharing', __name__, url_prefix='/documents/sharing')

@document_sharing_bp.route('/')
@login_required
@has_permission(Permissions.VIEW_DOCUMENT)
def index():
    """Document sharing dashboard"""
    # Get documents shared by the current user
    shared_documents = Document.query.filter(
        Document.created_by_id == current_user.id,
        Document.shared_with.any()
    ).order_by(Document.created_at.desc()).all()
    
    # Get all client portal users
    client_portal_users = ClientPortalUser.query.all()
    
    # Get all clients
    clients = Client.query.all()
    
    return render_template('document_sharing/index.html',
                          shared_documents=shared_documents,
                          client_portal_users=client_portal_users,
                          clients=clients)

@document_sharing_bp.route('/share/<int:document_id>', methods=['GET', 'POST'])
@login_required
@has_permission(Permissions.VIEW_DOCUMENT)
def share_document(document_id):
    """Share a document with client portal users"""
    document = Document.query.get_or_404(document_id)
    
    # Check if the user has permission to share this document
    if document.created_by_id != current_user.id and not current_user.has_permission(Permissions.ADMIN_ACCESS):
        flash('You do not have permission to share this document.', 'danger')
        return redirect(url_for('documents.view', document_id=document_id))
    
    # Get all clients
    clients = Client.query.all()
    
    # Get all client portal users
    client_portal_users = ClientPortalUser.query.all()
    
    if request.method == 'POST':
        # Get the selected client portal users
        selected_user_ids = request.form.getlist('client_portal_users')
        
        # Clear current sharing
        document.shared_with = []
        
        # Add selected users
        for user_id in selected_user_ids:
            user = ClientPortalUser.query.get(int(user_id))
            if user:
                document.shared_with.append(user)
                
                # Send notification to user
                try:
                    notification_service.client_document_shared(
                        user, 
                        document, 
                        shared_by=current_user
                    )
                except Exception as e:
                    flash(f'Document shared but notification failed: {str(e)}', 'warning')
        
        db.session.commit()
        flash('Document sharing updated successfully.', 'success')
        return redirect(url_for('document_sharing.index'))
    
    return render_template('document_sharing/share_document.html',
                          document=document,
                          clients=clients,
                          client_portal_users=client_portal_users)

@document_sharing_bp.route('/client/<int:client_id>/users')
@login_required
@has_permission(Permissions.VIEW_CLIENT)
def get_client_users(client_id):
    """Get client portal users for a specific client (AJAX)"""
    client = Client.query.get_or_404(client_id)
    users = ClientPortalUser.query.filter_by(client_id=client_id).all()
    
    users_data = [{'id': user.id, 'email': user.email} for user in users]
    return {'users': users_data}

@document_sharing_bp.route('/create-portal-user/<int:client_id>', methods=['GET', 'POST'])
@login_required
@has_permission(Permissions.EDIT_CLIENT)
def create_portal_user(client_id):
    """Create a new portal user for a client"""
    client = Client.query.get_or_404(client_id)
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return redirect(url_for('document_sharing.create_portal_user', client_id=client_id))
        
        # Check if email is already used
        existing_user = ClientPortalUser.query.filter_by(email=email).first()
        if existing_user:
            flash('A user with this email already exists.', 'danger')
            return redirect(url_for('document_sharing.create_portal_user', client_id=client_id))
        
        # Create portal user
        try:
            portal_user = client.create_portal_user(email, password)
            
            # Send welcome notification
            try:
                notification_service.client_portal_welcome(
                    portal_user, 
                    created_by=current_user
                )
            except Exception as e:
                flash(f'Portal user created but welcome notification failed: {str(e)}', 'warning')
                
            flash('Portal user created successfully.', 'success')
            return redirect(url_for('document_sharing.index'))
        except Exception as e:
            flash(f'Error creating portal user: {str(e)}', 'danger')
    
    return render_template('document_sharing/create_portal_user.html', client=client)

@document_sharing_bp.route('/manage-portal-users/<int:client_id>')
@login_required
@has_permission(Permissions.VIEW_CLIENT)
def manage_portal_users(client_id):
    """Manage portal users for a client"""
    client = Client.query.get_or_404(client_id)
    portal_users = ClientPortalUser.query.filter_by(client_id=client_id).all()
    
    return render_template('document_sharing/manage_portal_users.html',
                          client=client,
                          portal_users=portal_users)

@document_sharing_bp.route('/delete-portal-user/<int:user_id>', methods=['POST'])
@login_required
@has_permission(Permissions.EDIT_CLIENT)
def delete_portal_user(user_id):
    """Delete a portal user"""
    user = ClientPortalUser.query.get_or_404(user_id)
    client_id = user.client_id
    
    # Remove shared documents
    user.shared_with = []
    
    # Delete the user
    db.session.delete(user)
    db.session.commit()
    
    flash('Portal user deleted successfully.', 'success')
    return redirect(url_for('document_sharing.manage_portal_users', client_id=client_id))

@document_sharing_bp.route('/reset-token/<int:user_id>', methods=['POST'])
@login_required
@has_permission(Permissions.EDIT_CLIENT)
def reset_token(user_id):
    """Reset a portal user's access token"""
    user = ClientPortalUser.query.get_or_404(user_id)
    
    # Generate new token
    user.generate_access_token()
    db.session.commit()
    
    flash('Access token reset successfully.', 'success')
    return redirect(url_for('document_sharing.manage_portal_users', client_id=user.client_id))

@document_sharing_bp.route('/reset-password/<int:user_id>', methods=['GET', 'POST'])
@login_required
@has_permission(Permissions.EDIT_CLIENT)
def reset_password(user_id):
    """Reset a portal user's password"""
    user = ClientPortalUser.query.get_or_404(user_id)
    
    if request.method == 'POST':
        password = request.form.get('password')
        
        if not password:
            flash('Password is required.', 'danger')
            return redirect(url_for('document_sharing.reset_password', user_id=user_id))
        
        # Update password
        user.set_password(password)
        db.session.commit()
        
        # Send notification about password reset
        try:
            notification_service.client_password_reset(
                user, 
                reset_by=current_user
            )
        except Exception as e:
            flash(f'Password reset but notification failed: {str(e)}', 'warning')
            
        flash('Password reset successfully.', 'success')
        return redirect(url_for('document_sharing.manage_portal_users', client_id=user.client_id))
    
    return render_template('document_sharing/reset_password.html', user=user)