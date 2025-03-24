"""
Database migration script for adding role-based permissions.
This adds the Permission, Role, and Organization models and updates User model relationships.
"""
import logging
from app import app, db
from models import Role, Permission, Organization, User

logger = logging.getLogger(__name__)

def migrate_roles_permissions():
    """Add role and permission tables and initialize default roles and permissions"""
    with app.app_context():
        # Create tables if they don't exist
        try:
            # Create the new tables
            db.create_all()
            
            # Initialize default roles and permissions
            Role.init_roles()
            
            # Update existing users to use the new role system
            # Admin users remain admin, all other users get 'individual' role
            users = User.query.all()
            for user in users:
                # Keep role field as is (admin, individual, organization)
                # but make sure it's one of the valid roles
                if user.role not in ['admin', 'individual', 'organization', 'organization_member', 'free']:
                    user.role = 'individual'
            
            db.session.commit()
            logger.info("Role and permission tables created and initialized")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error migrating roles and permissions: {str(e)}")
            return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = migrate_roles_permissions()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed. Check logs for details.")