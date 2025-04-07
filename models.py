from datetime import datetime, timedelta
import json
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from utils.permissions import DEFAULT_ROLE_PERMISSIONS, Permissions

# Association tables for many-to-many relationships
case_client_association = db.Table(
    'case_client_association',
    db.Column('case_id', db.Integer, db.ForeignKey('case.id')),
    db.Column('client_id', db.Integer, db.ForeignKey('client.id'))
)

case_document_association = db.Table(
    'case_document_association',
    db.Column('case_id', db.Integer, db.ForeignKey('case.id')),
    db.Column('document_id', db.Integer, db.ForeignKey('document.id'))
)

# Association table for document sharing
document_sharing_association = db.Table(
    'document_sharing_association',
    db.Column('document_id', db.Integer, db.ForeignKey('document.id')),
    db.Column('client_portal_user_id', db.Integer, db.ForeignKey('client_portal_user.id'))
)

# Association table for role permissions
role_permission_association = db.Table(
    'role_permission_association',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id')),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'))
)

# Association table for user organizations
user_organization_association = db.Table(
    'user_organization_association',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('organization_id', db.Integer, db.ForeignKey('organization.id'))
)

class Permission(db.Model):
    """Permission model defining granular access permissions"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    
    def __repr__(self):
        return f'<Permission {self.name}>'

class Role(db.Model):
    """Role model defining user roles and their permissions"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    is_default = db.Column(db.Boolean, default=False)  # Whether this is a default role
    is_custom = db.Column(db.Boolean, default=False)  # Whether this is a custom role
    
    # Relationships
    permissions = db.relationship('Permission', secondary=role_permission_association, 
                               backref=db.backref('roles', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    @staticmethod
    def init_roles():
        """Initialize default roles and their permissions"""
        # Create all permissions
        for permission_name in Permissions.get_all_permissions():
            description = permission_name.replace('_', ' ').title()
            permission = Permission.query.filter_by(name=permission_name).first()
            if not permission:
                permission = Permission(name=permission_name, description=description)
                db.session.add(permission)
        
        # Create default roles
        for role_name, permissions in DEFAULT_ROLE_PERMISSIONS.items():
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                role = Role(
                    name=role_name,
                    description=f"{role_name.replace('_', ' ').title()} Role",
                    is_default=True
                )
                db.session.add(role)
                
            # Clear existing permissions for this role
            role.permissions = []
            
            # Add permissions to the role
            for permission_name in permissions:
                permission = Permission.query.filter_by(name=permission_name).first()
                if permission:
                    role.permissions.append(permission)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing roles: {str(e)}")

class Organization(db.Model):
    """Organization model for multi-user organizations"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    size = db.Column(db.Integer)  # Number of users
    account_type = db.Column(db.String(20), default='basic')  # basic, premium, enterprise
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    subscription_end = db.Column(db.DateTime)
    
    # Owner foreign key (the user who created the organization)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    owner = db.relationship('User', foreign_keys=[owner_id], backref='owned_organizations')
    members = db.relationship('User', secondary=user_organization_association, 
                             backref=db.backref('organizations', lazy='dynamic'))
                             
    def is_subscription_active(self):
        """Check if the organization has an active subscription"""
        if not self.subscription_end:
            return False
        return self.subscription_end > datetime.utcnow() and self.is_active
    
    def __repr__(self):
        return f'<Organization {self.name}>'

class User(UserMixin, db.Model):
    """User model representing legal professionals in the system"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    role = db.Column(db.String(20), default='individual')  # admin, organization, organization_member, individual
    account_type = db.Column(db.String(20), default='free')  # free, basic, premium, enterprise
    organization_name = db.Column(db.String(100))
    organization_size = db.Column(db.Integer)  # Number of users in organization
    tokens_available = db.Column(db.Integer, default=0)  # Available tokens for AI features
    max_cases = db.Column(db.Integer, default=5)  # Maximum number of cases allowed
    is_active = db.Column(db.Boolean, default=True)  # Account active status
    subscription_end = db.Column(db.DateTime)  # When subscription expires
    phone = db.Column(db.String(20))  # Phone number for SMS notifications
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Role foreign key (for custom roles)
    custom_role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    
    # Active organization (for organization_member users)
    active_organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    
    # Relationships
    cases = db.relationship('Case', backref='assigned_user', lazy='dynamic')
    documents = db.relationship('Document', backref='created_by', lazy='dynamic')
    contracts = db.relationship('Contract', backref='created_by', lazy='dynamic')
    custom_role = db.relationship('Role', foreign_keys=[custom_role_id])
    active_organization = db.relationship('Organization', foreign_keys=[active_organization_id])
    
    def set_password(self, password):
        """Set the user's password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify the user's password"""
        return check_password_hash(self.password_hash, password)
    
    def use_tokens(self, amount):
        """Use tokens for AI features and return True if successful"""
        if self.tokens_available >= amount:
            self.tokens_available -= amount
            return True
        return False
    
    def add_tokens(self, amount):
        """Add tokens to user account"""
        self.tokens_available += amount
        
    def can_create_case(self):
        """Check if user can create more cases"""
        if self.role == 'admin':
            return True
        return self.cases.count() < self.max_cases
    
    def is_subscription_active(self):
        """Check if user's subscription is active"""
        if self.role == 'admin':
            return True
        if self.account_type == 'free':
            return True
        if self.role == 'organization_member' and self.active_organization:
            return self.active_organization.is_subscription_active()
        if not self.subscription_end:
            return False
        return self.subscription_end > datetime.utcnow()
    
    def has_permission(self, permission):
        """Check if user has a specific permission"""
        # Admins have all permissions
        if self.role == 'admin':
            return True
            
        # Check if user has a custom role with this permission
        if self.custom_role_id:
            for perm in self.custom_role.permissions:
                if perm.name == permission:
                    return True
        
        # Check default role permissions
        role_permissions = DEFAULT_ROLE_PERMISSIONS.get(self.role, [])
        return permission in role_permissions
    
    def get_permissions(self):
        """Get all permissions for this user"""
        if self.role == 'admin':
            # Admin has all permissions
            return Permissions.get_all_permissions()
            
        # Start with default role permissions
        permissions = DEFAULT_ROLE_PERMISSIONS.get(self.role, [])
        
        # Add custom role permissions
        if self.custom_role_id:
            for perm in self.custom_role.permissions:
                if perm.name not in permissions:
                    permissions.append(perm.name)
                    
        return permissions
    
    def is_admin(self):
        """Check if user is an admin"""
        return self.role == 'admin'
    
    def is_organization_owner(self):
        """Check if user is an organization owner"""
        if not self.active_organization:
            return False
        return self.active_organization.owner_id == self.id
        
    def get_full_name(self):
        """Get user's full name or username if not available"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        else:
            return self.username
        
    def __repr__(self):
        return f'<User {self.username}>'

class Client(db.Model):
    """Client model representing individuals or organizations associated with cases"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    client_type = db.Column(db.String(20))  # individual, organization, government
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    has_portal_access = db.Column(db.Boolean, default=False)  # Whether client has portal access
    
    # Relationships
    cases = db.relationship('Case', secondary=case_client_association, backref='clients')
    contracts = db.relationship('Contract', backref='client', lazy='dynamic')
    portal_users = db.relationship('ClientPortalUser', backref='client', lazy='dynamic')
    
    def __repr__(self):
        return f'<Client {self.name}>'
        
    def create_portal_user(self, email, password):
        """Create a portal user for this client"""
        if not self.has_portal_access:
            self.has_portal_access = True
            
        # Check if a portal user with this email already exists
        existing_user = ClientPortalUser.query.filter_by(email=email, client_id=self.id).first()
        if existing_user:
            return existing_user
            
        # Create new portal user
        portal_user = ClientPortalUser(
            email=email,
            client_id=self.id,
            is_active=True
        )
        portal_user.set_password(password)
        
        db.session.add(portal_user)
        return portal_user


class ClientPortalUser(UserMixin, db.Model):
    """User model for client portal access"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    access_token = db.Column(db.String(100))  # For secure document links
    token_expiry = db.Column(db.DateTime)  # When the token expires
    
    # Foreign keys
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    
    # Relationships
    shared_documents = db.relationship('Document', secondary=document_sharing_association, 
                                     backref=db.backref('shared_with', lazy='dynamic'))
    
    def set_password(self, password):
        """Set the user's password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify the user's password"""
        return check_password_hash(self.password_hash, password)
        
    def generate_access_token(self):
        """Generate a secure access token for document sharing links"""
        import secrets
        import string
        
        # Generate a secure random token
        alphabet = string.ascii_letters + string.digits
        token = ''.join(secrets.choice(alphabet) for _ in range(64))
        
        # Set token expiry to 30 days from now
        self.access_token = token
        self.token_expiry = datetime.utcnow() + timedelta(days=30)
        
        return token
        
    def is_token_valid(self):
        """Check if the access token is valid"""
        if not self.access_token or not self.token_expiry:
            return False
        return self.token_expiry > datetime.utcnow()
    
    def __repr__(self):
        return f'<ClientPortalUser {self.email}>'

class Case(db.Model):
    """Case model representing legal cases in the Kenyan court system"""
    id = db.Column(db.Integer, primary_key=True)
    case_number = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    court_level = db.Column(db.String(100))  # Supreme, Court of Appeal, High Court, etc.
    case_type = db.Column(db.String(50))  # Civil, Criminal, etc.
    practice_area = db.Column(db.String(100))  # Corporate, Dispute Resolution, etc.
    filing_date = db.Column(db.Date)
    status = db.Column(db.String(20))  # Active, Closed, Pending, etc.
    court_stage = db.Column(db.String(20))  # Filing, Mention, Hearing, Judgment, Appeal
    next_court_date = db.Column(db.DateTime)
    outcome = db.Column(db.Text)  # Outcome of the case when closed
    closing_date = db.Column(db.DateTime)  # Date when case was closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    documents = db.relationship('Document', secondary=case_document_association, backref='cases')
    events = db.relationship('Event', backref='case', lazy='dynamic')
    # Note: milestones relationship is defined in the CaseMilestone model with order_by
    
    def __repr__(self):
        return f'<Case {self.case_number}: {self.title}>'

class Document(db.Model):
    """Document model representing legal documents in the system"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    document_type = db.Column(db.String(50))  # Pleading, Affidavit, Contract, etc.
    content = db.Column(db.Text)
    version = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20))  # Draft, Final, Submitted, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    template_id = db.Column(db.Integer, db.ForeignKey('document_template.id'), nullable=True)
    
    # Relationships
    template = db.relationship('DocumentTemplate', backref='documents')
    
    def __repr__(self):
        return f'<Document {self.id}: {self.title}>'

class DocumentTemplate(db.Model):
    """Template model for document generation"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    template_type = db.Column(db.String(50), nullable=False)  # Pleading, Affidavit, Contract, etc.
    content = db.Column(db.Text, nullable=False)
    is_public = db.Column(db.Boolean, default=False)  # Whether template is available to all users
    placeholder_vars = db.Column(db.Text)  # JSON string of variables used in the template
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    user = db.relationship('User', backref='templates')
    
    def get_variables(self):
        """Get list of variables used in the template"""
        if not self.placeholder_vars:
            return []
        try:
            return json.loads(self.placeholder_vars)
        except:
            return []
    
    def __repr__(self):
        return f'<DocumentTemplate {self.id}: {self.title}>'

class Contract(db.Model):
    """Contract model representing legal contracts in the system"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    contract_type = db.Column(db.String(50))  # Sale, Lease, Employment, etc.
    content = db.Column(db.Text)
    status = db.Column(db.String(20))  # Draft, Review, Negotiation, Executed, Active, Expired
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    key_terms = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    
    def __repr__(self):
        return f'<Contract {self.id}: {self.title}>'

class Event(db.Model):
    """Event model representing calendar events such as court dates and meetings"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_type = db.Column(db.String(50))  # Court Appearance, Meeting, Deadline, etc.
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    location = db.Column(db.String(200))
    priority = db.Column(db.Integer, default=2)  # 1=High, 2=Medium, 3=Low
    is_all_day = db.Column(db.Boolean, default=False)
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_pattern = db.Column(db.String(50))  # daily, weekly, monthly, custom
    recurrence_end_date = db.Column(db.DateTime)
    reminder_sent = db.Column(db.Boolean, default=False)
    reminder_time = db.Column(db.Integer, default=24)  # Hours before event to send reminder
    conflict_status = db.Column(db.String(20))  # potential, confirmed, resolved, none
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Advanced scheduling fields
    is_flexible = db.Column(db.Boolean, default=False)  # Whether this event has flexible timing
    buffer_before = db.Column(db.Integer, default=0)  # Minutes required before the event
    buffer_after = db.Column(db.Integer, default=0)  # Minutes required after the event
    related_event_id = db.Column(db.Integer, db.ForeignKey('event.id'))  # For linking related events
    court_reference_number = db.Column(db.String(100))  # Court-issued reference number
    participants = db.Column(db.Text)  # Stored as JSON list of participant details
    travel_time_minutes = db.Column(db.Integer, default=0)  # Estimated travel time to event location
    notification_preferences = db.Column(db.String(200))  # JSON string of notification preferences
    synchronization_status = db.Column(db.String(50))  # For tracking sync with external calendars
    
    # Foreign keys
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    milestones = db.relationship('CaseMilestone', backref='linked_event', lazy='dynamic')
    related_events = db.relationship('Event', backref=db.backref('parent_event', remote_side=[id]), 
                                    foreign_keys='Event.related_event_id')
    
    def get_duration_minutes(self):
        """Get event duration in minutes"""
        if not self.end_time:
            return 60  # Default to 1 hour if no end time
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 60
    
    def overlaps_with(self, other_event):
        """Check if this event overlaps with another event"""
        # If either event is all-day, they overlap if on the same day
        if self.is_all_day or other_event.is_all_day:
            return self.start_time.date() == other_event.start_time.date()
        
        # Consider buffer times for more accurate conflict detection
        self_start = self.start_time - timedelta(minutes=self.buffer_before or 0)
        self_end = self.end_time + timedelta(minutes=self.buffer_after or 0) if self.end_time else self.start_time + timedelta(hours=1)
        
        other_start = other_event.start_time - timedelta(minutes=other_event.buffer_before or 0)
        other_end = other_event.end_time + timedelta(minutes=other_event.buffer_after or 0) if other_event.end_time else other_event.start_time + timedelta(hours=1)
        
        # Events overlap if one starts before the other ends
        return self_start < other_end and other_start < self_end
               
    def is_court_related(self):
        """Check if this event is related to court proceedings"""
        court_event_types = ['Court Appearance', 'Hearing', 'Mention', 'Filing']
        return self.event_type in court_event_types
    
    def get_total_time_required(self):
        """Calculate total time required for this event including travel and buffers"""
        duration = self.get_duration_minutes()
        return duration + (self.buffer_before or 0) + (self.buffer_after or 0) + (self.travel_time_minutes or 0)
    
    def get_participants_list(self):
        """Get participants as a Python list"""
        if not self.participants:
            return []
        try:
            return json.loads(self.participants)
        except:
            return []
            
    def get_conflict_severity(self, other_event):
        """
        Calculate the severity of a conflict with another event
        Returns: critical, significant, or minor
        """
        # Calculate overlap duration in minutes
        self_start = self.start_time - timedelta(minutes=self.buffer_before or 0)
        self_end = self.end_time + timedelta(minutes=self.buffer_after or 0) if self.end_time else self.start_time + timedelta(hours=1)
        
        other_start = other_event.start_time - timedelta(minutes=other_event.buffer_before or 0)
        other_end = other_event.end_time + timedelta(minutes=other_event.buffer_after or 0) if other_event.end_time else other_event.start_time + timedelta(hours=1)
        
        # Calculate the overlap period
        overlap_start = max(self_start, other_start)
        overlap_end = min(self_end, other_end)
        overlap_minutes = (overlap_end - overlap_start).total_seconds() / 60
        
        # Determine severity based on event types, priority, and overlap duration
        both_court_related = self.is_court_related() and other_event.is_court_related()
        either_high_priority = self.priority == 1 or other_event.priority == 1
        
        if both_court_related:
            return "critical"  # Two court events overlapping is always critical
        elif overlap_minutes > 30 and either_high_priority:
            return "critical"  # Major overlap with high priority event
        elif overlap_minutes > 15:
            return "significant"  # Moderate overlap
        else:
            return "minor"  # Minor overlap
            
    def get_suggested_alternatives(self, date):
        """
        Get suggested alternative times on the same day
        Returns list of datetime objects representing possible start times
        """
        from datetime import datetime, time
        
        # Start with standard business hours (8am to 5pm)
        business_start = time(8, 0)
        business_end = time(17, 0)
        
        # For court events, prefer morning slots (courts typically have more hearings in the mornings)
        if self.is_court_related():
            preferred_slots = [
                datetime.combine(date, time(9, 0)),
                datetime.combine(date, time(10, 0)),
                datetime.combine(date, time(11, 0)),
                datetime.combine(date, time(14, 0)),
                datetime.combine(date, time(15, 0))
            ]
        else:
            # For general events, offer evenly spaced slots
            preferred_slots = [
                datetime.combine(date, time(9, 0)),
                datetime.combine(date, time(11, 0)),
                datetime.combine(date, time(13, 0)),
                datetime.combine(date, time(15, 0)),
                datetime.combine(date, time(16, 0))
            ]
            
        # Add the next day as an option if this is flexible
        if self.is_flexible:
            next_day = date + timedelta(days=1)
            preferred_slots.append(datetime.combine(next_day, time(9, 0)))
            
        return preferred_slots
        
    def get_notification_recipients(self):
        """Get a list of notification recipients based on event type and participants"""
        recipients = []
        
        # Always include the event owner
        if hasattr(self, 'user') and self.user and self.user.email:
            recipients.append({
                'name': self.user.name if hasattr(self.user, 'name') else 'User',
                'email': self.user.email,
                'role': 'owner'
            })
            
        # Include case participants if this is a case-related event
        if self.case_id and hasattr(self, 'case') and self.case:
            # Add client
            if hasattr(self.case, 'client') and self.case.client and self.case.client.email:
                recipients.append({
                    'name': self.case.client.name,
                    'email': self.case.client.email,
                    'role': 'client'
                })
                
        # Add any additional participants specified in the event
        participant_list = self.get_participants_list()
        for participant in participant_list:
            if isinstance(participant, dict) and 'email' in participant:
                recipients.append(participant)
                
        return recipients
    
    def add_participant(self, name, role=None, email=None, phone=None):
        """Add a participant to this event"""
        participants = self.get_participants_list()
        participants.append({
            'name': name,
            'role': role,
            'email': email,
            'phone': phone
        })
        self.participants = json.dumps(participants)
        
    def get_notification_settings(self):
        """Get notification preferences as a Python dict"""
        if not self.notification_preferences:
            return {'email': True, 'sms': False, 'in_app': True}
        try:
            return json.loads(self.notification_preferences)
        except:
            return {'email': True, 'sms': False, 'in_app': True}
    
    def __repr__(self):
        return f'<Event {self.id}: {self.title}>'
        
        
class CaseMilestone(db.Model):
    """Model for tracking important milestones in a case's timeline"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    milestone_type = db.Column(db.String(50))  # Filing, Hearing, Decision, etc.
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, delayed
    order_index = db.Column(db.Integer, default=0)  # For ordering milestones in timeline
    target_date = db.Column(db.DateTime)  # Expected completion date
    completion_date = db.Column(db.DateTime)  # Actual completion date
    is_critical = db.Column(db.Boolean, default=False)  # Whether this is a critical milestone
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'))
    
    # Relationships
    case = db.relationship('Case', backref=db.backref('milestones', lazy='dynamic', order_by='CaseMilestone.order_index'))
    linked_document = db.relationship('Document', backref='milestones')
    
    def is_completed(self):
        """Check if milestone is completed"""
        return self.status == 'completed' and self.completion_date is not None
    
    def days_remaining(self):
        """Return days remaining until target date, negative if overdue"""
        if not self.target_date:
            return None
        now = datetime.utcnow().date()
        target = self.target_date.date()
        return (target - now).days
    
    def is_delayed(self):
        """Check if milestone is delayed (target date passed but not completed)"""
        if self.status == 'completed':
            return False
        if not self.target_date:
            return False
        return self.target_date.date() < datetime.utcnow().date()
    
    def __repr__(self):
        return f'<CaseMilestone {self.id}: {self.title}>'

class LegalResearch(db.Model):
    """Legal research model for tracking research history and saved research"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    query = db.Column(db.Text, nullable=False)
    results = db.Column(db.Text)  # JSON string of results
    source = db.Column(db.String(100))  # kenyalaw.org, vector_db, llm, etc.
    court_filter = db.Column(db.String(50))  # Court code filter (e.g. KESC, KECA)
    result_count = db.Column(db.Integer, default=0)  # Number of results found
    has_arguments = db.Column(db.Boolean, default=False)  # Whether this research includes arguments
    has_rebuttals = db.Column(db.Boolean, default=False)  # Whether this research includes rebuttals
    tokens_used = db.Column(db.Integer, default=0)  # Number of tokens used for this research
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'))
    
    # Relationships
    user = db.relationship('User', backref='research')
    case = db.relationship('Case', backref='research')
    
    def get_results_list(self):
        """Get results as a list of dictionaries"""
        if not self.results:
            return []
        try:
            return json.loads(self.results)
        except:
            return []
            
    def get_summary(self):
        """Generate a summary of the research results"""
        if not self.results:
            return "No results available."
            
        try:
            results_data = self.get_results_list()
            
            # Handle different result formats based on source
            if self.source == "kenyalaw.org":
                cases = results_data.get('cases', [])
                legislation = results_data.get('legislation', [])
                
                case_count = len(cases)
                legislation_count = len(legislation)
                
                summary = f"Found {case_count} cases and {legislation_count} legislation items"
                
                if self.court_filter:
                    summary += f" filtered by court: {self.court_filter}"
                    
                return summary
                
            elif self.source == "ai_research":
                analysis = results_data.get('analysis', '')
                result_count = len(results_data.get('results', []))
                arguments = results_data.get('arguments', [])
                rebuttals = results_data.get('rebuttals', [])
                
                summary_parts = []
                
                if analysis and len(analysis) > 200:
                    # Truncate long analysis
                    analysis_summary = analysis[:200] + "..."
                else:
                    analysis_summary = analysis
                
                summary_parts.append(f"AI Research with {result_count} results")
                
                if analysis_summary:
                    summary_parts.append(f"Analysis: {analysis_summary}")
                
                if arguments and len(arguments) > 0:
                    summary_parts.append(f"{len(arguments)} legal arguments")
                    
                if rebuttals and len(rebuttals) > 0:
                    summary_parts.append(f"{len(rebuttals)} rebuttals to opposition")
                
                return ". ".join(summary_parts)
                
            elif self.source == "ai_analysis":
                doc_type = results_data.get('document_type', 'Unknown document')
                has_arguments = "arguments" in results_data and len(results_data.get('arguments', [])) > 0
                
                summary = f"Analysis of {doc_type} document"
                if has_arguments:
                    summary += f" with {len(results_data.get('arguments', []))} potential arguments"
                    
                return summary
                
            elif self.source == "precedent_search":
                binding = results_data.get('binding_precedents', [])
                persuasive = results_data.get('persuasive_precedents', [])
                arguments = results_data.get('arguments', [])
                
                summary_parts = [f"Found {len(binding)} binding and {len(persuasive)} persuasive precedents"]
                
                if arguments and len(arguments) > 0:
                    summary_parts.append(f"{len(arguments)} potential arguments based on precedents")
                    
                return ". ".join(summary_parts)
                
            elif self.source == "legal_arguments":
                arguments = results_data.get('arguments', [])
                rebuttals = results_data.get('rebuttals', [])
                evidence = results_data.get('evidence', [])
                
                summary_parts = []
                
                if arguments and len(arguments) > 0:
                    summary_parts.append(f"{len(arguments)} legal arguments")
                    
                if rebuttals and len(rebuttals) > 0:
                    summary_parts.append(f"{len(rebuttals)} rebuttals")
                    
                if evidence and len(evidence) > 0:
                    summary_parts.append(f"{len(evidence)} pieces of evidence")
                    
                if not summary_parts:
                    return "Legal argument analysis"
                    
                return ". ".join(summary_parts)
                
            else:
                # Generic fallback
                return f"Research with {self.result_count} results from {self.source}"
                
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def __repr__(self):
        return f'<LegalResearch {self.id}: {self.title}>'

class LegalCitation(db.Model):
    """Legal citation model for tracking citations used in documents"""
    id = db.Column(db.Integer, primary_key=True)
    citation_text = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(100))  # Case citation, Act of Parliament, etc.
    url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'))
    
    # Relationships
    document = db.relationship('Document', backref='citations')
    
    def __repr__(self):
        return f'<LegalCitation {self.id}: {self.source}>'
        
class Subscription(db.Model):
    """Subscription plans available in the system"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)  # free, basic, premium, enterprise
    price = db.Column(db.Float, nullable=False)  # Price in Kenyan Shillings
    duration_days = db.Column(db.Integer, default=30)  # Subscription duration in days
    max_cases = db.Column(db.Integer, default=5)  # Maximum number of cases
    tokens_included = db.Column(db.Integer, default=0)  # Tokens included in subscription
    is_organization = db.Column(db.Boolean, default=False)  # Whether this is for organizations
    max_users = db.Column(db.Integer, default=1)  # For organization plans
    is_active = db.Column(db.Boolean, default=True)  # Whether this plan is available
    features = db.Column(db.Text)  # JSON string of features
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Subscription {self.name}>'
        
class TokenPackage(db.Model):
    """Available token packages for purchase"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # Small, Medium, Large
    token_count = db.Column(db.Integer, nullable=False)  # Number of tokens
    price = db.Column(db.Float, nullable=False)  # Price in Kenyan Shillings
    is_active = db.Column(db.Boolean, default=True)  # Whether this package is available
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<TokenPackage {self.name}: {self.token_count} tokens>'
        
class Payment(db.Model):
    """Payment records for subscriptions and token purchases"""
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)  # Amount in Kenyan Shillings
    payment_type = db.Column(db.String(20), nullable=False)  # subscription, tokens
    payment_method = db.Column(db.String(20))  # pesapal, manual, etc.
    transaction_id = db.Column(db.String(100), unique=True)  # External transaction ID
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    payment_data = db.Column(db.Text)  # JSON string with payment details
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'))
    token_package_id = db.Column(db.Integer, db.ForeignKey('token_package.id'))
    
    # Relationships
    user = db.relationship('User', backref='payments')
    subscription = db.relationship('Subscription', backref='payments')
    token_package = db.relationship('TokenPackage', backref='payments')
    
    def __repr__(self):
        return f'<Payment {self.id}: {self.amount} KES ({self.status})>'
        
class TokenUsage(db.Model):
    """Records of token usage for tracking and analytics"""
    id = db.Column(db.Integer, primary_key=True)
    tokens_used = db.Column(db.Integer, nullable=False)
    feature = db.Column(db.String(50), nullable=False)  # research, document_generation, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='token_usage')
    
    def __repr__(self):
        return f'<TokenUsage {self.id}: {self.tokens_used} tokens for {self.feature}>'

# Gamification Models
class UserProfile(db.Model):
    """User profile with gamification stats"""
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.Integer, default=1)
    total_points = db.Column(db.Integer, default=0)
    title = db.Column(db.String(100), default='Legal Novice')
    streak_days = db.Column(db.Integer, default=0)
    longest_streak = db.Column(db.Integer, default=0)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    last_reward_claim = db.Column(db.DateTime)
    total_cases_managed = db.Column(db.Integer, default=0)
    total_documents_created = db.Column(db.Integer, default=0)
    total_research_conducted = db.Column(db.Integer, default=0)
    total_tokens_earned = db.Column(db.Integer, default=0)
    social_shares = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('profile', uselist=False))
    
    def add_points(self, points):
        """Add points and update level if necessary"""
        # Initialize total_points if None
        if self.total_points is None:
            self.total_points = 0
            
        self.total_points += points
        
        # Update level (simple level calculation based on points)
        new_level = 1 + (self.total_points // 100)  # Level up every 100 points
        
        # Initialize level if None
        if self.level is None:
            self.level = 1
            
        if new_level > self.level:
            self.level = new_level
            # Update title based on level
            self.update_title()
        
        return self.level
    
    def update_streak(self):
        """Update login streak if user was active in the last 36 hours"""
        now = datetime.utcnow()
        if self.last_active and (now - self.last_active) < timedelta(hours=36):
            # If last active within 36 hours but on a different day
            if self.last_active.date() < now.date():
                self.streak_days += 1
                # Update longest streak if current streak is longer
                if self.longest_streak is None or self.streak_days > self.longest_streak:
                    self.longest_streak = self.streak_days
        else:
            # Reset streak if more than 36 hours have passed
            self.streak_days = 1
        
        self.last_active = now
        
    def can_claim_daily_reward(self):
        """Check if user can claim daily reward"""
        if not self.last_reward_claim:
            return True
            
        now = datetime.utcnow()
        return self.last_reward_claim.date() < now.date()
        
    def claim_daily_reward(self):
        """Claim daily reward and return the amount of tokens earned"""
        # Base tokens for daily rewards
        base_tokens = 2
        
        # Calculate streak bonus based on thresholds
        streak_bonus = 0
        if self.streak_days >= 7:
            streak_bonus = 3
        elif self.streak_days >= 5:
            streak_bonus = 2
        elif self.streak_days >= 3:
            streak_bonus = 1
        
        # Total tokens earned
        tokens_earned = base_tokens + streak_bonus
        
        # Update user's tokens
        self.user.add_tokens(tokens_earned)
        self.total_tokens_earned += tokens_earned
        self.last_reward_claim = datetime.utcnow()
        
        # Check if the streak is a multiple of 7 for achievement tracking
        is_special_streak = (self.streak_days == 7 or self.streak_days == 14 or self.streak_days == 21 
                            or self.streak_days == 30)
            
        return tokens_earned
    
    def update_title(self):
        """Update user title based on level"""
        titles = {
            1: 'Legal Novice',
            2: 'Law Apprentice',
            3: 'Legal Assistant',
            4: 'Junior Advocate',
            5: 'Associate Advocate',
            6: 'Senior Associate',
            7: 'Legal Expert',
            8: 'Seasoned Advocate',
            9: 'Legal Strategist',
            10: 'Master Advocate',
            15: 'Legal Virtuoso',
            20: 'Legal Luminary',
            25: 'Legal Titan'
        }
        
        # Find the highest level title the user qualifies for
        for level in sorted(titles.keys(), reverse=True):
            if self.level >= level:
                self.title = titles[level]
                break
    
    def __repr__(self):
        return f'<UserProfile {self.user_id}: Level {self.level} - {self.title}>'

class Achievement(db.Model):
    """System achievements that users can earn"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))  # case, document, research, general
    points = db.Column(db.Integer, default=10)
    icon = db.Column(db.String(100))  # Icon CSS class or filename
    requirement = db.Column(db.Text)  # JSON string of requirements
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Achievement {self.name}>'
    
    def get_requirements(self):
        """Get achievement requirements as dictionary"""
        if not self.requirement:
            return {}
        return json.loads(self.requirement)

class UserAchievement(db.Model):
    """Achievements earned by users"""
    id = db.Column(db.Integer, primary_key=True)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='achievements')
    achievement = db.relationship('Achievement')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'achievement_id'),)
    
    def __repr__(self):
        return f'<UserAchievement {self.user_id} - {self.achievement_id}>'

class Activity(db.Model):
    """User activity for gamification tracking"""
    id = db.Column(db.Integer, primary_key=True)
    activity_type = db.Column(db.String(50), nullable=False)  # login, create_case, etc.
    description = db.Column(db.String(200))
    points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='activities')
    
    def __repr__(self):
        return f'<Activity {self.id}: {self.activity_type} by User {self.user_id}>'

class Challenge(db.Model):
    """Time-limited challenges for users to complete"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    challenge_type = db.Column(db.String(50))  # daily, weekly, custom
    points = db.Column(db.Integer, default=20)
    requirements = db.Column(db.Text)  # JSON string of requirements
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Challenge {self.id}: {self.title}>'
    
    def get_requirements(self):
        """Get challenge requirements as dictionary"""
        if not self.requirements:
            return {}
        return json.loads(self.requirements)
    
    def is_ongoing(self):
        """Check if challenge is currently active"""
        now = datetime.utcnow()
        return (self.start_date <= now <= self.end_date) and self.is_active

class UserChallenge(db.Model):
    """Challenges accepted or completed by users"""
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default='accepted')  # accepted, completed, expired
    progress = db.Column(db.Text)  # JSON string of progress stats
    accepted_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'), nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='challenges')
    challenge = db.relationship('Challenge')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'challenge_id'),)
    
    def get_progress(self):
        """Get progress as dictionary"""
        if not self.progress:
            return {}
        return json.loads(self.progress)
    
    def update_progress(self, progress_data):
        """Update progress with new data"""
        current = self.get_progress()
        current.update(progress_data)
        self.progress = json.dumps(current)
    
    def __repr__(self):
        return f'<UserChallenge {self.id}: {self.status}>'

# Ruling-related association tables
ruling_tag_association = db.Table('ruling_tag',
    db.Column('ruling_id', db.Integer, db.ForeignKey('ruling.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

ruling_judge_association = db.Table('ruling_judge',
    db.Column('ruling_id', db.Integer, db.ForeignKey('ruling.id'), primary_key=True),
    db.Column('judge_id', db.Integer, db.ForeignKey('judge.id'), primary_key=True)
)

class Ruling(db.Model):
    """Ruling model representing judicial decisions from Kenyan courts"""
    id = db.Column(db.Integer, primary_key=True)
    case_number = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    court = db.Column(db.String(100), nullable=False)  # Supreme Court, Court of Appeal, etc.
    date_of_ruling = db.Column(db.Date, nullable=False)
    citation = db.Column(db.String(200))  # Official citation
    url = db.Column(db.String(500))  # URL to the original ruling
    summary = db.Column(db.Text)  # Brief summary of the ruling
    full_text = db.Column(db.Text)  # Full text of the ruling
    outcome = db.Column(db.String(50))  # Allowed, Dismissed, etc.
    category = db.Column(db.String(100))  # Constitutional, Criminal, Civil, etc.
    importance_score = db.Column(db.Integer)  # 1-10 importance score
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_landmark = db.Column(db.Boolean, default=False)  # Whether this is a landmark case
    
    # Relationships
    tags = db.relationship('Tag', secondary=ruling_tag_association, backref=db.backref('rulings', lazy='dynamic'))
    judges = db.relationship('Judge', secondary=ruling_judge_association, backref=db.backref('rulings', lazy='dynamic'))
    references = db.relationship('RulingReference', backref='source_ruling', lazy='dynamic', 
                                 foreign_keys='RulingReference.source_ruling_id')
    annotations = db.relationship('RulingAnnotation', backref='ruling', lazy='dynamic')
    analyses = db.relationship('RulingAnalysis', backref='ruling', lazy='dynamic')
    
    # User who added or imported this ruling
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('rulings', lazy='dynamic'))

    def __repr__(self):
        return f'<Ruling {self.case_number} - {self.title[:30]}>'

class Judge(db.Model):
    """Judge model representing judges who have delivered rulings"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    title = db.Column(db.String(50))  # Chief Justice, Justice, etc.
    court = db.Column(db.String(100))  # Supreme Court, Court of Appeal, etc.
    bio = db.Column(db.Text)
    photo_url = db.Column(db.String(500))
    start_date = db.Column(db.Date)  # When they started as a judge
    end_date = db.Column(db.Date)  # When they retired/ended (if applicable)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Judge {self.name}>'
        
class Tag(db.Model):
    """Tag model for categorizing rulings by legal concepts"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('tag.id'))  # For hierarchical tags
    
    # Self-referential relationship for hierarchical tags
    children = db.relationship('Tag', 
                              backref=db.backref('parent', remote_side=[id]),
                              lazy='dynamic')
    
    def __repr__(self):
        return f'<Tag {self.name}>'

class RulingReference(db.Model):
    """Model for tracking references between rulings (citations)"""
    id = db.Column(db.Integer, primary_key=True)
    source_ruling_id = db.Column(db.Integer, db.ForeignKey('ruling.id'), nullable=False)
    target_ruling_id = db.Column(db.Integer, db.ForeignKey('ruling.id'), nullable=False)
    reference_type = db.Column(db.String(50))  # followed, distinguished, overruled, etc.
    context = db.Column(db.Text)  # Context of the reference
    
    # Reference to the target ruling
    target_ruling = db.relationship('Ruling', foreign_keys=[target_ruling_id])
    
    def __repr__(self):
        return f'<RulingReference {self.source_ruling_id} -> {self.target_ruling_id}>'

class RulingAnnotation(db.Model):
    """User annotations on rulings for private notes"""
    id = db.Column(db.Integer, primary_key=True)
    ruling_id = db.Column(db.Integer, db.ForeignKey('ruling.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_private = db.Column(db.Boolean, default=True)  # Whether the annotation is private to the user
    
    user = db.relationship('User', backref=db.backref('ruling_annotations', lazy='dynamic'))
    
    def __repr__(self):
        return f'<RulingAnnotation by {self.user_id} on {self.ruling_id}>'

class RulingAnalysis(db.Model):
    """AI analysis of rulings for trend analysis"""
    id = db.Column(db.Integer, primary_key=True)
    ruling_id = db.Column(db.Integer, db.ForeignKey('ruling.id'), nullable=False)
    analysis_type = db.Column(db.String(50))  # sentiment, precedent, impact, etc.
    result = db.Column(db.Text)  # JSON or text result of the analysis
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<RulingAnalysis {self.analysis_type} for {self.ruling_id}>'
