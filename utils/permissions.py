"""
Permissions and access control utilities for role-based access.
This module provides a comprehensive permission system with multi-level access control.
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
    SHARE_CASE = 'share_case'
    ASSIGN_CASE = 'assign_case'
    
    # Document permissions
    VIEW_DOCUMENT = 'view_document'
    CREATE_DOCUMENT = 'create_document'
    EDIT_DOCUMENT = 'edit_document'
    DELETE_DOCUMENT = 'delete_document'
    SHARE_DOCUMENT = 'share_document'
    EXPORT_DOCUMENT = 'export_document'
    
    # Template permissions
    VIEW_TEMPLATE = 'view_template'
    CREATE_TEMPLATE = 'create_template'
    EDIT_TEMPLATE = 'edit_template'
    DELETE_TEMPLATE = 'delete_template'
    SHARE_TEMPLATE = 'share_template'
    
    # Client permissions
    VIEW_CLIENT = 'view_client'
    CREATE_CLIENT = 'create_client'
    EDIT_CLIENT = 'edit_client'
    DELETE_CLIENT = 'delete_client'
    VIEW_CLIENT_DOCUMENTS = 'view_client_documents'
    
    # Event permissions
    VIEW_EVENT = 'view_event'
    CREATE_EVENT = 'create_event'
    EDIT_EVENT = 'edit_event'
    DELETE_EVENT = 'delete_event'
    
    # Research permissions
    BASIC_RESEARCH = 'basic_research'
    ADVANCED_RESEARCH = 'advanced_research'
    SAVE_RESEARCH = 'save_research'
    SHARE_RESEARCH = 'share_research'
    
    # User management
    VIEW_USERS = 'view_users'
    CREATE_USER = 'create_user'
    EDIT_USER = 'edit_user'
    DELETE_USER = 'delete_user'
    ASSIGN_ROLE = 'assign_role'
    
    # Milestone and task permissions
    VIEW_MILESTONE = 'view_milestone'
    CREATE_MILESTONE = 'create_milestone'
    EDIT_MILESTONE = 'edit_milestone'
    DELETE_MILESTONE = 'delete_milestone'
    
    # Organization permissions
    MANAGE_ORGANIZATION = 'manage_organization'
    VIEW_ORGANIZATION_ANALYTICS = 'view_organization_analytics'
    INVITE_MEMBER = 'invite_member'
    REMOVE_MEMBER = 'remove_member'
    MANAGE_ORGANIZATION_TEMPLATES = 'manage_organization_templates'
    
    # Subscription and token permissions
    MANAGE_SUBSCRIPTIONS = 'manage_subscriptions'
    MANAGE_TOKENS = 'manage_tokens'
    VIEW_BILLING = 'view_billing'
    
    # Feature permissions
    USE_WRITING_ASSISTANT = 'use_writing_assistant'
    USE_ANALYTICS = 'use_analytics'
    USE_DOCUMENT_GENERATION = 'use_document_generation'
    
    # Admin permissions
    ADMIN_ACCESS = 'admin_access'
    SYSTEM_SETTINGS = 'system_settings'
    MANAGE_ALL_ORGANIZATIONS = 'manage_all_organizations'
    VIEW_SYSTEM_LOGS = 'view_system_logs'
    
    # API Access
    API_ACCESS = 'api_access'
    
    @classmethod
    def get_all_permissions(cls):
        """Get a list of all permission constants"""
        return [getattr(cls, attr) for attr in dir(cls) if not attr.startswith('_') and attr.isupper()]
        
    @classmethod
    def get_permission_groups(cls):
        """Get all permission groups with their permissions"""
        return {
            'Case Management': [
                cls.VIEW_CASE, cls.CREATE_CASE, cls.EDIT_CASE, 
                cls.DELETE_CASE, cls.SHARE_CASE, cls.ASSIGN_CASE
            ],
            'Document Management': [
                cls.VIEW_DOCUMENT, cls.CREATE_DOCUMENT, cls.EDIT_DOCUMENT, 
                cls.DELETE_DOCUMENT, cls.SHARE_DOCUMENT, cls.EXPORT_DOCUMENT
            ],
            'Template Management': [
                cls.VIEW_TEMPLATE, cls.CREATE_TEMPLATE, 
                cls.EDIT_TEMPLATE, cls.DELETE_TEMPLATE, cls.SHARE_TEMPLATE
            ],
            'Client Management': [
                cls.VIEW_CLIENT, cls.CREATE_CLIENT, cls.EDIT_CLIENT, 
                cls.DELETE_CLIENT, cls.VIEW_CLIENT_DOCUMENTS
            ],
            'Calendar and Events': [
                cls.VIEW_EVENT, cls.CREATE_EVENT, cls.EDIT_EVENT, cls.DELETE_EVENT
            ],
            'Legal Research': [
                cls.BASIC_RESEARCH, cls.ADVANCED_RESEARCH, 
                cls.SAVE_RESEARCH, cls.SHARE_RESEARCH
            ],
            'User Management': [
                cls.VIEW_USERS, cls.CREATE_USER, cls.EDIT_USER, 
                cls.DELETE_USER, cls.ASSIGN_ROLE
            ],
            'Milestone Management': [
                cls.VIEW_MILESTONE, cls.CREATE_MILESTONE, 
                cls.EDIT_MILESTONE, cls.DELETE_MILESTONE
            ],
            'Organization Management': [
                cls.MANAGE_ORGANIZATION, cls.VIEW_ORGANIZATION_ANALYTICS, 
                cls.INVITE_MEMBER, cls.REMOVE_MEMBER, cls.MANAGE_ORGANIZATION_TEMPLATES
            ],
            'Billing and Subscriptions': [
                cls.MANAGE_SUBSCRIPTIONS, cls.MANAGE_TOKENS, cls.VIEW_BILLING
            ],
            'Feature Access': [
                cls.USE_WRITING_ASSISTANT, cls.USE_ANALYTICS, 
                cls.USE_DOCUMENT_GENERATION, cls.API_ACCESS
            ],
            'Administration': [
                cls.ADMIN_ACCESS, cls.SYSTEM_SETTINGS, 
                cls.MANAGE_ALL_ORGANIZATIONS, cls.VIEW_SYSTEM_LOGS
            ]
        }


# Define default role levels and their permissions
DEFAULT_ROLE_PERMISSIONS = {
    'admin': [
        # Admin has all permissions
        # Case Management
        Permissions.VIEW_CASE, Permissions.CREATE_CASE, Permissions.EDIT_CASE, 
        Permissions.DELETE_CASE, Permissions.SHARE_CASE, Permissions.ASSIGN_CASE,
        
        # Document Management
        Permissions.VIEW_DOCUMENT, Permissions.CREATE_DOCUMENT, Permissions.EDIT_DOCUMENT, 
        Permissions.DELETE_DOCUMENT, Permissions.SHARE_DOCUMENT, Permissions.EXPORT_DOCUMENT,
        
        # Template Management
        Permissions.VIEW_TEMPLATE, Permissions.CREATE_TEMPLATE, Permissions.EDIT_TEMPLATE, 
        Permissions.DELETE_TEMPLATE, Permissions.SHARE_TEMPLATE,
        
        # Client Management
        Permissions.VIEW_CLIENT, Permissions.CREATE_CLIENT, Permissions.EDIT_CLIENT, 
        Permissions.DELETE_CLIENT, Permissions.VIEW_CLIENT_DOCUMENTS,
        
        # Calendar and Events
        Permissions.VIEW_EVENT, Permissions.CREATE_EVENT, Permissions.EDIT_EVENT, Permissions.DELETE_EVENT,
        
        # Legal Research
        Permissions.BASIC_RESEARCH, Permissions.ADVANCED_RESEARCH, 
        Permissions.SAVE_RESEARCH, Permissions.SHARE_RESEARCH,
        
        # User Management
        Permissions.VIEW_USERS, Permissions.CREATE_USER, Permissions.EDIT_USER, 
        Permissions.DELETE_USER, Permissions.ASSIGN_ROLE,
        
        # Milestone Management
        Permissions.VIEW_MILESTONE, Permissions.CREATE_MILESTONE, 
        Permissions.EDIT_MILESTONE, Permissions.DELETE_MILESTONE,
        
        # Organization Management
        Permissions.MANAGE_ORGANIZATION, Permissions.VIEW_ORGANIZATION_ANALYTICS, 
        Permissions.INVITE_MEMBER, Permissions.REMOVE_MEMBER, Permissions.MANAGE_ORGANIZATION_TEMPLATES,
        
        # Billing and Subscriptions
        Permissions.MANAGE_SUBSCRIPTIONS, Permissions.MANAGE_TOKENS, Permissions.VIEW_BILLING,
        
        # Feature Access
        Permissions.USE_WRITING_ASSISTANT, Permissions.USE_ANALYTICS, 
        Permissions.USE_DOCUMENT_GENERATION, Permissions.API_ACCESS,
        
        # Administration
        Permissions.ADMIN_ACCESS, Permissions.SYSTEM_SETTINGS, 
        Permissions.MANAGE_ALL_ORGANIZATIONS, Permissions.VIEW_SYSTEM_LOGS
    ],
    
    'organization_owner': [
        # Organization owner has extensive permissions for their organization
        # Case Management
        Permissions.VIEW_CASE, Permissions.CREATE_CASE, Permissions.EDIT_CASE, 
        Permissions.DELETE_CASE, Permissions.SHARE_CASE, Permissions.ASSIGN_CASE,
        
        # Document Management
        Permissions.VIEW_DOCUMENT, Permissions.CREATE_DOCUMENT, Permissions.EDIT_DOCUMENT, 
        Permissions.DELETE_DOCUMENT, Permissions.SHARE_DOCUMENT, Permissions.EXPORT_DOCUMENT,
        
        # Template Management
        Permissions.VIEW_TEMPLATE, Permissions.CREATE_TEMPLATE, Permissions.EDIT_TEMPLATE, 
        Permissions.DELETE_TEMPLATE, Permissions.SHARE_TEMPLATE,
        
        # Client Management
        Permissions.VIEW_CLIENT, Permissions.CREATE_CLIENT, Permissions.EDIT_CLIENT, 
        Permissions.DELETE_CLIENT, Permissions.VIEW_CLIENT_DOCUMENTS,
        
        # Calendar and Events
        Permissions.VIEW_EVENT, Permissions.CREATE_EVENT, Permissions.EDIT_EVENT, Permissions.DELETE_EVENT,
        
        # Legal Research
        Permissions.BASIC_RESEARCH, Permissions.ADVANCED_RESEARCH, 
        Permissions.SAVE_RESEARCH, Permissions.SHARE_RESEARCH,
        
        # User Management
        Permissions.VIEW_USERS, Permissions.CREATE_USER, Permissions.EDIT_USER, 
        Permissions.ASSIGN_ROLE,
        
        # Milestone Management
        Permissions.VIEW_MILESTONE, Permissions.CREATE_MILESTONE, 
        Permissions.EDIT_MILESTONE, Permissions.DELETE_MILESTONE,
        
        # Organization Management
        Permissions.MANAGE_ORGANIZATION, Permissions.VIEW_ORGANIZATION_ANALYTICS, 
        Permissions.INVITE_MEMBER, Permissions.REMOVE_MEMBER, Permissions.MANAGE_ORGANIZATION_TEMPLATES,
        
        # Billing and Subscriptions
        Permissions.MANAGE_SUBSCRIPTIONS, Permissions.MANAGE_TOKENS, Permissions.VIEW_BILLING,
        
        # Feature Access
        Permissions.USE_WRITING_ASSISTANT, Permissions.USE_ANALYTICS, 
        Permissions.USE_DOCUMENT_GENERATION, Permissions.API_ACCESS
    ],
    
    'organization': [
        # Standard organization member with management capabilities
        # Case Management
        Permissions.VIEW_CASE, Permissions.CREATE_CASE, Permissions.EDIT_CASE, 
        Permissions.DELETE_CASE, Permissions.SHARE_CASE,
        
        # Document Management
        Permissions.VIEW_DOCUMENT, Permissions.CREATE_DOCUMENT, Permissions.EDIT_DOCUMENT, 
        Permissions.DELETE_DOCUMENT, Permissions.SHARE_DOCUMENT, Permissions.EXPORT_DOCUMENT,
        
        # Template Management
        Permissions.VIEW_TEMPLATE, Permissions.CREATE_TEMPLATE, Permissions.EDIT_TEMPLATE, 
        Permissions.DELETE_TEMPLATE, Permissions.SHARE_TEMPLATE,
        
        # Client Management
        Permissions.VIEW_CLIENT, Permissions.CREATE_CLIENT, Permissions.EDIT_CLIENT, 
        Permissions.DELETE_CLIENT, Permissions.VIEW_CLIENT_DOCUMENTS,
        
        # Calendar and Events
        Permissions.VIEW_EVENT, Permissions.CREATE_EVENT, Permissions.EDIT_EVENT, Permissions.DELETE_EVENT,
        
        # Legal Research
        Permissions.BASIC_RESEARCH, Permissions.ADVANCED_RESEARCH, 
        Permissions.SAVE_RESEARCH, Permissions.SHARE_RESEARCH,
        
        # User Management
        Permissions.VIEW_USERS,
        
        # Milestone Management
        Permissions.VIEW_MILESTONE, Permissions.CREATE_MILESTONE, 
        Permissions.EDIT_MILESTONE, Permissions.DELETE_MILESTONE,
        
        # Organization Management
        Permissions.VIEW_ORGANIZATION_ANALYTICS,
        
        # Billing and Subscriptions
        Permissions.VIEW_BILLING,
        
        # Feature Access
        Permissions.USE_WRITING_ASSISTANT, Permissions.USE_ANALYTICS, 
        Permissions.USE_DOCUMENT_GENERATION
    ],
    
    'organization_member': [
        # Basic organization member with limited permissions
        # Case Management
        Permissions.VIEW_CASE, Permissions.CREATE_CASE, Permissions.EDIT_CASE,
        
        # Document Management
        Permissions.VIEW_DOCUMENT, Permissions.CREATE_DOCUMENT, Permissions.EDIT_DOCUMENT,
        Permissions.SHARE_DOCUMENT, Permissions.EXPORT_DOCUMENT,
        
        # Template Management
        Permissions.VIEW_TEMPLATE, Permissions.CREATE_TEMPLATE,
        
        # Client Management
        Permissions.VIEW_CLIENT, Permissions.CREATE_CLIENT, Permissions.EDIT_CLIENT,
        Permissions.VIEW_CLIENT_DOCUMENTS,
        
        # Calendar and Events
        Permissions.VIEW_EVENT, Permissions.CREATE_EVENT, Permissions.EDIT_EVENT,
        
        # Legal Research
        Permissions.BASIC_RESEARCH, Permissions.ADVANCED_RESEARCH,
        Permissions.SAVE_RESEARCH,
        
        # Milestone Management
        Permissions.VIEW_MILESTONE, Permissions.CREATE_MILESTONE,
        
        # Feature Access
        Permissions.USE_WRITING_ASSISTANT, Permissions.USE_DOCUMENT_GENERATION
    ],
    
    'organization_readonly': [
        # Read-only organization member
        # Case Management
        Permissions.VIEW_CASE,
        
        # Document Management
        Permissions.VIEW_DOCUMENT,
        
        # Template Management
        Permissions.VIEW_TEMPLATE,
        
        # Client Management
        Permissions.VIEW_CLIENT, Permissions.VIEW_CLIENT_DOCUMENTS,
        
        # Calendar and Events
        Permissions.VIEW_EVENT,
        
        # Legal Research
        Permissions.BASIC_RESEARCH,
        
        # Milestone Management
        Permissions.VIEW_MILESTONE
    ],
    
    'individual_premium': [
        # Premium individual user with advanced features
        # Case Management
        Permissions.VIEW_CASE, Permissions.CREATE_CASE, Permissions.EDIT_CASE, 
        Permissions.DELETE_CASE, Permissions.SHARE_CASE,
        
        # Document Management
        Permissions.VIEW_DOCUMENT, Permissions.CREATE_DOCUMENT, Permissions.EDIT_DOCUMENT, 
        Permissions.DELETE_DOCUMENT, Permissions.SHARE_DOCUMENT, Permissions.EXPORT_DOCUMENT,
        
        # Template Management
        Permissions.VIEW_TEMPLATE, Permissions.CREATE_TEMPLATE, Permissions.EDIT_TEMPLATE, 
        Permissions.DELETE_TEMPLATE,
        
        # Client Management
        Permissions.VIEW_CLIENT, Permissions.CREATE_CLIENT, Permissions.EDIT_CLIENT, 
        Permissions.DELETE_CLIENT, Permissions.VIEW_CLIENT_DOCUMENTS,
        
        # Calendar and Events
        Permissions.VIEW_EVENT, Permissions.CREATE_EVENT, Permissions.EDIT_EVENT, Permissions.DELETE_EVENT,
        
        # Legal Research
        Permissions.BASIC_RESEARCH, Permissions.ADVANCED_RESEARCH,
        Permissions.SAVE_RESEARCH,
        
        # Milestone Management
        Permissions.VIEW_MILESTONE, Permissions.CREATE_MILESTONE, 
        Permissions.EDIT_MILESTONE, Permissions.DELETE_MILESTONE,
        
        # Feature Access
        Permissions.USE_WRITING_ASSISTANT, Permissions.USE_ANALYTICS, 
        Permissions.USE_DOCUMENT_GENERATION
    ],
    
    'individual': [
        # Standard individual user
        # Case Management
        Permissions.VIEW_CASE, Permissions.CREATE_CASE, Permissions.EDIT_CASE, Permissions.DELETE_CASE,
        
        # Document Management
        Permissions.VIEW_DOCUMENT, Permissions.CREATE_DOCUMENT, Permissions.EDIT_DOCUMENT, 
        Permissions.DELETE_DOCUMENT, Permissions.EXPORT_DOCUMENT,
        
        # Template Management
        Permissions.VIEW_TEMPLATE, Permissions.CREATE_TEMPLATE, Permissions.EDIT_TEMPLATE, 
        Permissions.DELETE_TEMPLATE,
        
        # Client Management
        Permissions.VIEW_CLIENT, Permissions.CREATE_CLIENT, Permissions.EDIT_CLIENT, 
        Permissions.DELETE_CLIENT,
        
        # Calendar and Events
        Permissions.VIEW_EVENT, Permissions.CREATE_EVENT, Permissions.EDIT_EVENT, Permissions.DELETE_EVENT,
        
        # Legal Research
        Permissions.BASIC_RESEARCH,
        
        # Milestone Management
        Permissions.VIEW_MILESTONE, Permissions.CREATE_MILESTONE,
        
        # Feature Access
        Permissions.USE_WRITING_ASSISTANT, Permissions.USE_DOCUMENT_GENERATION
    ],
    
    'free': [
        # Free tier user with basic access
        # Case Management
        Permissions.VIEW_CASE, Permissions.CREATE_CASE, Permissions.EDIT_CASE,
        
        # Document Management
        Permissions.VIEW_DOCUMENT, Permissions.CREATE_DOCUMENT, Permissions.EDIT_DOCUMENT,
        
        # Template Management
        Permissions.VIEW_TEMPLATE,
        
        # Client Management
        Permissions.VIEW_CLIENT, Permissions.CREATE_CLIENT,
        
        # Calendar and Events
        Permissions.VIEW_EVENT, Permissions.CREATE_EVENT,
        
        # Legal Research
        Permissions.BASIC_RESEARCH,
        
        # Milestone Management
        Permissions.VIEW_MILESTONE
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
    
    # Admin has all permissions
    if user.role == 'admin':
        return True
    
    # Check if user has a custom role with this permission
    if user.custom_role_id:
        for perm in user.custom_role.permissions:
            if perm.name == permission:
                return True
    
    # Check user's organization role if they are part of an organization
    if user.active_organization_id and user.is_organization_owner():
        owner_permissions = DEFAULT_ROLE_PERMISSIONS.get('organization_owner', [])
        if permission in owner_permissions:
            return True
    
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
    
    # Organization owners/admins have access to all cases in their organization
    if user.is_organization_owner() and user.active_organization_id:
        from models import User
        case_owner = User.query.get(case.user_id)
        if case_owner and case_owner.active_organization_id == user.active_organization_id:
            return True
        
    # Case owner has access
    if case.user_id == user.id:
        return True
    
    # For organization users, check if case belongs to the organization and user has VIEW_CASE permission
    if user.active_organization_id and user.has_permission(Permissions.VIEW_CASE):
        # Get the case owner
        from models import User
        case_owner = User.query.get(case.user_id)
        
        # Allow access if case owner is in the same organization
        if case_owner and case_owner.active_organization_id == user.active_organization_id:
            return True
    
    # For shared cases
    if hasattr(case, 'shared_users') and case.shared_users and user.id in [shared_user.id for shared_user in case.shared_users]:
        return True
    
    return False

def check_document_access(document, user):
    """
    Check if a user has access to a specific document.
    
    Args:
        document: The document object to check access for
        user: The user attempting to access the document
        
    Returns:
        bool: True if user has access, False otherwise
    """
    # Admins have access to all documents
    if user.role == 'admin':
        return True
    
    # Document owner has access
    if document.user_id == user.id:
        return True
    
    # Organization owners have access to all organization documents
    if user.is_organization_owner() and user.active_organization_id:
        from models import User
        document_owner = User.query.get(document.user_id)
        if document_owner and document_owner.active_organization_id == user.active_organization_id:
            return True
    
    # Organization members with VIEW_DOCUMENT permission
    if user.active_organization_id and user.has_permission(Permissions.VIEW_DOCUMENT):
        from models import User
        document_owner = User.query.get(document.user_id)
        if document_owner and document_owner.active_organization_id == user.active_organization_id:
            return True
    
    # For shared documents
    if hasattr(document, 'shared_users') and document.shared_users and user.id in [shared_user.id for shared_user in document.shared_users]:
        return True
    
    # For client portal access
    if hasattr(document, 'shared_with_clients') and document.shared_with_clients:
        from models import ClientPortalUser, Client
        if hasattr(user, 'client_id'):  # User is a client portal user
            client = Client.query.get(user.client_id)
            if client and client.id in [client.id for client in document.shared_with_clients]:
                return True
    
    return False

def check_template_access(template, user):
    """
    Check if a user has access to a specific template.
    
    Args:
        template: The template object to check access for
        user: The user attempting to access the template
        
    Returns:
        bool: True if user has access, False otherwise
    """
    # Admins have access to all templates
    if user.role == 'admin':
        return True
    
    # Template owner has access
    if template.user_id == user.id:
        return True
    
    # If template is public, everyone can access
    if hasattr(template, 'is_public') and template.is_public:
        return True
    
    # Organization templates are available to all organization members
    if user.active_organization_id and user.has_permission(Permissions.VIEW_TEMPLATE):
        if hasattr(template, 'organization_id') and template.organization_id == user.active_organization_id:
            return True
        
        # Check if template owner is in same organization
        from models import User
        template_owner = User.query.get(template.user_id)
        if template_owner and template_owner.active_organization_id == user.active_organization_id:
            return True
    
    return False

def organization_member_required(f):
    """
    Decorator to check if current user is an organization member.
    
    Usage:
        @organization_member_required
        def organization_dashboard():
            # Only organization members can access this
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login'))
            
        if not current_user.active_organization_id:
            flash('You need to be a member of an organization to access this page', 'warning')
            return redirect(url_for('dashboard.index'))
            
        return f(*args, **kwargs)
    return decorated_function

def organization_owner_required(f):
    """
    Decorator to check if current user is an organization owner.
    
    Usage:
        @organization_owner_required
        def manage_organization():
            # Only organization owners can access this
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login'))
            
        if not current_user.is_organization_owner() and current_user.role != 'admin':
            flash('You need to be an organization owner to access this page', 'warning')
            return redirect(url_for('dashboard.index'))
            
        return f(*args, **kwargs)
    return decorated_function

def permissions_required(*permissions):
    """
    Decorator to check if current user has all specified permissions.
    
    Args:
        *permissions: Variable number of permissions to check for
        
    Usage:
        @permissions_required(Permissions.VIEW_CASE, Permissions.EDIT_CASE)
        def edit_case(case_id):
            # Only users with both VIEW_CASE and EDIT_CASE permissions can access this
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page', 'warning')
                return redirect(url_for('auth.login'))
                
            for permission in permissions:
                if not current_user.has_permission(permission):
                    flash(f'You do not have the necessary permissions to access this resource', 'error')
                    return redirect(url_for('dashboard.index'))
                    
            return f(*args, **kwargs)
        return decorated_function
    return decorator