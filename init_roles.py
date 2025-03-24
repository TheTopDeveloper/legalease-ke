"""
Initialize default roles and permissions for the system.
Run this script after setting up the database to add initial roles and permissions.
"""
import logging
import inspect
from app import app, db
from models import Role, Permission
from utils.permissions import Permissions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_roles_and_permissions():
    """Initialize default roles and permissions"""
    
    # First, create all permissions
    logger.info("Creating permissions...")
    
    # Get all permission constants from the Permissions class
    permissions_list = []
    for name, value in inspect.getmembers(Permissions):
        if not name.startswith('_') and isinstance(value, str) and name.isupper():
            permissions_list.append(value)
    
    for permission_name in permissions_list:
        # Check if permission already exists
        permission = Permission.query.filter_by(name=permission_name).first()
        if not permission:
            # Create permission with a description
            description = permission_name.replace('_', ' ').title()
            permission = Permission(name=permission_name, description=description)
            db.session.add(permission)
            logger.info(f"Created permission: {permission_name}")
    
    # Commit permissions
    db.session.commit()
    logger.info(f"Created {len(permissions_list)} permissions")
    
    # Create default roles
    logger.info("Creating default roles...")
    
    # Admin role with all permissions
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(
            name='admin',
            description='Administrator with full system access',
            is_default=True
        )
        # Get all permissions
        all_permissions = Permission.query.all()
        admin_role.permissions = all_permissions
        db.session.add(admin_role)
        logger.info("Created admin role with all permissions")
    
    # Organization Owner role
    org_owner_role = Role.query.filter_by(name='organization_owner').first()
    if not org_owner_role:
        org_owner_role = Role(
            name='organization_owner',
            description='Organization owner with management permissions',
            is_default=True
        )
        # Add organization management permissions
        permissions = Permission.query.filter(
            Permission.name.in_([
                Permissions.VIEW_CASE,
                Permissions.CREATE_CASE,
                Permissions.EDIT_CASE,
                Permissions.DELETE_CASE,
                Permissions.VIEW_DOCUMENT,
                Permissions.CREATE_DOCUMENT,
                Permissions.EDIT_DOCUMENT,
                Permissions.DELETE_DOCUMENT,
                Permissions.VIEW_TEMPLATE,
                Permissions.CREATE_TEMPLATE,
                Permissions.EDIT_TEMPLATE,
                Permissions.DELETE_TEMPLATE,
                Permissions.VIEW_CLIENT,
                Permissions.CREATE_CLIENT,
                Permissions.EDIT_CLIENT,
                Permissions.DELETE_CLIENT,
                Permissions.VIEW_EVENT,
                Permissions.CREATE_EVENT,
                Permissions.EDIT_EVENT,
                Permissions.DELETE_EVENT,
                Permissions.BASIC_RESEARCH,
                Permissions.ADVANCED_RESEARCH,
                Permissions.VIEW_USERS,
                Permissions.CREATE_USER,
                Permissions.EDIT_USER,
                Permissions.DELETE_USER,
                Permissions.ASSIGN_ROLE,
                Permissions.USE_WRITING_ASSISTANT,
            ])
        ).all()
        org_owner_role.permissions = permissions
        db.session.add(org_owner_role)
        logger.info("Created organization owner role")
    
    # Organization Member role
    org_member_role = Role.query.filter_by(name='organization_member').first()
    if not org_member_role:
        org_member_role = Role(
            name='organization_member',
            description='Organization member with limited permissions',
            is_default=True
        )
        # Add basic permissions
        permissions = Permission.query.filter(
            Permission.name.in_([
                Permissions.VIEW_CASE,
                Permissions.CREATE_CASE,
                Permissions.EDIT_CASE,
                Permissions.VIEW_DOCUMENT,
                Permissions.CREATE_DOCUMENT,
                Permissions.EDIT_DOCUMENT,
                Permissions.VIEW_TEMPLATE,
                Permissions.USE_WRITING_ASSISTANT,
                Permissions.VIEW_CLIENT,
                Permissions.CREATE_CLIENT,
                Permissions.EDIT_CLIENT,
                Permissions.VIEW_EVENT,
                Permissions.CREATE_EVENT,
                Permissions.EDIT_EVENT,
                Permissions.BASIC_RESEARCH,
            ])
        ).all()
        org_member_role.permissions = permissions
        db.session.add(org_member_role)
        logger.info("Created organization member role")
    
    # Individual User role
    individual_role = Role.query.filter_by(name='individual').first()
    if not individual_role:
        individual_role = Role(
            name='individual',
            description='Individual user with personal permissions',
            is_default=True
        )
        # Add basic permissions
        permissions = Permission.query.filter(
            Permission.name.in_([
                Permissions.VIEW_CASE,
                Permissions.CREATE_CASE,
                Permissions.EDIT_CASE,
                Permissions.DELETE_CASE,
                Permissions.VIEW_DOCUMENT,
                Permissions.CREATE_DOCUMENT,
                Permissions.EDIT_DOCUMENT,
                Permissions.DELETE_DOCUMENT,
                Permissions.VIEW_TEMPLATE,
                Permissions.CREATE_TEMPLATE,
                Permissions.EDIT_TEMPLATE,
                Permissions.DELETE_TEMPLATE,
                Permissions.VIEW_CLIENT,
                Permissions.CREATE_CLIENT,
                Permissions.EDIT_CLIENT,
                Permissions.DELETE_CLIENT,
                Permissions.VIEW_EVENT,
                Permissions.CREATE_EVENT,
                Permissions.EDIT_EVENT,
                Permissions.DELETE_EVENT,
                Permissions.BASIC_RESEARCH,
                Permissions.USE_WRITING_ASSISTANT,
            ])
        ).all()
        individual_role.permissions = permissions
        db.session.add(individual_role)
        logger.info("Created individual role")
    
    # Commit all roles
    db.session.commit()
    logger.info("Default roles and permissions created successfully")

if __name__ == "__main__":
    with app.app_context():
        init_roles_and_permissions()