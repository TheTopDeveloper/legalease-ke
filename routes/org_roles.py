"""
Routes for organization role management.
Allows organization owners to assign roles to members within their organization.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from sqlalchemy import select

from app import db
from models import User, Organization, Role, Permission
from utils.permissions import Permissions, has_permission

# Create blueprint
org_roles = Blueprint('org_roles', __name__)

@org_roles.route('/organization/roles')
@login_required
def index():
    """View organization roles and members"""
    # Check if user has active organization
    if not current_user.active_organization:
        flash("You need to select an active organization first.", "warning")
        return redirect(url_for('dashboard.index'))
    
    # Get the active organization
    organization = current_user.active_organization
    
    # Check permissions (only organization owners or admins can manage roles)
    if not (current_user.is_organization_owner() or current_user.is_admin()):
        flash("You don't have permission to manage organization roles.", "danger")
        return redirect(url_for('dashboard.index'))
    
    # Get all members of the organization
    members = organization.members
    
    # Get all available custom roles
    roles = db.session.scalars(select(Role).where(Role.is_custom == True)).all()
    
    return render_template(
        'organization/roles.html',
        organization=organization,
        members=members,
        roles=roles
    )

@org_roles.route('/organization/roles/assign/<int:user_id>', methods=['GET', 'POST'])
@login_required
def assign_role(user_id):
    """Assign a role to an organization member"""
    # Check if user has active organization
    if not current_user.active_organization:
        flash("You need to select an active organization first.", "warning")
        return redirect(url_for('dashboard.index'))
    
    # Get the active organization
    organization = current_user.active_organization
    
    # Check permissions (only organization owners or admins can assign roles)
    if not (current_user.is_organization_owner() or current_user.is_admin()):
        flash("You don't have permission to assign roles.", "danger")
        return redirect(url_for('org_roles.index'))
    
    # Get the user to assign role to
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('org_roles.index'))
    
    # Check if user is a member of the organization
    if user not in organization.members:
        flash("User is not a member of this organization.", "danger")
        return redirect(url_for('org_roles.index'))
    
    # Get all available custom roles
    roles = db.session.scalars(select(Role).where(Role.is_custom == True)).all()
    
    if request.method == 'POST':
        role_id = request.form.get('role_id', '')
        
        # If empty, remove custom role
        if not role_id:
            user.custom_role_id = None
            db.session.commit()
            flash(f"Custom role removed from {user.get_full_name()}.", "success")
            return redirect(url_for('org_roles.index'))
        
        # Otherwise, assign the role
        role = db.session.get(Role, role_id)
        if not role:
            flash("Role not found.", "danger")
            return redirect(url_for('org_roles.assign_role', user_id=user.id))
        
        user.custom_role_id = role.id
        db.session.commit()
        
        flash(f"Role '{role.name}' assigned to {user.get_full_name()}.", "success")
        return redirect(url_for('org_roles.index'))
    
    return render_template(
        'organization/assign_role.html',
        organization=organization,
        user=user,
        roles=roles
    )

@org_roles.route('/organization/roles/revoke/<int:user_id>', methods=['POST'])
@login_required
def revoke_role(user_id):
    """Revoke a custom role from an organization member"""
    # Check if user has active organization
    if not current_user.active_organization:
        flash("You need to select an active organization first.", "warning")
        return redirect(url_for('dashboard.index'))
    
    # Get the active organization
    organization = current_user.active_organization
    
    # Check permissions (only organization owners or admins can revoke roles)
    if not (current_user.is_organization_owner() or current_user.is_admin()):
        flash("You don't have permission to revoke roles.", "danger")
        return redirect(url_for('org_roles.index'))
    
    # Get the user to revoke role from
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('org_roles.index'))
    
    # Check if user is a member of the organization
    if user not in organization.members:
        flash("User is not a member of this organization.", "danger")
        return redirect(url_for('org_roles.index'))
    
    # Check if user has a custom role
    if not user.custom_role_id:
        flash("User doesn't have a custom role assigned.", "warning")
        return redirect(url_for('org_roles.index'))
    
    # Store the role name for the flash message
    role_name = user.custom_role.name
    
    # Remove the custom role
    user.custom_role_id = None
    db.session.commit()
    
    flash(f"Role '{role_name}' revoked from {user.get_full_name()}.", "success")
    return redirect(url_for('org_roles.index'))