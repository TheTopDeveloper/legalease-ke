"""
Routes for admin functionality, including role and permission management.
"""
import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import current_user, login_required
from sqlalchemy import desc

from models import db, User, Role, Permission, Organization
from utils.permissions import admin_required, Permissions

logger = logging.getLogger(__name__)

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard with overview of system statistics"""
    # Get system statistics
    user_count = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    admin_users = User.query.filter_by(role='admin').count()
    organization_count = Organization.query.count()
    
    # Recent users
    recent_users = User.query.order_by(desc(User.created_at)).limit(10).all()
    
    return render_template('admin/index.html', 
                          user_count=user_count,
                          active_users=active_users,
                          admin_users=admin_users,
                          organization_count=organization_count,
                          recent_users=recent_users)

# User Management
@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """User management page"""
    users = User.query.all()
    roles = Role.query.all()
    return render_template('admin/users.html', users=users, roles=roles)

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
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        role = request.form.get('role', 'individual')
        account_type = request.form.get('account_type', 'free')
        is_active = 'is_active' in request.form
        
        # Validate required fields
        if not username or not email or not password:
            flash("Username, email, and password are required", "error")
            return render_template('admin/create_user.html', roles=roles)
            
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists", "error")
            return render_template('admin/create_user.html', roles=roles)
            
        if User.query.filter_by(email=email).first():
            flash("Email already exists", "error")
            return render_template('admin/create_user.html', roles=roles)
            
        # Create new user
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            account_type=account_type,
            is_active=is_active
        )
        user.set_password(password)
        
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
            flash(f"User {username} created successfully", "success")
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {str(e)}")
            flash(f"Error creating user: {str(e)}", "error")
    
    return render_template('admin/create_user.html', roles=roles)

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
    """Role management page"""
    roles = Role.query.all()
    permissions = Permission.query.all()
    return render_template('admin/roles.html', roles=roles, permissions=permissions)

@admin_bp.route('/roles/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_role():
    """Create a new custom role"""
    permissions = Permission.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash("Role name is required", "error")
            return render_template('admin/create_role.html', permissions=permissions)
            
        # Check if role already exists
        if Role.query.filter_by(name=name).first():
            flash("Role already exists", "error")
            return render_template('admin/create_role.html', permissions=permissions)
            
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
    
    return render_template('admin/create_role.html', permissions=permissions)

@admin_bp.route('/roles/<int:role_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_role(role_id):
    """Edit a role's details and permissions"""
    role = Role.query.get_or_404(role_id)
    permissions = Permission.query.all()
    
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
    
    return render_template('admin/edit_role.html', role=role, permissions=permissions)

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
    users = User.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        # Update members
        organization.members = []
        for key, value in request.form.items():
            if key.startswith('member_') and value == 'on':
                user_id = int(key.split('_')[1])
                user = User.query.get(user_id)
                if user:
                    organization.members.append(user)
                    # If user is a member, set their role appropriately
                    if user.id == organization.owner_id:
                        user.role = 'organization'
                    else:
                        user.role = 'organization_member'
                        
                    # Set this as their active organization if not already part of one
                    if not user.active_organization_id:
                        user.active_organization_id = organization.id
        
        try:
            db.session.commit()
            flash(f"Organization members updated successfully", "success")
            return redirect(url_for('admin.organizations'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating organization members: {str(e)}")
            flash(f"Error updating organization members: {str(e)}", "error")
    
    return render_template('admin/organization_members.html', organization=organization, users=users)

# System Settings
@admin_bp.route('/system-settings', methods=['GET', 'POST'])
@login_required
@admin_required
def system_settings():
    """System settings page"""
    # This would be expanded to include various system settings
    return render_template('admin/system_settings.html')