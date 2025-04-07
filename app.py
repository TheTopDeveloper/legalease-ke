import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create base for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

# Create Flask application
app = Flask(__name__)

# Load configuration
app.config.from_object("config")
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///kenyalaw.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions with app
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = "auth.login"

# Create database tables within app context
with app.app_context():
    # Import models here to avoid circular imports
    from models import (
        User, Case, Document, DocumentTemplate, Contract, Client, Event, LegalResearch,
        LegalCitation, Subscription, TokenPackage, Payment, TokenUsage,
        UserProfile, Achievement, UserAchievement, Activity, Challenge, UserChallenge,
        # Ruling database models
        Ruling, Judge, Tag, RulingReference, RulingAnnotation, RulingAnalysis,
        # Client portal models
        ClientPortalUser,
        # Case milestone models
        CaseMilestone
    )
    db.create_all()
    logger.info("Database tables created")

# Register blueprints
from routes.auth import auth_bp
from routes.cases import cases_bp
from routes.documents import documents_bp
from routes.research import research_bp
from routes.contracts import contracts_bp
from routes.dashboard import dashboard_bp
from routes.billing import billing_bp
from routes.gamification import gamification_bp
from routes.notifications import notifications_bp
from routes.templates import templates_bp
from routes.events import events_bp
from routes.writing_assistant import writing_bp
from routes.admin import admin_bp
from routes.rulings import rulings_bp
from routes.client_portal import client_portal_bp
from routes.document_sharing import document_sharing_bp
from routes.milestone import milestone_bp

app.register_blueprint(auth_bp)
app.register_blueprint(cases_bp)
app.register_blueprint(documents_bp)
app.register_blueprint(research_bp)
app.register_blueprint(contracts_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(billing_bp)
app.register_blueprint(gamification_bp)
app.register_blueprint(notifications_bp)
app.register_blueprint(templates_bp)
app.register_blueprint(events_bp)
app.register_blueprint(writing_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(rulings_bp, url_prefix='/rulings')
app.register_blueprint(client_portal_bp)
app.register_blueprint(document_sharing_bp)
app.register_blueprint(milestone_bp)

# Load user loader callback
from models import User, ClientPortalUser

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID - works for both User and ClientPortalUser"""
    # Try loading as regular user first
    user = User.query.get(int(user_id))
    if user:
        return user
    
    # If not found, try as client portal user
    return ClientPortalUser.query.get(int(user_id))

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return "Page not found", 404

@app.errorhandler(500)
def internal_server_error(e):
    return "Internal server error", 500
