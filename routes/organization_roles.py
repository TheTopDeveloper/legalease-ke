"""
Routes for organization role management, allowing organization owners to assign roles to members.
"""
import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import current_user, login_required
from sqlalchemy import desc

from models import db, User, Role, Permission, Organization
from utils.permissions import has_permission, Permissions

logger = logging.getLogger(__name__)

# Create organization roles blueprint
org_roles_bp = Blueprint('org_roles', __name__, url_prefix='/organization/roles')

@org_roles_bp.route('/')
@login_required
@has_permission(Permissions.VIEW_USERS)
def index():
    """View organization roles and members"""
    # Check if user has an active organization
    if not current_user.active_organization:
        flash("You need to select an active organization first", "warning")
        return redirect(url_for('dashboard.index'))
    
    # Get organization members
    organization = current_user.active_organization
    members = organization.members
    roles = Role.query.filter_by(is_default=False).all()  # Get non-default roles
    
    return render_template('organization/roles.html', 
                          organization=organization,
                          members=members,
                          roles=roles)

@org_roles_bp.route('/assign/<int:user_id>', methods=['GET', 'POST'])
@login_required
@has_permission(Permissions.ASSIGN_ROLE)
def assign_role(user_id):
    """Assign a role to an organization member"""
    # Check if user has an active organization
    if not current_user.active_organization:
        flash("You need to select an active organization first", "warning")
        return redirect(url_for('dashboard.index'))
    
    # Check if user is organization owner
    organization = current_user.active_organization
    if not current_user.is_admin() and not current_user.is_organization_owner():
        flash("Only organization owners can assign roles", "error")
        return redirect(url_for('org_roles.index'))
    
    # Get the user to assign role to
    user = User.query.get_or_404(user_id)
    
    # Check if user is a member of the organization
    if user not in organization.members:
        flash("User is not a member of this organization", "error")
        return redirect(url_for('org_roles.index'))
    
    # Get available roles
    roles = Role.query.filter_by(is_default=False).all()
    
    if request.method == 'POST':
        role_id = request.form.get('role_id')
        
        if role_id:
            # Set the user's custom role
            try:
                user.custom_role_id = int(role_id)
                db.session.commit()
                flash(f"Role assigned to {user.username} successfully", "success")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error assigning role: {str(e)}")
                flash(f"Error assigning role: {str(e)}", "error")
        else:
            # Remove custom role
            user.custom_role_id = None
            db.session.commit()
            flash(f"Custom role removed from {user.username}", "success")
            
        return redirect(url_for('org_roles.index'))
    
    return render_template('organization/assign_role.html',
                          user=user,
                          organization=organization,
                          roles=roles)

@org_roles_bp.route('/revoke/<int:user_id>', methods=['POST'])
@login_required
@has_permission(Permissions.ASSIGN_ROLE)
def revoke_role(user_id):
    """Revoke a custom role from an organization member"""
    # Check if user has an active organization
    if not current_user.active_organization:
        flash("You need to select an active organization first", "warning")
        return redirect(url_for('dashboard.index'))
    
    # Check if user is organization owner
    organization = current_user.active_organization
    if not current_user.is_admin() and not current_user.is_organization_owner():
        flash("Only organization owners can revoke roles", "error")
        return redirect(url_for('org_roles.index'))
    
    # Get the user to revoke role from
    user = User.query.get_or_404(user_id)
    
    # Check if user is a member of the organization
    if user not in organization.members:
        flash("User is not a member of this organization", "error")
        return redirect(url_for('org_roles.index'))
    
    # Remove custom role
    user.custom_role_id = None
    db.session.commit()
    flash(f"Custom role removed from {user.username}", "success")
    
    return redirect(url_for('org_roles.index'))