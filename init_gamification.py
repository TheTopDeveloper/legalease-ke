"""
Initialize database with default gamification achievements and challenges.
Run this script after setting up the database to add initial data.
"""
import json
from datetime import datetime, timedelta
import logging
from app import app, db
from models import Achievement, Challenge

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_achievements():
    """Create default achievements"""
    achievements = [
        # General achievements
        {
            'name': 'First Login',
            'description': 'Log into the system for the first time',
            'category': 'general',
            'points': 5,
            'icon': 'bi bi-door-open',
            'requirement': json.dumps({})
        },
        {
            'name': 'Profile Completer',
            'description': 'Complete your user profile with all information',
            'category': 'general',
            'points': 15,
            'icon': 'bi bi-person-check',
            'requirement': json.dumps({})
        },
        {
            'name': 'Consistent Professional',
            'description': 'Maintain a login streak of 5 days',
            'category': 'general',
            'points': 20,
            'icon': 'bi bi-calendar-check',
            'requirement': json.dumps({'min_streak': 5})
        },
        {
            'name': 'Legal Expert',
            'description': 'Reach level 5',
            'category': 'general',
            'points': 30,
            'icon': 'bi bi-award',
            'requirement': json.dumps({'min_level': 5})
        },
        
        # Case achievements
        {
            'name': 'Case Novice',
            'description': 'Create your first legal case',
            'category': 'case',
            'points': 10,
            'icon': 'bi bi-folder-plus',
            'requirement': json.dumps({'min_cases': 1})
        },
        {
            'name': 'Case Manager',
            'description': 'Manage 5 different legal cases',
            'category': 'case',
            'points': 25,
            'icon': 'bi bi-folder2-open',
            'requirement': json.dumps({'min_cases': 5})
        },
        {
            'name': 'Case Expert',
            'description': 'Manage 20 different legal cases',
            'category': 'case',
            'points': 50,
            'icon': 'bi bi-briefcase',
            'requirement': json.dumps({'min_cases': 20})
        },
        
        # Document achievements
        {
            'name': 'Document Author',
            'description': 'Create your first legal document',
            'category': 'document',
            'points': 10,
            'icon': 'bi bi-file-earmark-text',
            'requirement': json.dumps({'min_documents': 1})
        },
        {
            'name': 'Prolific Writer',
            'description': 'Create 10 different legal documents',
            'category': 'document',
            'points': 25,
            'icon': 'bi bi-file-earmark-richtext',
            'requirement': json.dumps({'min_documents': 10})
        },
        {
            'name': 'Document Master',
            'description': 'Create 30 different legal documents',
            'category': 'document',
            'points': 50,
            'icon': 'bi bi-file-earmark-check',
            'requirement': json.dumps({'min_documents': 30})
        },
        
        # Research achievements
        {
            'name': 'Legal Researcher',
            'description': 'Conduct your first legal research',
            'category': 'research',
            'points': 10,
            'icon': 'bi bi-search',
            'requirement': json.dumps({'min_research': 1})
        },
        {
            'name': 'Research Explorer',
            'description': 'Conduct 5 different legal research queries',
            'category': 'research',
            'points': 25,
            'icon': 'bi bi-book',
            'requirement': json.dumps({'min_research': 5})
        },
        {
            'name': 'Research Scholar',
            'description': 'Conduct 15 different legal research queries',
            'category': 'research',
            'points': 50,
            'icon': 'bi bi-journal-check',
            'requirement': json.dumps({'min_research': 15})
        },
        
        # Point-based achievements
        {
            'name': 'Point Collector',
            'description': 'Earn 100 points',
            'category': 'general',
            'points': 20,
            'icon': 'bi bi-graph-up',
            'requirement': json.dumps({'min_points': 100})
        },
        {
            'name': 'Point Gatherer',
            'description': 'Earn 500 points',
            'category': 'general',
            'points': 30,
            'icon': 'bi bi-graph-up-arrow',
            'requirement': json.dumps({'min_points': 500})
        },
        {
            'name': 'Point Master',
            'description': 'Earn 1000 points',
            'category': 'general',
            'points': 50,
            'icon': 'bi bi-trophy',
            'requirement': json.dumps({'min_points': 1000})
        },
    ]
    
    # Check if achievements already exist
    if Achievement.query.count() > 0:
        logger.info("Achievements already exist in the database. Skipping creation.")
        return
    
    # Create achievements
    for achievement_data in achievements:
        achievement = Achievement(**achievement_data)
        db.session.add(achievement)
    
    db.session.commit()
    logger.info(f"Created {len(achievements)} achievements")

def create_challenges():
    """Create default challenges"""
    # Set dates for challenges
    now = datetime.utcnow()
    tomorrow = now + timedelta(days=1)
    tomorrow_end = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 23, 59, 59)
    next_week = now + timedelta(days=7)
    next_week_end = datetime(next_week.year, next_week.month, next_week.day, 23, 59, 59)
    
    challenges = [
        # Daily challenges
        {
            'title': 'Login Streak',
            'description': 'Login to the system today to maintain your streak',
            'challenge_type': 'daily',
            'points': 5,
            'requirements': json.dumps({'activity_type': 'login', 'count': 1}),
            'start_date': now,
            'end_date': tomorrow_end,
            'is_active': True
        },
        {
            'title': 'Create a Document',
            'description': 'Create at least one new legal document today',
            'challenge_type': 'daily',
            'points': 10,
            'requirements': json.dumps({'activity_type': 'create_document', 'count': 1}),
            'start_date': now,
            'end_date': tomorrow_end,
            'is_active': True
        },
        {
            'title': 'Update a Case',
            'description': 'Update at least one case with new information',
            'challenge_type': 'daily',
            'points': 8,
            'requirements': json.dumps({'activity_type': 'update_case', 'count': 1}),
            'start_date': now,
            'end_date': tomorrow_end,
            'is_active': True
        },
        
        # Weekly challenges
        {
            'title': 'Research Champion',
            'description': 'Conduct at least 3 legal research queries this week',
            'challenge_type': 'weekly',
            'points': 25,
            'requirements': json.dumps({'activity_type': 'research', 'count': 3}),
            'start_date': now,
            'end_date': next_week_end,
            'is_active': True
        },
        {
            'title': 'Document Expert',
            'description': 'Create 5 different legal documents this week',
            'challenge_type': 'weekly',
            'points': 30,
            'requirements': json.dumps({'activity_type': 'create_document', 'count': 5}),
            'start_date': now,
            'end_date': next_week_end,
            'is_active': True
        },
        {
            'title': 'Case Manager',
            'description': 'Create or update at least 3 different cases this week',
            'challenge_type': 'weekly',
            'points': 30,
            'requirements': json.dumps({'activity_types': ['create_case', 'update_case'], 'count': 3}),
            'start_date': now,
            'end_date': next_week_end,
            'is_active': True
        },
        
        # Special challenge
        {
            'title': 'Complete Your Profile',
            'description': 'Update your profile with all required information',
            'challenge_type': 'special',
            'points': 20,
            'requirements': json.dumps({'activity_type': 'complete_profile', 'count': 1}),
            'start_date': now,
            'end_date': now + timedelta(days=30),
            'is_active': True
        },
    ]
    
    # Check if challenges already exist for today
    today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
    existing_challenges = Challenge.query.filter(
        Challenge.challenge_type == 'daily',
        Challenge.start_date >= today_start
    ).count()
    
    if existing_challenges > 0:
        logger.info("Challenges already exist for today. Skipping creation.")
        return
    
    # Create challenges
    for challenge_data in challenges:
        challenge = Challenge(**challenge_data)
        db.session.add(challenge)
    
    db.session.commit()
    logger.info(f"Created {len(challenges)} challenges")

def main():
    """Main function to initialize gamification data"""
    with app.app_context():
        create_achievements()
        create_challenges()
        logger.info("Gamification data initialized successfully")

if __name__ == "__main__":
    main()