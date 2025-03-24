"""
Initialize database with default gamification achievements and challenges.
Run this script after setting up the database to add initial data.
"""

import json
import os
from datetime import datetime, timedelta
from app import app, db
from models import Achievement, Challenge

def create_achievements():
    """Create default achievements"""
    achievements = [
        {
            'name': 'First Login',
            'description': 'Logged in for the first time.',
            'category': 'general',
            'points': 10,
            'icon': 'fas fa-door-open',
            'requirement': json.dumps({'login_count': 1})
        },
        {
            'name': 'Legal Beginner',
            'description': 'Reached level 2.',
            'category': 'general',
            'points': 20,
            'icon': 'fas fa-graduation-cap',
            'requirement': json.dumps({'min_level': 2})
        },
        {
            'name': 'Point Collector',
            'description': 'Earned 500 points.',
            'category': 'general',
            'points': 25,
            'icon': 'fas fa-star',
            'requirement': json.dumps({'min_points': 500})
        },
        {
            'name': 'Case Handler',
            'description': 'Created your first case.',
            'category': 'case',
            'points': 15,
            'icon': 'fas fa-gavel',
            'requirement': json.dumps({'min_cases': 1})
        },
        {
            'name': 'Case Master',
            'description': 'Managed 10 cases.',
            'category': 'case',
            'points': 30,
            'icon': 'case_master.svg',
            'requirement': json.dumps({'min_cases': 10})
        },
        {
            'name': 'Documentalist',
            'description': 'Created your first document.',
            'category': 'document',
            'points': 15,
            'icon': 'fas fa-file-alt',
            'requirement': json.dumps({'min_documents': 1})
        },
        {
            'name': 'Legal Researcher',
            'description': 'Conducted your first research.',
            'category': 'research',
            'points': 15,
            'icon': 'fas fa-search',
            'requirement': json.dumps({'min_research': 1})
        },
        {
            'name': 'Legal Eagle',
            'description': 'Conducted 10 research sessions.',
            'category': 'research',
            'points': 30,
            'icon': 'legal_eagle.svg',
            'requirement': json.dumps({'min_research': 10})
        },
        {
            'name': 'Streak Master',
            'description': 'Maintained a 7-day login streak.',
            'category': 'general',
            'points': 50,
            'icon': 'streak_master.svg',
            'requirement': json.dumps({'min_streak': 7})
        }
    ]
    
    existing_achievements = {a.name: a for a in Achievement.query.all()}
    
    for achievement_data in achievements:
        name = achievement_data['name']
        if name not in existing_achievements:
            achievement = Achievement(**achievement_data)
            db.session.add(achievement)
            print(f"Added achievement: {name}")
        else:
            # Update existing achievement
            for key, value in achievement_data.items():
                setattr(existing_achievements[name], key, value)
            print(f"Updated achievement: {name}")
    
    db.session.commit()

def create_challenges():
    """Create default challenges"""
    now = datetime.utcnow()
    tomorrow = now + timedelta(days=1)
    next_week = now + timedelta(days=7)
    
    challenges = [
        {
            'title': 'Research Champion',
            'description': 'Conduct 3 legal research sessions in a week.',
            'challenge_type': 'weekly',
            'points': 50,
            'requirements': json.dumps({'type': 'research', 'target': 3}),
            'start_date': now,
            'end_date': next_week,
            'is_active': True
        },
        {
            'title': 'Document Master',
            'description': 'Create 2 legal documents in a week.',
            'challenge_type': 'weekly',
            'points': 40,
            'requirements': json.dumps({'type': 'document', 'target': 2}),
            'start_date': now,
            'end_date': next_week,
            'is_active': True
        },
        {
            'title': 'Daily Login',
            'description': 'Log in to the platform today.',
            'challenge_type': 'daily',
            'points': 10,
            'requirements': json.dumps({'type': 'login', 'target': 1}),
            'start_date': now,
            'end_date': tomorrow,
            'is_active': True
        }
    ]
    
    # Clear expired challenges
    expired = Challenge.query.filter(Challenge.end_date < now).all()
    for challenge in expired:
        db.session.delete(challenge)
    
    # Add or update challenges
    existing_challenges = {c.title: c for c in Challenge.query.filter(Challenge.end_date >= now).all()}
    
    for challenge_data in challenges:
        title = challenge_data['title']
        if title not in existing_challenges:
            challenge = Challenge(**challenge_data)
            db.session.add(challenge)
            print(f"Added challenge: {title}")
        else:
            # Update existing challenge if needed
            existing = existing_challenges[title]
            if existing.challenge_type == 'daily' and existing.end_date < tomorrow:
                # Update daily challenge
                existing.start_date = now
                existing.end_date = tomorrow
                print(f"Updated daily challenge: {title}")
    
    db.session.commit()

def main():
    """Main function to initialize gamification data"""
    with app.app_context():
        create_achievements()
        create_challenges()
        print("Gamification data initialized successfully!")

if __name__ == "__main__":
    main()