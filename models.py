from datetime import datetime, timedelta
import json
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
    role = db.Column(db.String(20), default='individual')  # admin, organization, individual
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
        if not self.subscription_end:
            return False
        return self.subscription_end > datetime.utcnow()
        
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
        # Calculate tokens based on streak
        tokens_map = {
            1: 5,   # Day 1: 5 tokens
            2: 5,   # Day 2: 5 tokens
            3: 10,  # Day 3: 10 tokens
            4: 10,  # Day 4: 10 tokens
            5: 15,  # Day 5: 15 tokens
            6: 15,  # Day 6: 15 tokens
            7: 25,  # Day 7: 25 tokens (Bonus day)
        }
        
        day = min(self.streak_days, 7)
        tokens_earned = tokens_map.get(day, 5)  # Default to 5 tokens
        
        # Update user's tokens
        self.user.tokens_available += tokens_earned
        self.total_tokens_earned += tokens_earned
        self.last_reward_claim = datetime.utcnow()
        
        # Reset streak after day 7
        if self.streak_days >= 7:
            self.streak_days = 0
            
        return {
            'tokens': tokens_earned,
            'is_bonus_day': day == 7,
            'streak_day': day
        }
    
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
