from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

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

class User(UserMixin, db.Model):
    """User model representing legal professionals in the system"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    role = db.Column(db.String(20), default='user')  # admin, legal_professional, paralegal
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    cases = db.relationship('Case', backref='assigned_user', lazy='dynamic')
    documents = db.relationship('Document', backref='created_by', lazy='dynamic')
    contracts = db.relationship('Contract', backref='created_by', lazy='dynamic')
    
    def set_password(self, password):
        """Set the user's password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify the user's password"""
        return check_password_hash(self.password_hash, password)
    
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
    
    # Relationships
    cases = db.relationship('Case', secondary=case_client_association, backref='clients')
    contracts = db.relationship('Contract', backref='client', lazy='dynamic')
    
    def __repr__(self):
        return f'<Client {self.name}>'

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    documents = db.relationship('Document', secondary=case_document_association, backref='cases')
    events = db.relationship('Event', backref='case', lazy='dynamic')
    
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
    
    def __repr__(self):
        return f'<Document {self.id}: {self.title}>'

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    def __repr__(self):
        return f'<Event {self.id}: {self.title}>'

class LegalResearch(db.Model):
    """Legal research model for tracking research history and saved research"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    query = db.Column(db.Text, nullable=False)
    results = db.Column(db.Text)
    source = db.Column(db.String(100))  # kenyalaw.org, vector_db, llm, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'))
    
    # Relationships
    user = db.relationship('User', backref='research')
    case = db.relationship('Case', backref='research')
    
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
