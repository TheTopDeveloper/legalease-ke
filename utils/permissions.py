"""
Permissions and access control utilities for role-based access.
"""
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

# Define permission constants
# These are the granular permissions in the system
class Permissions:
    # Case permissions
    VIEW_CASE = 'view_case'
    CREATE_CASE = 'create_case'
    EDIT_CASE = 'edit_case'
    DELETE_CASE = 'delete_case'
    
    # Document permissions
    VIEW_DOCUMENT = 'view_document'
    CREATE_DOCUMENT = 'create_document'
    EDIT_DOCUMENT = 'edit_document'
    DELETE_DOCUMENT = 'delete_document'
    
    # Template permissions
    VIEW_TEMPLATE = 'view_template'
    CREATE_TEMPLATE = 'create_template'
    EDIT_TEMPLATE = 'edit_template'
    DELETE_TEMPLATE = 'delete_template'
    
    # Client permissions
    VIEW_CLIENT = 'view_client'
    CREATE_CLIENT = 'create_client'
    EDIT_CLIENT = 'edit_client'
    DELETE_CLIENT = 'delete_client'
    
    # Event permissions
    VIEW_EVENT = 'view_event'
    CREATE_EVENT = 'create_event'
    EDIT_EVENT = 'edit_event'
    DELETE_EVENT = 'delete_event'
    
    # Research permissions
    BASIC_RESEARCH = 'basic_research'
    ADVANCED_RESEARCH = 'advanced_research'
    
    # User management
    VIEW_USERS = 'view_users'
    CREATE_USER = 'create_user'
    EDIT_USER = 'edit_user'
    DELETE_USER = 'delete_user'
    ASSIGN_ROLE = 'assign_role'
    
    # Subscription and token permissions
    MANAGE_SUBSCRIPTIONS = 'manage_subscriptions'
    MANAGE_TOKENS = 'manage_tokens'
    
    # Legal writing assistant
    USE_WRITING_ASSISTANT = 'use_writing_assistant'
    
    # Admin permissions
    ADMIN_ACCESS = 'admin_access'
    SYSTEM_SETTINGS = 'system_settings'
    
    @classmethod
    def get_all_permissions(cls):
        """Get a list of all permission constants"""
        return [attr for attr in dir(cls) if not attr.startswith('_') and attr.isupper()]


# Define role-based permission sets
DEFAULT_ROLE_PERMISSIONS = {
    'admin': [
        # Admin has all permissions
        Permissions.VIEW_CASE, Permissions.CREATE_CASE, Permissions.EDIT_CASE, Permissions.DELETE_CASE,
        Permissions.VIEW_DOCUMENT, Permissions.CREATE_DOCUMENT, Permissions.EDIT_DOCUMENT, Permissions.DELETE_DOCUMENT,
        Permissions.VIEW_TEMPLATE, Permissions.CREATE_TEMPLATE, Permissions.EDIT_TEMPLATE, Permissions.DELETE_TEMPLATE,
        Permissions.VIEW_CLIENT, Permissions.CREATE_CLIENT, Permissions.EDIT_CLIENT, Permissions.DELETE_CLIENT,
        Permissions.VIEW_EVENT, Permissions.CREATE_EVENT, Permissions.EDIT_EVENT, Permissions.DELETE_EVENT,
        Permissions.BASIC_RESEARCH, Permissions.ADVANCED_RESEARCH,
        Permissions.VIEW_USERS, Permissions.CREATE_USER, Permissions.EDIT_USER, Permissions.DELETE_USER, Permissions.ASSIGN_ROLE,
        Permissions.MANAGE_SUBSCRIPTIONS, Permissions.MANAGE_TOKENS,
        Permissions.USE_WRITING_ASSISTANT,
        Permissions.ADMIN_ACCESS, Permissions.SYSTEM_SETTINGS
    ],
    'organization': [
        # Organization has most permissions except admin ones
        Permissions.VIEW_CASE, Permissions.CREATE_CASE, Permissions.EDIT_CASE, Permissions.DELETE_CASE,
        Permissions.VIEW_DOCUMENT, Permissions.CREATE_DOCUMENT, Permissions.EDIT_DOCUMENT, Permissions.DELETE_DOCUMENT,
        Permissions.VIEW_TEMPLATE, Permissions.CREATE_TEMPLATE, Permissions.EDIT_TEMPLATE, Permissions.DELETE_TEMPLATE,
        Permissions.VIEW_CLIENT, Permissions.CREATE_CLIENT, Permissions.EDIT_CLIENT, Permissions.DELETE_CLIENT,
        Permissions.VIEW_EVENT, Permissions.CREATE_EVENT, Permissions.EDIT_EVENT, Permissions.DELETE_EVENT,
        Permissions.BASIC_RESEARCH, Permissions.ADVANCED_RESEARCH,
        Permissions.VIEW_USERS, Permissions.CREATE_USER, Permissions.EDIT_USER,  # Can manage their organization users
        Permissions.USE_WRITING_ASSISTANT
    ],
    'organization_member': [
        # Organization member has limited permissions within their organization
        Permissions.VIEW_CASE, Permissions.CREATE_CASE, Permissions.EDIT_CASE,
        Permissions.VIEW_DOCUMENT, Permissions.CREATE_DOCUMENT, Permissions.EDIT_DOCUMENT,
        Permissions.VIEW_TEMPLATE, Permissions.CREATE_TEMPLATE,
        Permissions.VIEW_CLIENT, Permissions.CREATE_CLIENT, Permissions.EDIT_CLIENT,
        Permissions.VIEW_EVENT, Permissions.CREATE_EVENT, Permissions.EDIT_EVENT,
        Permissions.BASIC_RESEARCH, Permissions.ADVANCED_RESEARCH,
        Permissions.USE_WRITING_ASSISTANT
    ],
    'individual': [
        # Individual user has personal permissions
        Permissions.VIEW_CASE, Permissions.CREATE_CASE, Permissions.EDIT_CASE, Permissions.DELETE_CASE,
        Permissions.VIEW_DOCUMENT, Permissions.CREATE_DOCUMENT, Permissions.EDIT_DOCUMENT, Permissions.DELETE_DOCUMENT,
        Permissions.VIEW_TEMPLATE, Permissions.CREATE_TEMPLATE, Permissions.EDIT_TEMPLATE, Permissions.DELETE_TEMPLATE,
        Permissions.VIEW_CLIENT, Permissions.CREATE_CLIENT, Permissions.EDIT_CLIENT, Permissions.DELETE_CLIENT,
        Permissions.VIEW_EVENT, Permissions.CREATE_EVENT, Permissions.EDIT_EVENT, Permissions.DELETE_EVENT,
        Permissions.BASIC_RESEARCH,  # Basic research only
        Permissions.USE_WRITING_ASSISTANT
    ],
    'free': [
        # Free user has very limited permissions
        Permissions.VIEW_CASE, Permissions.CREATE_CASE, Permissions.EDIT_CASE,
        Permissions.VIEW_DOCUMENT, Permissions.CREATE_DOCUMENT, Permissions.EDIT_DOCUMENT,
        Permissions.VIEW_TEMPLATE,
        Permissions.VIEW_CLIENT, Permissions.CREATE_CLIENT,
        Permissions.VIEW_EVENT, Permissions.CREATE_EVENT,
        Permissions.BASIC_RESEARCH
    ]
}

def check_permission(user, permission):
    """
    Check if a user has a specific permission.
    
    Args:
        user: The user to check permissions for
        permission: The permission to check
        
    Returns:
        bool: True if user has permission, False otherwise
    """
    # Check if user is authenticated
    if not user or not user.is_authenticated:
        return False
        
    # Get user's role permissions
    role_permissions = DEFAULT_ROLE_PERMISSIONS.get(user.role, [])
    
    # Check if permission is in role permissions
    return permission in role_permissions

def has_permission(permission):
    """
    Decorator to check if current user has a specific permission.
    
    Args:
        permission: The permission to check for
        
    Usage:
        @has_permission(Permissions.CREATE_CASE)
        def create_case():
            # Only users with CREATE_CASE permission can access this
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page', 'warning')
                return redirect(url_for('auth.login'))
                
            if not current_user.has_permission(permission):
                flash('You do not have permission to access this resource', 'error')
                return redirect(url_for('dashboard.index'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
    
def role_required(role):
    """
    Decorator to check if current user has a specific role.
    
    Args:
        role: The role to check for (e.g., 'admin', 'organization', 'individual')
        
    Usage:
        @role_required('admin')
        def admin_dashboard():
            # Only admins can access this
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page', 'warning')
                return redirect(url_for('auth.login'))
                
            if current_user.role != role and current_user.role != 'admin':
                flash(f'This area is restricted to {role} users', 'error')
                return redirect(url_for('dashboard.index'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """
    Decorator to check if current user is an admin.
    This is a shortcut for @role_required('admin')
    
    Usage:
        @admin_required
        def admin_dashboard():
            # Only admins can access this
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login'))
            
        if current_user.role != 'admin':
            flash('This area is restricted to administrators', 'error')
            return redirect(url_for('dashboard.index'))
            
        return f(*args, **kwargs)
    return decorated_function

def check_case_access(case, user):
    """
    Check if a user has access to a specific case.
    
    Args:
        case: The case object to check access for
        user: The user attempting to access the case
        
    Returns:
        bool: True if user has access, False otherwise
    """
    # Admins have access to all cases
    if user.role == 'admin':
        return True
        
    # Case owner has access
    if case.user_id == user.id:
        return True
        
    # For organization members, check if case belongs to the organization
    if user.role == 'organization_member' and user.organization_id:
        # Get the case owner
        from models import User
        case_owner = User.query.get(case.user_id)
        
        # Allow access if case owner is in the same organization
        if case_owner and case_owner.organization_id == user.organization_id:
            return True
    
    # For shared cases (implement this when case sharing is developed)
    # if user.id in [shared_user.id for shared_user in case.shared_users]:
    #     return True
    
    return False