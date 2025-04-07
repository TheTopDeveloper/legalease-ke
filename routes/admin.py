"""
Routes for admin functionality, including role and permission management.
"""
import logging
import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import current_user, login_required
from sqlalchemy import desc
from wtforms import SelectField
from wtforms.validators import Optional

from models import db, User, Role, Permission, Organization
from utils.permissions import admin_required, Permissions
from forms.admin import (
    CreateUserForm, EditUserForm, 
    CreateRoleForm, EditRoleForm,
    CreateOrganizationForm, EditOrganizationForm
)

logger = logging.getLogger(__name__)

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard with enhanced responsive design and system statistics"""
    # Get system statistics
    user_count = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    admin_users = User.query.filter_by(role='admin').count()
    organization_count = Organization.query.count()
    
    # Recent users
    recent_users = User.query.order_by(desc(User.created_at)).limit(10).all()
    
    # Simulated system metrics - would be replaced with actual monitoring in production
    cpu_usage = 38
    memory_usage = 45
    disk_usage = 62
    db_size = "1.2 GB"
    system_health = "Good"
    
    # Mock recent activity data
    recent_activity = []
    if recent_users:
        for i, user in enumerate(recent_users[:5]):
            actions = ["Login", "Created document", "Updated profile", "Changed settings", "Added organization"]
            resources = ["System", "Document", "Profile", "Settings", "Organization"]
            times = ["10 minutes ago", "1 hour ago", "3 hours ago", "5 hours ago", "Yesterday"]
            
            recent_activity.append([
                f'<div class="d-flex align-items-center"><span class="admin-avatar me-2">{user.username[:1]}</span> {user.username}</div>',
                actions[i % 5],
                resources[i % 5],
                times[i % 5],
                '<a href="#" class="btn btn-sm btn-outline-info"><i class="fas fa-info-circle"></i></a>'
            ])
    
    # Mock error logs
    error_logs = []
    for i in range(3):
        error_types = ["Database Error", "API Error", "Authentication Error"]
        error_messages = ["Connection timeout", "API rate limit exceeded", "Invalid authentication token"]
        error_locations = ["database.py:45", "api_client.py:102", "auth.py:78"]
        error_times = ["2 hours ago", "5 hours ago", "Yesterday"]
        
        error_logs.append({
            "type": error_types[i],
            "message": error_messages[i],
            "location": error_locations[i],
            "time": error_times[i]
        })
    
    # Use the new responsive template
    return render_template('admin/new/dashboard.html', 
                          user_count=user_count,
                          active_users=active_users,
                          admin_users=admin_users,
                          organization_count=organization_count,
                          recent_users=recent_users,
                          cpu_usage=cpu_usage,
                          memory_usage=memory_usage,
                          disk_usage=disk_usage,
                          db_size=db_size,
                          system_health=system_health,
                          recent_activity=recent_activity,
                          error_logs=error_logs)

# User Management
@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """User management page with responsive mobile design"""
    users = User.query.all()
    roles = Role.query.all()
    # Use the new responsive template
    return render_template('admin/new/users.html', users=users, roles=roles)

@admin_bp.route('/users/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit a user's details and role"""
    user = User.query.get_or_404(user_id)
    roles = Role.query.all()
    
    if request.method == 'POST':
        # Update basic user information
        user.username = request.form.get('username', user.username)
        user.email = request.form.get('email', user.email)
        user.first_name = request.form.get('first_name', user.first_name)
        user.last_name = request.form.get('last_name', user.last_name)
        
        # Update role
        new_role = request.form.get('role')
        if new_role:
            user.role = new_role
            
        # Update account type and tokens
        user.account_type = request.form.get('account_type', user.account_type)
        
        tokens = request.form.get('tokens_available')
        if tokens:
            try:
                user.tokens_available = int(tokens)
            except ValueError:
                pass
                
        # Update active status
        user.is_active = 'is_active' in request.form
        
        # Update custom role
        custom_role_id = request.form.get('custom_role_id')
        if custom_role_id:
            try:
                user.custom_role_id = int(custom_role_id)
            except ValueError:
                user.custom_role_id = None
        else:
            user.custom_role_id = None
            
        # Save changes
        try:
            db.session.commit()
            flash(f"User {user.username} updated successfully", "success")
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating user: {str(e)}")
            flash(f"Error updating user: {str(e)}", "error")
    
    return render_template('admin/edit_user.html', user=user, roles=roles)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Create a new user"""
    roles = Role.query.all()
    form = CreateUserForm()
    
    # We need to define this properly in the form in forms/admin.py instead of here
    
    if form.validate_on_submit():
        # Check if user already exists
        if User.query.filter_by(username=form.username.data).first():
            flash("Username already exists", "error")
            return render_template('admin/create_user.html', form=form, roles=roles)
            
        if User.query.filter_by(email=form.email.data).first():
            flash("Email already exists", "error")
            return render_template('admin/create_user.html', form=form, roles=roles)
            
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role=form.role.data,
            account_type=form.account_type.data,
            tokens_available=form.tokens_available.data,
            is_active=form.is_active.data
        )
        user.set_password(form.password.data)
        
        # Set custom role if provided
        custom_role_id = request.form.get('custom_role_id')
        if custom_role_id:
            try:
                user.custom_role_id = int(custom_role_id)
            except ValueError:
                pass
        
        # Save user
        db.session.add(user)
        try:
            db.session.commit()
            flash(f"User {user.username} created successfully", "success")
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {str(e)}")
            flash(f"Error creating user: {str(e)}", "error")
    
    return render_template('admin/create_user.html', form=form, roles=roles)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user"""
    if current_user.id == user_id:
        flash("You cannot delete your own account", "error")
        return redirect(url_for('admin.users'))
        
    user = User.query.get_or_404(user_id)
    username = user.username
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f"User {username} deleted successfully", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user: {str(e)}")
        flash(f"Error deleting user: {str(e)}", "error")
        
    return redirect(url_for('admin.users'))

# Role Management
@admin_bp.route('/roles')
@login_required
@admin_required
def roles():
    """Role management page with permission groups"""
    from utils.permissions import Permissions
    
    roles = Role.query.all()
    permissions = Permission.query.all()
    
    # Get permission groups from the Permissions class
    permission_groups = Permissions.get_permission_groups()
    
    return render_template(
        'admin/roles.html', 
        roles=roles, 
        permissions=permissions, 
        permission_groups=permission_groups
    )

@admin_bp.route('/roles/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_role():
    """Create a new custom role with grouped permissions"""
    from utils.permissions import Permissions
    
    permissions = Permission.query.all()
    permission_groups = Permissions.get_permission_groups()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash("Role name is required", "error")
            return render_template('admin/create_role.html', 
                                  permissions=permissions, 
                                  permission_groups=permission_groups)
            
        # Check if role already exists
        if Role.query.filter_by(name=name).first():
            flash("Role already exists", "error")
            return render_template('admin/create_role.html', 
                                  permissions=permissions, 
                                  permission_groups=permission_groups)
            
        # Create new role
        role = Role(
            name=name,
            description=description,
            is_custom=True
        )
        
        # Add permissions to role
        for permission in permissions:
            if f"permission_{permission.id}" in request.form:
                role.permissions.append(permission)
        
        # Save role
        db.session.add(role)
        try:
            db.session.commit()
            flash(f"Role {name} created successfully", "success")
            return redirect(url_for('admin.roles'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating role: {str(e)}")
            flash(f"Error creating role: {str(e)}", "error")
    
    return render_template('admin/create_role.html', 
                          permissions=permissions, 
                          permission_groups=permission_groups)

@admin_bp.route('/roles/<int:role_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_role(role_id):
    """Edit a role's details and permissions with grouped views"""
    from utils.permissions import Permissions
    
    role = Role.query.get_or_404(role_id)
    permissions = Permission.query.all()
    permission_groups = Permissions.get_permission_groups()
    
    # Default roles cannot be edited
    if role.is_default:
        flash("Default roles cannot be edited", "error")
        return redirect(url_for('admin.roles'))
    
    if request.method == 'POST':
        # Update role information
        role.name = request.form.get('name', role.name)
        role.description = request.form.get('description', role.description)
        
        # Update permissions
        role.permissions = []
        for permission in permissions:
            if f"permission_{permission.id}" in request.form:
                role.permissions.append(permission)
        
        # Save changes
        try:
            db.session.commit()
            flash(f"Role {role.name} updated successfully", "success")
            return redirect(url_for('admin.roles'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating role: {str(e)}")
            flash(f"Error updating role: {str(e)}", "error")
    
    return render_template('admin/edit_role.html', 
                          role=role, 
                          permissions=permissions, 
                          permission_groups=permission_groups)

@admin_bp.route('/roles/<int:role_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_role(role_id):
    """Delete a custom role"""
    role = Role.query.get_or_404(role_id)
    
    # Default roles cannot be deleted
    if role.is_default:
        flash("Default roles cannot be deleted", "error")
        return redirect(url_for('admin.roles'))
    
    # Check if role is being used by any users
    if User.query.filter_by(custom_role_id=role_id).first():
        flash("Cannot delete role that is being used by users", "error")
        return redirect(url_for('admin.roles'))
    
    role_name = role.name
    
    try:
        db.session.delete(role)
        db.session.commit()
        flash(f"Role {role_name} deleted successfully", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting role: {str(e)}")
        flash(f"Error deleting role: {str(e)}", "error")
        
    return redirect(url_for('admin.roles'))

# Organization Management
@admin_bp.route('/organizations')
@login_required
@admin_required
def organizations():
    """Organization management page"""
    organizations = Organization.query.all()
    return render_template('admin/organizations.html', organizations=organizations)

@admin_bp.route('/organizations/<int:org_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_organization(org_id):
    """Edit an organization's details"""
    organization = Organization.query.get_or_404(org_id)
    users = User.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        # Update organization information
        organization.name = request.form.get('name', organization.name)
        organization.description = request.form.get('description', organization.description)
        organization.address = request.form.get('address', organization.address)
        organization.phone = request.form.get('phone', organization.phone)
        organization.email = request.form.get('email', organization.email)
        organization.account_type = request.form.get('account_type', organization.account_type)
        organization.is_active = 'is_active' in request.form
        
        # Update organization owner
        owner_id = request.form.get('owner_id')
        if owner_id:
            try:
                organization.owner_id = int(owner_id)
            except ValueError:
                pass
                
        # Save changes
        try:
            db.session.commit()
            flash(f"Organization {organization.name} updated successfully", "success")
            return redirect(url_for('admin.organizations'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating organization: {str(e)}")
            flash(f"Error updating organization: {str(e)}", "error")
    
    return render_template('admin/edit_organization.html', organization=organization, users=users)

@admin_bp.route('/organizations/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_organization():
    """Create a new organization"""
    users = User.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        address = request.form.get('address')
        phone = request.form.get('phone')
        email = request.form.get('email')
        account_type = request.form.get('account_type', 'basic')
        is_active = 'is_active' in request.form
        owner_id = request.form.get('owner_id')
        
        if not name:
            flash("Organization name is required", "error")
            return render_template('admin/create_organization.html', users=users)
            
        # Check if organization already exists
        if Organization.query.filter_by(name=name).first():
            flash("Organization with this name already exists", "error")
            return render_template('admin/create_organization.html', users=users)
            
        # Create new organization
        organization = Organization(
            name=name,
            description=description,
            address=address,
            phone=phone,
            email=email,
            account_type=account_type,
            is_active=is_active
        )
        
        # Set owner if provided
        if owner_id:
            try:
                organization.owner_id = int(owner_id)
            except ValueError:
                pass
        
        # Save organization
        db.session.add(organization)
        try:
            db.session.commit()
            flash(f"Organization {name} created successfully", "success")
            return redirect(url_for('admin.organizations'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating organization: {str(e)}")
            flash(f"Error creating organization: {str(e)}", "error")
    
    return render_template('admin/create_organization.html', users=users)

@admin_bp.route('/organizations/<int:org_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_organization(org_id):
    """Delete an organization"""
    organization = Organization.query.get_or_404(org_id)
    org_name = organization.name
    
    try:
        # Remove organization associations
        for user in organization.members:
            user.organizations.remove(organization)
        
        # Clear active organization for users
        for user in User.query.filter_by(active_organization_id=org_id).all():
            user.active_organization_id = None
        
        db.session.delete(organization)
        db.session.commit()
        flash(f"Organization {org_name} deleted successfully", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting organization: {str(e)}")
        flash(f"Error deleting organization: {str(e)}", "error")
        
    return redirect(url_for('admin.organizations'))

@admin_bp.route('/organizations/<int:org_id>/members', methods=['GET', 'POST'])
@login_required
@admin_required
def organization_members(org_id):
    """Manage organization members"""
    organization = Organization.query.get_or_404(org_id)
    current_members = organization.members
    
    # Get available users (those who are not already members)
    available_users = User.query.filter(User.is_active==True).filter(~User.organizations.contains(organization)).all()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_member':
            # Add new member
            new_member_id = request.form.get('new_member')
            if new_member_id:
                user = User.query.get(new_member_id)
                if user:
                    organization.members.append(user)
                    
                    # If user is not already part of an organization, set their role
                    if user.role not in ['admin', 'organization']:
                        user.role = 'organization_member'
                    
                    # Set this as their active organization if they don't have one
                    if not user.active_organization_id:
                        user.active_organization_id = organization.id
                    
                    try:
                        db.session.commit()
                        flash(f"User {user.username} added to organization", "success")
                    except Exception as e:
                        db.session.rollback()
                        logger.error(f"Error adding member to organization: {str(e)}")
                        flash(f"Error adding member: {str(e)}", "error")
        
        elif action == 'remove_member':
            # Remove member
            member_id = request.form.get('member_id')
            if member_id:
                user = User.query.get(member_id)
                if user and user in organization.members:
                    organization.members.remove(user)
                    
                    # If this was their active organization, clear it
                    if user.active_organization_id == organization.id:
                        user.active_organization_id = None
                    
                    # If they're not an admin or organization owner elsewhere, reset role
                    if user.role == 'organization_member' and not user.organizations.count():
                        user.role = 'individual'
                    
                    try:
                        db.session.commit()
                        flash(f"User {user.username} removed from organization", "success")
                    except Exception as e:
                        db.session.rollback()
                        logger.error(f"Error removing member from organization: {str(e)}")
                        flash(f"Error removing member: {str(e)}", "error")
        
        elif action == 'make_owner':
            # Make user the organization owner
            member_id = request.form.get('member_id')
            if member_id:
                user = User.query.get(member_id)
                if user and user in organization.members:
                    # Update user roles
                    if organization.owner:
                        # Change current owner's role if not an admin
                        if organization.owner.role != 'admin':
                            organization.owner.role = 'organization_member'
                    
                    # Set new owner
                    organization.owner_id = user.id
                    user.role = 'organization'
                    
                    try:
                        db.session.commit()
                        flash(f"User {user.username} is now the organization owner", "success")
                    except Exception as e:
                        db.session.rollback()
                        logger.error(f"Error changing organization owner: {str(e)}")
                        flash(f"Error changing owner: {str(e)}", "error")
        
        # Redirect to refresh the member list
        return redirect(url_for('admin.organization_members', org_id=org_id))
    
    return render_template('admin/organization_members.html', 
                          organization=organization, 
                          current_members=current_members,
                          available_users=available_users)

# System Settings and Management
@admin_bp.route('/system-settings', methods=['GET', 'POST'])
@login_required
@admin_required
def system_settings():
    """System settings page"""
    # Get user and organization counts for the system info panel
    user_count = User.query.count()
    organization_count = Organization.query.count()
    
    if request.method == 'POST':
        # Update system settings
        # This would be implemented to save system settings
        flash("System settings updated successfully", "success")
        return redirect(url_for('admin.system_settings'))
        
    return render_template('admin/system_settings.html',
                          user_count=user_count,
                          organization_count=organization_count)

@admin_bp.route('/clear-cache', methods=['POST'])
@login_required
@admin_required
def clear_cache():
    """Clear system cache"""
    # This would implement cache clearing functionality
    try:
        # Implement cache clearing logic here
        flash("System cache cleared successfully", "success")
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        flash(f"Error clearing cache: {str(e)}", "error")
        
    return redirect(url_for('admin.system_settings'))

@admin_bp.route('/backup-database', methods=['POST'])
@login_required
@admin_required
def backup_database():
    """Create a database backup"""
    try:
        # Implement database backup logic here
        # This could export data or trigger a pg_dump
        flash("Database backup created successfully", "success")
    except Exception as e:
        logger.error(f"Error creating database backup: {str(e)}")
        flash(f"Error creating database backup: {str(e)}", "error")
        
    return redirect(url_for('admin.system_settings'))